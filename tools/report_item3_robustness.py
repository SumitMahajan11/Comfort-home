#!/usr/bin/env python3
"""
tools/report_item3_robustness.py

Item 3: ROBUSTNESS ANALYSIS (NO RE-OPTIMIZATION) ACROSS 5 FLAGSHIP CITIES
- Cities: Shimla, Jodhpur, New_Delhi, Mumbai, Bengaluru
- Designs: Verified Pareto Front + R1, R2, R3 baselines
- Scenarios:
    1. Baseline Climate (TMYx 2011-2025 raw EPW)
    2. +1.5 °C Uniform Warming Sensitivity Scenario (*_plus1p5.epw)
    3. +3.0 °C Uniform Warming Sensitivity Scenario (*_plus3p0.epw)
- Setup: Free-running comfort (O1_ml, O1_adapt) + ideal-loads HVAC energy (O2)
- Rank Preservation & Regret:
    a) Replace verdict labels with a computed rule; print the rule.
    b) Compute Spearman rho on verified front only (exclude R1/R2/R3). If N < 5, print 'not testable'.
    c) Add regret per city and scenario:
       O1_ml of baseline-best minus lowest O1_ml on front in that scenario (pp).
       Same for O2 (kWh/m2 and %).
       Print the ID of each scenario's own best design.
- Output:
    * Detailed data written to reports/robustness_flagship_details.csv
    * Formatted report and tables written to reports/item3_robustness.txt
"""

import os
import sys
import time
import math
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FLAGSHIPS = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
MAX_WORKERS = 6

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def compute_rank_verdict(shift_o1_15, shift_o1_30, shift_o2_15, shift_o2_30):
    """
    Computed Rule for Rank Preservation Verdict:
    M = max(shift_o1_15, shift_o1_30, shift_o2_15, shift_o2_30) where shift = rank - 1.
    If M == 0: 'PERFECT_RANK_PRESERVED (Max rank shift = 0)'
    elif max(shift_o1_15, shift_o1_30) == 0: 'O1_PRESERVED_O2_SHIFTED (O1 shift = 0, O2 max shift = X)'
    elif max(shift_o2_15, shift_o2_30) == 0: 'O2_PRESERVED_O1_SHIFTED (O2 shift = 0, O1 max shift = Y)'
    else: 'BOTH_SHIFTED (O1 max shift = X, O2 max shift = Y)'
    """
    max_o1 = max(shift_o1_15, shift_o1_30)
    max_o2 = max(shift_o2_15, shift_o2_30)
    max_total = max(max_o1, max_o2)

    if max_total == 0:
        return "PERFECT_RANK_PRESERVED (Max rank shift = 0)"
    elif max_o1 == 0 and max_o2 > 0:
        return f"O1_PRESERVED_O2_SHIFTED (O1 shift = 0, O2 max shift = {max_o2})"
    elif max_o2 == 0 and max_o1 > 0:
        return f"O2_PRESERVED_O1_SHIFTED (O2 shift = 0, O1 max shift = {max_o1})"
    else:
        return f"BOTH_SHIFTED (O1 max shift = {max_o1}, O2 max shift = {max_o2})"

def compute_monotonicity_verdict(front_size, rho_o1_15, rho_o1_30, rho_o2_15, rho_o2_30):
    """
    Computed Rule for Spearman Rank Monotonicity Verdict:
    Evaluated across all four rho columns on the verified Pareto front only (excluding R1/R2/R3):
      min_all_4 = min(rho(O1_ml, +1.5C), rho(O1_ml, +3.0C), rho(O2, +1.5C), rho(O2, +3.0C))
    If front_size < 5: 'not testable (front size < 5)'
    elif min_all_4 >= 0.95: 'HIGH (min rho >= 0.95)'
    elif min_all_4 >= 0.85: 'STRONG (min rho >= 0.85)'
    elif min_all_4 >= 0.70: 'MODERATE (min rho >= 0.70)'
    else: 'LOW (min rho < 0.70)'
    """
    if front_size < 5:
        return "not testable (front size < 5)"
    min_all_4 = min(rho_o1_15, rho_o1_30, rho_o2_15, rho_o2_30)
    if min_all_4 >= 0.95:
        return f"HIGH (min rho = {min_all_4:.4f} >= 0.95)"
    elif min_all_4 >= 0.85:
        return f"STRONG (min rho = {min_all_4:.4f} >= 0.85)"
    elif min_all_4 >= 0.70:
        return f"MODERATE (min rho = {min_all_4:.4f} >= 0.70)"
    else:
        return f"LOW (min rho = {min_all_4:.4f} < 0.70)"

def run_or_load_robustness_data(out_csv_path, force_resim=False):
    if os.path.exists(out_csv_path) and not force_resim:
        print(f"Loading existing robustness simulation dataset from {out_csv_path}...")
        df_all = pd.read_csv(out_csv_path)
        return df_all

    print("Re-simulating robustness evaluations across 5 flagship cities...")
    from src.sim.render import render_shelter_idf
    from src.sim.runner import run_single_simulation
    from src.sim.parse import parse_simulation_csv
    from src.optimize.coupling import (
        calculate_daily_mean_series,
        compute_running_mean_outdoor_temperature_db2,
        compute_clo_schedule_a004,
        evaluate_adaptive_90_comfort,
        evaluate_ml_champion_comfort,
        load_champion_model
    )

    manifest_df = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    champ_model = load_champion_model()
    sim_root = os.path.join("data", "processed", "robustness_sims")
    os.makedirs(sim_root, exist_ok=True)

    all_detailed_records = []

    for city in FLAGSHIPS:
        print(f"  Simulating {city}...")
        cdir = f"data/processed/flagship_2011_2025/{city}"
        base_csv = os.path.join(cdir, "baseline_results.csv")
        pareto_pq = os.path.join(cdir, f"final_verified_pareto_{city}.parquet")

        df_base = pd.read_csv(base_csv)
        df_base['is_pareto'] = False

        df_pareto = pd.read_parquet(pareto_pq)
        df_pareto['is_pareto'] = True

        eval_cols = [
            'city', 'design_id', 'is_pareto',
            'roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class',
            'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach',
            'O1_ml', 'O1_adapt', 'O2', 'top_gt_35'
        ]

        df_designs_to_sim = pd.concat([
            df_base[eval_cols],
            df_pareto[eval_cols]
        ], ignore_index=True)

        p15_path = f"data/processed/weather_morphed/{city}_plus1p5.epw"
        p30_path = f"data/processed/weather_morphed/{city}_plus3p0.epw"

        # Sim worker
        def _sim_set(df_d, epw_p, sub_d):
            rows = []
            for _, row_d in df_d.iterrows():
                did = str(row_d['design_id'])
                params = {
                    'roof_insulation_thickness': float(row_d['roof_insulation_thickness']),
                    'wall_insulation_thickness': float(row_d['wall_insulation_thickness']),
                    'wall_mass_class': str(row_d['wall_mass_class']),
                    'roof_solar_absorptance': float(row_d['roof_solar_absorptance']),
                    'wwr': float(row_d['wwr']),
                    'orientation': float(row_d['orientation']),
                    'shading_depth': float(row_d['shading_depth']),
                    'ventilation_ach': float(row_d['ventilation_ach'])
                }
                rdir_fr = os.path.join(sub_d, f"{did}_fr")
                rdir_il = os.path.join(sub_d, f"{did}_il")
                os.makedirs(rdir_fr, exist_ok=True)
                os.makedirs(rdir_il, exist_ok=True)
                idf_fr = os.path.join(rdir_fr, "shelter.idf")
                idf_il = os.path.join(rdir_il, "shelter.idf")
                render_shelter_idf(params, idf_fr, mode='free_running', city=city, epw_path=epw_p)
                render_shelter_idf(params, idf_il, mode='ideal_loads', city=city, epw_path=epw_p)
                run_single_simulation(idf_fr, epw_p, rdir_fr)
                run_single_simulation(idf_il, epw_p, rdir_il)

                hdf_fr, _ = parse_simulation_csv(os.path.join(rdir_fr, "eplusout.csv"))
                _, sm_il = parse_simulation_csv(os.path.join(rdir_il, "eplusout.csv"))

                ta = hdf_fr['ta'].values.astype(np.float32)
                tr = hdf_fr['tr'].values.astype(np.float32)
                rh = hdf_fr['rh'].values.astype(np.float32)
                tout = hdf_fr['t_out'].values.astype(np.float32)
                daily_tout = calculate_daily_mean_series(tout)
                t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
                t_rm_hourly = np.repeat(t_rm_daily, 24)
                clo_hourly = compute_clo_schedule_a004(daily_tout)

                adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
                ml_res = evaluate_ml_champion_comfort(
                    model=champ_model, ta=ta, tr=tr, rh=rh,
                    t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly, met=1.1, vel=0.15
                )
                o2_val = float(sm_il['o2_energy_kwh_per_m2'])
                top = (ta + tr) / 2.0
                top_gt_35 = int(np.sum(top > 35.0))

                rows.append({
                    'design_id': did,
                    'O1_ml': float(ml_res['O1_ml']),
                    'O1_adapt': float(adapt_res['O1_adapt']),
                    'O2': round(o2_val, 2),
                    'top_gt_35': top_gt_35
                })
                # cleanup
                shutil.rmtree(rdir_fr, ignore_errors=True)
                shutil.rmtree(rdir_il, ignore_errors=True)
            return pd.DataFrame(rows)

        df_p15 = _sim_set(df_designs_to_sim, p15_path, os.path.join(sim_root, city, "p15"))
        df_p30 = _sim_set(df_designs_to_sim, p30_path, os.path.join(sim_root, city, "p30"))

        df_merged = df_designs_to_sim.merge(
            df_p15[['design_id', 'O1_ml', 'O1_adapt', 'O2', 'top_gt_35']],
            on='design_id', suffixes=('_base', '_plus1p5')
        ).merge(
            df_p30[['design_id', 'O1_ml', 'O1_adapt', 'O2', 'top_gt_35']],
            on='design_id'
        ).rename(columns={
            'O1_ml': 'O1_ml_plus3p0',
            'O1_adapt': 'O1_adapt_plus3p0',
            'O2': 'O2_plus3p0',
            'top_gt_35': 'top_gt_35_plus3p0'
        })

        df_merged['dO1_ml_p15'] = df_merged['O1_ml_plus1p5'] - df_merged['O1_ml_base']
        df_merged['dO1_adapt_p15'] = df_merged['O1_adapt_plus1p5'] - df_merged['O1_adapt_base']
        df_merged['dO2_p15'] = df_merged['O2_plus1p5'] - df_merged['O2_base']
        df_merged['dHours35_p15'] = df_merged['top_gt_35_plus1p5'] - df_merged['top_gt_35_base']

        df_merged['dO1_ml_p30'] = df_merged['O1_ml_plus3p0'] - df_merged['O1_ml_base']
        df_merged['dO1_adapt_p30'] = df_merged['O1_adapt_plus3p0'] - df_merged['O1_adapt_base']
        df_merged['dO2_p30'] = df_merged['O2_plus3p0'] - df_merged['O2_base']
        df_merged['dHours35_p30'] = df_merged['top_gt_35_plus3p0'] - df_merged['top_gt_35_base']

        all_detailed_records.append(df_merged)

    df_all_full = pd.concat(all_detailed_records, ignore_index=True)
    df_all_full.to_csv(out_csv_path, index=False)
    return df_all_full

def main():
    manifest_df = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    out_txt_path = os.path.join("reports", "item3_robustness.txt")
    out_csv_path = os.path.join("reports", "robustness_flagship_details.csv")

    df_all_full = run_or_load_robustness_data(out_csv_path, force_resim=False)

    lines = []
    lines.append("=" * 145)
    lines.append("ITEM 3: ROBUSTNESS & CLIMATE SENSITIVITY AUDIT ACROSS 5 FLAGSHIP CITIES (NO RE-OPTIMIZATION)")
    lines.append("Performance Preservation & Regret Under +1.5 °C and +3.0 °C Uniform Warming Scenarios")
    lines.append("=" * 145)

    # 1. Weather File Identities & Hashes
    lines.append("\nWEATHER FILE IDENTITIES & SHA-256 HASHES:")
    lines.append("-" * 145)
    lines.append(f"{'City':<12} | {'Scenario':<10} | {'EPW File Path':<70} | {'SHA-256 Hash'}")
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        base_path = manifest_df.loc[city, 'path']
        p15_path = f"data/processed/weather_morphed/{city}_plus1p5.epw"
        p30_path = f"data/processed/weather_morphed/{city}_plus3p0.epw"

        base_sha = compute_sha256(base_path)
        p15_sha = compute_sha256(p15_path)
        p30_sha = compute_sha256(p30_path)

        lines.append(f"{city:<12} | {'Baseline':<10} | {base_path:<70} | {base_sha}")
        lines.append(f"{city:<12} | {'+1.5 °C':<10} | {p15_path:<70} | {p15_sha}")
        lines.append(f"{city:<12} | {'+3.0 °C':<10} | {p30_path:<70} | {p30_sha}")
    lines.append("-" * 145)

    # Computed Rule Explanations
    lines.append("\n" + "=" * 145)
    lines.append("COMPUTED RULES FOR VERDICT LABELS")
    lines.append("=" * 145)
    lines.append("1. Computed Rule for Table 1 Rank Preservation Verdict:")
    lines.append("   Let shift_O1_15 = rank_O1_15 - 1, shift_O1_30 = rank_O1_30 - 1,")
    lines.append("       shift_O2_15 = rank_O2_15 - 1, shift_O2_30 = rank_O2_30 - 1.")
    lines.append("   Max rank shift M = max(shift_O1_15, shift_O1_30, shift_O2_15, shift_O2_30).")
    lines.append("   - If M == 0: 'PERFECT_RANK_PRESERVED (Max rank shift = 0)'")
    lines.append("   - Elif max(shift_O1_15, shift_O1_30) == 0: 'O1_PRESERVED_O2_SHIFTED (O1 shift = 0, O2 max shift = max_O2)'")
    lines.append("   - Elif max(shift_O2_15, shift_O2_30) == 0: 'O2_PRESERVED_O1_SHIFTED (O2 shift = 0, O1 max shift = max_O1)'")
    lines.append("   - Else: 'BOTH_SHIFTED (O1 max shift = max_O1, O2 max shift = max_O2)'")
    lines.append("\n2. Computed Rule for Table 2 Spearman Rank Correlation (Rho) Verdict:")
    lines.append("   Evaluated across all four rho columns on verified Pareto front designs (excluding baselines R1, R2, R3).")
    lines.append("   Let min_all_4 = min(rho_O1_15, rho_O1_30, rho_O2_15, rho_O2_30).")
    lines.append("   - If front size N < 5: 'not testable (front size < 5)'")
    lines.append("   - Elif min_all_4 >= 0.95: 'HIGH (min rho >= 0.95)'")
    lines.append("   - Elif min_all_4 >= 0.85: 'STRONG (min rho >= 0.85)'")
    lines.append("   - Elif min_all_4 >= 0.70: 'MODERATE (min rho >= 0.70)'")
    lines.append("   - Else: 'LOW (min rho < 0.70)'")
    lines.append("=" * 145)

    # Process City Summaries
    city_summaries = {}
    for city in FLAGSHIPS:
        df_city = df_all_full[df_all_full['city'] == city].copy()
        df_pareto = df_city[df_city['is_pareto'] == True].copy()

        n_designs = len(df_city)
        n_pareto = len(df_pareto)

        # Baseline best designs on verified Pareto front
        base_best_o1_row = df_pareto.loc[df_pareto['O1_ml_base'].idxmin()]
        base_best_o2_row = df_pareto.loc[df_pareto['O2_base'].idxmin()]
        best_o1_base_id = base_best_o1_row['design_id']
        best_o2_base_id = base_best_o2_row['design_id']

        # Ranks under each scenario on verified front (1 = best)
        df_pareto['rank_o1_base'] = df_pareto['O1_ml_base'].rank(method='min')
        df_pareto['rank_o1_p15']  = df_pareto['O1_ml_plus1p5'].rank(method='min')
        df_pareto['rank_o1_p30']  = df_pareto['O1_ml_plus3p0'].rank(method='min')

        df_pareto['rank_o2_base'] = df_pareto['O2_base'].rank(method='min')
        df_pareto['rank_o2_p15']  = df_pareto['O2_plus1p5'].rank(method='min')
        df_pareto['rank_o2_p30']  = df_pareto['O2_plus3p0'].rank(method='min')

        row_best_o1 = df_pareto[df_pareto['design_id'] == best_o1_base_id].iloc[0]
        row_best_o2 = df_pareto[df_pareto['design_id'] == best_o2_base_id].iloc[0]

        rank_o1_15 = int(row_best_o1['rank_o1_p15'])
        rank_o1_30 = int(row_best_o1['rank_o1_p30'])
        rank_o2_15 = int(row_best_o2['rank_o2_p15'])
        rank_o2_30 = int(row_best_o2['rank_o2_p30'])

        shift_o1_15 = rank_o1_15 - 1
        shift_o1_30 = rank_o1_30 - 1
        shift_o2_15 = rank_o2_15 - 1
        shift_o2_30 = rank_o2_30 - 1

        rank_verdict = compute_rank_verdict(shift_o1_15, shift_o1_30, shift_o2_15, shift_o2_30)

        # Spearman rho on verified front ONLY
        if n_pareto >= 5:
            rho_o1_p15, _ = spearmanr(df_pareto['O1_ml_base'], df_pareto['O1_ml_plus1p5'])
            rho_o1_p30, _ = spearmanr(df_pareto['O1_ml_base'], df_pareto['O1_ml_plus3p0'])
            rho_o2_p15, _ = spearmanr(df_pareto['O2_base'], df_pareto['O2_plus1p5'])
            rho_o2_p30, _ = spearmanr(df_pareto['O2_base'], df_pareto['O2_plus3p0'])
            mono_verdict = compute_monotonicity_verdict(n_pareto, float(rho_o1_p15), float(rho_o1_p30), float(rho_o2_p15), float(rho_o2_p30))
            rho_o1_15_str = f"{rho_o1_p15:.4f}"
            rho_o1_30_str = f"{rho_o1_p30:.4f}"
            rho_o2_15_str = f"{rho_o2_p15:.4f}"
            rho_o2_30_str = f"{rho_o2_p30:.4f}"
        else:
            rho_o1_15_str = "not testable"
            rho_o1_30_str = "not testable"
            rho_o2_15_str = "not testable"
            rho_o2_30_str = "not testable"
            mono_verdict = "not testable (front size < 5)"

        city_summaries[city] = {
            'n_designs': n_designs,
            'n_pareto': n_pareto,
            'best_o1_base_id': best_o1_base_id,
            'rank_o1_15': rank_o1_15,
            'rank_o1_30': rank_o1_30,
            'best_o2_base_id': best_o2_base_id,
            'rank_o2_15': rank_o2_15,
            'rank_o2_30': rank_o2_30,
            'rank_verdict': rank_verdict,
            'rho_o1_15_str': rho_o1_15_str,
            'rho_o1_30_str': rho_o1_30_str,
            'rho_o2_15_str': rho_o2_15_str,
            'rho_o2_30_str': rho_o2_30_str,
            'mono_verdict': mono_verdict,
            'df_city': df_city,
            'df_pareto': df_pareto
        }

    # TABLE 1: RANK PRESERVATION
    lines.append("\n" + "=" * 145)
    lines.append("TABLE 1: BEST DESIGN RANK PRESERVATION SUMMARY ACROSS 5 FLAGSHIPS")
    lines.append("Evaluates whether baseline-best designs remain #1 under +1.5 °C and +3.0 °C warming scenarios")
    lines.append("=" * 145)
    lines.append(f"{'City':<12} | {'Front':<6} | {'Best O1_ml ID':<22} | {'Base':<5} | {'+1.5C':<6} | {'+3.0C':<6} | {'Best O2 ID':<22} | {'Base':<5} | {'+1.5C':<6} | {'+3.0C':<6} | {'Computed Verdict'}")
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        if s['n_pareto'] >= 5:
            lines.append(
                f"{city:<12} | {s['n_pareto']:<6} | {s['best_o1_base_id']:<22} | {'#1':<5} | "
                f"{'#'+str(s['rank_o1_15']):<6} | {'#'+str(s['rank_o1_30']):<6} | "
                f"{s['best_o2_base_id']:<22} | {'#1':<5} | "
                f"{'#'+str(s['rank_o2_15']):<6} | {'#'+str(s['rank_o2_30']):<6} | "
                f"{s['rank_verdict']}"
            )
        else:
            lines.append(
                f"{city:<12} | {s['n_pareto']:<6} | {s['best_o1_base_id']:<22} | {'#1':<5} | "
                f"{'not testable':<6} | {'not testable':<6} | "
                f"{s['best_o2_base_id']:<22} | {'#1':<5} | "
                f"{'not testable':<6} | {'not testable':<6} | "
                f"not testable (front size < 5)"
            )
    lines.append("-" * 145)

    # TABLE 2: SPEARMAN RANK CORRELATIONS ON VERIFIED FRONT ONLY
    lines.append("\n" + "=" * 145)
    lines.append("TABLE 2: SPEARMAN RANK CORRELATIONS (RHO) ON VERIFIED PARETO FRONT ONLY (EXCLUDING R1/R2/R3)")
    lines.append("Evaluates monotonicity of front design ordering between Baseline and Future Warming Scenarios")
    lines.append("=" * 145)
    lines.append(f"{'City':<12} | {'Front Size':<11} | {'rho(O1_ml, +1.5C)':<18} | {'rho(O1_ml, +3.0C)':<18} | {'rho(O2, +1.5C)':<16} | {'rho(O2, +3.0C)':<16} | {'Computed Monotonicity Verdict'}")
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        lines.append(
            f"{city:<12} | {s['n_pareto']:<11} | {s['rho_o1_15_str']:<18} | {s['rho_o1_30_str']:<18} | "
            f"{s['rho_o2_15_str']:<16} | {s['rho_o2_30_str']:<16} | "
            f"{s['mono_verdict']}"
        )
    lines.append("-" * 145)

    # TABLE 3: REGRET PER CITY AND SCENARIO
    lines.append("\n" + "=" * 145)
    lines.append("TABLE 3: REGRET ANALYSIS PER CITY AND SCENARIO (VERIFIED PARETO FRONT)")
    lines.append("Regret = Value achieved by Baseline-Best design in scenario minus Lowest value achieved on front in that scenario")
    lines.append("O1_ml Regret in percentage points (pp) | O2 Regret in kWh/m2 and percentage (%)")
    lines.append("=" * 145)

    lines.append(
        f"{'City':<10} | {'Scenario':<9} | "
        f"{'BaseBest O1 ID':<20} | {'Achieved O1':<11} | {'ScenBest O1 ID':<20} | {'Min O1':<7} | {'Regret O1':<10} | "
        f"{'BaseBest O2 ID':<20} | {'Achieved O2':<11} | {'ScenBest O2 ID':<20} | {'Min O2':<7} | {'Regret O2 (kWh)':<15} | {'Regret O2 (%)'}"
    )
    lines.append("-" * 175)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        df_p = s['df_pareto']
        base_o1_id = s['best_o1_base_id']
        base_o2_id = s['best_o2_base_id']

        scenarios = [
            ('Baseline', 'O1_ml_base', 'O2_base'),
            ('+1.5 °C',  'O1_ml_plus1p5', 'O2_plus1p5'),
            ('+3.0 °C',  'O1_ml_plus3p0', 'O2_plus3p0')
        ]

        if s['n_pareto'] < 5:
            for sname, _, _ in scenarios:
                lines.append(
                    f"{city:<10} | {sname:<9} | "
                    f"{base_o1_id:<20} | {'not testable':<11} | {'not testable':<20} | {'N/A':<7} | {'not testable':<10} | "
                    f"{base_o2_id:<20} | {'not testable':<11} | {'not testable':<20} | {'N/A':<7} | {'not testable':<15} | {'not testable'}"
                )
            continue

        for sname, col_o1, col_o2 in scenarios:
            row_scen_best_o1 = df_p.loc[df_p[col_o1].idxmin()]
            row_scen_best_o2 = df_p.loc[df_p[col_o2].idxmin()]
            scen_best_o1_id = row_scen_best_o1['design_id']
            scen_best_o2_id = row_scen_best_o2['design_id']
            min_o1 = float(row_scen_best_o1[col_o1])
            min_o2 = float(row_scen_best_o2[col_o2])

            achieved_o1 = float(df_p.loc[df_p['design_id'] == base_o1_id, col_o1].values[0])
            achieved_o2 = float(df_p.loc[df_p['design_id'] == base_o2_id, col_o2].values[0])

            regret_o1_pp = achieved_o1 - min_o1
            regret_o2_kwh = achieved_o2 - min_o2
            regret_o2_pct = (regret_o2_kwh / min_o2 * 100.0) if min_o2 > 0 else 0.0

            lines.append(
                f"{city:<10} | {sname:<9} | "
                f"{base_o1_id:<20} | {achieved_o1:<11.2f} | {scen_best_o1_id:<20} | {min_o1:<7.2f} | {f'{regret_o1_pp:+.2f} pp':<10} | "
                f"{base_o2_id:<20} | {achieved_o2:<11.2f} | {scen_best_o2_id:<20} | {min_o2:<7.2f} | {f'{regret_o2_kwh:+.2f} kWh/m2':<15} | {f'{regret_o2_pct:.2f}%'}"
            )
        lines.append("-" * 175)

    # TABLE 4: DETAILED PERFORMANCE OF KEY DESIGNS
    lines.append("\n" + "=" * 145)
    lines.append("TABLE 4: KEY DESIGNS CLIMATE PERFORMANCE COMPARISON (BASELINE vs +1.5 °C vs +3.0 °C)")
    lines.append("=" * 145)
    lines.append(
        f"{'City':<10} | {'Design ID':<20} | {'Scenario':<10} | {'O1_ml(%)':<9} | {'dO1_ml':<8} | "
        f"{'O1_ad(%)':<9} | {'dO1_ad':<8} | {'O2(kWh)':<8} | {'dO2':<8} | {'Hr>35C':<7} | {'dHr>35C'}"
    )
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        df_c = s['df_city']
        key_ids = [
            'R1_Lightweight', 'R2_Conventional', 'R3_Code_Compliant',
            s['best_o1_base_id'], s['best_o2_base_id']
        ]
        # remove duplicate if best_o1 == best_o2
        seen = set()
        dedup_key_ids = [x for x in key_ids if not (x in seen or seen.add(x))]

        for did in dedup_key_ids:
            row_d = df_c[df_c['design_id'] == did].iloc[0]
            lines.append(
                f"{city:<10} | {did:<20} | {'Baseline':<10} | "
                f"{row_d['O1_ml_base']:<9.2f} | {'--':<8} | {row_d['O1_adapt_base']:<9.2f} | {'--':<8} | "
                f"{row_d['O2_base']:<8.2f} | {'--':<8} | {row_d['top_gt_35_base']:<7} | {'--'}"
            )
            d_o1_15_str = f"{row_d['dO1_ml_p15']:+.2f}"
            d_ad_15_str = f"{row_d['dO1_adapt_p15']:+.2f}"
            d_o2_15_str = f"{row_d['dO2_p15']:+.2f}"
            d_h35_15_str = f"{row_d['dHours35_p15']:+}"
            lines.append(
                f"{city:<10} | {did:<20} | {'+1.5 °C':<10} | "
                f"{row_d['O1_ml_plus1p5']:<9.2f} | {d_o1_15_str:<8} | "
                f"{row_d['O1_adapt_plus1p5']:<9.2f} | {d_ad_15_str:<8} | "
                f"{row_d['O2_plus1p5']:<8.2f} | {d_o2_15_str:<8} | "
                f"{row_d['top_gt_35_plus1p5']:<7} | {d_h35_15_str:<7}"
            )
            d_o1_30_str = f"{row_d['dO1_ml_p30']:+.2f}"
            d_ad_30_str = f"{row_d['dO1_adapt_p30']:+.2f}"
            d_o2_30_str = f"{row_d['dO2_p30']:+.2f}"
            d_h35_30_str = f"{row_d['dHours35_p30']:+}"
            lines.append(
                f"{city:<10} | {did:<20} | {'+3.0 °C':<10} | "
                f"{row_d['O1_ml_plus3p0']:<9.2f} | {d_o1_30_str:<8} | "
                f"{row_d['O1_adapt_plus3p0']:<9.2f} | {d_ad_30_str:<8} | "
                f"{row_d['O2_plus3p0']:<8.2f} | {d_o2_30_str:<8} | "
                f"{row_d['top_gt_35_plus3p0']:<7} | {d_h35_30_str:<7}"
            )
            lines.append("." * 145)
        lines.append("-" * 145)

    output_text = "\n".join(lines)
    with open(out_txt_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"Successfully generated {out_txt_path} ({len(output_text)} characters).")

if __name__ == "__main__":
    main()
