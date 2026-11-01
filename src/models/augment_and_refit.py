"""
Phase 4B Remedy: Sample 500 additional designs per city (seed=1042),
simulate free-running & ideal-loads modes, evaluate dual comfort judges,
merge with original 1,000 designs (total 1,500 designs per city),
and re-fit surrogates to report before vs after S2 metrics.
"""

import os
import sys
import time
import shutil
import joblib
import optuna
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import r2_score, mean_absolute_error
from xgboost import XGBRegressor

sys.path.insert(0, os.path.abspath("."))

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
from src.models.train_surrogates import prepare_features, compute_top_k_overlap, tune_surrogate_xgboost, TARGETS, CITIES

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

def worker_sim_both_modes(task):
    """Runs both free_running and ideal_loads for a design, parses hourly & energy, cleans up."""
    p = task['params']
    city = task['city']
    epw = task['epw']
    d_id = task['design_id']
    work_dir = task['work_dir']
    
    dir_fr = os.path.join(work_dir, "fr")
    dir_il = os.path.join(work_dir, "il")
    os.makedirs(dir_fr, exist_ok=True)
    os.makedirs(dir_il, exist_ok=True)
    
    try:
        # 1. Free running
        idf_fr = os.path.join(dir_fr, "shelter.idf")
        render_shelter_idf(p, idf_fr, mode='free_running')
        res_fr = run_single_simulation(idf_fr, epw, dir_fr)
        if res_fr['status'] != 'SUCCESS':
            shutil.rmtree(work_dir, ignore_errors=True)
            return None
            
        csv_fr = os.path.join(dir_fr, "eplusout.csv")
        hdf_fr, sm_fr = parse_simulation_csv(csv_fr)
        
        ta = hdf_fr['ta'].values.astype(np.float32)
        tr = hdf_fr['tr'].values.astype(np.float32)
        rh = hdf_fr['rh'].values.astype(np.float32)
        tout = hdf_fr['t_out'].values.astype(np.float32)
        
        # 2. Ideal loads
        idf_il = os.path.join(dir_il, "shelter.idf")
        render_shelter_idf(p, idf_il, mode='ideal_loads')
        res_il = run_single_simulation(idf_il, epw, dir_il)
        if res_il['status'] != 'SUCCESS':
            shutil.rmtree(work_dir, ignore_errors=True)
            return None
            
        csv_il = os.path.join(dir_il, "eplusout.csv")
        hdf_il, sm_il = parse_simulation_csv(csv_il)
        o2_energy = float(sm_il['o2_energy_kwh_per_m2'])
        
        shutil.rmtree(work_dir, ignore_errors=True)
        
        return {
            'city': city,
            'design_id': d_id,
            'params': p,
            'ta': ta,
            'tr': tr,
            'rh': rh,
            't_out': tout,
            'o2': o2_energy
        }
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

def run_augmentation_pipeline(n_new=500, max_workers=10):
    print("="*80)
    print(f"SAMPLING AND SIMULATING {n_new} ADDITIONAL DESIGNS PER CITY (SEED 1042)")
    print("="*80)
    
    # 1. Sample 500 new designs with new ID prefix D_01000..D_01499
    df_samples = sample_designs(n_samples=n_new, seed=1042)
    # Re-index design IDs to avoid collision
    df_samples['design_id'] = [f"D_{1000 + i:05d}" for i in range(len(df_samples))]
    
    temp_work = "data/processed/temp_aug_sims"
    os.makedirs(temp_work, exist_ok=True)
    
    tasks = []
    for city, epw in CITIES_EPW.items():
        for _, row in df_samples.iterrows():
            d_id = row['design_id']
            p_dict = row.to_dict()
            work_dir = os.path.join(temp_work, f"{city}_{d_id}")
            tasks.append({
                'city': city,
                'design_id': d_id,
                'epw': epw,
                'params': p_dict,
                'work_dir': work_dir
            })
            
    total_tasks = len(tasks)
    print(f"Prepared {total_tasks:,} paired simulation tasks ({n_new*5} designs x 2 modes). Running...")
    
    t0 = time.time()
    results = []
    completed = 0
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_sim_both_modes, t): t for t in tasks}
        for future in as_completed(futures):
            res = future.result()
            completed += 1
            if res is not None:
                results.append(res)
            if completed % 250 == 0 or completed == total_tasks:
                elapsed = time.time() - t0
                rate = completed / elapsed
                print(f"Progress: {completed}/{total_tasks} ({completed/total_tasks*100:.1f}%) | Success: {len(results)} | Speed: {rate:.1f} tasks/s")
                
    print(f"Completed simulation runs in {time.time()-t0:.1f}s. Valid new pairs: {len(results):,}/{total_tasks:,}")
    
    # Load ML Champion model
    model = load_champion_model()
    
    # Compute objectives for new designs
    new_records = []
    for r in results:
        city = r['city']
        d_id = r['design_id']
        p = r['params']
        ta = r['ta']
        tr = r['tr']
        rh = r['rh']
        tout = r['t_out']
        o2 = r['o2']
        
        daily_tout = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)
        
        adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
        ml_res = evaluate_ml_champion_comfort(
            model=model, ta=ta, tr=tr, rh=rh,
            t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
            met=1.1, vel=0.15
        )
        
        rec = {
            'city': city,
            'design_id': d_id,
            **p,
            'O1_ml': ml_res['O1_ml'],
            'warm_ml': ml_res['warm_ml'],
            'cool_ml': ml_res['cool_ml'],
            'O1_adapt': adapt_res['O1_adapt'],
            'hot_adapt': adapt_res['hot_adapt'],
            'cold_adapt': adapt_res['cold_adapt'],
            'invalid_share_adapt': adapt_res['invalid_share_adapt'],
            'O2': o2
        }
        new_records.append(rec)
        
    df_new = pd.DataFrame(new_records)
    
    # Merge with original objectives.parquet
    df_orig = pd.read_parquet("data/processed/objectives.parquet")
    df_augmented = pd.concat([df_orig, df_new], ignore_index=True)
    
    aug_parquet = "data/processed/objectives_augmented.parquet"
    df_augmented.to_parquet(aug_parquet, index=False)
    print(f"\nSaved augmented objectives ({len(df_augmented):,} rows) to {aug_parquet}")
    
    # Clean temp dir
    shutil.rmtree(temp_work, ignore_errors=True)
    
    # Now re-fit surrogates on augmented dataset (1,500 designs per city)
    print("\n" + "="*80)
    print("RE-FITTING ALL 25 SURROGATE MODELS ON AUGMENTED DATASET (1,500 DESIGNS/CITY)")
    print("="*80)
    
    aug_metrics = []
    for city in CITIES:
        df_city = df_augmented[df_augmented['city'] == city].reset_index(drop=True)
        print(f"\nCity: {city} ({len(df_city)} designs)")
        X = prepare_features(df_city)
        
        for target in TARGETS:
            if df_city[target].isna().all():
                continue
            y = df_city[target].values
            valid_mask = ~np.isnan(y)
            X_v = X[valid_mask].reset_index(drop=True)
            y_v = y[valid_mask]
            
            X_train, X_test, y_train, y_test = train_test_split(
                X_v, y_v, test_size=0.20, random_state=42
            )
            
            best_model, best_params, cv_r2 = tune_surrogate_xgboost(
                X_train, y_train, n_trials=40, seed=42
            )
            y_pred = best_model.predict(X_test)
            
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            t_range = float(y_v.max() - y_v.min())
            nmae = (mae / t_range * 100.0) if t_range > 0 else 0.0
            top10 = compute_top_k_overlap(y_test, y_pred, k_pct=0.10)
            s2_pass = bool(r2 >= 0.95)
            s2_str = "PASS" if s2_pass else "FAIL"
            
            print(f"  Target: {target:10s} | N=1500 Test R2: {r2:.4f} | MAE: {mae:.3f} | NMAE: {nmae:5.2f}% | Top10: {top10:5.1f}% | S2: {s2_str} (CV: {cv_r2:.4f})")
            
            # Save updated artifact
            model_save_path = f"models/surrogate_{city}_{target}.joblib"
            joblib.dump({
                'city': city,
                'target': target,
                'model': best_model,
                'best_params': best_params,
                'feature_names': list(X.columns),
                'n_samples': len(df_city),
                'metrics': {
                    'r2': float(r2),
                    'mae': float(mae),
                    'nmae_pct': float(nmae),
                    'top10_overlap_pct': float(top10),
                    's2_status': s2_str,
                    'cv_r2': float(cv_r2)
                }
            }, model_save_path)
            
            aug_metrics.append({
                'city': city,
                'target': target,
                'r2_aug': float(r2),
                'mae_aug': float(mae),
                'nmae_pct_aug': float(nmae),
                'top10_overlap_pct_aug': float(top10),
                's2_status_aug': s2_str,
                'cv_r2_aug': float(cv_r2)
            })
            
    df_aug_metrics = pd.DataFrame(aug_metrics)
    
    # Compare before vs after
    df_orig_metrics = pd.read_csv("data/processed/surrogate_metrics.csv")
    df_cmp = pd.merge(df_orig_metrics, df_aug_metrics, on=['city', 'target'])
    
    cmp_csv = "data/processed/surrogate_metrics_comparison.csv"
    df_cmp.to_csv(cmp_csv, index=False)
    print("\n" + "="*80)
    print("BEFORE (N=1,000) VS AFTER (N=1,500) SURROGATE COMPARISON TABLE")
    print("="*80)
    print(df_cmp[['city', 'target', 'r2', 'r2_aug', 'mae', 'mae_aug', 's2_status', 's2_status_aug']].to_string(index=False))
    
    # Overwrite surrogate_metrics.csv with final production metrics
    df_final = df_aug_metrics.rename(columns={
        'r2_aug': 'r2',
        'mae_aug': 'mae',
        'nmae_pct_aug': 'nmae_pct',
        'top10_overlap_pct_aug': 'top10_overlap_pct',
        's2_status_aug': 's2_status',
        'cv_r2_aug': 'cv_r2'
    })
    df_final.to_csv("data/processed/surrogate_metrics.csv", index=False)
    
    # Overwrite objectives.parquet with full augmented dataset
    df_augmented.to_parquet("data/processed/objectives.parquet", index=False)
    print("\nUpdated data/processed/objectives.parquet and data/processed/surrogate_metrics.csv with N=1,500 models.")
    return df_cmp

if __name__ == "__main__":
    run_augmentation_pipeline(n_new=500, max_workers=10)
