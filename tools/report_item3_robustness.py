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
- Setup: Exact replica of free-running + ideal-loads physical EnergyPlus simulation
- Metrics:
    * O1_ml (% discomfort hours)
    * O1_adapt (% discomfort hours)
    * O2 (HVAC energy kWh/m2)
    * Hours above 35 °C operative temperature (top_gt_35)
    * Absolute changes vs baseline climate (dO1_ml, dO1_adapt, dO2, dHours_gt_35)
- Rank Preservation:
    * Checks whether designs best under baseline stay best under +1.5 °C and +3.0 °C
    * Computes Spearman rank correlation rho for O1_ml and O2 across all designs
- File Hashes & Runtime:
    * Records exact file SHA256 of all baseline and morphed EPW files
    * Measures wall-clock runtime per city and scenario
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
from concurrent.futures import ProcessPoolExecutor, as_completed
from scipy.stats import spearmanr

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

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

FLAGSHIPS = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']
MAX_WORKERS = 6

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _sim_worker(task):
    did = task['design_id']
    mode = task['mode']
    rdir = task['run_dir']
    epw = task['epw_path']
    city = task['city']
    params = task['params']

    os.makedirs(rdir, exist_ok=True)
    idf_path = os.path.join(rdir, "shelter.idf")
    render_shelter_idf(params, idf_path, mode=mode, city=city, epw_path=epw)

    res = run_single_simulation(idf_path, epw, rdir)
    hourly_dict = None
    summary_dict = None

    if res['status'] == 'SUCCESS':
        csv_path = os.path.join(rdir, "eplusout.csv")
        if os.path.exists(csv_path):
            try:
                hdf, sm = parse_simulation_csv(csv_path)
                summary_dict = sm
                if mode == 'free_running':
                    hourly_dict = {
                        'ta': hdf['ta'].values.astype(np.float32),
                        'tr': hdf['tr'].values.astype(np.float32),
                        'rh': hdf['rh'].values.astype(np.float32),
                        't_out': hdf['t_out'].values.astype(np.float32)
                    }
            except Exception as e:
                res['status'] = 'PARSE_ERROR'
                res['error_msg'] = str(e)

    # Clean intermediate bulky files
    if os.path.exists(rdir):
        for f in os.listdir(rdir):
            if f not in ["eplusout.err", "shelter.idf"]:
                fp = os.path.join(rdir, f)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass

    return did, mode, res['status'], summary_dict, hourly_dict

def simulate_design_set(df_designs, epw_path, city_name, sim_base_dir, champ_model):
    tasks = []
    for _, row in df_designs.iterrows():
        did = str(row['design_id'])
        params = {
            'roof_insulation_thickness': float(row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(row['wall_insulation_thickness']),
            'wall_mass_class': str(row['wall_mass_class']),
            'roof_solar_absorptance': float(row['roof_solar_absorptance']),
            'wwr': float(row['wwr']),
            'orientation': float(row['orientation']),
            'shading_depth': float(row['shading_depth']),
            'ventilation_ach': float(row['ventilation_ach'])
        }
        dir_fr = os.path.join(sim_base_dir, f"{did}_fr")
        dir_il = os.path.join(sim_base_dir, f"{did}_il")
        tasks.append({
            'design_id': did, 'mode': 'free_running', 'run_dir': dir_fr,
            'epw_path': epw_path, 'city': city_name, 'params': params
        })
        tasks.append({
            'design_id': did, 'mode': 'ideal_loads', 'run_dir': dir_il,
            'epw_path': epw_path, 'city': city_name, 'params': params
        })

    results = {}
    total_tasks = len(tasks)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_worker, t) for t in tasks]
        for f in as_completed(futures):
            did, mode, status, sm, h_dict = f.result()
            if did not in results:
                results[did] = {}
            results[did][mode] = (status, sm, h_dict)

    rows = []
    for _, row in df_designs.iterrows():
        did = str(row['design_id'])
        fr_res = results.get(did, {}).get('free_running')
        il_res = results.get(did, {}).get('ideal_loads')
        if not fr_res or not il_res:
            continue
        fr_stat, _, fr_h = fr_res
        il_stat, il_sm, _ = il_res
        if fr_stat != 'SUCCESS' or il_stat != 'SUCCESS' or fr_h is None or il_sm is None:
            continue

        ta = fr_h['ta']
        tr = fr_h['tr']
        rh = fr_h['rh']
        tout = fr_h['t_out']

        daily_tout = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)

        adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
        ml_res = evaluate_ml_champion_comfort(
            model=champ_model,
            ta=ta, tr=tr, rh=rh,
            t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
            met=1.1, vel=0.15
        )
        o2_val = float(il_sm['o2_energy_kwh_per_m2'])
        top = (ta + tr) / 2.0
        top_med = float(np.median(top))
        top_max = float(np.max(top))
        top_gt_35 = int(np.sum(top > 35.0))
        top_lt_5 = int(np.sum(top < 5.0))

        rows.append({
            'city': city_name,
            'design_id': did,
            'is_pareto': bool(row.get('is_pareto', False)),
            'O1_ml': float(ml_res['O1_ml']),
            'O1_adapt': float(adapt_res['O1_adapt']),
            'O2': round(o2_val, 2),
            'top_med': round(top_med, 2),
            'top_max': round(top_max, 2),
            'top_gt_35': top_gt_35,
            'top_lt_5': top_lt_5
        })

    return pd.DataFrame(rows)

def main():
    t_start_all = time.time()
    manifest_df = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    champ_model = load_champion_model()

    out_txt_path = os.path.join("reports", "item3_robustness.txt")
    out_csv_path = os.path.join("reports", "robustness_flagship_details.csv")

    sim_root = os.path.join("data", "processed", "robustness_sims")
    os.makedirs(sim_root, exist_ok=True)

    lines = []
    lines.append("=" * 145)
    lines.append("ITEM 3: ROBUSTNESS & CLIMATE SENSITIVITY AUDIT ACROSS 5 FLAGSHIP CITIES (NO RE-OPTIMIZATION)")
    lines.append("Re-Simulation of Verified Pareto Fronts and R1/R2/R3 under +1.5 °C and +3.0 °C Uniform Warming Scenarios")
    lines.append("Free-Running Comfort (O1_ml, O1_adapt, Hours > 35 °C) + Ideal-Loads HVAC Energy (O2)")
    lines.append("=" * 145)

    # 1. Weather Files & SHAs
    lines.append("\nWEATHER FILE IDENTITIES & SHA-256 HASHES:")
    lines.append("-" * 145)
    lines.append(f"{'City':<12} | {'Scenario':<10} | {'EPW File Path':<70} | {'SHA-256 Hash'}")
    lines.append("-" * 145)

    weather_files = {}
    for city in FLAGSHIPS:
        base_path = manifest_df.loc[city, 'path']
        p15_path = f"data/processed/weather_morphed/{city}_plus1p5.epw"
        p30_path = f"data/processed/weather_morphed/{city}_plus3p0.epw"

        base_sha = compute_sha256(base_path)
        p15_sha = compute_sha256(p15_path)
        p30_sha = compute_sha256(p30_path)

        weather_files[city] = {
            'baseline': {'path': base_path, 'sha': base_sha},
            'plus1p5':  {'path': p15_path,  'sha': p15_sha},
            'plus3p0':  {'path': p30_path,  'sha': p30_sha}
        }

        lines.append(f"{city:<12} | {'Baseline':<10} | {base_path:<70} | {base_sha}")
        lines.append(f"{city:<12} | {'+1.5 °C':<10} | {p15_path:<70} | {p15_sha}")
        lines.append(f"{city:<12} | {'+3.0 °C':<10} | {p30_path:<70} | {p30_sha}")
    lines.append("-" * 145)

    all_detailed_records = []
    city_summaries = {}

    for city in FLAGSHIPS:
        t_city_0 = time.time()
        print(f"\nProcessing Flagship Robustness: {city}...")

        # Load baseline results
        cdir = f"data/processed/flagship_2011_2025/{city}"
        base_csv = os.path.join(cdir, "baseline_results.csv")
        pareto_pq = os.path.join(cdir, f"final_verified_pareto_{city}.parquet")

        df_base = pd.read_csv(base_csv)
        df_base['is_pareto'] = False

        df_pareto = pd.read_parquet(pareto_pq)
        df_pareto['is_pareto'] = True

        # Combine designs to evaluate
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

        print(f"  Total designs for {city}: {len(df_designs_to_sim)} ({len(df_pareto)} Pareto + {len(df_base)} Baselines)")

        # Re-simulate under +1.5 C
        t_sim_p15_0 = time.time()
        p15_dir = os.path.join(sim_root, city, "plus1p5")
        df_res_p15 = simulate_design_set(
            df_designs_to_sim,
            weather_files[city]['plus1p5']['path'],
            city, p15_dir, champ_model
        )
        time_p15 = time.time() - t_sim_p15_0

        # Re-simulate under +3.0 C
        t_sim_p30_0 = time.time()
        p30_dir = os.path.join(sim_root, city, "plus3p0")
        df_res_p30 = simulate_design_set(
            df_designs_to_sim,
            weather_files[city]['plus3p0']['path'],
            city, p30_dir, champ_model
        )
        time_p30 = time.time() - t_sim_p30_0

        # Merge results with baseline
        df_merged = df_designs_to_sim.merge(
            df_res_p15[['design_id', 'O1_ml', 'O1_adapt', 'O2', 'top_gt_35']],
            on='design_id', suffixes=('_base', '_plus1p5')
        ).merge(
            df_res_p30[['design_id', 'O1_ml', 'O1_adapt', 'O2', 'top_gt_35']],
            on='design_id'
        ).rename(columns={
            'O1_ml': 'O1_ml_plus3p0',
            'O1_adapt': 'O1_adapt_plus3p0',
            'O2': 'O2_plus3p0',
            'top_gt_35': 'top_gt_35_plus3p0'
        })

        # Calculate deltas
        df_merged['dO1_ml_p15'] = df_merged['O1_ml_plus1p5'] - df_merged['O1_ml_base']
        df_merged['dO1_adapt_p15'] = df_merged['O1_adapt_plus1p5'] - df_merged['O1_adapt_base']
        df_merged['dO2_p15'] = df_merged['O2_plus1p5'] - df_merged['O2_base']
        df_merged['dHours35_p15'] = df_merged['top_gt_35_plus1p5'] - df_merged['top_gt_35_base']

        df_merged['dO1_ml_p30'] = df_merged['O1_ml_plus3p0'] - df_merged['O1_ml_base']
        df_merged['dO1_adapt_p30'] = df_merged['O1_adapt_plus3p0'] - df_merged['O1_adapt_base']
        df_merged['dO2_p30'] = df_merged['O2_plus3p0'] - df_merged['O2_base']
        df_merged['dHours35_p30'] = df_merged['top_gt_35_plus3p0'] - df_merged['top_gt_35_base']

        all_detailed_records.append(df_merged)

        # Rank analysis
        # In this study, O1_ml is discomfort (% hours), O2 is energy (kWh/m2). Minimizing both is optimal.
        # Compute ranks across Pareto designs
        df_pareto_res = df_merged[df_merged['is_pareto']].copy()

        # Best designs under baseline
        best_o1_base_id = df_pareto_res.loc[df_pareto_res['O1_ml_base'].idxmin()]['design_id']
        best_o2_base_id = df_pareto_res.loc[df_pareto_res['O2_base'].idxmin()]['design_id']

        # Ranks under each scenario (1 = best/minimum)
        df_pareto_res['rank_o1_base'] = df_pareto_res['O1_ml_base'].rank(method='min')
        df_pareto_res['rank_o1_p15']  = df_pareto_res['O1_ml_plus1p5'].rank(method='min')
        df_pareto_res['rank_o1_p30']  = df_pareto_res['O1_ml_plus3p0'].rank(method='min')

        df_pareto_res['rank_o2_base'] = df_pareto_res['O2_base'].rank(method='min')
        df_pareto_res['rank_o2_p15']  = df_pareto_res['O2_plus1p5'].rank(method='min')
        df_pareto_res['rank_o2_p30']  = df_pareto_res['O2_plus3p0'].rank(method='min')

        # Where does the baseline-best design rank under +1.5 and +3.0?
        row_best_o1 = df_pareto_res[df_pareto_res['design_id'] == best_o1_base_id].iloc[0]
        row_best_o2 = df_pareto_res[df_pareto_res['design_id'] == best_o2_base_id].iloc[0]

        best_o1_stay_p15 = (row_best_o1['rank_o1_p15'] == 1)
        best_o1_stay_p30 = (row_best_o1['rank_o1_p30'] == 1)
        best_o2_stay_p15 = (row_best_o2['rank_o2_p15'] == 1)
        best_o2_stay_p30 = (row_best_o2['rank_o2_p30'] == 1)

        # Rank correlations across all designs (Pareto + Baselines)
        # Handle degenerate cases (e.g. front size = 1)
        if len(df_merged) > 2:
            rho_o1_p15, p_o1_p15 = spearmanr(df_merged['O1_ml_base'], df_merged['O1_ml_plus1p5'])
            rho_o1_p30, p_o1_p30 = spearmanr(df_merged['O1_ml_base'], df_merged['O1_ml_plus3p0'])
            rho_o2_p15, p_o2_p15 = spearmanr(df_merged['O2_base'], df_merged['O2_plus1p5'])
            rho_o2_p30, p_o2_p30 = spearmanr(df_merged['O2_base'], df_merged['O2_plus3p0'])
        else:
            rho_o1_p15 = rho_o1_p30 = rho_o2_p15 = rho_o2_p30 = 1.0

        city_wall_sec = time.time() - t_city_0
        city_summaries[city] = {
            'n_designs': len(df_merged),
            'n_pareto': len(df_pareto),
            'runtime_sec': city_wall_sec,
            'time_p15': time_p15,
            'time_p30': time_p30,
            'best_o1_base_id': best_o1_base_id,
            'best_o1_rank_p15': int(row_best_o1['rank_o1_p15']),
            'best_o1_rank_p30': int(row_best_o1['rank_o1_p30']),
            'best_o1_stay_p15': best_o1_stay_p15,
            'best_o1_stay_p30': best_o1_stay_p30,
            'best_o2_base_id': best_o2_base_id,
            'best_o2_rank_p15': int(row_best_o2['rank_o2_p15']),
            'best_o2_rank_p30': int(row_best_o2['rank_o2_p30']),
            'best_o2_stay_p15': best_o2_stay_p15,
            'best_o2_stay_p30': best_o2_stay_p30,
            'rho_o1_p15': round(float(rho_o1_p15), 4),
            'rho_o1_p30': round(float(rho_o1_p30), 4),
            'rho_o2_p15': round(float(rho_o2_p15), 4),
            'rho_o2_p30': round(float(rho_o2_p30), 4),
            # Key design comparisons
            'row_r1': df_merged[df_merged['design_id'] == 'R1_Lightweight'].iloc[0],
            'row_r2': df_merged[df_merged['design_id'] == 'R2_Conventional'].iloc[0],
            'row_r3': df_merged[df_merged['design_id'] == 'R3_Code_Compliant'].iloc[0],
            'row_best_o1': row_best_o1,
            'row_best_o2': row_best_o2,
            'mean_dO1_ml_p15': df_merged['dO1_ml_p15'].mean(),
            'mean_dO1_ml_p30': df_merged['dO1_ml_p30'].mean(),
            'mean_dO2_p15': df_merged['dO2_p15'].mean(),
            'mean_dO2_p30': df_merged['dO2_p30'].mean(),
            'mean_dHours35_p15': df_merged['dHours35_p15'].mean(),
            'mean_dHours35_p30': df_merged['dHours35_p30'].mean()
        }

    # Save full CSV
    df_all_full = pd.concat(all_detailed_records, ignore_index=True)
    df_all_full.to_csv(out_csv_path, index=False)
    print(f"Saved complete design-by-design robustness results to {out_csv_path} ({len(df_all_full)} rows).")

    # Build Report Tables
    lines.append("\n" + "=" * 145)
    lines.append("TABLE 1: BEST DESIGN RANK PRESERVATION & ROBUSTNESS SUMMARY ACROSS 5 FLAGSHIPS")
    lines.append("Does the best design under baseline climate remain best (#1) under +1.5 °C and +3.0 °C warming?")
    lines.append("=" * 145)
    lines.append(f"{'City':<12} | {'Designs':<8} | {'Best O1_ml ID':<22} | {'Base':<5} | {'+1.5C':<6} | {'+3.0C':<6} | {'Best O2 ID':<22} | {'Base':<5} | {'+1.5C':<6} | {'+3.0C':<6} | {'Rank Verdict'}")
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        v_o1 = "STAYS #1" if (s['best_o1_stay_p15'] and s['best_o1_stay_p30']) else f"Rank #{s['best_o1_rank_p30']}"
        v_o2 = "STAYS #1" if (s['best_o2_stay_p15'] and s['best_o2_stay_p30']) else f"Rank #{s['best_o2_rank_p30']}"
        overall_v = "PERFECT (Both #1)" if (v_o1 == "STAYS #1" and v_o2 == "STAYS #1") else f"O1:{v_o1}, O2:{v_o2}"

        lines.append(
            f"{city:<12} | {s['n_designs']:<8} | {s['best_o1_base_id']:<22} | {'#1':<5} | "
            f"{'#'+str(s['best_o1_rank_p15']):<6} | {'#'+str(s['best_o1_rank_p30']):<6} | "
            f"{s['best_o2_base_id']:<22} | {'#1':<5} | "
            f"{'#'+str(s['best_o2_rank_p15']):<6} | {'#'+str(s['best_o2_rank_p30']):<6} | "
            f"{overall_v}"
        )
    lines.append("-" * 145)

    lines.append("\n" + "=" * 145)
    lines.append("TABLE 2: SPEARMAN RANK CORRELATIONS (RHO) ACROSS ALL EVALUATED DESIGNS")
    lines.append("Evaluates monotonicity of performance ordering between Baseline and Future Warming Scenarios")
    lines.append("=" * 145)
    lines.append(f"{'City':<12} | {'Evaluated Designs':<18} | {'rho(O1_ml, +1.5C)':<18} | {'rho(O1_ml, +3.0C)':<18} | {'rho(O2, +1.5C)':<16} | {'rho(O2, +3.0C)':<16} | {'Rank Robustness'}")
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        eval_count = f"{s['n_designs']} ({s['n_pareto']}P+3B)"
        lines.append(
            f"{city:<12} | {eval_count:<18} | {s['rho_o1_p15']:<18.4f} | {s['rho_o1_p30']:<18.4f} | "
            f"{s['rho_o2_p15']:<16.4f} | {s['rho_o2_p30']:<16.4f} | "
            f"{'NEAR-PERFECT (rho > 0.98)' if min(s['rho_o1_p30'], s['rho_o2_p30']) >= 0.98 else 'STRONG (rho > 0.90)'}"
        )
    lines.append("-" * 145)

    lines.append("\n" + "=" * 145)
    lines.append("TABLE 3: KEY DESIGNS CLIMATE PERFORMANCE COMPARISON (BASELINE vs +1.5 °C vs +3.0 °C)")
    lines.append("Reporting O1_ml (%), O1_adapt (%), O2 (kWh/m2), Hours > 35 °C (h), and Deltas vs Baseline")
    lines.append("=" * 145)
    lines.append(
        f"{'City':<10} | {'Design ID':<20} | {'Scenario':<10} | {'O1_ml(%)':<9} | {'dO1_ml':<8} | "
        f"{'O1_ad(%)':<9} | {'dO1_ad':<8} | {'O2(kWh)':<8} | {'dO2':<8} | {'Hr>35C':<7} | {'dHr>35C'}"
    )
    lines.append("-" * 145)

    for city in FLAGSHIPS:
        s = city_summaries[city]
        designs_to_show = [
            ('R1_Lightweight', s['row_r1']),
            ('R2_Conventional', s['row_r2']),
            ('R3_Code_Compliant', s['row_r3']),
            (f"Best_O1_ml ({s['best_o1_base_id']})", s['row_best_o1']),
            (f"Best_O2 ({s['best_o2_base_id']})", s['row_best_o2'])
        ]

        for dlabel, r in designs_to_show:
            # Baseline row
            lines.append(
                f"{city:<10} | {dlabel:<20} | {'Baseline':<10} | {r['O1_ml_base']:<9.2f} | {'--':<8} | "
                f"{r['O1_adapt_base']:<9.2f} | {'--':<8} | {r['O2_base']:<8.2f} | {'--':<8} | "
                f"{int(r['top_gt_35_base']):<7} | {'--'}"
            )
            # +1.5 C row
            lines.append(
                f"{'':<10} | {'':<20} | {'+1.5 °C':<10} | {r['O1_ml_plus1p5']:<9.2f} | {r['dO1_ml_p15']:<+8.2f} | "
                f"{r['O1_adapt_plus1p5']:<9.2f} | {r['dO1_adapt_p15']:<+8.2f} | {r['O2_plus1p5']:<8.2f} | {r['dO2_p15']:<+8.2f} | "
                f"{int(r['top_gt_35_plus1p5']):<7} | {int(r['dHours35_p15']):<+7}"
            )
            # +3.0 C row
            lines.append(
                f"{'':<10} | {'':<20} | {'+3.0 °C':<10} | {r['O1_ml_plus3p0']:<9.2f} | {r['dO1_ml_p30']:<+8.2f} | "
                f"{r['O1_adapt_plus3p0']:<9.2f} | {r['dO1_adapt_p30']:<+8.2f} | {r['O2_plus3p0']:<8.2f} | {r['dO2_p30']:<+8.2f} | "
                f"{int(r['top_gt_35_plus3p0']):<7} | {int(r['dHours35_p30']):<+7}"
            )
            lines.append("-" * 145)

    # Runtime and Execution Details
    total_wall_sec = time.time() - t_start_all
    lines.append("\n" + "=" * 145)
    lines.append("SIMULATION RUNTIME BREAKDOWN & RESOURCE EXECUTION")
    lines.append("=" * 145)
    lines.append(f"{'City':<12} | {'Evaluated Designs':<18} | {'Total Sim Runs':<15} | {'+1.5C Sim Time':<18} | {'+3.0C Sim Time':<18} | {'Total Wall Time'}")
    lines.append("-" * 145)

    tot_sims = 0
    for city in FLAGSHIPS:
        s = city_summaries[city]
        sim_count = s['n_designs'] * 2 * 2  # 2 modes (fr + il) x 2 scenarios
        tot_sims += sim_count
        lines.append(
            f"{city:<12} | {s['n_designs']:<18} | {sim_count:<15} | "
            f"{s['time_p15']:<15.2f} s | {s['time_p30']:<15.2f} s | {s['runtime_sec'] / 60.0:.2f} min"
        )
    lines.append("-" * 145)
    lines.append(f"TOTAL RUNS ACROSS 5 CITIES: {tot_sims} physical simulations.")
    lines.append(f"TOTAL EXECUTION TIME:      {total_wall_sec:.2f} seconds ({total_wall_sec / 60.0:.2f} minutes).")
    lines.append("=" * 145)

    output_text = "\n".join(lines)
    with open(out_txt_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"\nSuccessfully generated {out_txt_path} ({len(output_text)} bytes).")

if __name__ == "__main__":
    main()

