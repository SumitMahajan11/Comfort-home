"""
tools/check5_ventilation_test.py
Executes CHECK 5: VENTILATION TEST (LEH)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import shutil
import tempfile
import pandas as pd
import numpy as np

from src.sim.render import render_building_idf, resolve_epw_path
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

def find_ventilation_lines():
    print("=" * 105)
    print("PART 1: WHERE ventilation_ach IS USED IN src/sim")
    print("=" * 105)
    
    sim_dir = "src/sim"
    found_lines = []
    for root, _, files in os.walk(sim_dir):
        for f in sorted(files):
            if f.endswith(".py"):
                p = os.path.join(root, f)
                rel_p = os.path.relpath(p).replace("\\", "/")
                with open(p, "r", encoding="utf-8") as fp:
                    for line_no, line in enumerate(fp, 1):
                        if "ventilation_ach" in line:
                            found_lines.append((rel_p, line_no, line.rstrip()))
                            
    for rel_p, line_no, line in found_lines:
        print(f"{rel_p}:{line_no}: {line}")
    return found_lines

def print_ventilation_explanation():
    print("\n" + "=" * 105)
    print("PART 2: VENTILATION MECHANISM IN PLAIN WORDS")
    print("=" * 105)
    print("1. Is ACH constant, scheduled, or temperature-controlled?")
    print("   - In plain words, it is TEMPERATURE-CONTROLLED with a constant design capacity:")
    print("     * It uses the EnergyPlus object 'ZoneVentilation:DesignFlowRate' with design ACH set to ventilation_ach.")
    print("     * The operational schedule is 'Always_On' (fraction = 1.0 continuous).")
    print("     * Crucially, it is constrained by two temperature thresholds:")
    print("       (a) Minimum Indoor Temperature = 24.0 C (for shelter_v1; 20.0 C for houses). If the zone operative/air")
    print("           temperature drops below 24.0 C, ventilation is automatically shut off to avoid extreme overcooling.")
    print("       (b) Delta Temperature = 1.0 C. Ventilation is permitted ONLY when the outdoor air is at least 1.0 C")
    print("           cooler than the indoor zone (IndoorTemp - OutdoorTemp >= 1.0 C), acting as free natural cooling.")
    print("     * In addition, there is an unconditioned continuous baseline infiltration of 0.5 ACH")
    print("       ('ZoneInfiltration:DesignFlowRate') that is constant and active 24/7.")
    print("")
    print("2. Is it the same in free-running mode and in heated/cooled mode?")
    print("   - YES: The exact same 'ZoneVentilation:DesignFlowRate' object is generated in the IDF for both modes.")
    print("     In 'ideal_loads' (heated/cooled) mode, the HVAC IdealLoadsAirSystem is added, while the natural ventilation")
    print("     object remains identical, obeying the same 24 C minimum cutoff and 1 C outdoor delta constraint.")

def run_ach_experiments():
    print("\n" + "=" * 105)
    print("PART 3: SENSITIVITY SIMULATION ON P_Leh_R3_042 ACROSS ACH = 2, 6, 13")
    print("=" * 105)
    
    # Load design P_Leh_R3_042
    pareto_csv = "data/processed/active_learning_leh/final_verified_pareto_Leh.csv"
    df_pareto = pd.read_csv(pareto_csv)
    p42_row = df_pareto[df_pareto['design_id'] == 'P_Leh_R3_042'].iloc[0]
    
    base_params = {
        'building_type': 'shelter_v1',
        'city': 'Leh',
        'roof_insulation_thickness': float(p42_row['roof_insulation_thickness_y']),
        'wall_insulation_thickness': float(p42_row['wall_insulation_thickness_y']),
        'wall_mass_class': str(p42_row['wall_mass_class_y']),
        'roof_solar_absorptance': float(p42_row['roof_solar_absorptance_y']),
        'wwr': float(p42_row['wwr_y']),
        'orientation': float(p42_row['orientation_y']),
        'shading_depth': float(p42_row['shading_depth_y']),
        'ventilation_ach': float(p42_row['ventilation_ach_y'])
    }
    
    epw_path = resolve_epw_path(city='Leh')
    print(f"Base Design P_Leh_R3_042 loaded:")
    for k, v in base_params.items():
        print(f"  * {k}: {v}")
    print(f"EPW Weather Path: {epw_path}")
    
    test_achs = [2.0, 6.0, 13.0]
    results = []
    
    scratch_dir = "data/processed/scratch_ach_test"
    os.makedirs(scratch_dir, exist_ok=True)
    
    for ach in test_achs:
        p = dict(base_params)
        p['ventilation_ach'] = ach
        
        # 1. Run free-running
        fr_dir = os.path.join(scratch_dir, f"P42_ACH_{int(ach)}_FR")
        os.makedirs(fr_dir, exist_ok=True)
        idf_fr_path = os.path.join(fr_dir, "shelter.idf")
        render_building_idf(p, idf_fr_path, building_type='shelter_v1', mode='free_running', epw_path=epw_path, city='Leh')
        
        res_fr = run_single_simulation(idf_fr_path, epw_path, fr_dir)
        csv_fr = os.path.join(fr_dir, "eplusout.csv")
        hdf_fr, _ = parse_simulation_csv(csv_fr)
        top = (hdf_fr['ta'].values + hdf_fr['tr'].values) / 2.0
        med_top = float(np.median(top))
        
        # 2. Run ideal_loads
        il_dir = os.path.join(scratch_dir, f"P42_ACH_{int(ach)}_IL")
        os.makedirs(il_dir, exist_ok=True)
        idf_il_path = os.path.join(il_dir, "shelter.idf")
        render_building_idf(p, idf_il_path, building_type='shelter_v1', mode='ideal_loads', epw_path=epw_path, city='Leh')
            
        res_il = run_single_simulation(idf_il_path, epw_path, il_dir)
        csv_il = os.path.join(il_dir, "eplusout.csv")
        _, sm_il = parse_simulation_csv(csv_il)
        o2_val = float(sm_il['o2_energy_kwh_per_m2'])
        
        results.append({
            'ACH': ach,
            'O2': o2_val,
            'Top_median': med_top
        })
        
        # Cleanup large csv files to conserve space
        shutil.rmtree(fr_dir, ignore_errors=True)
        shutil.rmtree(il_dir, ignore_errors=True)

    print("\nRESULTS TABLE FOR P_Leh_R3_042 ACROSS TESTED ACH VALUES:")
    header = f"{'Design ID':<18} | {'ACH':<8} | {'O2 (kWh/m2)':<16} | {'FR Median Top (C)':<20}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in results:
        print(f"{'P_Leh_R3_042':<18} | {r['ACH']:<8.1f} | {r['O2']:<16.2f} | {r['Top_median']:<20.2f}")
    print(sep)
    
    # State whether more ACH raised or lowered O2
    o2_at_2 = results[0]['O2']
    o2_at_6 = results[1]['O2']
    o2_at_13 = results[2]['O2']
    
    print("\nVERDICT ON O2 SENSITIVITY TO ACH IN LEH:")
    if o2_at_13 > o2_at_2:
        print(f"Higher ACH RAISED O2 (increased energy consumption from {o2_at_2:.2f} to {o2_at_13:.2f} kWh/m2).")
    elif o2_at_13 < o2_at_2:
        print(f"Higher ACH LOWERED O2 (decreased energy consumption from {o2_at_2:.2f} to {o2_at_13:.2f} kWh/m2).")
    else:
        print(f"Higher ACH resulted in IDENTICAL O2 ({o2_at_2:.2f} kWh/m2).")
        print("Reason: In sub-zero sub-alpine Leh, indoor operative temperature rarely exceeds the 24.0 C ventilation")
        print("activation threshold during heating periods, so the natural ventilation object remains shut off,")
        print("leaving infiltration (0.5 ACH) and envelope conduction dominant.")

if __name__ == '__main__':
    find_ventilation_lines()
    print_ventilation_explanation()
    run_ach_experiments()
