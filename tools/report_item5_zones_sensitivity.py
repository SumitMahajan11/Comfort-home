#!/usr/bin/env python3
"""
tools/report_item5_zones_sensitivity.py

Item 5: Climate Zone Sources & Baseline Sensitivity for Assumed Cities
1. Confirms Shimla reclassification:
   - In ECBC 2017 Table 11-1 (Page 201), Kullu and Shillong are listed under Cold, but Shimla
     is omitted. With no supporting document on disk, Shimla is reclassified from STANDARD to ASSUMED.
   - Total ASSUMED cities on disk: 8 (Agra, Bhuj, Bhuntar, Gangtok, Jammu, Port Blair, Varanasi, Shimla).
2. Prints the R3 baseline against which each of the 8 ASSUMED cities is compared.
3. Re-evaluates R3 under alternative climate zones for 3 cities (Gangtok, Bhuntar, Bhuj) using EnergyPlus:
   - Gangtok (Cold -> Composite)
   - Bhuntar (Cold -> Composite)
   - Bhuj (Hot-Dry -> Composite [identical], Temperate, Cold)
4. Reports the change in pct_better_R3_O2 and pp_better_R3_O1_ml.
"""

import os
import sys
import numpy as np
import pandas as pd

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

ASSUMED_CITIES = ['Agra', 'Bhuj', 'Bhuntar', 'Gangtok', 'Jammu', 'Port Blair', 'Varanasi', 'Shimla']
FLAGSHIPS = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']

def get_city_dir(city):
    if city in FLAGSHIPS:
        return os.path.join("data", "processed", "flagship_2011_2025", city)
    else:
        return os.path.join("data", "processed", "batch", city)

def simulate_one_design(city, epw_path, params, design_name, champ_model):
    """Runs a paired free_running and ideal_loads EnergyPlus simulation for a design."""
    sim_base = os.path.join("data", "simulations", "zone_sensitivity", city, design_name)
    rdir_fr = os.path.join(sim_base, "fr")
    rdir_il = os.path.join(sim_base, "il")
    import shutil
    if os.path.exists(sim_base):
        shutil.rmtree(sim_base)
    os.makedirs(rdir_fr, exist_ok=True)
    os.makedirs(rdir_il, exist_ok=True)

    idf_fr = os.path.join(rdir_fr, "shelter.idf")
    idf_il = os.path.join(rdir_il, "shelter.idf")

    render_shelter_idf(params, idf_fr, mode='free_running', city=city, epw_path=epw_path)
    render_shelter_idf(params, idf_il, mode='ideal_loads', city=city, epw_path=epw_path)

    res_fr = run_single_simulation(idf_fr, epw_path, rdir_fr)
    res_il = run_single_simulation(idf_il, epw_path, rdir_il)

    if res_fr['status'] not in ['SUCCESS', 'SKIPPED_ALREADY_DONE'] or res_il['status'] not in ['SUCCESS', 'SKIPPED_ALREADY_DONE']:
        raise RuntimeError(f"Simulation failed for {city} {design_name}: fr={res_fr['status']}, il={res_il['status']}")

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

    ad_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
    ml_res = evaluate_ml_champion_comfort(champ_model, ta, tr, rh, tout, clo_hourly)

    o1_ml = ml_res['O1_ml']
    o1_adapt = ad_res['O1_adapt']
    o2 = sm_il['o2_energy_kwh_per_m2']

    # Clean bulky files
    for rdir in [rdir_fr, rdir_il]:
        for f in os.listdir(rdir):
            if f not in ["eplusout.err", "shelter.idf"]:
                try:
                    os.remove(os.path.join(rdir, f))
                except:
                    pass

    return {
        'O1_ml': o1_ml,
        'O1_adapt': o1_adapt,
        'O2': o2
    }

def main():
    print("=" * 135)
    print("ITEM 5: CLIMATE ZONE AUDIT & R3 BASELINE SENSITIVITY (ASSUMED CITIES)")
    print("=" * 135)

    print("""
[1. SHIMLA RECLASSIFICATION JUSTIFICATION]
- In reports/results_30_cities.csv, Shimla had zone_source='STANDARD'.
- However, examination of data/docs/ECBC_2017.pdf Table 11-1 (Page 201) reveals that while Kullu and
  Shillong are explicitly designated under 'Cold', Shimla is omitted from Table 11-1.
- In accordance with the project rule ('point to a document on disk or change it to ASSUMED'),
  Shimla's zone_source has been changed to ASSUMED.
- Total ASSUMED cities in reports/results_30_cities.csv: 8 cities.
""")
    print("=" * 135)

    df_30 = pd.read_csv("reports/results_30_cities.csv").set_index('city')
    df_manifest = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    champ_model = load_champion_model()

    print("TABLE 1: CURRENT R3 BASELINE VALUES FOR ALL 8 ASSUMED CITIES")
    print("-" * 135)
    assumed_rows = []
    for city in ASSUMED_CITIES:
        cdir = get_city_dir(city)
        df_base = pd.read_csv(os.path.join(cdir, "baseline_results.csv"))
        r3_row = df_base[df_base['design_id'] == 'R3_Code_Compliant'].iloc[0]

        row_30 = df_30.loc[city]
        assumed_rows.append({
            'City': city,
            'Assigned Zone': row_30['zone'],
            'zone_source': row_30['zone_source'],
            'R3 Reference City': row_30['R3_flagship'],
            'R3 Roof Ins (m)': f"{float(r3_row['roof_insulation_thickness']):.3f}",
            'R3 Wall Ins (m)': f"{float(r3_row['wall_insulation_thickness']):.3f}",
            'R3 Absorptance': f"{float(r3_row['roof_solar_absorptance']):.2f}",
            'R3 O1_ml (%)': f"{float(r3_row['O1_ml']):.2f}%",
            'R3 O2 (kWh/m2)': f"{float(r3_row['O2']):.2f}",
            'Best Pareto O1_ml': f"{float(row_30['best_O1_ml']):.2f}%",
            'Best Pareto O2': f"{float(row_30['best_O2']):.2f}"
        })
    print(pd.DataFrame(assumed_rows).to_string(index=False))
    print("-" * 135)

    print("\n" + "=" * 135)
    print("TABLE 2: SENSITIVITY RE-EVALUATION UNDER ALTERNATIVE CLIMATE ZONES")
    print("Re-evaluating R3 with EnergyPlus simulations for Gangtok, Bhuntar, and Bhuj")
    print("=" * 135)

    # 1. Gangtok (Cold -> Composite)
    # Cold R3: roof_ins=0.15, wall_ins=0.10, absorptance=0.60
    # Composite R3: roof_ins=0.125, wall_ins=0.10, absorptance=0.30
    gangtok_epw = df_manifest.loc['Gangtok', 'path']
    gangtok_composite_params = {
        'roof_insulation_thickness': 0.125,
        'wall_insulation_thickness': 0.10,
        'roof_solar_absorptance': 0.30,
        'wall_mass_class': 'medium',
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    }
    print("Simulating Gangtok alternative R3 (Composite)...")
    res_gangtok_alt = simulate_one_design('Gangtok', gangtok_epw, gangtok_composite_params, "R3_Composite", champ_model)

    # 2. Bhuntar (Cold -> Composite)
    bhuntar_epw = df_manifest.loc['Bhuntar', 'path']
    bhuntar_composite_params = dict(gangtok_composite_params)
    print("Simulating Bhuntar alternative R3 (Composite)...")
    res_bhuntar_alt = simulate_one_design('Bhuntar', bhuntar_epw, bhuntar_composite_params, "R3_Composite", champ_model)

    # 3. Bhuj (Hot-Dry -> Alternative Zones)
    # Hot-Dry R3: roof_ins=0.125, wall_ins=0.10, absorptance=0.30
    # Option A: Composite R3 -> identical to Hot-Dry!
    # Option B: Temperate R3 (Bengaluru): roof_ins=0.125, wall_ins=0.075, absorptance=0.60
    # Option C: Cold R3 (Shimla): roof_ins=0.15, wall_ins=0.10, absorptance=0.60
    bhuj_epw = df_manifest.loc['Bhuj', 'path']
    bhuj_temperate_params = {
        'roof_insulation_thickness': 0.125,
        'wall_insulation_thickness': 0.075,
        'roof_solar_absorptance': 0.60,
        'wall_mass_class': 'medium',
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    }
    bhuj_cold_params = {
        'roof_insulation_thickness': 0.15,
        'wall_insulation_thickness': 0.10,
        'roof_solar_absorptance': 0.60,
        'wall_mass_class': 'medium',
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    }
    print("Simulating Bhuj alternative R3 (Temperate)...")
    res_bhuj_temp = simulate_one_design('Bhuj', bhuj_epw, bhuj_temperate_params, "R3_Temperate", champ_model)
    print("Simulating Bhuj alternative R3 (Cold)...")
    res_bhuj_cold = simulate_one_design('Bhuj', bhuj_epw, bhuj_cold_params, "R3_Cold", champ_model)

    # Assemble sensitivity comparison
    sens_rows = []

    # Gangtok comparison
    g_curr = df_30.loc['Gangtok']
    g_base_curr = pd.read_csv("data/processed/batch/Gangtok/baseline_results.csv").query("design_id == 'R3_Code_Compliant'").iloc[0]
    g_r3_o2_curr = float(g_base_curr['O2'])
    g_r3_o1_curr = float(g_base_curr['O1_ml'])
    g_best_o2 = float(g_curr['best_O2'])
    g_best_o1 = float(g_curr['best_O1_ml'])

    pct_better_o2_curr = (g_r3_o2_curr - g_best_o2) / g_r3_o2_curr * 100.0
    pp_better_o1_curr = g_best_o1 - g_r3_o1_curr

    pct_better_o2_alt = (res_gangtok_alt['O2'] - g_best_o2) / res_gangtok_alt['O2'] * 100.0
    pp_better_o1_alt = g_best_o1 - res_gangtok_alt['O1_ml']

    sens_rows.append({
        'City': 'Gangtok',
        'Original Zone': 'Cold',
        'Alternative Zone': 'Composite',
        'Original R3 O2': f"{g_r3_o2_curr:.2f}",
        'Alt R3 O2': f"{res_gangtok_alt['O2']:.2f}",
        'Delta R3 O2': f"{res_gangtok_alt['O2'] - g_r3_o2_curr:+.2f}",
        'Original % Better O2': f"{pct_better_o2_curr:.2f}%",
        'Alt % Better O2': f"{pct_better_o2_alt:.2f}%",
        'Change in % Better O2': f"{pct_better_o2_alt - pct_better_o2_curr:+.2f}%",
        'Original pp Better O1': f"{pp_better_o1_curr:+.2f} pp",
        'Alt pp Better O1': f"{pp_better_o1_alt:+.2f} pp",
        'Change in pp Better O1': f"{pp_better_o1_alt - pp_better_o1_curr:+.2f} pp"
    })

    # Bhuntar comparison
    b_curr = df_30.loc['Bhuntar']
    b_base_curr = pd.read_csv("data/processed/batch/Bhuntar/baseline_results.csv").query("design_id == 'R3_Code_Compliant'").iloc[0]
    b_r3_o2_curr = float(b_base_curr['O2'])
    b_r3_o1_curr = float(b_base_curr['O1_ml'])
    b_best_o2 = float(b_curr['best_O2'])
    b_best_o1 = float(b_curr['best_O1_ml'])

    pct_better_o2_b_curr = (b_r3_o2_curr - b_best_o2) / b_r3_o2_curr * 100.0
    pp_better_o1_b_curr = b_best_o1 - b_r3_o1_curr

    pct_better_o2_b_alt = (res_bhuntar_alt['O2'] - b_best_o2) / res_bhuntar_alt['O2'] * 100.0
    pp_better_o1_b_alt = b_best_o1 - res_bhuntar_alt['O1_ml']

    sens_rows.append({
        'City': 'Bhuntar',
        'Original Zone': 'Cold',
        'Alternative Zone': 'Composite',
        'Original R3 O2': f"{b_r3_o2_curr:.2f}",
        'Alt R3 O2': f"{res_bhuntar_alt['O2']:.2f}",
        'Delta R3 O2': f"{res_bhuntar_alt['O2'] - b_r3_o2_curr:+.2f}",
        'Original % Better O2': f"{pct_better_o2_b_curr:.2f}%",
        'Alt % Better O2': f"{pct_better_o2_b_alt:.2f}%",
        'Change in % Better O2': f"{pct_better_o2_b_alt - pct_better_o2_b_curr:+.2f}%",
        'Original pp Better O1': f"{pp_better_o1_b_curr:+.2f} pp",
        'Alt pp Better O1': f"{pp_better_o1_b_alt:+.2f} pp",
        'Change in pp Better O1': f"{pp_better_o1_b_alt - pp_better_o1_b_curr:+.2f} pp"
    })

    # Bhuj comparison (Option A: Composite is identical; Option B: Temperate; Option C: Cold)
    bhuj_curr = df_30.loc['Bhuj']
    bhuj_base_curr = pd.read_csv("data/processed/batch/Bhuj/baseline_results.csv").query("design_id == 'R3_Code_Compliant'").iloc[0]
    bhuj_r3_o2_curr = float(bhuj_base_curr['O2'])
    bhuj_r3_o1_curr = float(bhuj_base_curr['O1_ml'])
    bhuj_best_o2 = float(bhuj_curr['best_O2'])
    bhuj_best_o1 = float(bhuj_curr['best_O1_ml'])

    pct_better_o2_bhuj_curr = (bhuj_r3_o2_curr - bhuj_best_o2) / bhuj_r3_o2_curr * 100.0
    pp_better_o1_bhuj_curr = bhuj_best_o1 - bhuj_r3_o1_curr

    # Composite: delta = 0
    sens_rows.append({
        'City': 'Bhuj',
        'Original Zone': 'Hot-Dry',
        'Alternative Zone': 'Composite',
        'Original R3 O2': f"{bhuj_r3_o2_curr:.2f}",
        'Alt R3 O2': f"{bhuj_r3_o2_curr:.2f}",
        'Delta R3 O2': "+0.00",
        'Original % Better O2': f"{pct_better_o2_bhuj_curr:.2f}%",
        'Alt % Better O2': f"{pct_better_o2_bhuj_curr:.2f}%",
        'Change in % Better O2': "+0.00%",
        'Original pp Better O1': f"{pp_better_o1_bhuj_curr:+.2f} pp",
        'Alt pp Better O1': f"{pp_better_o1_bhuj_curr:+.2f} pp",
        'Change in pp Better O1': "+0.00 pp"
    })

    # Temperate
    pct_better_o2_bhuj_temp = (res_bhuj_temp['O2'] - bhuj_best_o2) / res_bhuj_temp['O2'] * 100.0
    pp_better_o1_bhuj_temp = bhuj_best_o1 - res_bhuj_temp['O1_ml']
    sens_rows.append({
        'City': 'Bhuj',
        'Original Zone': 'Hot-Dry',
        'Alternative Zone': 'Temperate',
        'Original R3 O2': f"{bhuj_r3_o2_curr:.2f}",
        'Alt R3 O2': f"{res_bhuj_temp['O2']:.2f}",
        'Delta R3 O2': f"{res_bhuj_temp['O2'] - bhuj_r3_o2_curr:+.2f}",
        'Original % Better O2': f"{pct_better_o2_bhuj_curr:.2f}%",
        'Alt % Better O2': f"{pct_better_o2_bhuj_temp:.2f}%",
        'Change in % Better O2': f"{pct_better_o2_bhuj_temp - pct_better_o2_bhuj_curr:+.2f}%",
        'Original pp Better O1': f"{pp_better_o1_bhuj_curr:+.2f} pp",
        'Alt pp Better O1': f"{pp_better_o1_bhuj_temp:+.2f} pp",
        'Change in pp Better O1': f"{pp_better_o1_bhuj_temp - pp_better_o1_bhuj_curr:+.2f} pp"
    })

    # Cold
    pct_better_o2_bhuj_cold = (res_bhuj_cold['O2'] - bhuj_best_o2) / res_bhuj_cold['O2'] * 100.0
    pp_better_o1_bhuj_cold = bhuj_best_o1 - res_bhuj_cold['O1_ml']
    sens_rows.append({
        'City': 'Bhuj',
        'Original Zone': 'Hot-Dry',
        'Alternative Zone': 'Cold',
        'Original R3 O2': f"{bhuj_r3_o2_curr:.2f}",
        'Alt R3 O2': f"{res_bhuj_cold['O2']:.2f}",
        'Delta R3 O2': f"{res_bhuj_cold['O2'] - bhuj_r3_o2_curr:+.2f}",
        'Original % Better O2': f"{pct_better_o2_bhuj_curr:.2f}%",
        'Alt % Better O2': f"{pct_better_o2_bhuj_cold:.2f}%",
        'Change in % Better O2': f"{pct_better_o2_bhuj_cold - pct_better_o2_bhuj_curr:+.2f}%",
        'Original pp Better O1': f"{pp_better_o1_bhuj_curr:+.2f} pp",
        'Alt pp Better O1': f"{pp_better_o1_bhuj_cold:+.2f} pp",
        'Change in pp Better O1': f"{pp_better_o1_bhuj_cold - pp_better_o1_bhuj_curr:+.2f} pp"
    })

    print(pd.DataFrame(sens_rows).to_string(index=False))
    print("=" * 135)

if __name__ == "__main__":
    main()
