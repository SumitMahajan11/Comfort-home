#!/usr/bin/env python3
"""
tools/build_results_30_cities.py

Builds reports/results_30_cities.csv containing comprehensive optimization and
verification results across all 30 cities (29 pipeline cities + Leh).
"""

import os
import sys
import hashlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("."))

from src.optimize.coupling import compute_valid_adaptive_hours_from_epw

# Climate zone mappings
CITY_CLIMATE_ZONES = {
    # Cold -> Leh
    "Srinagar": "Cold",
    "Manali": "Cold",
    "Bhuntar": "Cold",
    "Gangtok": "Cold",
    "Leh": "Cold",
    "Shimla": "Cold",
    # Composite -> New_Delhi
    "Jammu": "Composite",
    "Dehradun": "Composite",
    "Lucknow": "Composite",
    "Varanasi": "Composite",
    "Prayagraj": "Composite",
    "Agra": "Composite",
    "Gorakhpur": "Composite",
    "Patna": "Composite",
    "Nagpur": "Composite",
    "New_Delhi": "Composite",
    # Warm-humid -> Mumbai
    "Guwahati": "Warm-humid",
    "Dibrugarh": "Warm-humid",
    "Imphal": "Warm-humid",
    "Bhubaneswar": "Warm-humid",
    "Kolkata": "Warm-humid",
    "Visakhapatnam": "Warm-humid",
    "Chennai": "Warm-humid",
    "Kochi": "Warm-humid",
    "Port Blair": "Warm-humid",
    "Mumbai": "Warm-humid",
    # Hot-dry -> Jodhpur
    "Bhuj": "Hot-dry",
    "Jaisalmer": "Hot-dry",
    "Jodhpur": "Hot-dry",
    "Surat": "Hot-dry",
    # Temperate -> Bengaluru
    "Bengaluru": "Temperate"
}

ZONE_TO_FLAGSHIP_R3 = {
    "Cold": "Leh",
    "Composite": "New_Delhi",
    "Warm-humid": "Mumbai",
    "Hot-dry": "Jodhpur",
    "Temperate": "Bengaluru"
}

CITY_ZONE_SOURCE = {
    "Srinagar": "STANDARD",
    "Bhuntar": "ASSUMED",
    "Gangtok": "ASSUMED",
    "Jammu": "ASSUMED",
    "Dehradun": "STANDARD",
    "Lucknow": "STANDARD",
    "Varanasi": "ASSUMED",
    "Prayagraj": "STANDARD",
    "Agra": "ASSUMED",
    "Gorakhpur": "STANDARD",
    "Patna": "STANDARD",
    "Nagpur": "STANDARD",
    "Guwahati": "STANDARD",
    "Dibrugarh": "STANDARD",
    "Imphal": "STANDARD",
    "Bhubaneswar": "STANDARD",
    "Kolkata": "STANDARD",
    "Visakhapatnam": "STANDARD",
    "Chennai": "STANDARD",
    "Surat": "STANDARD",
    "Kochi": "STANDARD",
    "Port Blair": "ASSUMED",
    "Bhuj": "ASSUMED",
    "Jaisalmer": "STANDARD",
    "Leh": "STANDARD",
    "Shimla": "ASSUMED",
    "New_Delhi": "STANDARD",
    "Mumbai": "STANDARD",
    "Jodhpur": "STANDARD",
    "Bengaluru": "STANDARD"
}

PARAM_SPANS = {
    'roof_insulation_thickness': 0.15,
    'wall_insulation_thickness': 0.15,
    'roof_solar_absorptance': 0.60,
    'wwr': 0.35,
    'orientation': 359.0,
    'shading_depth': 0.70,
    'ventilation_ach': 14.0
}

BOUND_SPANS = {
    'roof_insulation_thickness': (0.0, 0.15),
    'wall_insulation_thickness': (0.0, 0.15),
    'roof_solar_absorptance': (0.30, 0.90),
    'wwr': (0.05, 0.40),
    # orientation excluded because circular
    'shading_depth': (0.30, 1.00),
    'ventilation_ach': (1.0, 15.0)
}

def compute_distinct_designs(df_p):
    """
    Computes distinct designs on Pareto front:
    - distinct_count: count of designs after filtering near-duplicates (within 1% of span on all 8 variables)
    - isolated_count: count of designs with zero other front designs within 1% of span
    - dup_pairs: list of duplicate pairs
    """
    n_p = len(df_p)
    dup_pairs = []
    dup_indices = set()
    for i in range(n_p):
        for j in range(i + 1, n_p):
            r1 = df_p.iloc[i]
            r2 = df_p.iloc[j]
            if r1['wall_mass_class'] != r2['wall_mass_class']:
                continue
            is_dup = True
            for var, s_val in PARAM_SPANS.items():
                if abs(float(r1[var]) - float(r2[var])) > 0.01 * s_val:
                    is_dup = False
                    break
            if is_dup:
                dup_pairs.append((i, j))
                dup_indices.add(i)
                dup_indices.add(j)

    # Greedy representative selection
    kept = []
    for i in range(n_p):
        r1 = df_p.iloc[i]
        dup_with_kept = False
        for k in kept:
            r2 = df_p.iloc[k]
            if r1['wall_mass_class'] != r2['wall_mass_class']:
                continue
            match = True
            for var, s_val in PARAM_SPANS.items():
                if abs(float(r1[var]) - float(r2[var])) > 0.01 * s_val:
                    match = False
                    break
            if match:
                dup_with_kept = True
                break
        if not dup_with_kept:
            kept.append(i)

    return len(kept), n_p - len(dup_indices), len(dup_pairs)

def compute_at_bound_variables(df_p):
    """
    Evaluates at_bound status using 2/3 rule:
    (#low + #up) / front_size >= 2/3.
    Orientation is excluded because circular.
    """
    front_size = len(df_p)
    at_bound_vars = []
    for var, (lb, ub) in BOUND_SPANS.items():
        span = ub - lb
        tol = 0.05 * span
        n_b = np.sum((df_p[var] <= lb + tol + 1e-6) | (df_p[var] >= ub - tol - 1e-6))
        if n_b / front_size >= (2.0 / 3.0):
            at_bound_vars.append(var)

    counts = df_p['wall_mass_class'].value_counts()
    n_b_mass = counts.get('light', 0) + counts.get('heavy', 0)
    if n_b_mass / front_size >= (2.0 / 3.0):
        at_bound_vars.append('wall_mass_class')

    return "; ".join(at_bound_vars) if at_bound_vars else "None"

def build_results_table():
    manifest_df = pd.read_csv("reports/batch_epw_manifest.csv")

    flagships = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
    batch_cities = sorted([
        d for d in os.listdir('data/processed/batch')
        if os.path.isdir(os.path.join('data/processed/batch', d))
    ])

    city_entries = []
    for f in flagships:
        city_entries.append((f, f'data/processed/flagship_2011_2025/{f}', 'flagship', 'run_city_pipeline'))
    for b in batch_cities:
        city_entries.append((b, f'data/processed/batch/{b}', 'batch', 'run_city_pipeline'))

    table_rows = []

    for city, cdir, group, pipeline in city_entries:
        zone = CITY_CLIMATE_ZONES[city]
        zone_source = CITY_ZONE_SOURCE.get(city, "ASSUMED")
        r3_flagship = ZONE_TO_FLAGSHIP_R3[zone]

        # EPW resolution
        if city == 'Leh':
            epw_path = "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
            epw_file = os.path.basename(epw_path)
            with open(epw_path, 'rb') as fp:
                epw_sha256 = hashlib.sha256(fp.read()).hexdigest()
        else:
            m_row = manifest_df[manifest_df['city'].str.lower() == city.lower()].iloc[0]
            epw_path = m_row['path']
            epw_file = os.path.basename(epw_path)
            epw_sha256 = m_row['sha256']

        # Canonical valid adaptive hours
        valid_adaptive_hours = compute_valid_adaptive_hours_from_epw(epw_path)

        # Pareto front loading
        if city == 'Leh':
            p_pareto = os.path.join(cdir, "final_verified_pareto_Leh.parquet")
            df_p = pd.read_parquet(p_pareto)
            # Normalize column names for Leh
            for v in list(PARAM_SPANS.keys()):
                if v not in df_p.columns and v + '_x' in df_p.columns:
                    df_p[v] = df_p[v + '_x']
            if 'wall_mass_class' not in df_p.columns and 'wall_mass_class_x' in df_p.columns:
                df_p['wall_mass_class'] = df_p['wall_mass_class_x']
            if 'design_id' not in df_p.columns and 'pareto_id' in df_p.columns:
                df_p['design_id'] = df_p['pareto_id']
        else:
            p_pareto = os.path.join(cdir, f"final_verified_pareto_{city}.parquet")
            df_p = pd.read_parquet(p_pareto)

        front_size = len(df_p)
        distinct_count, isolated_count, n_dup_pairs = compute_distinct_designs(df_p)
        at_bound_str = compute_at_bound_variables(df_p)

        # Baseline results loading
        if city == 'Leh':
            df_b = pd.read_csv("data/processed/active_learning_leh/leh_baselines_summary.csv")
            r1_row = df_b[df_b['design'] == 'R1_Lightweight'].iloc[0]
            r2_row = df_b[df_b['design'] == 'R2_Conventional'].iloc[0]
            r3_row = df_b[df_b['design'] == 'R3_Code_Compliant'].iloc[0]
            r1_o1_ml, r1_o2 = round(float(r1_row['O1_ml']), 2), round(float(r1_row['O2']), 2)
            r2_o1_ml, r2_o2 = round(float(r2_row['O1_ml']), 2), round(float(r2_row['O2']), 2)
            r3_o1_ml, r3_o2 = round(float(r3_row['O1_ml']), 2), round(float(r3_row['O2']), 2)
        else:
            df_b = pd.read_csv(os.path.join(cdir, "baseline_results.csv"))
            r1_row = df_b[df_b['design_id'] == 'R1_Lightweight'].iloc[0]
            r2_row = df_b[df_b['design_id'] == 'R2_Conventional'].iloc[0]
            r3_row = df_b[df_b['design_id'] == 'R3_Code_Compliant'].iloc[0]
            r1_o1_ml, r1_o2 = round(float(r1_row['O1_ml']), 2), round(float(r1_row['O2']), 2)
            r2_o1_ml, r2_o2 = round(float(r2_row['O1_ml']), 2), round(float(r2_row['O2']), 2)
            r3_o1_ml, r3_o2 = round(float(r3_row['O1_ml']), 2), round(float(r3_row['O2']), 2)

        # Best Pareto metrics
        best_o1_ml_row = df_p.loc[df_p['O1_ml'].idxmin()]
        best_o1_ml = round(float(best_o1_ml_row['O1_ml']), 2)
        best_o1_ml_id = str(best_o1_ml_row['design_id'])

        best_o1_ad = round(float(df_p['O1_adapt'].min()), 2)

        best_o2_row = df_p.loc[df_p['O2'].idxmin()]
        best_o2 = round(float(best_o2_row['O2']), 2)
        best_o2_id = str(best_o2_row['design_id'])

        # Top < 5 and Top > 35 of the best-O2 design, best-O1_ml design, and worst across front
        if city == 'Leh' and 'leh_baselines_summary.csv' in os.listdir(cdir):
            sum_b2 = df_b[df_b['design'] == best_o2_id]
            if not sum_b2.empty:
                top_lt_5_best_o2 = int(sum_b2.iloc[0]['T_op_lt_5'])
                top_gt_35_best_o2 = int(sum_b2.iloc[0]['T_op_gt_35'])
            else:
                top_lt_5_best_o2 = int(best_o2_row.get('top_lt_5', 0))
                top_gt_35_best_o2 = int(best_o2_row.get('top_gt_35', 0))
            top_lt_5_best_o1_ml = int(best_o1_ml_row.get('top_lt_5', top_lt_5_best_o2))
            top_gt_35_best_o1_ml = int(best_o1_ml_row.get('top_gt_35', top_gt_35_best_o2))
            top_lt_5_worst_front = int(df_p['top_lt_5'].max()) if 'top_lt_5' in df_p.columns else top_lt_5_best_o2
            top_gt_35_worst_front = int(df_p['top_gt_35'].max()) if 'top_gt_35' in df_p.columns else top_gt_35_best_o2
        else:
            top_lt_5_best_o2 = int(best_o2_row.get('top_lt_5', 0))
            top_gt_35_best_o2 = int(best_o2_row.get('top_gt_35', 0))
            top_lt_5_best_o1_ml = int(best_o1_ml_row.get('top_lt_5', 0))
            top_gt_35_best_o1_ml = int(best_o1_ml_row.get('top_gt_35', 0))
            top_lt_5_worst_front = int(df_p['top_lt_5'].max()) if 'top_lt_5' in df_p.columns else top_lt_5_best_o2
            top_gt_35_worst_front = int(df_p['top_gt_35'].max()) if 'top_gt_35' in df_p.columns else top_gt_35_best_o2

        # Improvement in percentage points (pp) and percentage (%)
        # Comfort improvement over R3 (pp): R3 - Best (percentage points)
        pp_better_r3_o1_ml = round(r3_o1_ml - best_o1_ml, 2)
        # Percent better than R3 for best O1_ml and best O2: (R3 - Best) / R3 * 100
        pct_better_r3_o1_ml = round((r3_o1_ml - best_o1_ml) / r3_o1_ml * 100.0, 2)
        pct_better_r3_o2 = round((r3_o2 - best_o2) / r3_o2 * 100.0, 2)

        # Simulation-derived valid adaptive hours & reliability flag
        inv_share = float(df_p['invalid_share_adapt'].iloc[0]) if 'invalid_share_adapt' in df_p.columns else 0.0
        valid_adaptive_hours_sim = int(round(8760 * (1.0 - inv_share / 100.0)))
        o1_adapt_reliable = bool(valid_adaptive_hours >= int(0.75 * 8760)) # >= 6570 hours

        # Active learning history errors and new flags
        df_hist = pd.read_csv(os.path.join(cdir, "active_learning_history.csv"))
        raw_errs_pct = df_hist['mean_err_O2_pct'].values
        raw_errs_abs = df_hist['mean_err_O2_abs'].values if 'mean_err_O2_abs' in df_hist.columns else []
        o2_err_str = "; ".join(f"{e:.2f}%" for e in raw_errs_pct)
        o2_err_abs_str = "; ".join(f"{e:.2f}" for e in raw_errs_abs)

        last_round_err_pct = float(raw_errs_pct[-1])
        round_1_err_pct = float(raw_errs_pct[0])
        flag_error_high = bool(last_round_err_pct > 5.0)

        # Updated flag_error_rising: last abs error > 1.5 * round-1 abs error AND increase > 2.0 kWh/m2
        r1_abs_err = float(raw_errs_abs[0])
        last_abs_err = float(raw_errs_abs[-1])
        flag_error_rising = bool((last_abs_err > 1.5 * r1_abs_err) and ((last_abs_err - r1_abs_err) > 2.0))

        # Round 3 signed error & share negative
        p_r3_cand = os.path.join(cdir, "round_3_candidates.parquet")
        p_r3_ver = os.path.join(cdir, f"final_verified_all_100_{city}.parquet")
        round_3_mean_signed_err = np.nan
        round_3_share_neg = np.nan
        if os.path.exists(p_r3_cand) and os.path.exists(p_r3_ver):
            df_v3 = pd.read_parquet(p_r3_ver)
            df_c3 = pd.read_parquet(p_r3_cand)
            m3 = pd.merge(df_v3, df_c3, left_on='design_id', right_on='pareto_id', suffixes=('', '_pred'))
            if not m3.empty:
                s_err = m3['pred_O2'] - m3['O2']
                round_3_mean_signed_err = round(float(np.mean(s_err)), 3)
                round_3_share_neg = round(float(np.mean(s_err < 0) * 100.0), 1)

        # Timing (minutes)
        if city == 'Leh' and 'timing.csv' not in os.listdir(cdir):
            total_minutes = round(float(df_hist['wall_time_min'].sum()), 2)
        else:
            p_time = os.path.join(cdir, "timing.csv")
            if os.path.exists(p_time):
                df_t = pd.read_csv(p_time)
                total_minutes = round(float(df_t['elapsed_seconds'].sum() / 60.0), 2)
            else:
                total_minutes = round(float(df_hist['wall_time_sec'].sum() / 60.0), 2) if 'wall_time_sec' in df_hist.columns else 0.0

        table_rows.append({
            'city': city,
            'pipeline': pipeline,
            'group': group,
            'zone': zone,
            'zone_source': zone_source,
            'R3_flagship': r3_flagship,
            'epw_file': epw_file,
            'epw_sha256': epw_sha256,
            'front_size': front_size,
            'distinct_designs': distinct_count,
            'R1_O1_ml': r1_o1_ml,
            'R1_O2': r1_o2,
            'R2_O1_ml': r2_o1_ml,
            'R2_O2': r2_o2,
            'R3_O1_ml': r3_o1_ml,
            'R3_O2': r3_o2,
            'best_O1_ml': best_o1_ml,
            'best_O1_ml_design_id': best_o1_ml_id,
            'best_O1_adapt': best_o1_ad,
            'best_O2': best_o2,
            'best_O2_design_id': best_o2_id,
            'pp_better_R3_O1_ml': pp_better_r3_o1_ml,
            'pct_better_R3_O1_ml': pct_better_r3_o1_ml,
            'pct_better_R3_O2': pct_better_r3_o2,
            'top_lt_5_best_o2': top_lt_5_best_o2,
            'top_gt_35_best_o2': top_gt_35_best_o2,
            'top_lt_5_best_o1_ml': top_lt_5_best_o1_ml,
            'top_gt_35_best_o1_ml': top_gt_35_best_o1_ml,
            'top_lt_5_worst_front': top_lt_5_worst_front,
            'top_gt_35_worst_front': top_gt_35_worst_front,
            'valid_adaptive_hours': valid_adaptive_hours,
            'valid_adaptive_hours_sim': valid_adaptive_hours_sim,
            'o1_adapt_reliable': o1_adapt_reliable,
            'at_bound_variables': at_bound_str,
            'O2_mean_error_pct_per_round': o2_err_str,
            'O2_mean_err_abs_per_round': o2_err_abs_str,
            'round_3_mean_signed_error': round_3_mean_signed_err,
            'round_3_share_negative_errors': round_3_share_neg,
            'flag_error_high': flag_error_high,
            'flag_error_rising': flag_error_rising,
            'total_minutes': total_minutes
        })

    df_out = pd.DataFrame(table_rows)
    out_csv = "reports/results_30_cities.csv"
    os.makedirs("reports", exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print(f"Saved {len(df_out)} city results to {out_csv}")
    return df_out

def run_optimism_check():
    flagships = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
    batch_cities = sorted([
        d for d in os.listdir('data/processed/batch')
        if os.path.isdir(os.path.join('data/processed/batch', d))
    ])

    all_cities = [(f, f'data/processed/flagship_2011_2025/{f}', 'flagship') for f in flagships] + \
                 [(b, f'data/processed/batch/{b}', 'batch') for b in batch_cities]

    print("=" * 115)
    print("SURROGATE OPTIMISM CHECK ACROSS ALL 29 PIPELINE CITIES (ROUND 3 CANDIDATES)")
    print("Signed Error = Predicted O2 - Verified O2 (Negative = Underpredicted Energy / Optimistic)")
    print("=" * 115)

    rows = []
    r1_r2_saved_status = {}

    for city, cdir, group in all_cities:
        p_ver = os.path.join(cdir, f'final_verified_all_100_{city}.parquet')
        p_cand = os.path.join(cdir, 'round_3_candidates.parquet')

        if not os.path.exists(p_ver) or not os.path.exists(p_cand):
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

        p_r1 = os.path.join(cdir, 'round_1_candidates.parquet')
        p_r2 = os.path.join(cdir, 'round_2_candidates.parquet')
        r1_r2_saved_status[city] = {
            'round_1_candidates_exists': os.path.exists(p_r1),
            'round_2_candidates_exists': os.path.exists(p_r2)
        }

    df_table = pd.DataFrame(rows)
    print(df_table.to_string(index=False))
    print("=" * 115)

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
    import argparse
    parser = argparse.ArgumentParser(description="Build results_30_cities.csv and optional optimism report")
    parser.add_argument("--optimism", action="store_true", help="Print optimism check across 29 cities")
    args = parser.parse_args()

    df_res = build_results_table()
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print("\n" + "=" * 140)
    print("RESULTS 30 CITIES TABLE:")
    print("=" * 140)
    print(df_res.to_string(index=False))
    print("\n" + "=" * 140)
    print("COLUMN LIST IN reports/results_30_cities.csv:")
    print("=" * 140)
    for i, col in enumerate(df_res.columns, 1):
        print(f"{i:2d}. {col}")

    if args.optimism:
        print("\n")
        run_optimism_check()
