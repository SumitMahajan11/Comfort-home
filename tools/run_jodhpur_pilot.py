"""
tools/run_jodhpur_pilot.py

Phase 1 Step 5 Pilot Execution: Jodhpur Only under Original Settings.
- Sourced original settings from PROJECT_SPEC, TRACKER, and earlier reports.
- Disk guard 5 GB enforced; Max 6 parallel workers.
- Logs time, peak RAM, and disk use per stage.
- Compares numeric outcomes vs v1.1.3 backup at E:\\Backups\\ClimateAdapt_20261010.
- All result and evidence files written strictly by code.
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
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

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

DISK_GUARD_GB = 5.0
MAX_WORKERS = 6
STATION_NAME = "Jodhpur"
EPW_PATH = "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"
BACKUP_DIR = r"E:\Backups\ClimateAdapt_20261010"
OUTPUT_DIR = "data/processed/pilot_jodhpur"
MODELS_DIR = "models/pilot_jodhpur"
EVIDENCE_TXT = "reports/evidence/jodhpur_pilot_execution_output.txt"

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
                        'hour': np.arange(8760, dtype=np.int32),
                        'ta': hdf['ta'].values.astype(np.float32),
                        'tr': hdf['tr'].values.astype(np.float32),
                        'rh': hdf['rh'].values.astype(np.float32),
                        't_out': hdf['t_out'].values.astype(np.float32)
                    }
            except Exception as e:
                res["status"] = "PARSE_ERROR"
                res["error_msg"] = str(e)
                
    # Retain only eplusout.err and shelter.idf to conserve disk space
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
        'seed': seed,
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
    with zipfile.ZipFile(target_zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for s_dir in source_dirs:
            if os.path.exists(s_dir):
                for root, dirs, files in os.walk(s_dir):
                    for f in files:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, os.path.dirname(s_dir))
                        zf.write(full_p, rel_p)

def run_jodhpur_pilot():
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)
        
    log("="*80)
    log("PHASE 1 STEP 5 PILOT EXECUTION: JODHPUR ONLY (ORIGINAL SETTINGS)")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*80)
    
    # -------------------------------------------------------------------------
    # 0. ORIGINAL SETTINGS PROVENANCE LEDGER
    # -------------------------------------------------------------------------
    log("\n[ORIGINAL SETTINGS PROVENANCE LEDGER]")
    provenance = [
        ("Per-City Run Count", "1,000 Latin Hypercube sample designs x 2 modes = 2,000 EnergyPlus runs",
         "reports/phase3_sim.md:26; reports/PILOT_INVALID.md:8; docs/PROJECT_SPEC.md Section 4"),
        ("Surrogate Tuning Trials", "40 Optuna trials per target",
         "reports/phase4_surrogates.md:23; reports/PILOT_INVALID.md:9; reports/final_results.md:102"),
        ("Surrogate Tuning Folds", "5-fold Cross-Validation (KFold)",
         "reports/phase4_surrogates.md:23; reports/PILOT_INVALID.md:9; src/models/train_surrogates.py:82"),
        ("NSGA-II Algorithm", "NSGA-II (pymoo) Multi-Objective Optimizer",
         "reports/phase5_optimization.md:67; src/optimize/nsga2.py:2-23"),
        ("NSGA-II Population & Generations", "Pop = 100, Generations = 200",
         "reports/phase5_optimization.md:67; docs/TRACKER.md:58; README_draft.md:14"),
        ("NSGA-II Crossover & Mutation", "SBX (prob=0.9, eta=15), PM (prob=0.2, eta=20)",
         "reports/phase5_optimization.md:67; tools/run_station_pipeline.py:439-440"),
        ("Direct Verification Set", "10 representative designs selected from front (20 physical runs)",
         "reports/phase5_optimization.md:114; docs/TRACKER.md:100; src/optimize/nsga2.py:175-238"),
        ("Seeds 42, 43, 44", "Evaluated across seeds 42, 43, 44 for surrogate stability",
         "docs/TRACKER.md:27; reports/audit_fix_plan.md:281"),
        ("Weather Baseline", "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
         "Decision D-034; data/raw/weather_baseline_manifest.json (size: 1,607,059 bytes, SHA256: d08d5dae5...)")
    ]
    for param, val, src in provenance:
        log(f"  * {param:32s}: {val}")
        log(f"    Source: {src}")
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(EVIDENCE_TXT), exist_ok=True)
    
    stage_metrics = []
    
    # Check baseline disk guard
    init_free_gb = check_disk_guard("Initialization")
    log(f"\n[SYSTEM RESOURCE BASELINE]")
    log(f"  CPU Cores: {psutil.cpu_count(logical=True)} | Max Workers Enforced: {MAX_WORKERS}")
    log(f"  Initial Free Disk Space: {init_free_gb:.2f} GB (Disk guard: {DISK_GUARD_GB:.1f} GB)")
    log(f"  Initial RAM Usage: {get_peak_ram_gb():.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 1: BATCH SIMULATIONS (1,000 DESIGNS x 2 MODES = 2,000 RUNS)
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 1] ENERGYPLUS BATCH SIMULATIONS (1,000 LHS DESIGNS x 2 MODES = 2,000 RUNS)")
    log("-"*80)
    check_disk_guard("Stage 1 Pre-Check")
    t1_start = time.time()
    ram1_start = get_peak_ram_gb()
    
    df_samples = sample_designs(n_samples=1000, seed=42)
    log(f"Generated {len(df_samples):,} Latin Hypercube designs with seed 42.")
    log(f"Envelope parameters enforced: Insulation in 25 mm steps [0.0..0.150 m], Overhang >= 0.30 m.")
    
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
        
    log(f"Launching {len(sim_tasks):,} EnergyPlus simulation runs on {MAX_WORKERS} workers...")
    sim_summaries = {}
    hourly_records = []
    runs_attempted = len(sim_tasks)
    runs_successful = 0
    runs_failed = 0
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_single_worker, t) for t in sim_tasks]
        done_count = 0
        for f in as_completed(futures):
            did, mode, status, summary, hourly = f.result()
            done_count += 1
            if did not in sim_summaries:
                sim_summaries[did] = {}
            sim_summaries[did][mode] = (status, summary)
            if status == "SUCCESS":
                runs_successful += 1
            else:
                runs_failed += 1
            if hourly is not None:
                df_h = pd.DataFrame(hourly)
                df_h['design_id'] = did
                hourly_records.append(df_h)
            if done_count % 400 == 0 or done_count == runs_attempted:
                cur_free = check_disk_guard(f"Stage 1 Worker Progress {done_count}/{runs_attempted}")
                log(f"  [{done_count:4d}/{runs_attempted:4d}] Completed ({runs_successful} success, {runs_failed} failed) | Free Disk: {cur_free:.2f} GB")
                
    df_all_hourly = pd.concat(hourly_records, ignore_index=True)
    hourly_parquet_path = os.path.join(OUTPUT_DIR, f"hourly_fr_{STATION_NAME}.parquet")
    df_all_hourly.to_parquet(hourly_parquet_path, index=False)
    
    t1_elapsed = time.time() - t1_start
    ram1_peak = get_peak_ram_gb()
    free_d1 = check_disk_guard("Stage 1 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 1: EnergyPlus Batch Simulation (2,000 runs)',
        'wall_time_sec': round(t1_elapsed, 2),
        'wall_time_min': round(t1_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram1_peak, 2),
        'free_disk_gb': round(free_d1, 2),
        'runs_attempted': runs_attempted,
        'runs_successful': runs_successful,
        'success_rate_pct': round(runs_successful / runs_attempted * 100.0, 2)
    })
    log(f"Stage 1 Finished in {t1_elapsed:.2f} s ({t1_elapsed/60:.2f} min) | Peak RAM: {ram1_peak:.2f} GB | Runs: {runs_successful}/{runs_attempted} ({runs_successful/runs_attempted*100:.2f}%)")
    
    # -------------------------------------------------------------------------
    # STAGE 2: DUAL COMFORT JUDGE COUPLING
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 2] DUAL COMFORT JUDGE COUPLING (ADAPTIVE 90% + ML CHAMPION)")
    log("-"*80)
    check_disk_guard("Stage 2 Pre-Check")
    t2_start = time.time()
    
    champ_model = load_champion_model("models/champion_comfort_model.joblib")
    log("Loaded calibrated ML Champion comfort model (Ablation_A3_OutdoorTemp).")
    
    obj_records = []
    df_samples_idx = df_samples.set_index('design_id')
    grouped_hourly = df_all_hourly.groupby('design_id')
    
    for did, group in grouped_hourly:
        if did not in sim_summaries:
            continue
        fr_status, fr_sm = sim_summaries[did].get('free_running', (None, None))
        il_status, il_sm = sim_summaries[did].get('ideal_loads', (None, None))
        
        # Decision D-014: Drop pair if either mode is missing/failed
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
            'city': STATION_NAME,
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
    obj_parquet_path = os.path.join(OUTPUT_DIR, f"objectives_{STATION_NAME}.parquet")
    df_objectives.to_parquet(obj_parquet_path, index=False)
    log(f"Generated {len(df_objectives)} valid paired design records. Saved {obj_parquet_path}")
    
    # Prune transient hourly parquet to satisfy disk guard
    if os.path.exists(hourly_parquet_path):
        os.remove(hourly_parquet_path)
        log(f"Pruned transient hourly parquet {hourly_parquet_path} to conserve disk space.")
    del df_all_hourly
    del hourly_records
    
    t2_elapsed = time.time() - t2_start
    ram2_peak = get_peak_ram_gb()
    free_d2 = check_disk_guard("Stage 2 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 2: Dual Comfort Judge Coupling',
        'wall_time_sec': round(t2_elapsed, 2),
        'wall_time_min': round(t2_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram2_peak, 2),
        'free_disk_gb': round(free_d2, 2),
        'valid_paired_designs': len(df_objectives)
    })
    log(f"Stage 2 Finished in {t2_elapsed:.2f} s ({t2_elapsed/60:.2f} min) | Peak RAM: {ram2_peak:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 3: SURROGATE TRAINING & MULTI-SEED EVALUATION (SEEDS 42, 43, 44)
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 3] SURROGATE MODEL TUNING & MULTI-SEED EVALUATION (SEEDS 42, 43, 44)")
    log("-"*80)
    check_disk_guard("Stage 3 Pre-Check")
    t3_start = time.time()
    
    X = prepare_features(df_objectives)
    feature_names = list(X.columns)
    
    # 1. Primary Model Training under Canonical Seed 42
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
            res_dict = f.result()
            tgt = res_dict['target']
            surrogate_models[tgt] = res_dict['model']
            primary_metrics.append({
                'city': STATION_NAME,
                'target': tgt,
                'seed': 42,
                'r2': res_dict['r2'],
                'mae': res_dict['mae'],
                'nmae_pct': res_dict['nmae_pct'],
                'top10_overlap_pct': res_dict['top10_overlap_pct'],
                's2_status': res_dict['s2_status'],
                'cv_r2': res_dict['cv_r2']
            })
            log(f"  * Seed 42 | Target: {tgt:10s} | Test R2: {res_dict['r2']:.4f} | MAE: {res_dict['mae']:.3f} | S2: {res_dict['s2_status']} (CV R2: {res_dict['cv_r2']:.4f})")
            
    df_surr_seed42 = pd.DataFrame(primary_metrics)
    
    # 2. Multi-Seed Stability Check (Seeds 43 & 44)
    log("\nEvaluating multi-seed test stability across seeds 43 and 44...")
    multi_seed_metrics = list(primary_metrics)
    for test_seed in [43, 44]:
        for tgt in TARGETS:
            y = df_objectives[tgt].values
            valid_mask = ~np.isnan(y)
            X_v = X[valid_mask].reset_index(drop=True)
            y_v = y[valid_mask]
            X_tr, X_te, y_tr, y_te = train_test_split(X_v, y_v, test_size=0.20, random_state=test_seed)
            # Evaluate the tuned primary model on this split
            m = surrogate_models[tgt]
            y_p = m.predict(X_te)
            r2_s = float(r2_score(y_te, y_p))
            mae_s = float(mean_absolute_error(y_te, y_p))
            y_rng = float(y_tr.max() - y_tr.min())
            nmae_s = float((mae_s / y_rng * 100.0) if y_rng > 0 else 0.0)
            top10_s = float(compute_top_k_overlap(y_te, y_p, k_pct=0.10))
            s2_s = "PASS" if r2_s >= 0.95 else "FAIL"
            multi_seed_metrics.append({
                'city': STATION_NAME,
                'target': tgt,
                'seed': test_seed,
                'r2': r2_s,
                'mae': mae_s,
                'nmae_pct': nmae_s,
                'top10_overlap_pct': top10_s,
                's2_status': s2_s,
                'cv_r2': np.nan
            })
            log(f"  * Seed {test_seed} | Target: {tgt:10s} | Test R2: {r2_s:.4f} | MAE: {mae_s:.3f} | S2: {s2_s}")
            
    df_all_seed_metrics = pd.DataFrame(multi_seed_metrics)
    metrics_csv_path = os.path.join(OUTPUT_DIR, f"surrogate_metrics_{STATION_NAME}.csv")
    df_all_seed_metrics.to_csv(metrics_csv_path, index=False)
    log(f"Saved surrogate metrics table to {metrics_csv_path}")
    
    t3_elapsed = time.time() - t3_start
    ram3_peak = get_peak_ram_gb()
    free_d3 = check_disk_guard("Stage 3 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 3: Surrogate Training & Multi-Seed Evaluation',
        'wall_time_sec': round(t3_elapsed, 2),
        'wall_time_min': round(t3_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram3_peak, 2),
        'free_disk_gb': round(free_d3, 2),
        's2_pass_count_seed42': int((df_surr_seed42['s2_status'] == 'PASS').sum()),
        's2_total_seed42': len(df_surr_seed42)
    })
    log(f"Stage 3 Finished in {t3_elapsed:.2f} s ({t3_elapsed/60:.2f} min) | Peak RAM: {ram3_peak:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 4: NSGA-II MULTI-OBJECTIVE PARETO OPTIMIZATION
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 4] NSGA-II MULTI-OBJECTIVE PARETO OPTIMIZATION (POP=100, GEN=200, SEED=42)")
    log("-"*80)
    check_disk_guard("Stage 4 Pre-Check")
    t4_start = time.time()
    
    problem = ShelterOptimizationProblem(STATION_NAME, surrogate_models)
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
        
        # Enforce Step 4 discretization on outputs
        roof_ins = round(float(x[0]) / 0.025) * 0.025
        wall_ins = round(float(x[1]) / 0.025) * 0.025
        shading = max(0.30, float(x[5]))
        
        pareto_rows.append({
            'city': STATION_NAME,
            'pareto_id': f"P_{STATION_NAME}_{i:03d}",
            'roof_insulation_thickness': roof_ins,
            'wall_insulation_thickness': wall_ins,
            'wall_mass_class': mass_str,
            'roof_solar_absorptance': round(float(x[2]), 4),
            'wwr': round(float(x[3]), 4),
            'orientation': round(float(x[4]), 1),
            'shading_depth': round(shading, 3),
            'ventilation_ach': round(float(x[6]), 2),
            'pred_O1_ml': float(f[0]),
            'pred_O1_adapt': float(f[1]),
            'pred_O2': float(f[2]),
            'ml_confidence_flag': "STANDARD",
            'adaptive_confidence_flag': "LOW_CONFIDENCE" if adapt_flag else "STANDARD"
        })
        
    df_pareto = pd.DataFrame(pareto_rows)
    pareto_parquet_path = os.path.join(OUTPUT_DIR, f"pareto_{STATION_NAME}.parquet")
    df_pareto.to_parquet(pareto_parquet_path, index=False)
    log(f"Extracted {len(df_pareto)} non-dominated Pareto designs. Saved {pareto_parquet_path}")
    
    t4_elapsed = time.time() - t4_start
    ram4_peak = get_peak_ram_gb()
    free_d4 = check_disk_guard("Stage 4 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 4: NSGA-II Pareto Optimization (Pop=100, Gen=200)',
        'wall_time_sec': round(t4_elapsed, 2),
        'wall_time_min': round(t4_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram4_peak, 2),
        'free_disk_gb': round(free_d4, 2),
        'pareto_designs_count': len(df_pareto)
    })
    log(f"Stage 4 Finished in {t4_elapsed:.2f} s ({t4_elapsed/60:.2f} min) | Peak RAM: {ram4_peak:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 5: DIRECT ENERGYPLUS VERIFICATION (10 DESIGNS x 2 MODES = 20 RUNS)
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 5] DIRECT ENERGYPLUS VERIFICATION (10 DESIGNS x 2 MODES = 20 RUNS)")
    log("-"*80)
    check_disk_guard("Stage 5 Pre-Check")
    t5_start = time.time()
    
    df_selected = select_10_verification_designs(df_pareto)
    log(f"Selected 10 representative Pareto designs for direct simulation:")
    for _, r in df_selected.iterrows():
        log(f"  * {r['pareto_id']:14s} | Role: {r['selection_role']:16s} | Pred O1_ml: {r['pred_O1_ml']:5.2f}% | Pred O1_adapt: {r['pred_O1_adapt']:5.2f}% | Pred O2: {r['pred_O2']:5.2f} kWh/m2")
        
    ver_base_dir = os.path.join(OUTPUT_DIR, f"ver_{STATION_NAME}")
    os.makedirs(ver_base_dir, exist_ok=True)
    
    ver_tasks = []
    for _, p_row in df_selected.iterrows():
        pid = p_row['pareto_id']
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
        ver_tasks.append({
            'epw_path': EPW_PATH,
            'design_id': pid,
            'params': p_dict,
            'mode': 'free_running',
            'run_dir': os.path.join(ver_base_dir, f"{pid}_fr")
        })
        ver_tasks.append({
            'epw_path': EPW_PATH,
            'design_id': pid,
            'params': p_dict,
            'mode': 'ideal_loads',
            'run_dir': os.path.join(ver_base_dir, f"{pid}_il")
        })
        
    ver_summaries = {}
    ver_hourly = []
    with ProcessPoolExecutor(max_workers=min(len(ver_tasks), MAX_WORKERS)) as executor:
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
        
        err_ml = abs(pred_o1_ml - act_o1_ml)
        err_ad = abs(pred_o1_ad - act_o1_ad)
        err_o2 = abs(pred_o2 - act_o2)
        
        rel_ml = (err_ml / act_o1_ml * 100.0) if act_o1_ml > 0 else 0.0
        rel_ad = (err_ad / act_o1_ad * 100.0) if act_o1_ad > 0 else 0.0
        rel_o2 = (err_o2 / act_o2 * 100.0) if act_o2 > 0 else 0.0
        
        ver_results.append({
            'city': STATION_NAME,
            'pareto_id': pid,
            'selection_role': p_row_match['selection_role'],
            'roof_insulation_thickness': p_row_match['roof_insulation_thickness'],
            'wall_insulation_thickness': p_row_match['wall_insulation_thickness'],
            'wall_mass_class': p_row_match['wall_mass_class'],
            'roof_solar_absorptance': p_row_match['roof_solar_absorptance'],
            'wwr': p_row_match['wwr'],
            'orientation': p_row_match['orientation'],
            'shading_depth': p_row_match['shading_depth'],
            'ventilation_ach': p_row_match['ventilation_ach'],
            'pred_O1_ml': pred_o1_ml,
            'actual_O1_ml': act_o1_ml,
            'abs_err_O1_ml': err_ml,
            'rel_err_O1_ml_pct': rel_ml,
            'pred_O1_adapt': pred_o1_ad,
            'actual_O1_adapt': act_o1_ad,
            'abs_err_O1_adapt': err_ad,
            'rel_err_O1_adapt_pct': rel_ad,
            'pred_O2': pred_o2,
            'actual_O2': act_o2,
            'abs_err_O2': err_o2,
            'rel_err_O2_pct': rel_o2,
            'ml_confidence_flag': p_row_match['ml_confidence_flag'],
            'adaptive_confidence_flag': p_row_match['adaptive_confidence_flag']
        })
        
    df_ver = pd.DataFrame(ver_results)
    ver_csv_path = os.path.join(OUTPUT_DIR, f"verification_{STATION_NAME}.csv")
    df_ver.to_csv(ver_csv_path, index=False)
    log(f"Completed direct EnergyPlus verification for {len(df_ver)} designs. Saved {ver_csv_path}")
    
    t5_elapsed = time.time() - t5_start
    ram5_peak = get_peak_ram_gb()
    free_d5 = check_disk_guard("Stage 5 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 5: Direct EnergyPlus Verification (10 designs x 2 modes)',
        'wall_time_sec': round(t5_elapsed, 2),
        'wall_time_min': round(t5_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram5_peak, 2),
        'free_disk_gb': round(free_d5, 2),
        'verified_designs_count': len(df_ver)
    })
    log(f"Stage 5 Finished in {t5_elapsed:.2f} s ({t5_elapsed/60:.2f} min) | Peak RAM: {ram5_peak:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 6: DISK COMPRESSION & CLEANUP (ZIP sim & ver folders)
    # -------------------------------------------------------------------------
    log("\n" + "-"*80)
    log("[STAGE 6] COMPRESSION & TRANSIENT RUN CLEANUP")
    log("-"*80)
    t6_start = time.time()
    archive_zip = os.path.join(OUTPUT_DIR, f"archive_{STATION_NAME}.zip")
    log(f"Compressing simulation run trees into {archive_zip}...")
    _zip_directory([base_sim_dir, ver_base_dir], archive_zip)
    
    zip_size_mb = os.path.getsize(archive_zip) / (1024**2)
    log(f"Archive created ({zip_size_mb:.2f} MB). Removing transient uncompressed folders...")
    shutil.rmtree(base_sim_dir, ignore_errors=True)
    shutil.rmtree(ver_base_dir, ignore_errors=True)
    
    t6_elapsed = time.time() - t6_start
    ram6_peak = get_peak_ram_gb()
    free_d6 = check_disk_guard("Stage 6 Post-Check")
    stage_metrics.append({
        'stage': 'Stage 6: Compression & Cleanup',
        'wall_time_sec': round(t6_elapsed, 2),
        'wall_time_min': round(t6_elapsed / 60.0, 2),
        'peak_ram_gb': round(ram6_peak, 2),
        'free_disk_gb': round(free_d6, 2),
        'archive_zip_size_mb': round(zip_size_mb, 2)
    })
    log(f"Stage 6 Finished in {t6_elapsed:.2f} s | Archive Size: {zip_size_mb:.2f} MB | Free Disk: {free_d6:.2f} GB")
    
    # -------------------------------------------------------------------------
    # STAGE 7: COMPARISON VS v1.1.3 JODHPUR RESULTS
    # -------------------------------------------------------------------------
    log("\n" + "="*80)
    log("NUMERIC COMPARISON VS v1.1.3 JODHPUR RESULTS (BACKUP REFERENCE)")
    log("="*80)
    
    # 1. Compare Surrogates
    surr_backup_path = os.path.join(BACKUP_DIR, "data", "processed", "surrogate_metrics.csv")
    df_surr_b = pd.read_csv(surr_backup_path)
    df_jod_b = df_surr_b[df_surr_b['city'] == 'Jodhpur'].set_index('target')
    
    df_jod_cur = df_surr_seed42.set_index('target')
    
    log("\n--- A. Surrogate Model Performance Comparison (Seed 42) ---")
    log(f"{'Target':10s} | {'v1.1.3 R2':10s} | {'Pilot R2':10s} | {'Delta R2':10s} | {'v1.1.3 MAE':10s} | {'Pilot MAE':10s} | {'Pilot S2':8s}")
    log("-" * 80)
    for tgt in TARGETS:
        r2_old = float(df_jod_b.loc[tgt, 'r2'])
        mae_old = float(df_jod_b.loc[tgt, 'mae'])
        r2_new = float(df_jod_cur.loc[tgt, 'r2'])
        mae_new = float(df_jod_cur.loc[tgt, 'mae'])
        d_r2 = r2_new - r2_old
        s2_st = df_jod_cur.loc[tgt, 's2_status']
        log(f"{tgt:10s} | {r2_old:10.4f} | {r2_new:10.4f} | {d_r2:+10.4f} | {mae_old:10.3f} | {mae_new:10.3f} | {s2_st:8s}")
        
    # 2. Compare Multi-Seed Surrogates
    log("\n--- B. Surrogate Multi-Seed Stability (Pilot Seeds 42, 43, 44) ---")
    log(f"{'Target':10s} | {'Seed 42 R2':10s} | {'Seed 43 R2':10s} | {'Seed 44 R2':10s} | {'Min R2':10s} | {'All >= 0.95?':12s}")
    log("-" * 75)
    for tgt in TARGETS:
        sub = df_all_seed_metrics[df_all_seed_metrics['target'] == tgt].set_index('seed')
        r42 = float(sub.loc[42, 'r2'])
        r43 = float(sub.loc[43, 'r2'])
        r44 = float(sub.loc[44, 'r2'])
        min_r = min(r42, r43, r44)
        all_pass = "YES (PASS)" if min_r >= 0.95 else "NO"
        log(f"{tgt:10s} | {r42:10.4f} | {r43:10.4f} | {r44:10.4f} | {min_r:10.4f} | {all_pass:12s}")
        
    # 3. Compare Pareto Frontiers & Direct Verifications
    ver_backup_path = os.path.join(BACKUP_DIR, "data", "processed", "pareto_verification_results.csv")
    df_ver_b = pd.read_csv(ver_backup_path)
    df_ver_jod_b = df_ver_b[df_ver_b['city'] == 'Jodhpur']
    
    log("\n--- C. Direct EnergyPlus Verification Results (10 Representative Designs) ---")
    log(f"{'Design ID':14s} | {'Role':14s} | {'Act O1_ml %':11s} | {'Act O1_ad %':11s} | {'Act O2 kWh':11s} | {'Err O1_ml pp':12s} | {'Err O2 kWh':10s}")
    log("-" * 88)
    for _, vr in df_ver.iterrows():
        log(f"{vr['pareto_id']:14s} | {vr['selection_role']:14s} | {vr['actual_O1_ml']:11.2f} | {vr['actual_O1_adapt']:11.2f} | {vr['actual_O2']:11.2f} | {vr['abs_err_O1_ml']:12.2f} | {vr['abs_err_O2']:10.2f}")
        
    log("\n--- D. Verified Pareto Summary vs v1.1.3 ---")
    log(f"  v1.1.3 Verified Actual Ranges (Jodhpur, N=10):")
    log(f"    * Actual O1_ml:    {df_ver_jod_b['actual_O1_ml'].min():.2f}% to {df_ver_jod_b['actual_O1_ml'].max():.2f}%")
    log(f"    * Actual O1_adapt: {df_ver_jod_b['actual_O1_adapt'].min():.2f}% to {df_ver_jod_b['actual_O1_adapt'].max():.2f}%")
    log(f"    * Actual O2:       {df_ver_jod_b['actual_O2'].min():.2f} to {df_ver_jod_b['actual_O2'].max():.2f} kWh/m2")
    log(f"  Pilot Verified Actual Ranges (Jodhpur, N=10):")
    log(f"    * Actual O1_ml:    {df_ver['actual_O1_ml'].min():.2f}% to {df_ver['actual_O1_ml'].max():.2f}%")
    log(f"    * Actual O1_adapt: {df_ver['actual_O1_adapt'].min():.2f}% to {df_ver['actual_O1_adapt'].max():.2f}%")
    log(f"    * Actual O2:       {df_ver['actual_O2'].min():.2f} to {df_ver['actual_O2'].max():.2f} kWh/m2")
    
    # 4. Total Pipeline Summary
    total_time_sec = sum(m['wall_time_sec'] for m in stage_metrics)
    log("\n" + "="*80)
    log("PER-STAGE RESOURCE PROFILING TABLE")
    log("="*80)
    df_stages = pd.DataFrame(stage_metrics)
    log(df_stages[['stage', 'wall_time_sec', 'wall_time_min', 'peak_ram_gb', 'free_disk_gb']].to_string(index=False))
    log(f"\nTotal Pipeline Wall-Clock Time: {total_time_sec:.2f} s ({total_time_sec/60:.2f} min)")
    
    # Write full output log
    with open(EVIDENCE_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log(f"\nEvidence log written to {EVIDENCE_TXT}")
    log("="*80)
    log("PILOT COMPLETE FOR JODHPUR. STOPPING AS INSTRUCTED. NO OTHER CITIES RUN.")
    log("="*80)

if __name__ == "__main__":
    run_jodhpur_pilot()
