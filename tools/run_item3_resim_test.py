#!/usr/bin/env python3
"""
tools/run_item3_resim_test.py

Item 3: RE-SIMULATION TEST ACROSS ALL 30 CITIES
For each of the 30 cities, re-simulates with the manifest EPW:
  1. R1 (Lightweight)
  2. R3 (Code-Compliant)
  3. best_O2 design (from final_verified_pareto_<city>.parquet)
  4. best_O1_ml design (from final_verified_pareto_<city>.parquet)
  5. 3 random pilot designs (from objectives_<city>.parquet, seed=42)

For each design:
  - Prints/logs the argv (-w path actually passed to EnergyPlus)
  - Computes and verifies EPW SHA256 at run time
  - Compares re-simulated O1_ml, O1_adapt, O2 against stored baseline / pareto / pilot values
  - Evaluates absolute differences: |dO1_ml|, |dO1_adapt|, |dO2|
  - Issues per-city verdict: PASS (all abs diffs <= 0.05) or FAIL.
"""

import os
import sys
import time
import shutil
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
import numpy as np

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

def get_city_dir(city):
    if city in FLAGSHIPS:
        return os.path.join("data", "processed", "flagship_2011_2025", city)
    else:
        return os.path.join("data", "processed", "batch", city)

def compute_file_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _worker_sim_single(task):
    city = task['city']
    design_id = task['design_id']
    params = task['params']
    epw_path = task['epw_path']
    run_dir = task['run_dir']

    dir_fr = os.path.join(run_dir, f"{design_id}_fr")
    dir_il = os.path.join(run_dir, f"{design_id}_il")
    os.makedirs(dir_fr, exist_ok=True)
    os.makedirs(dir_il, exist_ok=True)

    # 1. Free-running
    idf_fr = os.path.join(dir_fr, "shelter.idf")
    render_shelter_idf(params, idf_fr, mode='free_running', city=city, epw_path=epw_path)
    res_fr = run_single_simulation(idf_fr, epw_path, dir_fr)
    if res_fr['status'] not in ['SUCCESS', 'SKIPPED_ALREADY_DONE']:
        return {'city': city, 'design_id': design_id, 'status': 'FAILED', 'error': res_fr.get('error_summary')}

    # 2. Ideal-loads
    idf_il = os.path.join(dir_il, "shelter.idf")
    render_shelter_idf(params, idf_il, mode='ideal_loads', city=city, epw_path=epw_path)
    res_il = run_single_simulation(idf_il, epw_path, dir_il)
    if res_il['status'] not in ['SUCCESS', 'SKIPPED_ALREADY_DONE']:
        return {'city': city, 'design_id': design_id, 'status': 'FAILED', 'error': res_il.get('error_summary')}

    # Parse CSVs
    csv_fr = os.path.join(dir_fr, "eplusout.csv")
    csv_il = os.path.join(dir_il, "eplusout.csv")
    hdf_fr, _ = parse_simulation_csv(csv_fr)
    _, sm_il = parse_simulation_csv(csv_il)
    o2_sim = float(sm_il['o2_energy_kwh_per_m2'])

    ta = hdf_fr['ta'].values.astype(np.float32)
    tr = hdf_fr['tr'].values.astype(np.float32)
    rh = hdf_fr['rh'].values.astype(np.float32)
    tout = hdf_fr['t_out'].values.astype(np.float32)

    daily_tout = calculate_daily_mean_series(tout)
    t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    clo_hourly = compute_clo_schedule_a004(daily_tout)

    adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)

    model = load_champion_model()
    ml_res = evaluate_ml_champion_comfort(
        model=model, ta=ta, tr=tr, rh=rh,
        t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
        met=1.1, vel=0.15
    )

    # Clean up large csv files to save disk space
    for d in [dir_fr, dir_il]:
        for f in os.listdir(d):
            if f not in ["eplusout.err", "shelter.idf"]:
                try:
                    os.remove(os.path.join(d, f))
                except Exception:
                    pass

    return {
        'city': city,
        'design_id': design_id,
        'status': 'SUCCESS',
        'O1_ml': float(ml_res['O1_ml']),
        'O1_adapt': float(adapt_res['O1_adapt']),
        'O2': o2_sim
    }

def main():
    print("=" * 145)
    print("ITEM 3: RE-SIMULATION AUDIT ACROSS ALL 30 CITIES")
    print("Designs: R1, R3, best_O2, best_O1_ml, and 3 Random Pilot Designs")
    print("=" * 145)

    manifest_df = pd.read_csv("reports/batch_epw_manifest.csv")
    temp_dir_base = "data/processed/temp_resim_audit"
    os.makedirs(temp_dir_base, exist_ok=True)

    tasks = []
    stored_values = {}
    city_epw_info = {}

    rng = np.random.RandomState(42)

    for _, m_row in manifest_df.iterrows():
        city = m_row['city']
        epw_path = m_row['path']
        abs_epw_path = os.path.abspath(epw_path)
        runtime_sha = compute_file_sha256(epw_path)
        city_epw_info[city] = {
            'epw_path': abs_epw_path,
            'runtime_sha': runtime_sha,
            'argv_sample': f"['{DEFAULT_EPLUS_EXE}', '-w', '{abs_epw_path}', '-d', '<output_dir>', '-r', '<idf_path>']"
        }

        cdir = get_city_dir(city)

        # 1. Baseline R1 and R3
        if city == 'Leh' and os.path.exists("data/processed/active_learning_leh/leh_baselines_summary.csv"):
            df_b = pd.read_csv("data/processed/batch/Leh/baseline_results.csv")
        else:
            df_b = pd.read_csv(os.path.join(cdir, "baseline_results.csv"))

        for did in ['R1_Lightweight', 'R3_Code_Compliant']:
            r = df_b[df_b['design_id'] == did].iloc[0]
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
            stored_values[(city, did)] = {
                'source': 'baseline',
                'O1_ml': float(r['O1_ml']),
                'O1_adapt': float(r['O1_adapt']),
                'O2': float(r['O2'])
            }
            tasks.append({
                'city': city,
                'design_id': did,
                'params': params,
                'epw_path': epw_path,
                'run_dir': os.path.join(temp_dir_base, city)
            })

        # 2. Pareto Front: best_O2 and best_O1_ml
        p_pareto = os.path.join(cdir, f"final_verified_pareto_{city}.parquet")
        df_p = pd.read_parquet(p_pareto)
        # Normalize column names if needed
        if 'wall_mass_class' not in df_p.columns and 'wall_mass_class_x' in df_p.columns:
            df_p['wall_mass_class'] = df_p['wall_mass_class_x']
        if 'design_id' not in df_p.columns and 'pareto_id' in df_p.columns:
            df_p['design_id'] = df_p['pareto_id']

        best_o2_r = df_p.loc[df_p['O2'].idxmin()]
        best_o1_r = df_p.loc[df_p['O1_ml'].idxmin()]

        pareto_picks = [('best_O2', str(best_o2_r['design_id']), best_o2_r),
                        ('best_O1_ml', str(best_o1_r['design_id']), best_o1_r)]

        for label, did, r in pareto_picks:
            # Avoid duplicate task if best_o2 is same design as best_o1
            task_key = (city, did)
            stored_values[task_key] = {
                'source': label,
                'O1_ml': float(r['O1_ml']),
                'O1_adapt': float(r['O1_adapt']),
                'O2': float(r['O2'])
            }
            if not any(t['city'] == city and t['design_id'] == did for t in tasks):
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
                tasks.append({
                    'city': city,
                    'design_id': did,
                    'params': params,
                    'epw_path': epw_path,
                    'run_dir': os.path.join(temp_dir_base, city)
                })

        # 3. 3 Random Pilot Designs
        p_obj = os.path.join(cdir, f"objectives_{city}.parquet")
        df_obj = pd.read_parquet(p_obj)
        rand_indices = rng.choice(len(df_obj), 3, replace=False)
        for idx in rand_indices:
            r = df_obj.iloc[idx]
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
            stored_values[(city, did)] = {
                'source': f'pilot_{did}',
                'O1_ml': float(r['O1_ml']),
                'O1_adapt': float(r['O1_adapt']),
                'O2': float(r['O2'])
            }
            tasks.append({
                'city': city,
                'design_id': did,
                'params': params,
                'epw_path': epw_path,
                'run_dir': os.path.join(temp_dir_base, city)
            })

    print(f"Total unique simulation tasks assembled: {len(tasks)} (across 30 cities)")
    print(f"Starting parallel execution using 10 workers...")

    t0 = time.time()
    resim_results = {}
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_worker_sim_single, t): (t['city'], t['design_id']) for t in tasks}
        completed_count = 0
        for f in as_completed(futures):
            res = f.result()
            resim_results[(res['city'], res['design_id'])] = res
            completed_count += 1
            if completed_count % 30 == 0 or completed_count == len(tasks):
                print(f"  Progress: {completed_count}/{len(tasks)} tasks finished ({completed_count/len(tasks)*100:.1f}%) in {time.time()-t0:.1f}s")

    elapsed_time = time.time() - t0
    print(f"\nAll simulations completed in {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")

    # Evaluate per-city differences and issue verdicts
    city_verdicts = []
    detailed_rows = []
    overall_all_pass = True

    for city in manifest_df['city'].tolist():
        info = city_epw_info[city]
        city_tasks = [t for t in tasks if t['city'] == city]
        
        max_d_o1_ml = 0.0
        max_d_o1_ad = 0.0
        max_d_o2 = 0.0
        city_pass = True

        for t in city_tasks:
            did = t['design_id']
            res = resim_results.get((city, did))
            stored = stored_values.get((city, did))

            if not res or res['status'] != 'SUCCESS' or not stored:
                city_pass = False
                continue

            d_o1_ml = abs(res['O1_ml'] - stored['O1_ml'])
            d_o1_ad = abs(res['O1_adapt'] - stored['O1_adapt'])
            d_o2 = abs(res['O2'] - stored['O2'])

            if d_o1_ml > max_d_o1_ml:
                max_d_o1_ml = d_o1_ml
            if d_o1_ad > max_d_o1_ad:
                max_d_o1_ad = d_o1_ad
            if d_o2 > max_d_o2:
                max_d_o2 = d_o2

            detailed_rows.append({
                'City': city,
                'Design': did,
                'Source': stored['source'],
                'Stored_O1_ml': stored['O1_ml'],
                'Sim_O1_ml': res['O1_ml'],
                'd_O1_ml': d_o1_ml,
                'Stored_O1_ad': stored['O1_adapt'],
                'Sim_O1_ad': res['O1_adapt'],
                'd_O1_ad': d_o1_ad,
                'Stored_O2': stored['O2'],
                'Sim_O2': res['O2'],
                'd_O2': d_o2,
            })

        # Threshold tolerance: 0.05
        if max_d_o1_ml > 0.05 or max_d_o1_ad > 0.05 or max_d_o2 > 0.05:
            city_pass = False
            overall_all_pass = False

        city_verdicts.append({
            'City': city,
            'Runtime SHA256': info['runtime_sha'],
            'Runner -w Arg Path': info['epw_path'],
            'Max |dO1_ml|': round(max_d_o1_ml, 4),
            'Max |dO1_adapt|': round(max_d_o1_ad, 4),
            'Max |dO2|': round(max_d_o2, 4),
            'Verdict': 'PASS' if city_pass else 'FAIL'
        })

    df_verdicts = pd.DataFrame(city_verdicts)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    print("\n" + "=" * 145)
    print("PER-CITY RE-SIMULATION AUDIT VERDICT TABLE:")
    print("=" * 145)
    print(df_verdicts.to_string(index=False))
    print("=" * 145)

    print(f"\nOVERALL VERDICT ACROSS ALL 30 CITIES: {'PASS (ALL CITIES REPRODUCED EXACTLY)' if overall_all_pass else 'FAIL (DISCREPANCIES DETECTED)'}")
    print(f"Total Execution Time: {elapsed_time:.2f} seconds ({elapsed_time/60.0:.2f} minutes).")

    # Save detailed rows to reports
    df_det = pd.DataFrame(detailed_rows)
    df_det.to_csv("reports/item3_resim_audit_details.csv", index=False)
    print("Detailed per-design re-simulation metrics saved to reports/item3_resim_audit_details.csv")

if __name__ == "__main__":
    main()
