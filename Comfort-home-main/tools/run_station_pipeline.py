"""
tools/run_station_pipeline.py

Executes the complete 5-stage ClimateAdapt-Comfort pipeline for a single weather station:
1. Physics Simulations: 1,000 Latin Hypercube designs (seed=42) x 2 modes in EnergyPlus.
   - Saves compressed hourly free-running parquet.
   - Retains only eplusout.err and shelter.idf in run folders; deletes intermediate simulation artifacts.
2. Dual Comfort Judge Coupling: Exact ASHRAE 55 Adaptive 90% and ML Champion (Ablation_A3).
   - Pruning: Deletes hourly free-running parquet immediately after objectives.parquet is written.
3. Surrogate Model Training: Optuna 5-fold CV (40 trials) XGBoost regressors for 5 targets in parallel.
4. NSGA-II Multi-Objective Optimization: 100 pop x 200 gen with confidence flagging.
5. Direct EnergyPlus Physical Verification: 10 representative Pareto designs (20 runs).
   - Post-verification Archiving: Zips sim_* and ver_* folders into archive_<station>.zip, then removes folders.
6. Checkpointing & Resumption: Automatically skips stations whose outputs and archives already exist.
7. Profiling: Tracks per-stage wall-clock time and peak RAM.

Strictly imports and calls existing src/ modules without altering algorithms or settings.
"""

import os
import sys
import time
import json
import zipfile
import shutil
import psutil
import joblib
import optuna
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

# Ensure project root in sys.path
REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.sampler import sample_designs
from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv
from src.optimize.coupling import (
    calculate_daily_mean_series,
    compute_running_mean_outdoor_temperature_db2,
    compute_clo_schedule_a004,
    evaluate_adaptive_90_comfort,
    evaluate_ml_champion_comfort,
    load_champion_model
)
from src.models.train_surrogates import (
    prepare_features,
    compute_top_k_overlap,
    tune_surrogate_xgboost,
    TARGETS
)
from src.optimize.nsga2 import (
    ShelterOptimizationProblem,
    select_10_verification_designs,
    MASS_CLASSES
)

optuna.logging.set_verbosity(optuna.logging.WARNING)

def _sim_single_worker(task):
    """
    Renders IDF, runs simulation, parses CSV, cleans bulky outputs, retaining eplusout.err and shelter.idf.
    """
    station_name = task['station_name']
    epw_path = task['epw_path']
    d_id = task['design_id']
    d_params = task['params']
    mode = task['mode']
    run_dir = task['run_dir']
    
    os.makedirs(run_dir, exist_ok=True)
    idf_path = os.path.join(run_dir, "shelter.idf")
    render_shelter_idf(d_params, idf_path, mode=mode)
    
    res = run_single_simulation(idf_path, epw_path, run_dir)
    
    hourly_dict = None
    summary_dict = None
    
    if res["status"] == "SUCCESS":
        csv_path = os.path.join(run_dir, "eplusout.csv")
        if os.path.exists(csv_path):
            try:
                hdf, sm = parse_simulation_csv(csv_path)
                summary_dict = sm
                if mode == "free_running":
                    hourly_dict = {
                        'hour': np.arange(8760, dtype=np.int32),
                        'ta': hdf['ta'].values.astype(np.float32),
                        'tr': hdf['tr'].values.astype(np.float32),
                        'rh': hdf['rh'].values.astype(np.float32),
                        't_out': hdf['t_out'].values.astype(np.float32)
                    }
            except Exception as e:
                res["status"] = "PARSE_ERROR"
                res["error_msg"] = str(e)
                
    # Clean run folder: retain only eplusout.err and shelter.idf
    for f in os.listdir(run_dir):
        if f not in ["eplusout.err", "shelter.idf"]:
            fp = os.path.join(run_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                elif os.path.isdir(fp):
                    shutil.rmtree(fp, ignore_errors=True)
            except Exception:
                pass
                
    return d_id, mode, res["status"], summary_dict, hourly_dict

def _train_single_target_surrogate(args):
    """
    Trains and tunes a single XGBoost surrogate model with Optuna 5-fold CV (40 trials, seed=42).
    """
    target, X_tr, y_tr, X_te, y_te, feature_names, station_name, out_model_dir = args
    best_model, best_params, cv_r2 = tune_surrogate_xgboost(X_tr, y_tr, n_trials=40, seed=42)
    
    y_pred = best_model.predict(X_te)
    r2 = float(r2_score(y_te, y_pred))
    mae = float(mean_absolute_error(y_te, y_pred))
    y_range = float(y_tr.max() - y_tr.min())
    nmae = float((mae / y_range * 100.0) if y_range > 0 else 0.0)
    top10_overlap = float(compute_top_k_overlap(y_te, y_pred, k_pct=0.10))
    s2_status = "PASS" if r2 >= 0.95 else "FAIL"
    
    os.makedirs(out_model_dir, exist_ok=True)
    model_path = os.path.join(out_model_dir, f"surrogate_{station_name}_{target}.joblib")
    artifact = {
        'city': station_name,
        'target': target,
        'model': best_model,
        'best_params': best_params,
        'feature_names': feature_names,
        'metrics': {
            'r2': r2,
            'mae': mae,
            'nmae_pct': nmae,
            'top10_overlap_pct': top10_overlap,
            's2_status': s2_status,
            'cv_r2': float(cv_r2)
        }
    }
    joblib.dump(artifact, model_path)
    
    return {
        'target': target,
        'r2': r2,
        'mae': mae,
        'nmae_pct': nmae,
        'top10_overlap_pct': top10_overlap,
        's2_status': s2_status,
        'cv_r2': float(cv_r2),
        'model_path': model_path,
        'model': best_model
    }

def _zip_directory(source_dirs, target_zip_path):
    """Zips one or more directories into a single archive."""
    with zipfile.ZipFile(target_zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for s_dir in source_dirs:
            if os.path.exists(s_dir):
                base_name = os.path.basename(s_dir)
                for root, dirs, files in os.walk(s_dir):
                    for f in files:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, os.path.dirname(s_dir))
                        zf.write(full_p, rel_p)

def run_pipeline_for_station(
    station_name: str,
    epw_path: str,
    output_dir: str = "data/processed/scaling",
    models_dir: str = "models/scaling",
    max_sim_workers: int = 8,
    force_rerun: bool = False
):
    print("\n" + "="*80)
    print(f"RUNNING STATION PIPELINE: {station_name}")
    print(f"EPW: {epw_path}")
    print("="*80)
    
    if not os.path.exists(epw_path):
        raise FileNotFoundError(f"EPW file not found: {epw_path}")
        
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    # Check if station is already completed (Resume support)
    obj_parquet_path = os.path.join(output_dir, f"objectives_{station_name}.parquet")
    pareto_parquet_path = os.path.join(output_dir, f"pareto_{station_name}.parquet")
    ver_csv_path = os.path.join(output_dir, f"verification_{station_name}.csv")
    archive_zip_path = os.path.join(output_dir, f"archive_{station_name}.zip")
    
    all_models_exist = all(
        os.path.exists(os.path.join(models_dir, f"surrogate_{station_name}_{tgt}.joblib"))
        for tgt in TARGETS
    )
    
    if (not force_rerun) and os.path.exists(obj_parquet_path) and os.path.exists(pareto_parquet_path) and os.path.exists(ver_csv_path) and (os.path.exists(archive_zip_path) or os.path.exists(os.path.join(output_dir, f"sim_{station_name}"))) and all_models_exist:
        print(f"Station {station_name} is already complete. Resuming/skipping.")
        df_obj = pd.read_parquet(obj_parquet_path)
        df_pareto = pd.read_parquet(pareto_parquet_path)
        df_ver = pd.read_csv(ver_csv_path)
        metrics = []
        for tgt in TARGETS:
            art = joblib.load(os.path.join(models_dir, f"surrogate_{station_name}_{tgt}.joblib"))
            metrics.append(art['metrics'])
        return {
            'station': station_name,
            'status': 'SKIPPED_ALREADY_DONE',
            'objectives_df': df_obj,
            'pareto_df': df_pareto,
            'verification_df': df_ver,
            'surrogate_metrics_df': pd.DataFrame(metrics)
        }
        
    timings = {}
    memory_profile = {}
    
    # -------------------------------------------------------------------------
    # STAGE 1: SIMULATIONS (1,000 DESIGNS x 2 MODES)
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 1] Running 1,000 designs x 2 modes = 2,000 EnergyPlus simulations...")
    t_sim_start = time.time()
    mem_sim_start = psutil.virtual_memory().used / (1024**3)
    
    df_samples = sample_designs(n_samples=1000, seed=42)
    base_sim_dir = os.path.join(output_dir, f"sim_{station_name}")
    os.makedirs(base_sim_dir, exist_ok=True)
    
    sim_tasks = []
    for _, d_row in df_samples.iterrows():
        did = d_row["design_id"]
        d_dict = d_row.to_dict()
        dir_fr = os.path.join(base_sim_dir, f"{did}_fr")
        dir_il = os.path.join(base_sim_dir, f"{did}_il")
        
        sim_tasks.append({
            'station_name': station_name,
            'epw_path': epw_path,
            'design_id': did,
            'params': d_dict,
            'mode': 'free_running',
            'run_dir': dir_fr
        })
        sim_tasks.append({
            'station_name': station_name,
            'epw_path': epw_path,
            'design_id': did,
            'params': d_dict,
            'mode': 'ideal_loads',
            'run_dir': dir_il
        })
        
    sim_summaries = {}
    hourly_records = []
    
    with ProcessPoolExecutor(max_workers=max_sim_workers) as executor:
        futures = [executor.submit(_sim_single_worker, t) for t in sim_tasks]
        for f in as_completed(futures):
            did, mode, status, summary, hourly = f.result()
            if did not in sim_summaries:
                sim_summaries[did] = {}
            sim_summaries[did][mode] = (status, summary)
            if hourly is not None:
                df_h = pd.DataFrame(hourly)
                df_h['design_id'] = did
                hourly_records.append(df_h)
                
    df_all_hourly = pd.concat(hourly_records, ignore_index=True)
    hourly_parquet_path = os.path.join(output_dir, f"hourly_fr_{station_name}.parquet")
    df_all_hourly.to_parquet(hourly_parquet_path, index=False)
    
    t_sim_elapsed = time.time() - t_sim_start
    mem_sim_end = psutil.virtual_memory().used / (1024**3)
    timings["simulations"] = round(t_sim_elapsed, 2)
    memory_profile["simulations_ram_gb"] = round(mem_sim_end, 2)
    print(f"Stage 1 Complete in {t_sim_elapsed:.2f} s ({t_sim_elapsed/60:.2f} min) | RAM: {mem_sim_end:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 2: DUAL COMFORT JUDGE COUPLING
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 2] Evaluating Dual Comfort Judges (Adaptive 90% + ML Champion)...")
    t_cpl_start = time.time()
    
    champ_model = load_champion_model("models/champion_comfort_model.joblib")
    grouped_hourly = df_all_hourly.groupby('design_id')
    
    obj_records = []
    df_samples_idx = df_samples.set_index('design_id')
    
    for did, group in grouped_hourly:
        if did not in sim_summaries:
            continue
        fr_status, fr_sm = sim_summaries[did].get('free_running', (None, None))
        il_status, il_sm = sim_summaries[did].get('ideal_loads', (None, None))
        
        if fr_status != 'SUCCESS' or il_status != 'SUCCESS' or il_sm is None:
            continue
            
        group_sorted = group.sort_values('hour')
        ta = group_sorted['ta'].values
        tr = group_sorted['tr'].values
        rh = group_sorted['rh'].values
        tout = group_sorted['t_out'].values
        
        daily_tout = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)
        
        adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
        ml_res = evaluate_ml_champion_comfort(
            model=champ_model,
            ta=ta,
            tr=tr,
            rh=rh,
            t_outdoor_hourly=t_rm_hourly,
            clo_hourly=clo_hourly,
            met=1.1,
            vel=0.15
        )
        
        d_params = df_samples_idx.loc[did].to_dict()
        o2_val = float(il_sm['o2_energy_kwh_per_m2'])
        
        obj_records.append({
            'city': station_name,
            'design_id': did,
            'roof_insulation_thickness': d_params['roof_insulation_thickness'],
            'wall_insulation_thickness': d_params['wall_insulation_thickness'],
            'roof_solar_absorptance': d_params['roof_solar_absorptance'],
            'wwr': d_params['wwr'],
            'orientation': d_params['orientation'],
            'shading_depth': d_params['shading_depth'],
            'ventilation_ach': d_params['ventilation_ach'],
            'wall_mass_class': d_params['wall_mass_class'],
            'O1_ml': ml_res['O1_ml'],
            'warm_ml': ml_res['warm_ml'],
            'cool_ml': ml_res['cool_ml'],
            'O1_adapt': adapt_res['O1_adapt'],
            'hot_adapt': adapt_res['hot_adapt'],
            'cold_adapt': adapt_res['cold_adapt'],
            'invalid_share_adapt': adapt_res['invalid_share_adapt'],
            'O2': o2_val
        })
        
    df_objectives = pd.DataFrame(obj_records)
    df_objectives.to_parquet(obj_parquet_path, index=False)
    
    # PRUNING RULE: delete transient hourly parquet after objectives are written
    if os.path.exists(hourly_parquet_path):
        try:
            os.remove(hourly_parquet_path)
            print(f"  [PRUNING] Cleaned transient {hourly_parquet_path} to conserve disk.")
        except Exception:
            pass
            
    # Clear large in-memory objects
    del df_all_hourly
    del hourly_records
    
    t_cpl_elapsed = time.time() - t_cpl_start
    mem_cpl_end = psutil.virtual_memory().used / (1024**3)
    timings["coupling"] = round(t_cpl_elapsed, 2)
    memory_profile["coupling_ram_gb"] = round(mem_cpl_end, 2)
    print(f"Stage 2 Complete in {t_cpl_elapsed:.2f} s ({len(df_objectives)} valid paired designs). Saved {obj_parquet_path} | RAM: {mem_cpl_end:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 3: SURROGATE TRAINING (PARALLEL OPTUNA 5-FOLD CV, 40 TRIALS)
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 3] Training 5 XGBoost Surrogates in parallel (Optuna 40 trials, 5-fold CV)...")
    t_surr_start = time.time()
    
    X = prepare_features(df_objectives)
    feature_names = list(X.columns)
    
    surr_tasks = []
    for tgt in TARGETS:
        y = df_objectives[tgt].values
        valid_mask = ~np.isnan(y)
        X_v = X[valid_mask].reset_index(drop=True)
        y_v = y[valid_mask]
        
        X_tr, X_te, y_tr, y_te = train_test_split(X_v, y_v, test_size=0.20, random_state=42)
        surr_tasks.append((tgt, X_tr, y_tr, X_te, y_te, feature_names, station_name, models_dir))
        
    surrogate_models = {}
    surrogate_metrics = []
    with ProcessPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_train_single_target_surrogate, t) for t in surr_tasks]
        for f in as_completed(futures):
            res_dict = f.result()
            tgt = res_dict['target']
            surrogate_models[tgt] = res_dict['model']
            surrogate_metrics.append({
                'city': station_name,
                'target': tgt,
                'r2': res_dict['r2'],
                'mae': res_dict['mae'],
                'nmae_pct': res_dict['nmae_pct'],
                'top10_overlap_pct': res_dict['top10_overlap_pct'],
                's2_status': res_dict['s2_status'],
                'cv_r2': res_dict['cv_r2']
            })
            print(f"  - Target: {tgt:10s} | Test R2: {res_dict['r2']:.4f} | MAE: {res_dict['mae']:.3f} | S2: {res_dict['s2_status']} (CV R2: {res_dict['cv_r2']:.4f})")
            
    df_surr_metrics = pd.DataFrame(surrogate_metrics)
    t_surr_elapsed = time.time() - t_surr_start
    mem_surr_end = psutil.virtual_memory().used / (1024**3)
    timings["surrogates"] = round(t_surr_elapsed, 2)
    memory_profile["surrogates_ram_gb"] = round(mem_surr_end, 2)
    print(f"Stage 3 Complete in {t_surr_elapsed:.2f} s | RAM: {mem_surr_end:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 4: MULTI-OBJECTIVE OPTIMIZATION (NSGA-II)
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 4] Running NSGA-II Multi-Objective Optimization (100 pop x 200 gen)...")
    t_opt_start = time.time()
    
    problem = ShelterOptimizationProblem(station_name, surrogate_models)
    algorithm = NSGA2(
        pop_size=100,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.2, eta=20),
        eliminate_duplicates=True
    )
    res_opt = minimize(problem, algorithm, ('n_gen', 200), seed=42, verbose=False)
    
    invalid_share_mean = df_objectives['invalid_share_adapt'].mean()
    adapt_flag = bool(invalid_share_mean > 20.0)
    
    pareto_rows = []
    for i in range(len(res_opt.X)):
        x = res_opt.X[i]
        f = res_opt.F[i]
        mass_idx = int(np.floor(x[7]))
        mass_idx = min(2, max(0, mass_idx))
        mass_str = MASS_CLASSES[mass_idx]
        
        pareto_rows.append({
            'city': station_name,
            'pareto_id': f"P_{station_name}_{i:03d}",
            'roof_insulation_thickness': float(x[0]),
            'wall_insulation_thickness': float(x[1]),
            'wall_mass_class': mass_str,
            'roof_solar_absorptance': float(x[2]),
            'wwr': float(x[3]),
            'orientation': float(x[4]),
            'shading_depth': float(x[5]),
            'ventilation_ach': float(x[6]),
            'pred_O1_ml': float(f[0]),
            'pred_O1_adapt': float(f[1]),
            'pred_O2': float(f[2]),
            'ml_confidence_flag': "STANDARD",
            'adaptive_confidence_flag': "LOW_CONFIDENCE" if adapt_flag else "STANDARD"
        })
        
    df_pareto = pd.DataFrame(pareto_rows)
    df_pareto.to_parquet(pareto_parquet_path, index=False)
    
    t_opt_elapsed = time.time() - t_opt_start
    mem_opt_end = psutil.virtual_memory().used / (1024**3)
    timings["optimization"] = round(t_opt_elapsed, 2)
    memory_profile["optimization_ram_gb"] = round(mem_opt_end, 2)
    print(f"Stage 4 Complete in {t_opt_elapsed:.2f} s ({len(df_pareto)} Pareto designs). Saved {pareto_parquet_path} | RAM: {mem_opt_end:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 5: DIRECT ENERGYPLUS VERIFICATION (10 DESIGNS X 2 MODES)
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 5] Direct EnergyPlus Verification of 10 Pareto designs...")
    t_ver_start = time.time()
    
    df_selected = select_10_verification_designs(df_pareto)
    ver_base_dir = os.path.join(output_dir, f"ver_{station_name}")
    os.makedirs(ver_base_dir, exist_ok=True)
    
    ver_tasks = []
    for _, p_row in df_selected.iterrows():
        p_id = p_row['pareto_id']
        p_dict = {
            'roof_insulation_thickness': float(p_row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(p_row['wall_insulation_thickness']),
            'wall_mass_class': str(p_row['wall_mass_class']),
            'roof_solar_absorptance': float(p_row['roof_solar_absorptance']),
            'wwr': float(p_row['wwr']),
            'orientation': float(p_row['orientation']),
            'shading_depth': float(p_row['shading_depth']),
            'ventilation_ach': float(p_row['ventilation_ach'])
        }
        
        dir_fr = os.path.join(ver_base_dir, f"{p_id}_fr")
        dir_il = os.path.join(ver_base_dir, f"{p_id}_il")
        ver_tasks.append({
            'station_name': station_name,
            'epw_path': epw_path,
            'design_id': p_id,
            'params': p_dict,
            'mode': 'free_running',
            'run_dir': dir_fr
        })
        ver_tasks.append({
            'station_name': station_name,
            'epw_path': epw_path,
            'design_id': p_id,
            'params': p_dict,
            'mode': 'ideal_loads',
            'run_dir': dir_il
        })
        
    ver_summaries = {}
    ver_hourly = []
    with ProcessPoolExecutor(max_workers=max_sim_workers) as executor:
        futures = [executor.submit(_sim_single_worker, t) for t in ver_tasks]
        for f in as_completed(futures):
            pid, mode, status, summary, hourly = f.result()
            if pid not in ver_summaries:
                ver_summaries[pid] = {}
            ver_summaries[pid][mode] = (status, summary)
            if hourly is not None:
                df_vh = pd.DataFrame(hourly)
                df_vh['design_id'] = pid
                ver_hourly.append(df_vh)
                
    df_ver_hourly_all = pd.concat(ver_hourly, ignore_index=True)
    grouped_vh = df_ver_hourly_all.groupby('design_id')
    
    ver_results = []
    for pid, group in grouped_vh:
        fr_status, fr_sm = ver_summaries[pid].get('free_running', (None, None))
        il_status, il_sm = ver_summaries[pid].get('ideal_loads', (None, None))
        if fr_status != 'SUCCESS' or il_status != 'SUCCESS' or il_sm is None:
            continue
            
        group_sorted = group.sort_values('hour')
        ta = group_sorted['ta'].values
        tr = group_sorted['tr'].values
        rh = group_sorted['rh'].values
        tout = group_sorted['t_out'].values
        
        daily_tout = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)
        
        adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
        ml_res = evaluate_ml_champion_comfort(
            model=champ_model,
            ta=ta,
            tr=tr,
            rh=rh,
            t_outdoor_hourly=t_rm_hourly,
            clo_hourly=clo_hourly,
            met=1.1,
            vel=0.15
        )
        
        p_row_match = df_selected[df_selected['pareto_id'] == pid].iloc[0]
        act_o1_ml = ml_res['O1_ml']
        act_o1_ad = adapt_res['O1_adapt']
        act_o2 = float(il_sm['o2_energy_kwh_per_m2'])
        
        pred_o1_ml = float(p_row_match['pred_O1_ml'])
        pred_o1_ad = float(p_row_match['pred_O1_adapt'])
        pred_o2 = float(p_row_match['pred_O2'])
        
        ver_results.append({
            'station': station_name,
            'pareto_id': pid,
            'pred_O1_ml': pred_o1_ml,
            'act_O1_ml': act_o1_ml,
            'err_O1_ml': act_o1_ml - pred_o1_ml,
            'pred_O1_adapt': pred_o1_ad,
            'act_O1_adapt': act_o1_ad,
            'err_O1_adapt': act_o1_ad - pred_o1_ad,
            'pred_O2': pred_o2,
            'act_O2': act_o2,
            'err_O2': act_o2 - pred_o2
        })
        
    df_ver_res = pd.DataFrame(ver_results)
    df_ver_res.to_csv(ver_csv_path, index=False)
    
    t_ver_elapsed = time.time() - t_ver_start
    mem_ver_end = psutil.virtual_memory().used / (1024**3)
    timings["verification"] = round(t_ver_elapsed, 2)
    memory_profile["verification_ram_gb"] = round(mem_ver_end, 2)
    print(f"Stage 5 Complete in {t_ver_elapsed:.2f} s ({len(df_ver_res)} verified designs). Saved {ver_csv_path} | RAM: {mem_ver_end:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 6: DISK COMPRESSION & CLEANUP (ZIP sim_* & ver_*)
    # -------------------------------------------------------------------------
    t_zip_start = time.time()
    print(f"\n[STAGE 6] Archiving run folders into {archive_zip_path} and cleaning directory trees...")
    _zip_directory([base_sim_dir, ver_base_dir], archive_zip_path)
    shutil.rmtree(base_sim_dir, ignore_errors=True)
    shutil.rmtree(ver_base_dir, ignore_errors=True)
    t_zip_elapsed = time.time() - t_zip_start
    timings["archiving"] = round(t_zip_elapsed, 2)
    print(f"Stage 6 Complete in {t_zip_elapsed:.2f} s. Cleaned sim and ver folders.")
    
    timings["total"] = round(sum(timings.values()), 2)
    
    return {
        'station': station_name,
        'timings': timings,
        'memory_profile': memory_profile,
        'objectives_df': df_objectives,
        'surrogate_metrics_df': df_surr_metrics,
        'pareto_df': df_pareto,
        'verification_df': df_ver_res
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/run_station_pipeline.py <station_name> <epw_path> [output_dir]")
        sys.exit(1)
        
    st_name = sys.argv[1]
    epw_file = sys.argv[2]
    out_d = sys.argv[3] if len(sys.argv) > 3 else "data/processed/scaling"
    
    run_pipeline_for_station(st_name, epw_file, output_dir=out_d)
