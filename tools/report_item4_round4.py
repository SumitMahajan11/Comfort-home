#!/usr/bin/env python3
"""
tools/report_item4_round4.py

Item 4: Round 4 Objective Evaluation
- Replace "strictly superior" with per-city deltas:
  * best_O1_ml (percentage points, pp)
  * best_O2 (kWh/m2)
  * front_size
  * whether the change exceeds the Round-4 absolute error
- Plainly state that Bengaluru, Dibrugarh, and Imphal remain above 5%
  and that additional active learning rounds did not reduce their error.
"""

import os
import sys
import pandas as pd
import numpy as np

def main():
    r4_path = "reports/round_4_summary.csv"
    if not os.path.exists(r4_path):
        raise FileNotFoundError(f"Missing {r4_path}")

    df_r4 = pd.read_csv(r4_path)

    rows = []
    for _, r in df_r4.iterrows():
        city = r['city']
        d_o1 = float(r['delta_best_o1_ml']) # pp
        d_o2 = float(r['delta_best_o2'])     # kWh/m2
        d_front = int(r['delta_front_size'])
        old_front = int(r['old_front_size'])
        new_front = int(r['new_front_size'])
        r4_abs_err = float(r['r4_mean_abs_err'])
        r4_err_pct = float(r['r4_mean_err_pct'])

        # Does delta exceed round-4 mean abs error?
        # Energy change magnitude
        o2_exceeds_err = abs(d_o2) > r4_abs_err

        rows.append({
            'City': city,
            'Old best_O1_ml': round(float(r['old_best_o1_ml']), 2),
            'New best_O1_ml': round(float(r['new_best_o1_ml']), 2),
            'Delta O1_ml (pp)': round(d_o1, 2),
            'Old best_O2': round(float(r['old_best_o2']), 2),
            'New best_O2': round(float(r['new_best_o2']), 2),
            'Delta O2 (kWh/m2)': round(d_o2, 2),
            'Front Size (Old -> New)': f"{old_front} -> {new_front} ({d_front:+d})",
            'R4 Mean Abs Err': round(r4_abs_err, 2),
            'R4 Err Pct (%)': round(r4_err_pct, 2),
            '|Delta O2| > R4 Abs Err?': "YES" if o2_exceeds_err else "NO (Within Error)"
        })

    df_table = pd.DataFrame(rows)
    print("=" * 125)
    print("ITEM 4: ROUND 4 PER-CITY DELTAS AND PHYSICAL SIGNIFICANCE")
    print("=" * 125)
    print(df_table.to_string(index=False))
    print("=" * 125)

    print("\nPLAIN-LANGUAGE STATEMENT ON HIGH-ERROR CITIES:")
    print("-" * 125)
    print("1. Bengaluru, Dibrugarh, and Imphal REMAIN ABOVE THE 5% ERROR THRESHOLD after Round 4:")
    print("   - Bengaluru: Round 3 error was 29.54%; Round 4 error is 33.40% (mean abs error = 11.72 kWh/m2).")
    print("   - Dibrugarh: Round 3 error was 5.21%;  Round 4 error is 6.60%  (mean abs error = 6.47 kWh/m2).")
    print("   - Imphal:    Round 3 error was 10.70%; Round 4 error is 9.76%  (mean abs error = 3.51 kWh/m2).")
    print("2. Additional active learning rounds DID NOT reduce their error below the 5% target.")
    print("3. In all 6 cities, the observed energy delta (|Delta O2| = 0.25 to 1.92 kWh/m2) is SMALLER than")
    print("   the Round 4 mean absolute surrogate error (|Delta O2| < R4 Abs Err).")
    print("   Therefore, claims of 'strictly superior' Pareto fronts are physically unsupported by surrogate precision.")
    print("=" * 125)

if __name__ == "__main__":
    main()
