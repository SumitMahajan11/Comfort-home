#!/usr/bin/env python3
"""
tools/report_item4_offset.py

Item 4: O1_ml OFFSET ANALYSIS FOR LEH AND BHUBANESWAR
For Leh and Bhubaneswar:
1. Prints O1_ml, warm_ml, cool_ml, O1_adapt at the old (c6f2ff1, 59645ee, 50d8908, cb3d19c)
   and current (a21331b, working tree) commits.
2. Extracts baseline and Pareto design components (warm discomfort vs cold discomfort).
3. Shows exactly which column the builder (tools/build_results_30_cities.py) reads.
"""

import subprocess
import io
import pandas as pd
import os

COMMITS = ['c6f2ff1', '59645ee', '50d8908', 'cb3d19c', 'a21331b', 'WORKING_TREE']
CITIES = ['Leh', 'Bhubaneswar']

def get_results_df(commit):
    if commit == 'WORKING_TREE':
        return pd.read_csv("reports/results_30_cities.csv")
    else:
        cmd = ["git", "show", f"{commit}:reports/results_30_cities.csv"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return pd.read_csv(io.StringIO(res.stdout))

def main():
    print("=" * 120)
    print("ITEM 4: O1_ml OFFSET ANALYSIS FOR LEH AND BHUBANESWAR")
    print("=" * 120)

    print("\n--- PART 1: RESULTS_30_CITIES.CSV ACROSS COMMITS ---")
    rows = []
    for commit in COMMITS:
        df = get_results_df(commit)
        for city in CITIES:
            sub = df[df['city'] == city]
            if not sub.empty:
                r = sub.iloc[0]
                rows.append({
                    'Commit': commit,
                    'City': city,
                    'R1_O1_ml': r.get('R1_O1_ml', 'N/A'),
                    'R2_O1_ml': r.get('R2_O1_ml', 'N/A'),
                    'R3_O1_ml': r.get('R3_O1_ml', 'N/A'),
                    'best_O1_ml': r.get('best_O1_ml', 'N/A'),
                    'best_O1_adapt': r.get('best_O1_adapt', 'N/A'),
                    'best_O2': r.get('best_O2', 'N/A')
                })
    df_history = pd.DataFrame(rows)
    print(df_history.to_string(index=False))

    print("\n--- PART 2: BASELINE COMPONENT BREAKDOWN (warm_ml vs cool_ml vs O1_adapt) ---")
    base_rows = []
    for city in CITIES:
        csv_path = f"data/processed/batch/{city}/baseline_results.csv"
        df_b = pd.read_csv(csv_path)
        for _, r in df_b.iterrows():
            base_rows.append({
                'City': city,
                'Design': r['design_id'],
                'O1_ml (%)': round(float(r['O1_ml']), 4),
                'warm_ml (%)': round(float(r['warm_ml']), 4),
                'cool_ml (%)': round(float(r['cool_ml']), 4),
                'O1_adapt (%)': round(float(r['O1_adapt']), 4),
                'O2 (kWh/m2)': round(float(r['O2']), 2)
            })
    df_base = pd.DataFrame(base_rows)
    print(df_base.to_string(index=False))

    print("\n--- PART 3: PARETO FRONT BEST DESIGNS BREAKDOWN ---")
    pareto_rows = []
    for city in CITIES:
        pq_path = f"data/processed/batch/{city}/final_verified_pareto_{city}.parquet"
        df_p = pd.read_parquet(pq_path)
        if 'wall_mass_class' not in df_p.columns and 'wall_mass_class_x' in df_p.columns:
            df_p['wall_mass_class'] = df_p['wall_mass_class_x']
        if 'design_id' not in df_p.columns and 'pareto_id' in df_p.columns:
            df_p['design_id'] = df_p['pareto_id']
            
        best_o1_row = df_p.loc[df_p['O1_ml'].idxmin()]
        best_o2_row = df_p.loc[df_p['O2'].idxmin()]
        
        picks = [('best_O1_ml_design', best_o1_row), ('best_O2_design', best_o2_row)]
        for label, r in picks:
            # Check if warm_ml / cool_ml exist in df_p
            w_ml = round(float(r['warm_ml']), 4) if 'warm_ml' in r else 'N/A'
            c_ml = round(float(r['cool_ml']), 4) if 'cool_ml' in r else 'N/A'
            pareto_rows.append({
                'City': city,
                'Selection': label,
                'Design_ID': r['design_id'],
                'O1_ml (%)': round(float(r['O1_ml']), 4),
                'warm_ml (%)': w_ml,
                'cool_ml (%)': c_ml,
                'O1_adapt (%)': round(float(r['O1_adapt']), 4),
                'O2 (kWh/m2)': round(float(r['O2']), 2)
            })
    df_par = pd.DataFrame(pareto_rows)
    print(df_par.to_string(index=False))

    print("\n--- PART 4: WHICH COLUMN THE BUILDER READS ---")
    builder_snippet = """
In `tools/build_results_30_cities.py`:
Lines 253-263:
    r1_o1_ml = round(float(r1_row['O1_ml']), 2)   # <--- reads 'O1_ml' directly
    r2_o1_ml = round(float(r2_row['O1_ml']), 2)   # <--- reads 'O1_ml' directly
    r3_o1_ml = round(float(r3_row['O1_ml']), 2)   # <--- reads 'O1_ml' directly

Lines 266-271:
    best_o1_ml_row = df_p.loc[df_p['O1_ml'].idxmin()]
    best_o1_ml = round(float(best_o1_ml_row['O1_ml']), 2)  # <--- reads 'O1_ml' directly
    best_o1_ad = round(float(df_p['O1_adapt'].min()), 2)   # <--- reads 'O1_adapt' directly

    Column Read Summary:
    1. For ML Discomfort: The builder reads column 'O1_ml' (which is warm_ml + cool_ml).
       - In Leh (cold alpine climate): warm_ml = 0.0, so O1_ml == cool_ml (100% cold discomfort).
       - In Bhubaneswar (hot-humid climate): cool_ml = 0.0, so O1_ml == warm_ml (100% warm discomfort).
    2. For Adaptive 90 Discomfort: The builder reads column 'O1_adapt'.
       - O1_adapt is the percentage of occupied hours outside the ASHRAE 55 Adaptive 90% acceptability limits.
    """
    print(builder_snippet.strip())
    print("=" * 120)

if __name__ == "__main__":
    main()
