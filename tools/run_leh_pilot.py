"""
tools/run_leh_pilot.py

Full Pilot Simulation, Dual Comfort Coupling, Surrogate Training, NSGA-II Optimization,
and Physical EnergyPlus Verification for LEH under Decision D-035 physics.

Station: Leh (Cold Climate Zone)
EPW: data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw
Ground Temps: Read from EPW header 0.5 m depth (D-035).
Settings: 1,000 LHS designs, 2 modes (2,000 runs), 6 workers, disk guard >= 5.0 GB.
Outputs:
- data/processed/pilot_leh/
- models/pilot_leh/
- reports/evidence/leh_pilot_execution_output.txt
"""

import os
import sys
import time
import shutil
import psutil
import joblib
import optuna
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from scipy.stats import qmc
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

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
    select_10_verification_designs,
    MASS_CLASSES
)

optuna.logging.set_verbosity(optuna.logging.WARNING)

DISK_GUARD_GB = 5.0
MAX_WORKERS = 6
STATION_NAME = "Leh"
EPW_PATH = "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
OUTPUT_DIR = "data/processed/pilot_leh"
MODELS_DIR = "models/pilot_leh"
EVIDENCE_TXT = "reports/evidence/leh_pilot_execution_output.txt"

def check_disk_guard(stage_name=""):
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    if free_gb < DISK_GUARD_GB:
        raise RuntimeError(
            f"DISK GUARD TRIGGERED during {stage_name}: Free disk space is {free_gb:.2f} GB, "
            f"which is below the mandatory {DISK_GUARD_GB:.1f} GB safety threshold. Aborting execution."
        )
    return free_gb

def get_peak_ram_gb():
    return psutil.virtual_memory().used / (1024**3)

def _sim_single_worker(task):
    epw_path = task['epw_path']
    d_id = task['design_id']
    d_params = task['params']
    mode = task['mode']
    run_dir = task['run_dir']
    
    os.makedirs(run_dir, exist_ok=True)
    idf_path = os.path.join(run_dir, "shelter.idf")
    render_shelter_idf(d_params, idf_path, mode=mode, epw_path=epw_path)
    
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
                        'ta': hdf['ta'].values.astype(np.float32),
                        'tr': hdf['tr'].values.astype(np.float32),
                        'rh': hdf['rh'].values.astype(np.float32),
                        't_out': hdf['t_out'].values.astype(np.float32)
                    }
            except Exception as e:
                res["status"] = "PARSE_ERROR"
                res["error_msg"] = str(e)
                
    # Retain only essential outputs to conserve disk space
    if os.path.exists(run_dir):
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
    target, X_tr, y_tr, X_te, y_te, feature_names, station_name, out_model_dir, seed = args
    best_model, best_params, cv_r2 = tune_surrogate_xgboost(X_tr, y_tr, n_trials=40, seed=seed)
    
    preds_te = best_model.predict(X_te)
    r2 = float(r2_score(y_te, preds_te))
    mae = float(mean_absolute_error(y_te, preds_te))
    rmse = float(np.sqrt(mean_squared_error(y_te, preds_te)))
    y_range = float(np.max(y_te) - np.min(y_te))
    nmae_pct = (mae / y_range * 100.0) if y_range > 0 else 0.0
    
    top10_overlap = float(compute_top_k_overlap(y_te, preds_te, k_pct=0.10))
    s2_gate = "PASS" if (r2 >= 0.90 and top10_overlap >= 70.0) else "FAIL"
    
    model_art = {
        'model': best_model,
        'best_params': best_params,
        'feature_names': feature_names,
        'target': target,
        'metrics': {
            'cv_r2': float(cv_r2),
            'test_r2': r2,
            'test_mae': mae,
            'test_rmse': rmse,
            'nmae_pct': nmae_pct,
            'top10_overlap_pct': top10_overlap,
            's2_gate': s2_gate
        }
    }
    joblib.dump(model_art, os.path.join(out_model_dir, f"surrogate_{station_name}_{target}.joblib"))
    return target, {
        'cv_r2': float(cv_r2),
        'r2': r2,
        'mae': mae,
        'rmse': rmse,
        'nmae_pct': nmae_pct,
        'top10_overlap_pct': top10_overlap,
        's2_gate': s2_gate
    }

class ClampedShelterOptimizationProblem(ElementwiseProblem):
    def __init__(self, city_name, surrogate_models):
        self.city_name = city_name
        self.surrogates = surrogate_models
        xl = np.array([0.0,  0.0,  0.30, 0.05,   0.0, 0.3,  1.0, 0.0])
        xu = np.array([0.15, 0.15, 0.90, 0.40, 359.0, 1.0, 15.0, 2.999])
        super().__init__(n_var=8, n_obj=3, n_ieq_constr=0, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        mass_idx = int(np.floor(x[7]))
        mass_idx = min(2, max(0, mass_idx))
        roof_ins = round(float(x[0]) / 0.025) * 0.025
        wall_ins = round(float(x[1]) / 0.025) * 0.025
        shading = max(0.3, float(x[5]))

        feat_dict = {
            'roof_insulation_thickness': [roof_ins],
            'wall_insulation_thickness': [wall_ins],
            'roof_solar_absorptance': [float(x[2])],
            'wwr': [float(x[3])],
            'orientation': [float(x[4])],
            'shading_depth': [shading],
            'ventilation_ach': [float(x[6])],
            'wall_mass_heavy': [1.0 if mass_idx == 0 else 0.0],
            'wall_mass_light': [1.0 if mass_idx == 1 else 0.0],
            'wall_mass_medium': [1.0 if mass_idx == 2 else 0.0]
        }
        df_feat = pd.DataFrame(feat_dict)
        pred_o1_ml = float(np.clip(self.surrogates['O1_ml'].predict(df_feat)[0], 0.0, 100.0))
        pred_o1_adapt = float(np.clip(self.surrogates['O1_adapt'].predict(df_feat)[0], 0.0, 100.0))
        pred_o2 = float(max(0.0, self.surrogates['O2'].predict(df_feat)[0]))
        out["F"] = [pred_o1_ml, pred_o1_adapt, pred_o2]

def sample_designs(n_samples=1000, seed=42):
    """Generates Latin Hypercube samples enforcing 25mm insulation increments and >= 0.3m overhang."""
    sampler = qmc.LatinHypercube(d=8, seed=seed)
    raw = sampler.random(n=n_samples)
    
    designs = []
    for i in range(n_samples):
        r = raw[i]
        roof_ins_raw = r[0] * 0.150
        roof_ins = round(roof_ins_raw / 0.025) * 0.025
        
        wall_ins_raw = r[1] * 0.150
        wall_ins = round(wall_ins_raw / 0.025) * 0.025
        
        wall_mass_idx = int(np.floor(r[2] * 3.0))
        wall_mass_idx = min(2, max(0, wall_mass_idx))
        wall_mass = MASS_CLASSES[wall_mass_idx]
        
        roof_abs = 0.30 + r[3] * (0.90 - 0.30)
        wwr = 0.05 + r[4] * (0.40 - 0.05)
        orientation = r[5] * 359.0
        shading_depth = 0.30 + r[6] * (1.00 - 0.30)
        vent_ach = 1.0 + r[7] * (15.0 - 1.0)
        
        designs.append({
            'design_id': f"P_{STATION_NAME}_{i:03d}",
            'roof_insulation_thickness': round(roof_ins, 3),
            'wall_insulation_thickness': round(wall_ins, 3),
            'wall_mass_class': wall_mass,
            'roof_solar_absorptance': round(roof_abs, 4),
            'wwr': round(wwr, 4),
            'orientation': round(orientation, 1),
            'shading_depth': round(shading_depth, 3),
            'ventilation_ach': round(vent_ach, 2)
        })
    return pd.DataFrame(designs)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(EVIDENCE_TXT), exist_ok=True)
    
    execution_lines = []
    def log(msg=""):
        print(msg)
        execution_lines.append(msg)
        
    log("="*80)
    log(f"PILOT EXECUTION FOR {STATION_NAME.upper()} UNDER DECISION D-035")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"EPW Weather File: {EPW_PATH}")
    log(f"Max Worker Processes: {MAX_WORKERS}")
    log(f"Disk Guard Threshold: >= {DISK_GUARD_GB:.1f} GB Free")
    log("="*80)
    
    initial_disk = check_disk_guard("Pilot Initialization")
    initial_ram = get_peak_ram_gb()
    log(f"Initial System Resources: Peak RAM = {initial_ram:.2f} GB | Free Disk = {initial_disk:.2f} GB")
    
    stage_metrics = []
    
    champ_model = load_champion_model()
    log("Loaded ML Champion Comfort Model.")
    
    obj_parquet_path = os.path.join(OUTPUT_DIR, f"objectives_{STATION_NAME}.parquet")
    if os.path.exists(obj_parquet_path):
        log(f"\n[STAGE 1 & 2 RESUME] Found existing verified simulation dataset: {obj_parquet_path}")
        df_objectives = pd.read_parquet(obj_parquet_path)
        log(f"Loaded {len(df_objectives)} valid paired design records.")
    else:
        # STAGE 1: BATCH SIMULATIONS (1,000 DESIGNS x 2 MODES = 2,000 RUNS)
        log("\n" + "-"*80)
        log("[STAGE 1] ENERGYPLUS BATCH SIMULATIONS (1,000 LHS DESIGNS x 2 MODES = 2,000 RUNS)")
        log("-"*80)
        check_disk_guard("Stage 1 Pre-Check")
        t1_start = time.time()
        
        df_samples = sample_designs(n_samples=1000, seed=42)
        log(f"Generated {len(df_samples):,} Latin Hypercube designs with seed 42.")
        
        base_sim_dir = os.path.join(OUTPUT_DIR, f"sim_{STATION_NAME}")
        os.makedirs(base_sim_dir, exist_ok=True)
        
        sim_tasks = []
        for _, d_row in df_samples.iterrows():
            did = d_row["design_id"]
            d_dict = d_row.to_dict()
            dir_fr = os.path.join(base_sim_dir, f"{did}_fr")
            dir_il = os.path.join(base_sim_dir, f"{did}_il")
            sim_tasks.append({
                'epw_path': EPW_PATH,
                'design_id': did,
                'params': d_dict,
                'mode': 'free_running',
                'run_dir': dir_fr
            })
            sim_tasks.append({
                'epw_path': EPW_PATH,
                'design_id': did,
                'params': d_dict,
                'mode': 'ideal_loads',
                'run_dir': dir_il
            })
            
        log(f"Dispatching {len(sim_tasks)} EnergyPlus simulation tasks across {MAX_WORKERS} workers...")
        
        sim_results = {}
        success_count = 0
        fail_count = 0
        
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(_sim_single_worker, t) for t in sim_tasks]
            for f in as_completed(futures):
                did, mode, status, sm, h_dict = f.result()
                if did not in sim_results:
                    sim_results[did] = {}
                sim_results[did][mode] = (status, sm, h_dict)
                
                if status == "SUCCESS":
                    success_count += 1
                else:
                    fail_count += 1
                    
        t1_elapsed = time.time() - t1_start
        ram1_peak = get_peak_ram_gb()
        free_d1 = check_disk_guard("Stage 1 Post-Check")
        
        log(f"Stage 1 Complete in {t1_elapsed:.2f} s ({t1_elapsed/60:.2f} min).")
        log(f"Simulation Runs: {success_count} Succeeded, {fail_count} Failed (Success Rate: {success_count/len(sim_tasks)*100:.2f}%).")
        log(f"Peak RAM: {ram1_peak:.2f} GB | Free Disk: {free_d1:.2f} GB")
        
        stage_metrics.append({
            'stage': 'Stage 1: Batch EnergyPlus Simulations',
            'wall_time_sec': round(t1_elapsed, 2),
            'wall_time_min': round(t1_elapsed / 60.0, 2),
            'peak_ram_gb': round(ram1_peak, 2),
            'free_disk_gb': round(free_d1, 2),
            'total_runs': len(sim_tasks),
            'success_rate_pct': round(success_count / len(sim_tasks) * 100.0, 2)
        })
        
        # STAGE 2: DUAL COMFORT JUDGE COUPLING
        log("\n" + "-"*80)
        log("[STAGE 2] DUAL COMFORT JUDGE COUPLING & HOURLY AGGREGATION")
        log("-"*80)
        check_disk_guard("Stage 2 Pre-Check")
        t2_start = time.time()
        
        champ_model = load_champion_model()
        log("Loaded ML Champion Comfort Model.")
        
        df_samples_idx = df_samples.set_index("design_id")
        obj_records = []
        
        for did, row in df_samples.iterrows():
            d_name = row['design_id']
            if d_name not in sim_results:
                continue
            fr_res = sim_results[d_name].get('free_running')
            il_res = sim_results[d_name].get('ideal_loads')
            if not fr_res or not il_res:
                continue
                
            fr_stat, _, fr_h = fr_res
            il_stat, il_sm, _ = il_res
            if fr_stat != 'SUCCESS' or il_stat != 'SUCCESS' or fr_h is None or il_sm is None:
                continue
                
            ta = fr_h['ta']
            tr = fr_h['tr']
            rh = fr_h['rh']
            tout = fr_h['t_out']
            
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
            
            d_params = df_samples_idx.loc[d_name].to_dict()
            o2_val = float(il_sm["o2_energy_kwh_per_m2"])
            
            obj_records.append({
                'city': STATION_NAME,
                'design_id': d_name,
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
        log(f"Generated {len(df_objectives)} valid paired design records. Saved to {obj_parquet_path}")
        
        t2_elapsed = time.time() - t2_start
        ram2_peak = get_peak_ram_gb()
        free_d2 = check_disk_guard("Stage 2 Post-Check")
        stage_metrics.append({
            'stage': 'Stage 2: Coupling & Objectives',
            'wall_time_sec': round(t2_elapsed, 2),
            'wall_time_min': round(t2_elapsed / 60.0, 2),
            'peak_ram_gb': round(ram2_peak, 2),
            'free_disk_gb': round(free_d2, 2),
            'valid_paired_designs': len(df_objectives)
        })
        log(f"Stage 2 Finished in {t2_elapsed:.2f} s ({t2_elapsed/60:.2f} min) | Peak RAM: {ram2_peak:.2f} GB")
    
    pareto_parquet_path = os.path.join(OUTPUT_DIR, f"pareto_{STATION_NAME}.parquet")
    if os.path.exists(pareto_parquet_path):
        log(f"\n[STAGE 3 & 4 RESUME] Found existing Pareto front: {pareto_parquet_path}")
        df_pareto = pd.read_parquet(pareto_parquet_path)
        log(f"Loaded {len(df_pareto)} Pareto designs.")
    else:
        # STAGE 3: SURROGATE MODEL TUNING (5 TARGETS)
        log("\n" + "-"*80)
        log("[STAGE 3] SURROGATE MODEL TUNING & TRAINING (5 TARGETS)")
        log("-"*80)
        check_disk_guard("Stage 3 Pre-Check")
        t3_start = time.time()
    
        X = prepare_features(df_objectives)
        feature_names = list(X.columns)
        
        log("Tuning 5 primary XGBoost surrogates with Optuna 5-fold CV (40 trials, seed 42)...")
        surr_tasks = []
        for tgt in TARGETS:
            y = df_objectives[tgt].values
            valid_mask = ~np.isnan(y)
            X_v = X[valid_mask].reset_index(drop=True)
            y_v = y[valid_mask]
            X_tr, X_te, y_tr, y_te = train_test_split(X_v, y_v, test_size=0.20, random_state=42)
            surr_tasks.append((tgt, X_tr, y_tr, X_te, y_te, feature_names, STATION_NAME, MODELS_DIR, 42))
            
        surrogate_models = {}
        primary_metrics = []
        with ProcessPoolExecutor(max_workers=min(5, MAX_WORKERS)) as executor:
            futures = [executor.submit(_train_single_target_surrogate, t) for t in surr_tasks]
            for f in as_completed(futures):
                tgt, m_dict = f.result()
                surrogate_models[tgt] = joblib.load(os.path.join(MODELS_DIR, f"surrogate_{STATION_NAME}_{tgt}.joblib"))['model']
                primary_metrics.append({
                    'target': tgt,
                    'cv_r2': m_dict['cv_r2'],
                    'test_r2': m_dict['r2'],
                    'test_mae': m_dict['mae'],
                    'nmae_pct': m_dict['nmae_pct'],
                    'top10_overlap_pct': m_dict['top10_overlap_pct'],
                    's2_gate': m_dict['s2_gate']
                })
                log(f"  * Target {tgt:<10s} -> Test R2: {m_dict['r2']:.4f} | Test MAE: {m_dict['mae']:.3f} | Top-10% Overlap: {m_dict['top10_overlap_pct']:.1f}% | S2: {m_dict['s2_gate']}")
                
        df_primary_metrics = pd.DataFrame(primary_metrics)
        csv_metrics_path = os.path.join(OUTPUT_DIR, f"surrogate_metrics_{STATION_NAME}.csv")
        df_primary_metrics.to_csv(csv_metrics_path, index=False)
        
        t3_elapsed = time.time() - t3_start
        ram3_peak = get_peak_ram_gb()
        free_d3 = check_disk_guard("Stage 3 Post-Check")
        stage_metrics.append({
            'stage': 'Stage 3: Surrogate Tuning',
            'wall_time_sec': round(t3_elapsed, 2),
            'wall_time_min': round(t3_elapsed / 60.0, 2),
            'peak_ram_gb': round(ram3_peak, 2),
            'free_disk_gb': round(free_d3, 2)
        })
        log(f"Stage 3 Complete in {t3_elapsed:.2f} s ({t3_elapsed/60:.2f} min) | Peak RAM: {ram3_peak:.2f} GB")
        
        # STAGE 4: NSGA-II PARETO OPTIMIZATION (POP=100, GEN=200)
        log("\n" + "-"*80)
        log("[STAGE 4] NSGA-II PARETO OPTIMIZATION (POP=100, GEN=200, SEED=42)")
        log("-"*80)
        check_disk_guard("Stage 4 Pre-Check")
        t4_start = time.time()
        
        problem = ClampedShelterOptimizationProblem(city_name=STATION_NAME, surrogate_models=surrogate_models)
        algorithm = NSGA2(
            pop_size=100,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=1.0/8.0, eta=20),
            eliminate_duplicates=True
        )
        
        log("Running NSGA-II minimization over [O1_ml, O1_adapt, O2]...")
        res_opt = minimize(problem, algorithm, ('n_gen', 200), seed=42, verbose=False)
        
        opt_X = res_opt.X
        opt_F = res_opt.F
        log(f"NSGA-II completed. Found {len(opt_F)} non-dominated solution designs.")
        
        pareto_records = []
        for i in range(len(opt_X)):
            x_vec = opt_X[i]
            f_vec = opt_F[i]
            
            m_idx = min(2, max(0, int(np.floor(x_vec[7]))))
            wall_mass = MASS_CLASSES[m_idx]
            roof_ins = round(float(x_vec[0]) / 0.025) * 0.025
            wall_ins = round(float(x_vec[1]) / 0.025) * 0.025
            shading = max(0.30, float(x_vec[5]))
            
            pareto_records.append({
                'city': STATION_NAME,
                'pareto_id': f"P_{STATION_NAME}_{i:03d}",
                'roof_insulation_thickness': round(roof_ins, 3),
                'wall_insulation_thickness': round(wall_ins, 3),
                'wall_mass_class': wall_mass,
                'roof_solar_absorptance': round(float(x_vec[2]), 4),
                'wwr': round(float(x_vec[3]), 4),
                'orientation': round(float(x_vec[4]), 1),
                'shading_depth': round(shading, 3),
                'ventilation_ach': round(float(x_vec[6]), 2),
                'pred_O1_ml': float(f_vec[0]),
                'pred_O1_adapt': float(f_vec[1]),
                'pred_O2': float(f_vec[2])
            })
            
        df_pareto = pd.DataFrame(pareto_records)
        pareto_parquet_path = os.path.join(OUTPUT_DIR, f"pareto_{STATION_NAME}.parquet")
        df_pareto.to_parquet(pareto_parquet_path, index=False)
        log(f"Saved {len(df_pareto)} Pareto designs to {pareto_parquet_path}")
        
        t4_elapsed = time.time() - t4_start
        ram4_peak = get_peak_ram_gb()
        free_d4 = check_disk_guard("Stage 4 Post-Check")
        stage_metrics.append({
            'stage': 'Stage 4: NSGA-II Optimization',
            'wall_time_sec': round(t4_elapsed, 2),
            'wall_time_min': round(t4_elapsed / 60.0, 2),
            'peak_ram_gb': round(ram4_peak, 2),
            'free_disk_gb': round(free_d4, 2),
            'pareto_front_size': len(df_pareto)
        })
        log(f"Stage 4 Finished in {t4_elapsed:.2f} s ({t4_elapsed/60:.2f} min) | Peak RAM: {ram4_peak:.2f} GB")
    
    # STAGE 5: PHYSICAL ENERGYPLUS VERIFICATION (10 DESIGNS x 2 MODES)
    log("\n" + "-"*80)
    log("[STAGE 5] PHYSICAL ENERGYPLUS VERIFICATION (10 SELECTED DESIGNS x 2 MODES)")
    log("-"*80)
    check_disk_guard("Stage 5 Pre-Check")
    t5_start = time.time()
    
    df_verif_10 = select_10_verification_designs(df_pareto)
    log(f"Selected {len(df_verif_10)} representative Pareto designs across diverse trade-off roles.")
    
    verif_sim_dir = os.path.join(OUTPUT_DIR, f"verif_{STATION_NAME}")
    os.makedirs(verif_sim_dir, exist_ok=True)
    
    v_tasks = []
    for _, v_row in df_verif_10.iterrows():
        pid = v_row["pareto_id"]
        v_dict = v_row.to_dict()
        dir_fr = os.path.join(verif_sim_dir, f"{pid}_fr")
        dir_il = os.path.join(verif_sim_dir, f"{pid}_il")
        v_tasks.append({
            'epw_path': EPW_PATH,
            'design_id': pid,
            'params': v_dict,
            'mode': 'free_running',
            'run_dir': dir_fr
        })
        v_tasks.append({
            'epw_path': EPW_PATH,
            'design_id': pid,
            'params': v_dict,
            'mode': 'ideal_loads',
            'run_dir': dir_il
        })
        
    log(f"Executing {len(v_tasks)} EnergyPlus verification runs across {MAX_WORKERS} workers...")
    
    v_sim_res = {}
    v_hourly = {}
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_single_worker, t) for t in v_tasks]
        for f in as_completed(futures):
            did, mode, status, sm, h_dict = f.result()
            if did not in v_sim_res:
                v_sim_res[did] = {}
            v_sim_res[did][mode] = (status, sm)
            if mode == "free_running" and h_dict is not None:
                v_hourly[did] = h_dict
                
    verif_records = []
    for _, v_row in df_verif_10.iterrows():
        pid = v_row["pareto_id"]
        role = v_row["selection_role"]
        
        fr_stat, _ = v_sim_res[pid].get('free_running', (None, None))
        il_stat, il_sm = v_sim_res[pid].get('ideal_loads', (None, None))
        h_dict = v_hourly.get(pid)
        
        if fr_stat != 'SUCCESS' or il_stat != 'SUCCESS' or h_dict is None or il_sm is None:
            continue
            
        ta = h_dict['ta']
        tr = h_dict['tr']
        rh = h_dict['rh']
        tout = h_dict['t_out']
        
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
        
        o2_sim = float(il_sm['o2_energy_kwh_per_m2'])
        pred_o1_ml = float(v_row['pred_O1_ml'])
        pred_o1_ad = float(v_row['pred_O1_adapt'])
        pred_o2 = float(v_row['pred_O2'])
        
        verif_records.append({
            'pareto_id': pid,
            'selection_role': role,
            'pred_O1_ml': pred_o1_ml,
            'sim_O1_ml': ml_res['O1_ml'],
            'abs_err_O1_ml': abs(pred_o1_ml - ml_res['O1_ml']),
            'pred_O1_adapt': pred_o1_ad,
            'sim_O1_adapt': adapt_res['O1_adapt'],
            'abs_err_O1_adapt': abs(pred_o1_ad - adapt_res['O1_adapt']),
            'pred_O2': pred_o2,
            'sim_O2': o2_sim,
            'abs_err_O2': abs(pred_o2 - o2_sim),
            'roof_insulation_thickness': v_row['roof_insulation_thickness'],
            'wall_insulation_thickness': v_row['wall_insulation_thickness'],
            'wall_mass_class': v_row['wall_mass_class'],
            'roof_solar_absorptance': v_row['roof_solar_absorptance'],
            'wwr': v_row['wwr'],
            'orientation': v_row['orientation'],
            'shading_depth': v_row['shading_depth'],
            'ventilation_ach': v_row['ventilation_ach']
        })
        
    df_verif_out = pd.DataFrame(verif_records)
    verif_csv_path = os.path.join(OUTPUT_DIR, f"verification_{STATION_NAME}.csv")
    df_verif_out.to_csv(verif_csv_path, index=False)
    log(f"Saved physical verification metrics to {verif_csv_path}")
    
    t5_elapsed = time.time() - t5_start
    ram5_peak = get_peak_ram_gb()
    free_d5 = check_disk_guard("Stage 5 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 5: Verification Simulations',
        'wall_time_sec': round(t5_elapsed, 2),
        'wall_time_min': round(t5_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram5_peak, 2),
        'free_disk_gb': round(free_d5, 2),
        'verified_designs': len(df_verif_out)
    })
    
    total_wall_sec = sum(m['wall_time_sec'] for m in stage_metrics)
    overall_peak_ram = max(m['peak_ram_gb'] for m in stage_metrics)
    
    log("\n" + "="*80)
    log(f"PILOT EXECUTION COMPLETE FOR {STATION_NAME.upper()}")
    log(f"Total Wall Time: {total_wall_sec:.2f} s ({total_wall_sec/60:.2f} min) | Overall Peak RAM: {overall_peak_ram:.2f} GB")
    log("="*80)
    
    with open(EVIDENCE_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(execution_lines))
    print(f"Evidence report written to {EVIDENCE_TXT}")

if __name__ == "__main__":
    main()
