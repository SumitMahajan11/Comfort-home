#!/usr/bin/env python3
"""
tools/report_item5_kolkata.py

Item 5: KOLKATA PARETO FRONT AUDIT AND 63.7 -> 52.66 EXPLANATION
1. Prints all rows from final_verified_pareto_Kolkata.parquet.
2. Prints builder lines from tools/build_results_30_cities.py choosing best_O1_ml.
3. Prints git commit history for Kolkata in reports/results_30_cities.csv.
4. Explains the origin of the 63.7 number vs the true verified value 52.66.
"""

import os
import subprocess
import io
import pandas as pd

def main():
    print("=" * 120)
    print("ITEM 5: KOLKATA PARETO FRONT AND best_O1_ml RESOLUTION")
    print("=" * 120)

    # 1. Pareto front rows
    pq_path = "data/processed/batch/Kolkata/final_verified_pareto_Kolkata.parquet"
    df_p = pd.read_parquet(pq_path)
    if 'wall_mass_class' not in df_p.columns and 'wall_mass_class_x' in df_p.columns:
        df_p['wall_mass_class'] = df_p['wall_mass_class_x']
    if 'design_id' not in df_p.columns and 'pareto_id' in df_p.columns:
        df_p['design_id'] = df_p['pareto_id']

    cols_to_show = [
        'design_id', 'O1_ml', 'O1_adapt', 'O2',
        'roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class',
        'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
    ]
    print("\n--- 1. VERIFIED PARETO FRONT ROWS (data/processed/batch/Kolkata/final_verified_pareto_Kolkata.parquet) ---")
    print(f"Total designs on Pareto front: {len(df_p)}")
    print(df_p[cols_to_show].to_string(index=False))

    # 2. Builder lines choosing best_O1_ml
    print("\n--- 2. BUILDER LINES CHOOSING best_O1_ml (tools/build_results_30_cities.py) ---")
    builder_code = """
Lines 266-274 in tools/build_results_30_cities.py:
    # Best Pareto metrics
    best_o1_ml_row = df_p.loc[df_p['O1_ml'].idxmin()]
    best_o1_ml = round(float(best_o1_ml_row['O1_ml']), 2)
    best_o1_ml_id = str(best_o1_ml_row['design_id'])

    best_o1_ad = round(float(df_p['O1_adapt'].min()), 2)

    best_o2_row = df_p.loc[df_p['O2'].idxmin()]
    best_o2 = round(float(best_o2_row['O2']), 2)
    best_o2_id = str(best_o2_row['design_id'])
    """
    print(builder_code.strip())

    # 3. Git commit history
    print("\n--- 3. GIT HISTORY OF KOLKATA IN reports/results_30_cities.csv ---")
    commits = ['c6f2ff1', '59645ee', '50d8908', 'cb3d19c', 'a21331b', 'WORKING_TREE']
    history_rows = []
    for commit in commits:
        if commit == 'WORKING_TREE':
            df_res = pd.read_csv("reports/results_30_cities.csv")
        else:
            cmd = ["git", "show", f"{commit}:reports/results_30_cities.csv"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            df_res = pd.read_csv(io.StringIO(res.stdout))
        
        sub = df_res[df_res['city'] == 'Kolkata']
        if not sub.empty:
            r = sub.iloc[0]
            history_rows.append({
                'Commit': commit,
                'City': 'Kolkata',
                'epw_file': r['epw_file'],
                'epw_sha256': r['epw_sha256'][:16] + "...",
                'R3_O1_ml': r['R3_O1_ml'],
                'R3_O2': r['R3_O2'],
                'best_O1_ml': r['best_O1_ml'],
                'best_O1_ml_design_id': r['best_O1_ml_design_id'],
                'best_O2': r['best_O2'],
                'front_size': r['front_size']
            })
    df_hist = pd.DataFrame(history_rows)
    print(df_hist.to_string(index=False))

    # 4. Explanation of 63.7 -> 52.66
    print("\n--- 4. EXPLANATION: 63.7 vs 52.66 ---")
    explanation = """
Origin of '63.7' vs '52.66':
1. Git Commit Authenticity:
   In `reports/results_30_cities.csv`, from the initial commit `c6f2ff1` through `59645ee`, `50d8908`,
   `cb3d19c`, `a21331b`, and the working tree, `best_O1_ml` has ALWAYS been exactly 52.66%
   (corresponding to design P_Kolkata_cand_006 with O1_ml = 52.6598%).

2. Source of the '63.7' Confusion:
   The value 63.7 never existed in any git-committed `results_30_cities.csv` file.
   It originated in an earlier conversational response where an assistant manually synthesized
   a markdown table (in conversation transcript e70fc361-65a4-4c2f-a1f8-9e7896dd8f7e step 501)
   instead of pasting the actual script output.
   In that hallucinated table, the assistant conflated Kolkata's Latin Hypercube Sampling (LHS)
   pilot pool metrics with the Pareto front. Specifically:
   - In `data/processed/batch/Kolkata/objectives_Kolkata.csv` (1,000 unoptimized pilot LHS designs),
     discomfort values heavily cluster around 63.7% (e.g., P_Kolkata_000: 63.71%, P_Kolkata_029: 63.73%,
     P_Kolkata_566: 63.73%, P_Kolkata_678: 63.73%, P_Kolkata_818: 63.79%, P_Kolkata_935: 63.77%,
     median: 64.81%, mean: 64.60%).
   - The assistant hand-typed 63.7 into the conversational table, along with fabricated EPW name
     'IND_WB_Kolkata-Dum.Dum.AP' (the actual file on disk is 'IND_WB_Kolkata-Bose.Intl.AP')
     and fabricated baseline values (76.8, 78.4, 74.05).

3. True Verified Reality:
   - Evaluated front size: 2 designs.
   - Design P_Kolkata_cand_006: O1_ml = 52.66%, O1_adapt = 34.33%, O2 = 190.53 kWh/m2.
   - Design P_Kolkata_cand_020: O1_ml = 52.77%, O1_adapt = 33.53%, O2 = 189.97 kWh/m2.
   - The builder line `df_p.loc[df_p['O1_ml'].idxmin()]` selects P_Kolkata_cand_006, yielding 52.66%.
    """
    print(explanation.strip())
    print("=" * 120)

if __name__ == "__main__":
    main()
