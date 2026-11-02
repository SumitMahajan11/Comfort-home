"""
tools/print_part_a.py
Generates exact reporting for PART A from saved files without simulations.
"""

import os
import sys
REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pandas as pd
import numpy as np

from src.sim.sampler import DESIGN_VARIABLE_RANGES
from src.optimize.references import REFERENCE_R3_PER_CITY
from src.sim.render import parse_epw_ground_temperatures

# -----------------------------------------------------------------------------
# A1. TABLE 1: RE-PRINT FOR CHENNAI FROM SAVED FILES
# -----------------------------------------------------------------------------
def print_table_1_chennai():
    base_csv = "data/processed/batch/Chennai/baseline_results.csv"
    pareto_parquet = "data/processed/batch/Chennai/final_verified_pareto_Chennai.parquet"
    
    df_base = pd.read_csv(base_csv)
    df_p = pd.read_parquet(pareto_parquet)
    
    # Lower is better for all objectives: O1_ml, O1_adapt, O2
    best_o1_ml_idx = df_p['O1_ml'].idxmin()
    best_o1_ad_idx = df_p['O1_adapt'].idxmin()
    best_o2_idx = df_p['O2'].idxmin()
    worst_o1_ml_idx = df_p['O1_ml'].idxmax()
    worst_o2_idx = df_p['O2'].idxmax()
    
    # Normalized midpoint Knee
    # 3-objective normalization: [O1_ml, O1_adapt, O2]
    F3 = df_p[['O1_ml', 'O1_adapt', 'O2']].values
    fn3 = (F3 - F3.min(axis=0)) / (F3.max(axis=0) - F3.min(axis=0) + 1e-12)
    d3 = np.linalg.norm(fn3 - 0.5, axis=1)
    knee_idx = np.argmin(d3)
    
    # Also 2-objective (O1_ml, O2) for completeness
    F2 = df_p[['O1_ml', 'O2']].values
    fn2 = (F2 - F2.min(axis=0)) / (F2.max(axis=0) - F2.min(axis=0) + 1e-12)
    d2 = np.linalg.norm(fn2 - 0.5, axis=1)
    knee2_idx = np.argmin(d2)

    rows = []
    # Baseline rows
    for _, r in df_base.iterrows():
        rows.append({
            'Design / Category': r['design_id'],
            'Design ID': r['design_id'],
            'O1_ml (%)': round(float(r['O1_ml']), 2),
            'O1_adapt (%)': round(float(r['O1_adapt']), 2),
            'O2 (kWh/m2)': round(float(r['O2']), 2),
            'Top Med (C)': round(float(r['top_med']), 2),
            'Top Max (C)': round(float(r['top_max']), 2),
            'Top < 5 C (h)': int(r['top_lt_5']),
            'Top > 35 C (h)': int(r['top_gt_35'])
        })
        
    def _add_p_row(cat_name, idx):
        row_s = df_p.loc[idx]
        rows.append({
            'Design / Category': cat_name,
            'Design ID': row_s['design_id'],
            'O1_ml (%)': round(float(row_s['O1_ml']), 2),
            'O1_adapt (%)': round(float(row_s['O1_adapt']), 2),
            'O2 (kWh/m2)': round(float(row_s['O2']), 2),
            'Top Med (C)': round(float(row_s['top_med']), 2),
            'Top Max (C)': round(float(row_s['top_max']), 2),
            'Top < 5 C (h)': int(row_s['top_lt_5']),
            'Top > 35 C (h)': int(row_s['top_gt_35'])
        })
        
    _add_p_row("Best O1_ml (Lowest Discomfort)", best_o1_ml_idx)
    _add_p_row("Best O1_adapt (Lowest Discomfort)", best_o1_ad_idx)
    _add_p_row("Best O2 (Lowest Energy)", best_o2_idx)
    _add_p_row(f"Knee (Normalized Midpoint)", knee_idx)
    
    rows.append({
        'Design / Category': 'Front Median',
        'Design ID': f"Median (N={len(df_p)})",
        'O1_ml (%)': round(float(df_p['O1_ml'].median()), 2),
        'O1_adapt (%)': round(float(df_p['O1_adapt'].median()), 2),
        'O2 (kWh/m2)': round(float(df_p['O2'].median()), 2),
        'Top Med (C)': round(float(df_p['top_med'].median()), 2),
        'Top Max (C)': round(float(df_p['top_max'].median()), 2),
        'Top < 5 C (h)': int(df_p['top_lt_5'].median()),
        'Top > 35 C (h)': int(df_p['top_gt_35'].median())
    })
    
    _add_p_row("Worst O1_ml (Highest Discomfort)", worst_o1_ml_idx)
    _add_p_row("Worst O2 (Highest Energy)", worst_o2_idx)
    
    df_t1 = pd.DataFrame(rows)
    print("=" * 130)
    print("TABLE 1: BASELINES (R1/R2/R3) vs VERIFIED PARETO FRONT (CHENNAI) [CORRECTED: LOWER O1 IS BETTER]")
    print("=" * 130)
    print(df_t1.to_string(index=False))
    print(f"\nNote on Knee: Closest to 3-objective normalized midpoint [0.5, 0.5, 0.5] is {df_p.loc[knee_idx, 'design_id']} (dist={d3[knee_idx]:.4f}).")
    print(f"Closest to 2-objective normalized midpoint [0.5, 0.5] in (O1_ml, O2) plane is {df_p.loc[knee2_idx, 'design_id']} (dist={d2[knee2_idx]:.4f}).")
    print("=" * 130 + "\n")

# -----------------------------------------------------------------------------
# A2. BOUNDS TABLE WITH RULE IN HEADER AND NEAR-DUPLICATES COUNT
# -----------------------------------------------------------------------------
def print_bounds_table_chennai():
    pareto_parquet = "data/processed/batch/Chennai/final_verified_pareto_Chennai.parquet"
    df_p = pd.read_parquet(pareto_parquet)
    n_p = len(df_p)
    threshold_count = int(np.ceil((2.0 / 3.0) * n_p))  # 8 for n_p = 11

    # Check near-duplicates: all 8 variables within 1% of span
    spans = {
        'roof_insulation_thickness': 0.15,
        'wall_insulation_thickness': 0.15,
        'roof_solar_absorptance': 0.60,
        'wwr': 0.35,
        'orientation': 359.0,
        'shading_depth': 0.70,
        'ventilation_ach': 14.0
    }
    dup_pairs = []
    dup_indices = set()
    for i in range(n_p):
        for j in range(i + 1, n_p):
            r1 = df_p.iloc[i]
            r2 = df_p.iloc[j]
            if r1['wall_mass_class'] != r2['wall_mass_class']:
                continue
            is_dup = True
            for var, span in spans.items():
                if abs(float(r1[var]) - float(r2[var])) > 0.01 * span:
                    is_dup = False
                    break
            if is_dup:
                dup_pairs.append((r1['design_id'], r2['design_id']))
                dup_indices.add(i)
                dup_indices.add(j)

    print("=" * 140)
    print(f"TABLE 2: BOUNDS TABLE (CHENNAI) - AT BOUND if (#low + #up) / front_size >= 2/3 (front_size = {n_p}, bound threshold >= {threshold_count})")
    print(f"Near-Duplicate Front Designs (all 8 variables within 1% of span): {len(dup_indices)} designs ({len(dup_pairs)} pair: {dup_pairs})")
    print("=" * 140)

    var_cols = [
        'roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance',
        'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
    ]
    b_header = f"{'Design Variable':<28} | {'Lower':<7} | {'Upper':<7} | {'Span':<7} | {'5% Span':<8} | {'Low Zone':<16} | {'Up Zone':<16} | {'# Low':<6} | {'# Up':<6} | {'Total Bound':<11} | {'Status':<12}"
    b_sep = "-" * len(b_header)
    print(b_header)
    print(b_sep)

    for var in var_cols:
        low_b, up_b = DESIGN_VARIABLE_RANGES[var]
        span = up_b - low_b
        tol = 0.05 * span
        low_thresh = low_b + tol
        up_thresh = up_b - tol
        vals = df_p[var].values
        n_low = int(np.sum(vals <= low_thresh + 1e-6))
        n_up = int(np.sum(vals >= up_thresh - 1e-6))
        n_tot = n_low + n_up
        ratio = n_tot / n_p
        status = "AT BOUND" if ratio >= (2.0 / 3.0) else "INTERIOR"
        low_str = f"[{low_b:.3f}, {low_thresh:.3f}]"
        up_str = f"[{up_thresh:.3f}, {up_b:.3f}]"
        print(f"{var:<28} | {low_b:<7.3f} | {up_b:<7.3f} | {span:<7.3f} | {tol:<8.4f} | {low_str:<16} | {up_str:<16} | {n_low:<6} | {n_up:<6} | {n_tot:<11} | {status:<12}")

    counts = df_p['wall_mass_class'].value_counts()
    n_light = counts.get('light', 0)
    n_hvy = counts.get('heavy', 0)
    n_tot_mass = n_light + n_hvy
    status_m = "AT BOUND" if (n_tot_mass / n_p) >= (2.0 / 3.0) else "INTERIOR"
    print(f"{'wall_mass_class (discrete)':<28} | {'light':<7} | {'heavy':<7} | {'3 cls':<7} | {'N/A':<8} | {'light: ' + str(n_light):<16} | {'heavy: ' + str(n_hvy):<16} | {n_light:<6} | {n_hvy:<6} | {n_tot_mass:<11} | {status_m:<12}")
    print(b_sep + "\n")

# -----------------------------------------------------------------------------
# A3. CHENNAI R3 REFERENCE ROW
# -----------------------------------------------------------------------------
def print_chennai_r3():
    flagship_source = "Mumbai"
    r3 = dict(REFERENCE_R3_PER_CITY[flagship_source])
    r3['city'] = 'Chennai'
    
    print("=" * 100)
    print(f"CHENNAI R3 CODE-COMPLIANT REFERENCE ROW (Copied from flagship: {flagship_source})")
    print("=" * 100)
    df_r3 = pd.DataFrame([r3])
    for col in df_r3.columns:
        print(f"{col:<26}: {df_r3[col].iloc[0]}")
    print("=" * 100 + "\n")

# -----------------------------------------------------------------------------
# A4. CSV PASTES AND 12 MONTHLY 0.5M GROUND TEMPS
# -----------------------------------------------------------------------------
def print_manifest_and_climate():
    print("=" * 100)
    print("REPORTS/BATCH_EPW_MANIFEST.CSV")
    print("=" * 100)
    with open("reports/batch_epw_manifest.csv", "r", encoding="utf-8") as f:
        print(f.read())

    print("=" * 100)
    print("REPORTS/BATCH_CLIMATE_TABLE.CSV")
    print("=" * 100)
    with open("reports/batch_climate_table.csv", "r", encoding="utf-8") as f:
        print(f.read())

    print("=" * 100)
    print("CHENNAI 12 MONTHLY 0.5 M GROUND TEMPERATURES (Parsed from EPW Header)")
    print("=" * 100)
    df_m = pd.read_csv("reports/batch_epw_manifest.csv")
    c_path = df_m[df_m['city'].str.lower() == 'chennai'].iloc[0]['path']
    depths = parse_epw_ground_temperatures(c_path)
    temps_05m = depths[0.5]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    df_gt = pd.DataFrame([temps_05m], columns=months, index=['Chennai 0.5m Temp (C)'])
    print(df_gt.to_string())
    print(f"\nRaw list: {temps_05m}")
    print("=" * 100 + "\n")

if __name__ == '__main__':
    print_table_1_chennai()
    print_bounds_table_chennai()
    print_chennai_r3()
    print_manifest_and_climate()
