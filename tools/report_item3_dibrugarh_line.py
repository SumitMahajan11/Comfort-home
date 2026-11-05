#!/usr/bin/env python3
"""
tools/report_item3_dibrugarh_line.py

Item 3: Show the exact line of active_learning_history.csv that produced 7.74 vs 5.21.
"""

import os
import sys
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def main():
    csv_path = "data/processed/batch/Dibrugarh/active_learning_history.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    df = pd.read_csv(csv_path)

    print("=" * 120)
    print("ITEM 3: DIBRUGARH ACTIVE LEARNING HISTORY RECONCILIATION")
    print(f"File Path: {csv_path}")
    print("=" * 120)

    print("\n[RAW FILE CONTENTS]")
    for i, l in enumerate(raw_lines):
        print(f"  Line {i+1}: {l.strip()}")

    print("\n" + "=" * 120)
    print("DETAILED LINE 4 (ROUND 3) COLUMN BREAKDOWN:")
    print("=" * 120)
    headers = [h.strip() for h in raw_lines[0].split(",")]
    r3_vals = [v.strip() for v in raw_lines[3].split(",")]

    for col_idx, (h, v) in enumerate(zip(headers, r3_vals)):
        marker = ""
        if h == "sim_time_sec":
            marker = " <--- 77.74 SECONDS (SOURCE OF THE '7.74' DISCREPANCY)"
        elif h == "mean_err_O2_pct":
            marker = " <--- 5.21 % (ACTUAL PERCENT ERROR ON DISK)"
        elif h == "mean_err_O2_abs":
            marker = " (Absolute error: 5.06 kWh/m2)"
        elif h == "median_O2":
            marker = " (Denominator: 97.00 kWh/m2; 5.06 / 97.00 = 5.21%)"
        print(f"  Col {col_idx+1:2d} | {h:18s} = {v:8s}{marker}")

    print("\n" + "=" * 120)
    print("ROOT-CAUSE EXPLANATION:")
    print("=" * 120)
    print("""
1. The line of active_learning_history.csv that produced the discrepancy is Line 4 (Round 3):
   '3,1200,1300,77.74,97.0,0.96,1.65,1.26,2.04,5.06,9.05,5.21,9.33,0.0,0.0,77.77'

2. Column 4 is 'sim_time_sec' with value 77.74 (the simulation wall-clock execution time in seconds).
3. Column 12 is 'mean_err_O2_pct' with value 5.21 (the mean absolute percentage error on O2).
4. In an earlier assistant draft, the agent erroneously extracted Column 4 ('sim_time_sec' = 77.74)
   instead of Column 12 ('mean_err_O2_pct' = 5.21) and misquoted it in markdown prose as '7.74%'.
5. The true value on disk has ALWAYS been 5.21% (computed from mean_err_O2_abs = 5.06 kWh/m2 divided
   by median_O2 = 97.00 kWh/m2).
""")
    print("=" * 120)

if __name__ == "__main__":
    main()

