#!/usr/bin/env python3
"""
tools/run_second_al_pass.py

Executes a second active learning pass (Round 4) for error-flagged cities:
- Retrains surrogates on all prior verified designs (pilot + AL rounds 1, 2, 3 = 1300 designs)
- Runs NSGA-II to generate round-4 candidates (100 designs)
- Verifies round-4 candidates via EnergyPlus physical simulation (free-running + ideal-loads)
- Computes round-4 signed and absolute O2 errors
- Checks whether verified Pareto front changed (best O1_ml, best O2, front size)
- Saves per-round verified outputs as compact parquet files (round_1_verified, round_2_verified, round_3_verified, round_4_verified) without pruning them
- Logs wall-clock time in minutes per city.
"""

import os
import sys
import time
import argparse
import numpy as np
import pandas as pd
from datetime import datetime

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.run_city_pipeline import (
    CityPipeline,
    run_nsga2,
    compute_non_dominated_front,
    prepare_features,
    TARGETS,
    MAX_WORKERS
)
from src.models.train_surrogates import tune_surrogate_xgboost
from sklearn.model_selection import train_test_split

FLAGSHIPS = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']

def resolve_city_dir(city_name):
    if city_name in FLAGSHIPS:
        return f"data/processed/flagship_2011_2025/{city_name}"
    return f"data/processed/batch/{city_name}"

def run_round_4_for_city(city_name, batch_dir=None, manifest_path=None):
    print("\n" + "=" * 100)
    print(f"RUNNING SECOND AL PASS (ROUND 4): {city_name.upper()}")
    print("=" * 100)
    t_city_0 = time.time()

    cdir = batch_dir or resolve_city_dir(city_name)
    pipeline = CityPipeline(city_name=city_name, batch_dir=cdir, manifest_path=manifest_path)

    # 1. Load Pilot
    p_obj = os.path.join(cdir, f"objectives_{city_name}.parquet")
    df_pilot = pd.read_parquet(p_obj)
    print(f"Loaded Pilot objectives: {len(df_pilot)} designs.")

    # 2. Check / simulate Round 1 verified
    p_r1_ver = os.path.join(cdir, "round_1_verified.parquet")
    if os.path.exists(p_r1_ver):
        df_r1_ver = pd.read_parquet(p_r1_ver)
        print(f"Loaded existing round_1_verified.parquet: {len(df_r1_ver)} designs.")
    else:
        p_r1_cand = os.path.join(cdir, "round_1_candidates.parquet")
        df_r1_cand = pd.read_parquet(p_r1_cand).iloc[:100]
        print(f"Simulating Round 1 candidates ({len(df_r1_cand)} designs)...")
        sim_dir_r1 = os.path.join(cdir, "round_1_sims")
        df_r1_ver = pipeline.simulate_designs(df_r1_cand, sim_dir_r1, id_col='pareto_id')
        df_r1_ver['epw_path'] = pipeline.epw_path
        df_r1_ver['epw_sha256'] = pipeline.epw_sha256
        df_r1_ver.to_parquet(p_r1_ver, index=False)
        print(f"Saved {p_r1_ver} ({len(df_r1_ver)} designs).")

    # 3. Check / simulate Round 2 verified
    p_r2_ver = os.path.join(cdir, "round_2_verified.parquet")
    if os.path.exists(p_r2_ver):
        df_r2_ver = pd.read_parquet(p_r2_ver)
        print(f"Loaded existing round_2_verified.parquet: {len(df_r2_ver)} designs.")
    else:
        p_r2_cand = os.path.join(cdir, "round_2_candidates.parquet")
        df_r2_cand = pd.read_parquet(p_r2_cand).iloc[:100]
        print(f"Simulating Round 2 candidates ({len(df_r2_cand)} designs)...")
        sim_dir_r2 = os.path.join(cdir, "round_2_sims")
        df_r2_ver = pipeline.simulate_designs(df_r2_cand, sim_dir_r2, id_col='pareto_id')
        df_r2_ver['epw_path'] = pipeline.epw_path
        df_r2_ver['epw_sha256'] = pipeline.epw_sha256
        df_r2_ver.to_parquet(p_r2_ver, index=False)
        print(f"Saved {p_r2_ver} ({len(df_r2_ver)} designs).")

    # 4. Check Round 3 verified
    p_r3_ver = os.path.join(cdir, "round_3_verified.parquet")
    p_r3_orig = os.path.join(cdir, f"final_verified_all_100_{city_name}.parquet")
    if os.path.exists(p_r3_ver):
        df_r3_ver = pd.read_parquet(p_r3_ver)
    elif os.path.exists(p_r3_orig):
        df_r3_ver = pd.read_parquet(p_r3_orig)
        df_r3_ver['epw_path'] = pipeline.epw_path
        df_r3_ver['epw_sha256'] = pipeline.epw_sha256
        df_r3_ver.to_parquet(p_r3_ver, index=False)
    else:
        p_r3_cand = os.path.join(cdir, "round_3_candidates.parquet")
        df_r3_cand = pd.read_parquet(p_r3_cand).iloc[:100]
        sim_dir_r3 = os.path.join(cdir, "round_3_sims")
        df_r3_ver = pipeline.simulate_designs(df_r3_cand, sim_dir_r3, id_col='pareto_id')
        df_r3_ver['epw_path'] = pipeline.epw_path
        df_r3_ver['epw_sha256'] = pipeline.epw_sha256
        df_r3_ver.to_parquet(p_r3_ver, index=False)

    print(f"Loaded round_3_verified.parquet: {len(df_r3_ver)} designs.")

    # 5. Form training pool for Round 4
    pool_r4 = pd.concat([df_pilot, df_r1_ver, df_r2_ver, df_r3_ver], ignore_index=True)
    print(f"Total training pool for Round 4: {len(pool_r4)} designs.")

    # 6. Check existing Pareto front before Round 4
    p_pareto = os.path.join(cdir, f"final_verified_pareto_{city_name}.parquet")
    df_pareto_old = pd.read_parquet(p_pareto)
    old_best_o1_ml = float(df_pareto_old['O1_ml'].min())
    old_best_o2 = float(df_pareto_old['O2'].min())
    old_front_size = len(df_pareto_old)

    # 7. Retrain surrogates
    t_retrain_0 = time.time()
    print("Retraining XGBoost surrogates with Optuna (30 trials, 5-fold CV)...")
    surrogates, _ = pipeline.train_surrogates(pool_r4, seed=42)
    t_retrain_sec = time.time() - t_retrain_0
    print(f"Surrogates retrained in {t_retrain_sec:.2f} s ({t_retrain_sec/60:.2f} min).")

    # 8. Run NSGA-II to generate Round 4 candidates
    t_nsga_0 = time.time()
    print("Running NSGA-II (pop 100, gen 100, seed 42, clamped)...")
    df_cand4 = run_nsga2(surrogates, seed=42, city_name=city_name, n_gen=pipeline.nsga2_gen, pop_size=pipeline.nsga2_pop)
    p_cand4 = os.path.join(cdir, "round_4_candidates.parquet")
    df_cand4['epw_path'] = pipeline.epw_path
    df_cand4['epw_sha256'] = pipeline.epw_sha256
    df_cand4.to_parquet(p_cand4, index=False)
    t_nsga_sec = time.time() - t_nsga_0
    print(f"Generated {len(df_cand4)} Round 4 candidates in {t_nsga_sec:.2f} s. Saved {p_cand4}.")

    # 9. Physically simulate / verify Round 4 candidates
    t_sim_0 = time.time()
    print("Dispatching physical EnergyPlus simulations for 100 Round 4 candidates...")
    sim_dir_r4 = os.path.join(cdir, "round_4_sims")
    df_to_sim4 = df_cand4.iloc[:100]
    df_r4_ver = pipeline.simulate_designs(df_to_sim4, sim_dir_r4, id_col='pareto_id')
    t_sim_sec = time.time() - t_sim_0
    p_r4_ver = os.path.join(cdir, "round_4_verified.parquet")
    df_r4_ver['epw_path'] = pipeline.epw_path
    df_r4_ver['epw_sha256'] = pipeline.epw_sha256
    df_r4_ver.to_parquet(p_r4_ver, index=False)
    print(f"Verified {len(df_r4_ver)} Round 4 candidates in {t_sim_sec:.2f} s. Saved compact parquet {p_r4_ver}.")

    # 10. Compute Round 4 error metrics
    merged4 = pd.merge(df_r4_ver, df_cand4, left_on='design_id', right_on='pareto_id', suffixes=('', '_pred'))
    signed_err_o2 = merged4['pred_O2'] - merged4['O2']
    abs_err_o2 = np.abs(signed_err_o2)
    median_o2 = float(np.median(merged4['O2']))
    mean_signed_err = float(np.mean(signed_err_o2))
    mean_abs_err = float(np.mean(abs_err_o2))
    mean_err_pct = (mean_abs_err / median_o2 * 100.0) if median_o2 > 0 else 0.0
    share_neg = float(np.mean(signed_err_o2 < 0) * 100.0)

    # Errors on O1_ml and O1_adapt
    err_o1_ml = np.abs(merged4['O1_ml'] - merged4['pred_O1_ml'])
    err_o1_ad = np.abs(merged4['O1_adapt'] - merged4['pred_O1_adapt'])

    print(f"\nRound 4 Error Summary ({city_name}):")
    print(f"  Mean Signed O2 Error:   {mean_signed_err:+.3f} kWh/m2")
    print(f"  Mean Absolute O2 Error: {mean_abs_err:.3f} kWh/m2")
    print(f"  Median O2:              {median_o2:.2f} kWh/m2")
    print(f"  Mean O2 Error %:        {mean_err_pct:.2f}%")
    print(f"  Share Negative (Pred<Ver): {share_neg:.1f}%")
    print(f"  O1_ml Mean Error:       {np.mean(err_o1_ml):.2f} pp")
    print(f"  O1_adapt Mean Error:    {np.mean(err_o1_ad):.2f} pp")

    # Update active_learning_history.csv
    hist_p = os.path.join(cdir, "active_learning_history.csv")
    df_hist = pd.read_csv(hist_p)
    # Check if round 4 already recorded
    if 4 not in df_hist['round'].values:
        rec4 = {
            'round': 4,
            'pool_size_before': len(pool_r4),
            'pool_size_after': len(pool_r4) + len(df_r4_ver),
            'sim_time_sec': round(t_sim_sec, 2),
            'median_O2': round(median_o2, 2),
            'mean_err_O1_ml': round(float(np.mean(err_o1_ml)), 2),
            'max_err_O1_ml': round(float(np.max(err_o1_ml)), 2),
            'mean_err_O1_adapt': round(float(np.mean(err_o1_ad)), 2),
            'max_err_O1_adapt': round(float(np.max(err_o1_ad)), 2),
            'mean_err_O2_abs': round(mean_abs_err, 2),
            'max_err_O2_abs': round(float(np.max(abs_err_o2)), 2),
            'mean_err_O2_pct': round(mean_err_pct, 2),
            'max_err_O2_pct': round(float(np.max(abs_err_o2) / median_o2 * 100.0), 2),
            'retrain_time_sec': round(t_retrain_sec, 2),
            'nsga_time_sec': round(t_nsga_sec, 2),
            'epw_path': pipeline.epw_path,
            'epw_sha256': pipeline.epw_sha256,
            'wall_time_sec': round(time.time() - t_city_0, 2)
        }
        df_hist = pd.concat([df_hist, pd.DataFrame([rec4])], ignore_index=True)
        df_hist.to_csv(hist_p, index=False)

    # 11. Compute updated verified Pareto front
    all_verified = pd.concat([df_pareto_old, df_r1_ver, df_r2_ver, df_r3_ver, df_r4_ver], ignore_index=True)
    df_pareto_new = compute_non_dominated_front(all_verified)
    
    # Save updated Pareto front
    df_pareto_new['epw_path'] = pipeline.epw_path
    df_pareto_new['epw_sha256'] = pipeline.epw_sha256
    df_pareto_new.to_parquet(p_pareto, index=False)
    csv_p = os.path.join(cdir, f"final_verified_pareto_{city_name}.csv")
    df_pareto_new.to_csv(csv_p, index=False)

    new_best_o1_ml = float(df_pareto_new['O1_ml'].min())
    new_best_o2 = float(df_pareto_new['O2'].min())
    new_front_size = len(df_pareto_new)

    delta_o1_ml = new_best_o1_ml - old_best_o1_ml
    delta_o2 = new_best_o2 - old_best_o2
    delta_size = new_front_size - old_front_size
    front_changed = (delta_size != 0) or (abs(delta_o1_ml) > 1e-4) or (abs(delta_o2) > 1e-4)

    t_total_min = (time.time() - t_city_0) / 60.0

    print(f"\nPareto Front Comparison ({city_name}):")
    print(f"  Best O1_ml: Old = {old_best_o1_ml:.2f}%, New = {new_best_o1_ml:.2f}% (Delta = {delta_o1_ml:+.2f} pp)")
    print(f"  Best O2:    Old = {old_best_o2:.2f} kWh/m2, New = {new_best_o2:.2f} kWh/m2 (Delta = {delta_o2:+.2f} kWh/m2)")
    print(f"  Front Size: Old = {old_front_size}, New = {new_front_size} (Delta = {delta_size:+d})")
    print(f"  Front Changed? {front_changed}")
    print(f"  Total Round 4 Execution Time: {t_total_min:.2f} minutes")

    return {
        'city': city_name,
        'old_best_o1_ml': old_best_o1_ml,
        'new_best_o1_ml': new_best_o1_ml,
        'delta_best_o1_ml': delta_o1_ml,
        'old_best_o2': old_best_o2,
        'new_best_o2': new_best_o2,
        'delta_best_o2': delta_o2,
        'old_front_size': old_front_size,
        'new_front_size': new_front_size,
        'delta_front_size': delta_size,
        'front_changed': front_changed,
        'r4_mean_signed_err': round(mean_signed_err, 3),
        'r4_mean_abs_err': round(mean_abs_err, 3),
        'r4_mean_err_pct': round(mean_err_pct, 2),
        'r4_share_neg': round(share_neg, 1),
        'minutes': round(t_total_min, 2)
    }

def main():
    parser = argparse.ArgumentParser(description="Run Second AL Pass (Round 4) for flagged cities.")
    parser.add_argument("--cities", nargs="+", default=None, help="List of cities to run")
    args = parser.parse_args()

    # Default to cities flagged by flag_error_high:
    # Bengaluru, Bhuj, Dibrugarh, Imphal, Port Blair, Visakhapatnam
    target_cities = args.cities if args.cities else [
        "Bengaluru", "Bhuj", "Dibrugarh", "Imphal", "Port Blair", "Visakhapatnam"
    ]

    print("=" * 100)
    print("SECOND AL PASS ORCHESTRATION")
    print(f"Target cities: {target_cities}")
    print("=" * 100)

    summary_rows = []
    for c in target_cities:
        res = run_round_4_for_city(c)
        summary_rows.append(res)

    df_sum = pd.DataFrame(summary_rows)
    print("\n" + "=" * 120)
    print("SECOND AL PASS SUMMARY REPORT (ROUND 4)")
    print("=" * 120)
    print(df_sum.to_string(index=False))

    out_csv = "reports/round_4_summary.csv"
    df_sum.to_csv(out_csv, index=False)
    print(f"\nSaved summary table to {out_csv}")

if __name__ == "__main__":
    main()

