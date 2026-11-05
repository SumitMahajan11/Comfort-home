#!/usr/bin/env python3
"""
tools/print_item5_table.py

Prints the single table required by Item 5:
city, zone, R3_O2, best_O2, pct_better_R3_O2, pp_better_R3_O1_ml (= R3 - best, positive = improvement), front_size.
Flags cities whose numbers changed vs c6f2ff1.
"""

import os
import subprocess
import pandas as pd
import numpy as np

def main():
    cur_df = pd.read_csv("reports/results_30_cities.csv")
    
    # Get c6f2ff1 version of results_30_cities.csv
    cmd = ["git", "show", "c6f2ff1:reports/results_30_cities.csv"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import io
    old_df = pd.read_csv(io.StringIO(res.stdout))
    
    # Set of numeric columns to check for changes
    num_cols = ['R3_O2', 'best_O2', 'pct_better_R3_O2', 'R3_O1_ml', 'best_O1_ml', 'pp_better_R3_O1_ml', 'front_size']
    
    old_map = {}
    for _, r in old_df.iterrows():
        old_map[r['city']] = r

    rows = []
    for _, r in cur_df.iterrows():
        city = r['city']
        zone = r['zone']
        r3_o2 = float(r['R3_O2'])
        best_o2 = float(r['best_O2'])
        pct_better_r3_o2 = float(r['pct_better_R3_O2'])
        r3_o1 = float(r['R3_O1_ml'])
        best_o1 = float(r['best_O1_ml'])
        pp_better_r3_o1 = r3_o1 - best_o1
        front_size = int(r['front_size'])
        
        # Check if numbers changed vs c6f2ff1
        changed = False
        change_reasons = []
        if city in old_map:
            old_r = old_map[city]
            for c in ['R3_O2', 'best_O2', 'pct_better_R3_O2', 'front_size']:
                if abs(float(r[c]) - float(old_r[c])) > 1e-3:
                    changed = True
                    change_reasons.append(f"{c}: {old_r[c]} -> {r[c]}")
            # check O1 metrics
            if abs(r3_o1 - float(old_r['R3_O1_ml'])) > 1e-3 or abs(best_o1 - float(old_r['best_O1_ml'])) > 1e-3:
                changed = True
                change_reasons.append(f"best_O1_ml: {old_r['best_O1_ml']} -> {best_o1}")
        else:
            changed = True
            change_reasons.append("New city")
            
        rows.append({
            'city': city,
            'zone': zone,
            'R3_O2': r3_o2,
            'best_O2': best_o2,
            'pct_better_R3_O2': pct_better_r3_o2,
            'pp_better_R3_O1_ml': pp_better_r3_o1,
            'front_size': front_size,
            'changed_vs_c6f2ff1': "CHANGED" if changed else "SAME",
            'notes': "; ".join(change_reasons) if changed else ""
        })

    out_df = pd.DataFrame(rows)
    
    print("=" * 120)
    print("ITEM 5: RESULTS 30 CITIES SUMMARY TABLE (vs c6f2ff1)")
    print("=" * 120)
    
    # Formatted display
    fmt_df = pd.DataFrame()
    fmt_df['city'] = out_df['city']
    fmt_df['zone'] = out_df['zone']
    fmt_df['R3_O2'] = out_df['R3_O2'].map(lambda x: f"{x:6.2f}")
    fmt_df['best_O2'] = out_df['best_O2'].map(lambda x: f"{x:6.2f}")
    fmt_df['pct_better_R3_O2'] = out_df['pct_better_R3_O2'].map(lambda x: f"{x:5.2f}%")
    fmt_df['pp_better_R3_O1_ml'] = out_df['pp_better_R3_O1_ml'].map(lambda x: f"{x:+6.2f} pp")
    fmt_df['front_size'] = out_df['front_size'].map(lambda x: f"{x:3d}")
    fmt_df['status_vs_c6f2ff1'] = out_df['changed_vs_c6f2ff1']
    
    print(fmt_df.to_string(index=False))
    print("=" * 120)
    
    changed_cities = out_df[out_df['changed_vs_c6f2ff1'] == "CHANGED"]
    print(f"\nTotal cities changed vs c6f2ff1: {len(changed_cities)} of {len(out_df)}")
    for _, r in changed_cities.iterrows():
        print(f"  * {r['city']:15s} [{r['zone']:10s}]: {r['notes']} (Due to Round 4 AL pass)")
    print("=" * 120)

if __name__ == "__main__":
    main()
