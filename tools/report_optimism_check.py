#!/usr/bin/env python3
"""
tools/report_optimism_check.py

Optimism check for all 29 pipeline cities (5 flagships + Chennai + 23 batch):
Reads final_verified_all_100_<city>.parquet and round_3_candidates.parquet.
Computes:
- Mean signed O2 error (predicted minus verified)
- Mean absolute O2 error
- Share of the 100 candidates with a negative signed error (predicted < verified)
Prints unified table and checks if predicted values are saved for Round 1 and Round 2.
"""

import os
import pandas as pd
import numpy as np

def run_optimism_check():
    flagships = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
    batch_cities = sorted([
        d for d in os.listdir('data/processed/batch')
        if os.path.isdir(os.path.join('data/processed/batch', d))
    ])

    all_cities = [(f, f'data/processed/flagship_2011_2025/{f}', 'flagship') for f in flagships] + \
                 [(b, f'data/processed/batch/{b}', 'batch') for b in batch_cities]

    print("=" * 105)
    print("SURROGATE OPTIMISM CHECK ACROSS ALL 29 PIPELINE CITIES (ROUND 3 CANDIDATES)")
    print("Signed Error = Predicted O2 - Verified O2 (Negative = Underpredicted Energy / Optimistic)")
    print("=" * 105)

    rows = []
    r1_r2_saved_status = {}

    for city, cdir, group in all_cities:
        p_ver = os.path.join(cdir, f'final_verified_all_100_{city}.parquet')
        p_cand = os.path.join(cdir, 'round_3_candidates.parquet')

        if not os.path.exists(p_ver) or not os.path.exists(p_cand):
            print(f"Skipping {city}: missing {p_ver} or {p_cand}")
            continue

        df_ver = pd.read_parquet(p_ver)
        df_cand = pd.read_parquet(p_cand)

        merged = pd.merge(df_ver, df_cand, left_on='design_id', right_on='pareto_id', suffixes=('', '_pred'))

        signed_err = merged['pred_O2'] - merged['O2']
        mean_signed_err = float(np.mean(signed_err))
        mean_abs_err = float(np.mean(np.abs(signed_err)))
        share_neg = float(np.mean(signed_err < 0.0) * 100.0)
        n_cands = len(merged)

        rows.append({
            'City': city,
            'Group': group,
            'Candidates': n_cands,
            'Mean Signed O2 Error (kWh/m2)': round(mean_signed_err, 4),
            'Mean Absolute O2 Error (kWh/m2)': round(mean_abs_err, 4),
            'Share with Negative Error (%)': round(share_neg, 2)
        })

        # Check Round 1 and Round 2 candidate paths
        p_r1 = os.path.join(cdir, 'round_1_candidates.parquet')
        p_r2 = os.path.join(cdir, 'round_2_candidates.parquet')
        r1_r2_saved_status[city] = {
            'round_1_candidates_exists': os.path.exists(p_r1),
            'round_2_candidates_exists': os.path.exists(p_r2),
            'r1_path': p_r1,
            'r2_path': p_r2
        }

    df_table = pd.DataFrame(rows)
    print(df_table.to_string(index=False))
    print("=" * 105)

    print("\nROUND 1 AND ROUND 2 PREDICTED VALUES STATUS:")
    all_r1_exist = all(v['round_1_candidates_exists'] for v in r1_r2_saved_status.values())
    all_r2_exist = all(v['round_2_candidates_exists'] for v in r1_r2_saved_status.values())

    print(f"  All 29 cities have round_1_candidates.parquet: {all_r1_exist}")
    print(f"  All 29 cities have round_2_candidates.parquet: {all_r2_exist}")
    print("  File path pattern: <city_dir>/round_1_candidates.parquet and <city_dir>/round_2_candidates.parquet")
    print("  Columns in round_1_candidates / round_2_candidates: ['pred_O1_ml', 'pred_O1_adapt', 'pred_O2', ...]")
    print("  Note: Per-candidate verified simulation outputs for Round 1 and Round 2 were NOT saved as standalone files;")
    print("        only their summary error statistics are preserved in active_learning_history.csv.")

if __name__ == "__main__":
    run_optimism_check()

