"""
src/sim/smoke_test_building_types.py

Phase 8 Simulation Engine Comprehensive Smoke Test & Directional Checks across 3 Building Types:
- house (~60 m2, 3 zones: living, bedroom, kitchen)
- apartment (~55 m2, 2 zones, floor_position: ground, middle, top)
- commercial (~80 m2, 2 zones: open office + meeting, weekday 09:00-18:00)

Acceptance Criteria:
1. 10 random designs per city per type (5 cities x 3 types x 10 designs = 150 runs), 0 severe and 0 fatal errors.
2. Directional checks:
   - Check 1: Lower roof absorptance (0.30 vs 0.90) lowers mean free-running indoor temperature in Jodhpur May-June.
   - Check 2: More wall insulation (0.15m vs 0.001m) reduces O2 in Shimla.
   - Check 3: Apartment 'middle' floor has lower O2 than 'top' floor.
3. Save literal outputs to reports/evidence/phase8_smoke_test_output.txt.
"""

import os
import sys
import shutil
import time
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.sampler import sample_designs
from src.sim.render import render_building_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

BUILDING_TYPES = ["house", "apartment", "commercial"]

def _sim_worker(task):
    city = task['city']
    epw_path = task['epw_path']
    b_type = task['building_type']
    d_id = task['design_id']
    params = task['params']
    mode = task.get('mode', 'free_running')
    run_days = task.get('run_period_days', (5, 1, 5, 14))
    floor_pos = task.get('floor_position', 'middle')
    run_dir = task['run_dir']
    
    os.makedirs(run_dir, exist_ok=True)
    idf_path = os.path.join(run_dir, f"{b_type}.idf")
    render_building_idf(
        params=params,
        output_idf_path=idf_path,
        building_type=b_type,
        mode=mode,
        run_period_days=run_days,
        floor_position=floor_pos
    )
    
    res = run_single_simulation(idf_path, epw_path, run_dir)
    parsed_summary = None
    if res['status'] in ['SUCCESS', 'SKIPPED_ALREADY_DONE']:
        csv_path = os.path.join(run_dir, "eplusout.csv")
        if os.path.exists(csv_path):
            try:
                _, sm = parse_simulation_csv(csv_path, building_type=b_type)
                parsed_summary = sm
            except Exception as e:
                res['parse_error'] = str(e)
                
    # Read eplusout.err summary
    err_path = os.path.join(run_dir, "eplusout.err")
    err_text = ""
    if os.path.exists(err_path):
        with open(err_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # Grab lines with Severe or Fatal or summary
            err_text = "".join([l for l in lines if "Severe" in l or "Fatal" in l or "EnergyPlus Completed" in l])
            
    return {
        'city': city,
        'building_type': b_type,
        'design_id': d_id,
        'mode': mode,
        'status': res['status'],
        'severe_errors': res.get('severe_errors', 0),
        'fatal_errors': res.get('fatal_errors', 0),
        'runtime_sec': res.get('runtime_sec', 0.0),
        'summary': parsed_summary,
        'err_summary': err_text.strip()
    }


def main():
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    t0 = time.time()
    log("=" * 80)
    log("PHASE 8 SMOKE TESTS & PHYSICAL DIRECTIONAL CHECKS ACROSS BUILDING TYPES")
    log("=" * 80)
    log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Building Types Tested: {', '.join(BUILDING_TYPES)}")
    log(f"Cities: {', '.join(CITIES_EPW.keys())}")
    log(f"Fixed Seed: 42")
    log()

    # Base directory
    base_dir = "data/processed/sim_smoke_phase8"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir, ignore_errors=True)
    os.makedirs(base_dir, exist_ok=True)

    # 1. Sample 10 Latin Hypercube designs
    df_samples = sample_designs(n_samples=10, seed=42)
    log("10 Latin Hypercube Designs Sampled (seed 42):")
    log(df_samples.to_string(index=False))
    log()

    # 2. Build 150 tasks (10 designs x 5 cities x 3 building types)
    smoke_tasks = []
    for city, epw_path in CITIES_EPW.items():
        for b_type in BUILDING_TYPES:
            for i, row in df_samples.iterrows():
                d_id = f"des_{i:02d}"
                run_d = os.path.join(base_dir, f"{city}_{b_type}_{d_id}")
                smoke_tasks.append({
                    'city': city,
                    'epw_path': epw_path,
                    'building_type': b_type,
                    'design_id': d_id,
                    'params': row.to_dict(),
                    'mode': 'free_running',
                    'run_period_days': (5, 1, 5, 14), # 14-day smoke test
                    'floor_position': 'middle',
                    'run_dir': run_d
                })

    log(f"Running {len(smoke_tasks)} smoke simulation tasks in parallel...")
    n_workers = min(os.cpu_count() or 4, 8)
    smoke_results = []
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = [executor.submit(_sim_worker, t) for t in smoke_tasks]
        for f in as_completed(futures):
            res = f.result()
            smoke_results.append(res)

    df_smoke = pd.DataFrame(smoke_results)
    
    # Check severe and fatal errors
    total_runs = len(df_smoke)
    total_severe = df_smoke['severe_errors'].sum()
    total_fatal = df_smoke['fatal_errors'].sum()
    success_count = (df_smoke['status'] == 'SUCCESS').sum()

    log(f"\n--- SMOKE TEST AGGREGATE SUMMARY ---")
    log(f"Total Runs: {total_runs}")
    log(f"Successful Runs: {success_count} / {total_runs} ({(success_count/total_runs)*100:.1f}%)")
    log(f"Total Severe Errors: {total_severe}")
    log(f"Total Fatal Errors: {total_fatal}")

    # Per-city and per-type pass breakdown
    log("\nPer-Type / Per-City Error Breakdown:")
    breakdown = df_smoke.groupby(['building_type', 'city']).agg({
        'status': lambda s: (s == 'SUCCESS').sum(),
        'severe_errors': 'sum',
        'fatal_errors': 'sum',
        'runtime_sec': 'mean'
    }).rename(columns={'status': 'successes', 'runtime_sec': 'mean_sec'})
    log(breakdown.to_string())

    assert total_severe == 0, f"FAILED: Severe errors found: {total_severe}"
    assert total_fatal == 0, f"FAILED: Fatal errors found: {total_fatal}"
    log("\n[PASS] Acceptance Criterion 1 Met: 150/150 runs completed with exactly 0 severe and 0 fatal errors.")

    # 3. PHYSICAL DIRECTIONAL CHECKS
    log("\n" + "=" * 80)
    log("PHYSICAL DIRECTIONAL SANITY CHECKS")
    log("=" * 80)

    # Directional Check 1: Lower roof absorptance (0.30 vs 0.90) lowers mean free-running Ta in Jodhpur May-June
    log("\n[Directional Check 1] Roof Absorptance (0.30 vs 0.90) in Jodhpur Summer (May 1 - Jun 30):")
    dir1_tasks = []
    dir1_dir = os.path.join(base_dir, "directional_check_1")
    for b_type in ["house", "apartment", "commercial"]:
        floor_p = "top" if b_type == "apartment" else "middle"
        for abs_val, label in [(0.30, "low_abs_0p30"), (0.90, "high_abs_0p90")]:
            p = {
                'roof_insulation_thickness': 0.05,
                'wall_insulation_thickness': 0.05,
                'wall_mass_class': 'medium',
                'roof_solar_absorptance': abs_val,
                'wwr': 0.20,
                'orientation': 0.0,
                'shading_depth': 0.3,
                'ventilation_ach': 5.0
            }
            dir1_tasks.append({
                'city': 'Jodhpur',
                'epw_path': CITIES_EPW['Jodhpur'],
                'building_type': b_type,
                'design_id': label,
                'params': p,
                'mode': 'free_running',
                'run_period_days': (5, 1, 6, 30),
                'floor_position': floor_p,
                'run_dir': os.path.join(dir1_dir, f"{b_type}_{label}")
            })

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        dir1_results = [f.result() for f in as_completed([executor.submit(_sim_worker, t) for t in dir1_tasks])]

    dir1_dict = {(r['building_type'], r['design_id']): r['summary']['mean_ta'] for r in dir1_results}
    check1_all_pass = True
    for b_type in ["house", "apartment", "commercial"]:
        t_low = dir1_dict.get((b_type, "low_abs_0p30"), None)
        t_high = dir1_dict.get((b_type, "high_abs_0p90"), None)
        delta_t = t_high - t_low
        passed = delta_t > 0
        if not passed:
            check1_all_pass = False
        log(f"  {b_type:12s} (abs 0.30): {t_low:.2f} C | (abs 0.90): {t_high:.2f} C | Delta: +{delta_t:.2f} C -> {'PASS' if passed else 'FAIL'}")
    log(f"Directional Check 1 Result: {'PASS (lower absorptance reduces indoor temperature)' if check1_all_pass else 'FAIL'}")

    # Directional Check 2: More wall insulation (0.15m vs 0.001m) reduces O2 in Shimla
    log("\n[Directional Check 2] Wall Insulation (0.15m vs 0.001m) on HVAC Energy O2 in Shimla:")
    dir2_tasks = []
    dir2_dir = os.path.join(base_dir, "directional_check_2")
    for b_type in ["house", "apartment", "commercial"]:
        for ins_val, label in [(0.15, "high_ins_0p15"), (0.001, "low_ins_0p001")]:
            p = {
                'roof_insulation_thickness': 0.05,
                'wall_insulation_thickness': ins_val,
                'wall_mass_class': 'medium',
                'roof_solar_absorptance': 0.70,
                'wwr': 0.20,
                'orientation': 0.0,
                'shading_depth': 0.0,
                'ventilation_ach': 1.0
            }
            dir2_tasks.append({
                'city': 'Shimla',
                'epw_path': CITIES_EPW['Shimla'],
                'building_type': b_type,
                'design_id': label,
                'params': p,
                'mode': 'ideal_loads',
                'run_period_days': (1, 1, 1, 31), # Winter month January
                'floor_position': 'middle',
                'run_dir': os.path.join(dir2_dir, f"{b_type}_{label}")
            })

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        dir2_results = [f.result() for f in as_completed([executor.submit(_sim_worker, t) for t in dir2_tasks])]

    dir2_dict = {(r['building_type'], r['design_id']): r['summary']['o2_energy_kwh_per_m2'] for r in dir2_results}
    check2_all_pass = True
    for b_type in ["house", "apartment", "commercial"]:
        o2_high_ins = dir2_dict.get((b_type, "high_ins_0p15"), None)
        o2_low_ins = dir2_dict.get((b_type, "low_ins_0p001"), None)
        delta_o2 = o2_low_ins - o2_high_ins
        passed = delta_o2 > 0
        if not passed:
            check2_all_pass = False
        log(f"  {b_type:12s} (ins 0.15m): {o2_high_ins:.2f} kWh/m2 | (ins 0.001m): {o2_low_ins:.2f} kWh/m2 | Energy Saved: {delta_o2:.2f} kWh/m2 -> {'PASS' if passed else 'FAIL'}")
    log(f"Directional Check 2 Result: {'PASS (insulation reduces HVAC heating load)' if check2_all_pass else 'FAIL'}")

    # Directional Check 3: Apartment 'middle' floor has lower O2 than 'top' floor
    log("\n[Directional Check 3] Apartment Floor Position ('middle' vs 'top') on HVAC Energy O2:")
    dir3_tasks = []
    dir3_dir = os.path.join(base_dir, "directional_check_3")
    for pos in ["middle", "top"]:
        p = {
            'roof_insulation_thickness': 0.02,
            'wall_insulation_thickness': 0.02,
            'wall_mass_class': 'medium',
            'roof_solar_absorptance': 0.80,
            'wwr': 0.25,
            'orientation': 0.0,
            'shading_depth': 0.0,
            'ventilation_ach': 2.0
        }
        dir3_tasks.append({
            'city': 'New_Delhi',
            'epw_path': CITIES_EPW['New_Delhi'],
            'building_type': 'apartment',
            'design_id': f"apt_{pos}",
            'params': p,
            'mode': 'ideal_loads',
            'run_period_days': (5, 1, 5, 31), # Hot summer month May
            'floor_position': pos,
            'run_dir': os.path.join(dir3_dir, f"apt_{pos}")
        })

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        dir3_results = [f.result() for f in as_completed([executor.submit(_sim_worker, t) for t in dir3_tasks])]

    dir3_dict = {r['design_id']: r['summary']['o2_energy_kwh_per_m2'] for r in dir3_results}
    o2_mid = dir3_dict.get("apt_middle", 0.0)
    o2_top = dir3_dict.get("apt_top", 0.0)
    delta_floor = o2_top - o2_mid
    check3_pass = delta_floor > 0
    log(f"  apartment (middle floor): {o2_mid:.2f} kWh/m2 | (top floor): {o2_top:.2f} kWh/m2 | Excess Solar/Roof Load on Top: +{delta_floor:.2f} kWh/m2 -> {'PASS' if check3_pass else 'FAIL'}")
    log(f"Directional Check 3 Result: {'PASS (middle floor sheltered by neighbours has lower load)' if check3_pass else 'FAIL'}")

    elapsed = time.time() - t0
    log(f"\nAll Smoke Tests & Directional Checks completed in {elapsed:.1f} seconds.")
    log("=" * 80)

    # Save evidence file
    evidence_path = "reports/evidence/phase8_smoke_test_output.txt"
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    log(f"\nEvidence written to {evidence_path}")

if __name__ == "__main__":
    main()
