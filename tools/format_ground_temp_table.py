"""
tools/format_ground_temp_table.py

Loads data/processed/ground_temp_quantification.csv and prints the exact markdown table
with the per-condition mean rows computed by code.
"""

import pandas as pd

def main():
    df = pd.read_csv('data/processed/ground_temp_quantification.csv')
    print("| pareto_id | selection_role | floor_type | T_op median (°C) | T_op 95th (°C) | T_op max (°C) | O1_ml (%) | O1_adapt (%) | O2 (kWh/m²) |")
    print("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for _, r in df.iterrows():
        print(f"| {r['pareto_id']} | {r['selection_role']} | {r['floor_type']} | {r['top_median']:.2f} | {r['top_95th']:.2f} | {r['top_max']:.2f} | {r['O1_ml']:.2f} | {r['O1_adapt']:.2f} | {r['O2']:.2f} |")
    
    print("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for ft in ['default_18c', 'epw_ground', 'adiabatic']:
        sub = df[df['floor_type'] == ft]
        label = f"**MEAN ({ft})**"
        print(f"| {label} | - | {ft} | {sub['top_median'].mean():.2f} | {sub['top_95th'].mean():.2f} | {sub['top_max'].mean():.2f} | {sub['O1_ml'].mean():.2f} | {sub['O1_adapt'].mean():.2f} | {sub['O2'].mean():.2f} |")

if __name__ == '__main__':
    main()
