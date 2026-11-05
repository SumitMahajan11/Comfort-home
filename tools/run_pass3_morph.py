#!/usr/bin/env python3
"""
tools/run_pass3_morph.py

Pass 3: Item 3 - CORRECTED MORPH AUDIT, 556-SIM ROBUSTNESS RE-RUN & REGRET DELTA ANALYSIS
1. Morph Integrity Checks for the 10 Corrected EPW Files:
   - Evaluates all 8760 hours per file
   - Counts hours with |dTdp - dTdb| > 0.5 C
   - Computes max diff of all other 33 columns vs baseline EPW
   - Computes baseline EPW SHA-256
2. Re-runs the 556-sim robustness evaluation on the 10 corrected files:
   - 139 designs across 5 flagship cities (Shimla: 41, Jodhpur: 29, New_Delhi: 48, Mumbai: 17, Bengaluru: 4)
   - 2 scenarios (+1.5 C and +3.0 C corrected EPWs)
   - 2 simulation modes per scenario (free_running and ideal_loads)
   - Total: 139 * 4 = 556 simulations using ProcessPoolExecutor
   - Writes to NEW output file: reports/robustness_flagship_details_corrected.csv (keeping old CSV untouched)
3. Computes and Reports Regret Deltas:
   - Compares regret under corrected morph vs regret under old morph for O1_ml, O1_adapt, and O2
   - Computes rank preservation and Spearman rho for corrected morph
   - Writes complete reports to:
     * reports/item3_robustness_corrected.txt
     * reports/pass3_morph.txt
"""

import os
import sys
import shutil
import hashlib
import tempfile
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation, DEFAULT_EPLUS_EXE
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
MAX_WORKERS = 10

def compute_sha256(filepath):
    if not filepath or not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def check_single_morph_file(corr_path, base_path, expected_delta_t):
    """
    Checks hours with |dTdp - dTdb| > 0.5 C and max diff of other columns vs baseline.
    """
    with open(base_path, 'r', encoding='latin-1') as f:
        base_lines = f.readlines()
    with open(corr_path, 'r', encoding='latin-1') as f:
        corr_lines = f.readlines()

    # EPW has 8 header lines
    base_data = base_lines[8:]
    corr_data = corr_lines[8:]
    assert len(base_data) == 8760, f"Expected 8760 hours, got {len(base_data)}"
    assert len(corr_data) == 8760, f"Expected 8760 hours, got {len(corr_data)}"

    hours_diff_gt_05 = 0
    max_dTdp_minus_dTdb = 0.0

    # Track max diff of all other columns (0-based indices, excluding 6: T_db, 7: T_dp)
    other_col_max_diffs = {}

    for h_idx in range(8760):
        b_parts = [p.strip() for p in base_data[h_idx].split(',')]
        c_parts = [p.strip() for p in corr_data[h_idx].split(',')]

        t_db_base = float(b_parts[6])
        t_dp_base = float(b_parts[7])
        t_db_corr = float(c_parts[6])
        t_dp_corr = float(c_parts[7])

        dTdb = t_db_corr - t_db_base
        dTdp = t_dp_corr - t_dp_base

        diff = abs(dTdp - dTdb)
        if diff > max_dTdp_minus_dTdb:
            max_dTdp_minus_dTdb = diff
        if diff > 0.5:
            hours_diff_gt_05 += 1

        for c_idx in range(len(b_parts)):
            if c_idx in (6, 7):
                continue
            b_val = b_parts[c_idx]
            c_val = c_parts[c_idx]
            if c_idx not in other_col_max_diffs:
                other_col_max_diffs[c_idx] = 0.0
            try:
                b_num = float(b_val)
                c_num = float(c_val)
                col_diff = abs(c_num - b_num)
                if col_diff > other_col_max_diffs[c_idx]:
                    other_col_max_diffs[c_idx] = col_diff
            except ValueError:
                if b_val != c_val:
                    other_col_max_diffs[c_idx] = 1.0  # string mismatch flag

    max_other_diff = max(other_col_max_diffs.values()) if other_col_max_diffs else 0.0

    return {
        'hours_diff_gt_05': hours_diff_gt_05,
        'max_dTdp_minus_dTdb': max_dTdp_minus_dTdb,
        'max_other_diff': max_other_diff
    }

def _sim_task_worker(task):
    """
    Worker function for running single design under a given EPW.
    """
    city, did, scen, epw_p, params, tmp_root = task
    rdir_fr = os.path.join(tmp_root, f"{city}_{did}_{scen}_fr")
    rdir_il = os.path.join(tmp_root, f"{city}_{did}_{scen}_il")
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

    # Note: ML model evaluation will be done in parent process to avoid pickling overhead
    o2_val = float(sm_il['o2_energy_kwh_per_m2'])
    top = (ta + tr) / 2.0
    top_gt_35 = int(np.sum(top > 35.0))

    # Free running arrays needed for parent comfort evaluation
    shutil.rmtree(rdir_fr, ignore_errors=True)
    shutil.rmtree(rdir_il, ignore_errors=True)

    return {
        'city': city,
        'design_id': did,
        'scen': scen,
        'ta': ta,
        'tr': tr,
        'rh': rh,
        't_rm_hourly': t_rm_hourly,
        'clo_hourly': clo_hourly,
        'o2_val': round(o2_val, 2),
        'top_gt_35': top_gt_35
    }

def main():
    t_start = time.time()
    manifest = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    old_details_csv = "reports/robustness_flagship_details.csv"
    df_old = pd.read_csv(old_details_csv)

    corr_details_csv = "reports/robustness_flagship_details_corrected.csv"
    corr_robustness_txt = "reports/item3_robustness_corrected.txt"
    out_pass3_morph_txt = "reports/pass3_morph.txt"

    lines = []
    lines.append("=" * 160)
    lines.append("PASS 3 - ITEM 3: CORRECTED MORPH AUDIT, 556-SIM ROBUSTNESS RE-RUN & REGRET DELTAS")
    lines.append("=" * 160)

    # 1. 10 CORRECTED FILES PSYCHROMETRIC AUDIT
    lines.append("\n" + "=" * 160)
    lines.append("1. PSYCHROMETRIC & COLUMN DIFF AUDIT FOR 10 CORRECTED MORPHED EPW FILES")
    lines.append("=" * 160)
    lines.append("Audit Criteria:")
    lines.append("  - Hours where |dTdp - dTdb| > 0.5 C (verifies absence of raw sensor discrepancy artifacts)")
    lines.append("  - Max diff of all other 33 columns vs baseline EPW (verifies strict differential preservation)")
    lines.append("  - Verbatim baseline EPW SHA-256 hash")
    lines.append("-" * 160)
    lines.append(
        f"{'City':<12} | {'Scenario':<10} | {'Hours |dTdp-dTdb|>0.5C':<26} | {'Max |dTdp-dTdb|':<18} | {'Max Diff Other Cols':<22} | {'Baseline EPW SHA-256'}"
    )
    lines.append("-" * 160)

    morph_audit_records = []
    for city in FLAGSHIPS:
        base_epw = manifest.loc[city, 'path']
        base_sha = compute_sha256(base_epw)
        for scen, exp_dt in [('plus1p5', 1.5), ('plus3p0', 3.0)]:
            corr_epw = f"data/processed/weather_morphed/{city}_{scen}_corrected.epw"
            stats = check_single_morph_file(corr_epw, base_epw, exp_dt)
            lines.append(
                f"{city:<12} | {scen:<10} | {stats['hours_diff_gt_05']:<26} | {stats['max_dTdp_minus_dTdb']:<18.4f} | {stats['max_other_diff']:<22.4f} | {base_sha}"
            )
            morph_audit_records.append({
                'city': city,
                'scen': scen,
                'hours_gt_05': stats['hours_diff_gt_05'],
                'max_diff': stats['max_dTdp_minus_dTdb'],
                'max_other': stats['max_other_diff'],
                'base_sha': base_sha
            })
    lines.append("-" * 160)

    # 2. RUN 556-SIM ROBUSTNESS ON CORRECTED MORPHED FILES
    lines.append("\n" + "=" * 160)
    lines.append("2. 556-SIMULATION CLIMATE ROBUSTNESS RE-RUN ON CORRECTED FILES")
    lines.append("=" * 160)

    champ_model = load_champion_model()
    tmp_sim_root = tempfile.mkdtemp(prefix='p3_robustness_sims_')

    tasks = []
    for city in FLAGSHIPS:
        df_city = df_old[df_old['city'] == city].copy()
        p15_corr = f"data/processed/weather_morphed/{city}_plus1p5_corrected.epw"
        p30_corr = f"data/processed/weather_morphed/{city}_plus3p0_corrected.epw"

        for _, r in df_city.iterrows():
            did = str(r['design_id'])
            params = {
                'roof_insulation_thickness': float(r['roof_insulation_thickness']),
                'wall_insulation_thickness': float(r['wall_insulation_thickness']),
                'wall_mass_class': str(r['wall_mass_class']),
                'roof_solar_absorptance': float(r['roof_solar_absorptance']),
                'wwr': float(r['wwr']),
                'orientation': float(r['orientation']),
                'shading_depth': float(r['shading_depth']),
                'ventilation_ach': float(r['ventilation_ach'])
            }
            # Task for plus1p5
            tasks.append((city, did, 'plus1p5', p15_corr, params, tmp_sim_root))
            # Task for plus3p0
            tasks.append((city, did, 'plus3p0', p30_corr, params, tmp_sim_root))

    print(f"Total design-scenario tasks to simulate: {len(tasks)} (each executes 2 modes = {len(tasks)*2} EnergyPlus runs)...")

    sim_results = {}
    done_count = 0
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(_sim_task_worker, t): t for t in tasks}
        for fut in as_completed(future_map):
            res = fut.result()
            c = res['city']
            d = res['design_id']
            s = res['scen']

            # Evaluate comfort in parent
            adapt_res = evaluate_adaptive_90_comfort(res['ta'], res['tr'], res['t_rm_hourly'])
            ml_res = evaluate_ml_champion_comfort(
                model=champ_model, ta=res['ta'], tr=res['tr'], rh=res['rh'],
                t_outdoor_hourly=res['t_rm_hourly'], clo_hourly=res['clo_hourly'], met=1.1, vel=0.15
            )

            sim_results[(c, d, s)] = {
                'O1_ml': float(ml_res['O1_ml']),
                'O1_adapt': float(adapt_res['O1_adapt']),
                'O2': res['o2_val'],
                'top_gt_35': res['top_gt_35']
            }
            done_count += 1
            if done_count % 25 == 0 or done_count == len(tasks):
                print(f"  Completed {done_count}/{len(tasks)} tasks ({done_count*2}/{len(tasks)*2} simulations)...")

    shutil.rmtree(tmp_sim_root, ignore_errors=True)

    # Build df_corrected
    corrected_rows = []
    for _, r in df_old.iterrows():
        c = r['city']
        did = r['design_id']

        res_15 = sim_results[(c, did, 'plus1p5')]
        res_30 = sim_results[(c, did, 'plus3p0')]

        row_dict = r.to_dict()
        # Update plus1p5
        row_dict['O1_ml_plus1p5'] = res_15['O1_ml']
        row_dict['O1_adapt_plus1p5'] = res_15['O1_adapt']
        row_dict['O2_plus1p5'] = res_15['O2']
        row_dict['top_gt_35_plus1p5'] = res_15['top_gt_35']

        # Update plus3p0
        row_dict['O1_ml_plus3p0'] = res_30['O1_ml']
        row_dict['O1_adapt_plus3p0'] = res_30['O1_adapt']
        row_dict['O2_plus3p0'] = res_30['O2']
        row_dict['top_gt_35_plus3p0'] = res_30['top_gt_35']

        # Recompute deltas
        row_dict['dO1_ml_p15'] = row_dict['O1_ml_plus1p5'] - row_dict['O1_ml_base']
        row_dict['dO1_adapt_p15'] = row_dict['O1_adapt_plus1p5'] - row_dict['O1_adapt_base']
        row_dict['dO2_p15'] = row_dict['O2_plus1p5'] - row_dict['O2_base']
        row_dict['dHours35_p15'] = row_dict['top_gt_35_plus1p5'] - row_dict['top_gt_35_base']

        row_dict['dO1_ml_p30'] = row_dict['O1_ml_plus3p0'] - row_dict['O1_ml_base']
        row_dict['dO1_adapt_p30'] = row_dict['O1_adapt_plus3p0'] - row_dict['O1_adapt_base']
        row_dict['dO2_p30'] = row_dict['O2_plus3p0'] - row_dict['O2_base']
        row_dict['dHours35_p30'] = row_dict['top_gt_35_plus3p0'] - row_dict['top_gt_35_base']

        corrected_rows.append(row_dict)

    df_corrected = pd.DataFrame(corrected_rows)
    df_corrected.to_csv(corr_details_csv, index=False)
    print(f"Corrected details CSV written to {corr_details_csv}")

    # 3. REGRET DELTA ANALYSIS: OLD MORPH VS CORRECTED MORPH
    lines.append("\n" + "=" * 160)
    lines.append("3. REGRET COMPARISON & DELTAS: CORRECTED MORPH VS OLD MORPH")
    lines.append("=" * 160)
    lines.append("Regret Formula: Regret = Achieved_by_BaseBest - Min_Achieved_on_Front")
    lines.append("Regret Delta = Regret_Corrected - Regret_Old")
    lines.append("-" * 160)
    lines.append(
        f"{'City':<12} | {'Scenario':<10} | "
        f"{'Old O1_ml Reg':<14} | {'New O1_ml Reg':<14} | {'dReg O1_ml':<12} | "
        f"{'Old O2 Reg':<14} | {'New O2 Reg':<14} | {'dReg O2':<12} | "
        f"{'Old O1_ad Reg':<14} | {'New O1_ad Reg':<14} | {'dReg O1_ad'}"
    )
    lines.append("-" * 160)

    regret_deltas_records = []

    for city in FLAGSHIPS:
        df_old_p = df_old[(df_old['city'] == city) & (df_old['is_pareto'] == True)].copy()
        df_new_p = df_corrected[(df_corrected['city'] == city) & (df_corrected['is_pareto'] == True)].copy()

        if len(df_old_p) <= 1:
            for scen in ['+1.5 C', '+3.0 C']:
                lines.append(
                    f"{city:<12} | {scen:<10} | {'not testable':<14} | {'not testable':<14} | {'--':<12} | "
                    f"{'not testable':<14} | {'not testable':<14} | {'--':<12} | "
                    f"{'not testable':<14} | {'not testable':<14} | {'--'}"
                )
            continue

        base_best_o1ml_id = df_old_p.loc[df_old_p['O1_ml_base'].idxmin(), 'design_id']
        base_best_o1ad_id = df_old_p.loc[df_old_p['O1_adapt_base'].idxmin(), 'design_id']
        base_best_o2_id = df_old_p.loc[df_old_p['O2_base'].idxmin(), 'design_id']

        row_old_bb_o1ml = df_old_p[df_old_p['design_id'] == base_best_o1ml_id].iloc[0]
        row_new_bb_o1ml = df_new_p[df_new_p['design_id'] == base_best_o1ml_id].iloc[0]

        row_old_bb_o1ad = df_old_p[df_old_p['design_id'] == base_best_o1ad_id].iloc[0]
        row_new_bb_o1ad = df_new_p[df_new_p['design_id'] == base_best_o1ad_id].iloc[0]

        row_old_bb_o2 = df_old_p[df_old_p['design_id'] == base_best_o2_id].iloc[0]
        row_new_bb_o2 = df_new_p[df_new_p['design_id'] == base_best_o2_id].iloc[0]

        for scen, col_suf in [('+1.5 C', 'plus1p5'), ('+3.0 C', 'plus3p0')]:
            # Old regret
            old_ach_o1ml = float(row_old_bb_o1ml[f'O1_ml_{col_suf}'])
            old_min_o1ml = float(df_old_p[f'O1_ml_{col_suf}'].min())
            old_reg_o1ml = old_ach_o1ml - old_min_o1ml

            old_ach_o2 = float(row_old_bb_o2[f'O2_{col_suf}'])
            old_min_o2 = float(df_old_p[f'O2_{col_suf}'].min())
            old_reg_o2 = old_ach_o2 - old_min_o2

            old_ach_o1ad = float(row_old_bb_o1ad[f'O1_adapt_{col_suf}'])
            old_min_o1ad = float(df_old_p[f'O1_adapt_{col_suf}'].min())
            old_reg_o1ad = old_ach_o1ad - old_min_o1ad

            # New regret
            new_ach_o1ml = float(row_new_bb_o1ml[f'O1_ml_{col_suf}'])
            new_min_o1ml = float(df_new_p[f'O1_ml_{col_suf}'].min())
            new_reg_o1ml = new_ach_o1ml - new_min_o1ml

            new_ach_o2 = float(row_new_bb_o2[f'O2_{col_suf}'])
            new_min_o2 = float(df_new_p[f'O2_{col_suf}'].min())
            new_reg_o2 = new_ach_o2 - new_min_o2

            new_ach_o1ad = float(row_new_bb_o1ad[f'O1_adapt_{col_suf}'])
            new_min_o1ad = float(df_new_p[f'O1_adapt_{col_suf}'].min())
            new_reg_o1ad = new_ach_o1ad - new_min_o1ad

            d_reg_o1ml = new_reg_o1ml - old_reg_o1ml
            d_reg_o2 = new_reg_o2 - old_reg_o2
            d_reg_o1ad = new_reg_o1ad - old_reg_o1ad

            lines.append(
                f"{city:<12} | {scen:<10} | "
                f"{old_reg_o1ml:<+14.2f} | {new_reg_o1ml:<+14.2f} | {d_reg_o1ml:<+12.2f} | "
                f"{old_reg_o2:<+14.2f} | {new_reg_o2:<+14.2f} | {d_reg_o2:<+12.2f} | "
                f"{old_reg_o1ad:<+14.2f} | {new_reg_o1ad:<+14.2f} | {d_reg_o1ad:<+12.2f}"
            )

            regret_deltas_records.append({
                'city': city,
                'scen': scen,
                'old_reg_o1ml': old_reg_o1ml,
                'new_reg_o1ml': new_reg_o1ml,
                'd_reg_o1ml': d_reg_o1ml,
                'old_reg_o2': old_reg_o2,
                'new_reg_o2': new_reg_o2,
                'd_reg_o2': d_reg_o2,
                'old_reg_o1ad': old_reg_o1ad,
                'new_reg_o1ad': new_reg_o1ad,
                'd_reg_o1ad': d_reg_o1ad
            })
    lines.append("-" * 160)

    # 4. SPEARMAN RHO FOR CORRECTED MORPH (WITHOUT VERDICT LABELS)
    lines.append("\n" + "=" * 160)
    lines.append("4. SPEARMAN RANK CORRELATIONS (RHO) UNDER CORRECTED MORPH (NO VERDICT LABELS)")
    lines.append("=" * 160)
    lines.append(
        f"{'City':<12} | {'Front N':<8} | {'rho(O1_ml, 1.5C)':<18} | {'rho(O1_ml, 3.0C)':<18} | {'rho(O2, 1.5C)':<18} | {'rho(O2, 3.0C)'}"
    )
    lines.append("-" * 160)

    for city in FLAGSHIPS:
        df_new_p = df_corrected[(df_corrected['city'] == city) & (df_corrected['is_pareto'] == True)].copy()
        if len(df_new_p) <= 1:
            lines.append(
                f"{city:<12} | {len(df_new_p):<8} | {'not testable':<18} | {'not testable':<18} | {'not testable':<18} | {'not testable'}"
            )
            continue
        rho_o1_15, _ = spearmanr(df_new_p['O1_ml_base'], df_new_p['O1_ml_plus1p5'])
        rho_o1_30, _ = spearmanr(df_new_p['O1_ml_base'], df_new_p['O1_ml_plus3p0'])
        rho_o2_15, _ = spearmanr(df_new_p['O2_base'], df_new_p['O2_plus1p5'])
        rho_o2_30, _ = spearmanr(df_new_p['O2_base'], df_new_p['O2_plus3p0'])

        lines.append(
            f"{city:<12} | {len(df_new_p):<8} | {rho_o1_15:<18.4f} | {rho_o1_30:<18.4f} | {rho_o2_15:<18.4f} | {rho_o2_30:<18.4f}"
        )
    lines.append("-" * 160)

    total_time = time.time() - t_start
    lines.append(f"\nExecution Time: {total_time:.2f} seconds ({total_time/60.0:.2f} minutes)")
    lines.append("\n" + "=" * 160)
    lines.append("END OF PASS 3 ITEM 3 MORPH REPORT")
    lines.append("=" * 160)

    report_content = "\n".join(lines)
    with open(out_pass3_morph_txt, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"Report written successfully to {out_pass3_morph_txt}")

    # Also generate full item3_robustness_corrected.txt
    with open(corr_robustness_txt, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"Report written successfully to {corr_robustness_txt}")

if __name__ == '__main__':
    main()
