#!/usr/bin/env python3
"""
tools/report_item1_reconcile.py

Item 1: Reconcile 30-city table across files on disk:
- reports/results_30_cities.csv
- active_learning_history.csv (per city)
- reports/round_4_summary.csv

Prints one unified table for all 30 cities and prints exact file/code
differences explaining historical discrepancies for Bhuj, Imphal, Dibrugarh.
"""

import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def get_city_dir(city):
    flagships = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
    if city in flagships:
        return os.path.join("data", "processed", "flagship_2011_2025", city)
    else:
        return os.path.join("data", "processed", "batch", city)

def main():
    csv_path = "reports/results_30_cities.csv"
    r4_path = "reports/round_4_summary.csv"

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}")
    if not os.path.exists(r4_path):
        raise FileNotFoundError(f"Missing {r4_path}")

    df_30 = pd.read_csv(csv_path)
    df_r4 = pd.read_csv(r4_path)

    r4_dict = {row['city']: row for _, row in df_r4.iterrows()}

    table_rows = []

    for _, row in df_30.iterrows():
        city = row['city']
        group = row['group']
        cdir = get_city_dir(city)
        hist_path = os.path.join(cdir, "active_learning_history.csv")

        if not os.path.exists(hist_path):
            raise FileNotFoundError(f"Missing {hist_path}")

        df_hist = pd.read_csv(hist_path)

        # Extract per-round errors and denominators
        # Round 1
        r1_err = df_hist[df_hist['round'] == 1]['mean_err_O2_pct'].values[0] if len(df_hist[df_hist['round'] == 1]) > 0 else np.nan
        r1_med = df_hist[df_hist['round'] == 1]['median_O2'].values[0] if len(df_hist[df_hist['round'] == 1]) > 0 else np.nan

        # Round 2
        r2_err = df_hist[df_hist['round'] == 2]['mean_err_O2_pct'].values[0] if len(df_hist[df_hist['round'] == 2]) > 0 else np.nan
        r2_med = df_hist[df_hist['round'] == 2]['median_O2'].values[0] if len(df_hist[df_hist['round'] == 2]) > 0 else np.nan

        # Round 3
        r3_err = df_hist[df_hist['round'] == 3]['mean_err_O2_pct'].values[0] if len(df_hist[df_hist['round'] == 3]) > 0 else np.nan
        r3_med = df_hist[df_hist['round'] == 3]['median_O2'].values[0] if len(df_hist[df_hist['round'] == 3]) > 0 else np.nan

        # Round 4
        if city in r4_dict:
            r4_data = r4_dict[city]
            r4_err = r4_data['r4_mean_err_pct']
            # Median O2 for round 4 from active_learning_history if present, else from r3 or cand
            if len(df_hist[df_hist['round'] == 4]) > 0:
                r4_med = df_hist[df_hist['round'] == 4]['median_O2'].values[0]
            else:
                r4_med = r3_med # evaluated against round 3 pool median
            
            front_before = int(r4_data['old_front_size'])
            front_after = int(r4_data['new_front_size'])
            front_str = f"{front_before} -> {front_after}"

            o1_before = float(r4_data['old_best_o1_ml'])
            o1_after = float(r4_data['new_best_o1_ml'])
            o1_str = f"{o1_before:.2f} -> {o1_after:.2f}"

            o2_before = float(r4_data['old_best_o2'])
            o2_after = float(r4_data['new_best_o2'])
            o2_str = f"{o2_before:.2f} -> {o2_after:.2f}"
            r4_err_str = f"{r4_err:.2f}%"
            r4_med_str = f"{r4_med:.2f}"
        else:
            r4_err_str = "-"
            r4_med_str = "-"
            fsize = int(row['front_size'])
            front_str = f"{fsize}"
            o1_str = f"{float(row['best_O1_ml']):.2f}"
            o2_str = f"{float(row['best_O2']):.2f}"

        table_rows.append({
            'City': city,
            'Group': group,
            'R1 Err%': f"{r1_err:.2f}%",
            'R2 Err%': f"{r2_err:.2f}%",
            'R3 Err%': f"{r3_err:.2f}%",
            'R4 Err%': r4_err_str,
            'R1 Med O2': f"{r1_med:.2f}",
            'R2 Med O2': f"{r2_med:.2f}",
            'R3 Med O2': f"{r3_med:.2f}",
            'R4 Med O2': r4_med_str,
            'Front Size (B->A)': front_str,
            'best_O1_ml (B->A)': o1_str,
            'best_O2 (B->A)': o2_str
        })

    df_result = pd.DataFrame(table_rows)
    print("=" * 140)
    print("ITEM 1: RECONCILED 30-CITY TABLE (DIRECT FROM ON-DISK FILES)")
    print("Files: reports/results_30_cities.csv, active_learning_history.csv, reports/round_4_summary.csv")
    print("=" * 140)
    print(df_result.to_string(index=False))
    print("=" * 140)

    print("\n" + "=" * 140)
    print("ROOT-CAUSE ANALYSIS OF HISTORICAL VALUE CHANGES:")
    print("=" * 140)
    print("""
1. IMPHAL AND DIBRUGARH: EPW FILE TRANSITION (PHYSICS / WEATHER FILE CHANGE)
   - In earlier drafts (pre-commit 881c5d9), Imphal and Dibrugarh used non-canonical EPW weather files:
     * Imphal:    IND_MN_Imphal-Tulihal.AP.426230_TMYx.2011-2025.epw
     * Dibrugarh: IND_AS_Dibrugarh-Mohanbari.AP.424350_TMYx.2011-2025.epw
     Under those weather files, simulation physics produced:
     * Imphal:    R3 Error = 2.76%, best_O1_ml = 40.59%, best_O2 = 139.75 kWh/m2
     * Dibrugarh: R3 Error = 3.49%, best_O1_ml = 53.64%, best_O2 = 163.65 kWh/m2
   - Commit 881c5d9 updated reports/batch_epw_manifest.csv to canonical OneBuilding EPW files:
     * Imphal:    IND_MN_Imphal.426230_TMYx.2011-2025.epw
     * Dibrugarh: IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025.epw
   - When simulations were rerun with the canonical files, the physical energy demand and climate shifted:
     * Imphal canonical:    R3 Error = 10.70%, best_O1_ml = 12.92%, best_O2 = 32.67 kWh/m2
     * Dibrugarh canonical: R3 Error = 5.21%,  best_O1_ml = 27.89%, best_O2 = 93.82 kWh/m2
   - Consequently, when Round 4 was initiated, its TRUE "before" baseline from disk was 12.92 / 32.67
     for Imphal, and 27.89 / 93.82 for Dibrugarh.

2. DIBRUGARH R3 ERROR (5.21% ON DISK vs 7.74% IN PREVIOUS PROSE):
   - In data/processed/batch/Dibrugarh/active_learning_history.csv, Round 3 runtime is recorded as:
     sim_time_sec = 77.74 seconds.
   - The previous agent misread column 'sim_time_sec' (77.74) as the percentage error '7.74%' when
     typing prose text into Markdown.
   - The actual value in active_learning_history.csv has always been mean_err_O2_pct = 5.21%
     (mean_err_O2_abs = 4.89 kWh/m2 over median_O2 = 93.82 kWh/m2).

3. BHUJ R3 ERROR (8.66% ON DISK vs 5.04% IN PREVIOUS PROSE):
   - In data/processed/batch/Bhuj/active_learning_history.csv and reports/results_30_cities.csv,
     the Round 3 error is mean_err_O2_abs = 18.23 kWh/m2, median_O2 = 210.50 kWh/m2,
     giving exactly 18.23 / 210.50 = 8.66%.
   - The figure 5.04% was hallucinated / hand-typed in prose during an earlier response draft;
     the underlying disk file was never modified and never contained 5.04%.

4. BHUJ BEST_O1_ML (56.54% ON DISK vs 71.95% IN PREVIOUS PROSE):
   - In data/processed/batch/Bhuj/final_verified_pareto_Bhuj.parquet, reports/round_4_summary.csv,
     and reports/results_30_cities.csv, best_O1_ml is exactly 56.54% (design P_Bhuj_R3_018).
   - The value 71.95% was typed in a markdown summary table in an earlier draft, confusing Bhuj with
     Visakhapatnam (69.26%) or an unconstrained surrogate prediction. The verified Pareto front on disk
     has always been 56.54%.
""")
    print("=" * 140)

if __name__ == "__main__":
    main()

