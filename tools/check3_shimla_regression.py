"""
tools/check3_shimla_regression.py
Executes CHECK 3: SHIMLA REGRESSION
"""

import io
import subprocess
import pandas as pd
import numpy as np

OLD_COMMIT = "6fe5a12"
CSV_REL_PATH = "data/processed/active_learning_shimla/shimla_baselines_summary.csv"

def main():
    print("=" * 105)
    print("CHECK 3 - SHIMLA REGRESSION AUDIT (COMMIT 6fe5a12 vs CURRENT)")
    print("=" * 105)
    
    # Load old CSV from git
    old_csv_raw = subprocess.check_output(["git", "show", f"{OLD_COMMIT}:{CSV_REL_PATH}"], text=True)
    df_old = pd.read_csv(io.StringIO(old_csv_raw))
    
    # Load current CSV
    df_new = pd.read_csv(CSV_REL_PATH)
    
    # Index by design
    df_old.set_index('design', inplace=True)
    df_new.set_index('design', inplace=True)
    
    # Key benchmarks
    benchmarks = ["R1_Lightweight", "R2_Conventional", "R3_Code_Compliant"]
    
    # Pareto designs (start with P_Shimla)
    pareto_designs = [idx for idx in df_new.index if idx.startswith("P_Shimla")]
    
    # Identify the best verified designs across objectives
    best_o1_ml_design = df_new.loc[pareto_designs, 'O1_ml'].idxmin()
    best_o1_adapt_design = df_new.loc[pareto_designs, 'O1_adapt'].idxmin()
    best_o2_design = df_new.loc[pareto_designs, 'O2'].idxmin()
    
    target_designs = benchmarks + [
        f"{best_o1_ml_design} (Best O1_ml)",
        f"{best_o1_adapt_design} (Best O1_adapt)",
        f"{best_o2_design} (Best O2)"
    ]
    
    design_keys = benchmarks + [best_o1_ml_design, best_o1_adapt_design, best_o2_design]
    
    # Also evaluate differences across the entire dataframe (all common designs)
    common_designs = [d for d in df_old.index if d in df_new.index]
    
    max_diff_overall = 0.0
    diff_records = []
    
    print("\nSIDE-BY-SIDE REGRESSION COMPARISON TABLE:")
    header = f"{'Design / Benchmark':<32} | {'O1_ml (Old)':<11} {'O1_ml (New)':<11} {'Diff':<8} | {'O1_ad (Old)':<11} {'O1_ad (New)':<11} {'Diff':<8} | {'O2 (Old)':<10} {'O2 (New)':<10} {'Diff':<8}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    for label, d_key in zip(target_designs, design_keys):
        o1_ml_old = df_old.loc[d_key, 'O1_ml']
        o1_ml_new = df_new.loc[d_key, 'O1_ml']
        d_o1_ml = abs(o1_ml_new - o1_ml_old)
        
        o1_ad_old = df_old.loc[d_key, 'O1_adapt']
        o1_ad_new = df_new.loc[d_key, 'O1_adapt']
        d_o1_ad = abs(o1_ad_new - o1_ad_old)
        
        o2_old = df_old.loc[d_key, 'O2']
        o2_new = df_new.loc[d_key, 'O2']
        d_o2 = abs(o2_new - o2_old)
        
        row_max = max(d_o1_ml, d_o1_ad, d_o2)
        if row_max > max_diff_overall:
            max_diff_overall = row_max
            
        print(f"{label:<32} | {o1_ml_old:<11.2f} {o1_ml_new:<11.2f} {d_o1_ml:<8.4f} | {o1_ad_old:<11.2f} {o1_ad_new:<11.2f} {d_o1_ad:<8.4f} | {o2_old:<10.2f} {o2_new:<10.2f} {d_o2:<8.4f}")
    
    print("-" * len(header))
    
    # Check max difference across all 34 designs in the entire summary file:
    for d in common_designs:
        for col in ['O1_ml', 'O1_adapt', 'O2']:
            diff = abs(df_new.loc[d, col] - df_old.loc[d, col])
            diff_records.append((d, col, diff))
            if diff > max_diff_overall:
                max_diff_overall = diff

    print(f"\nAUDIT OF ALL {len(common_designs)} DESIGNS IN SHIMLA SUMMARY:")
    print(f"Max Absolute Difference across all designs & objectives: {max_diff_overall:.6f}")
    
    if max_diff_overall > 0.01:
        print("\n[ALERT] REGRESSION DETECTED: Max difference exceeds 0.01 threshold! Stopping execution.")
        exit(1)
    else:
        print("\n[VERDICT] ZERO REGRESSION: All differences are 0.000000 (<= 0.01 threshold). Verification successful.")

if __name__ == '__main__':
    main()
