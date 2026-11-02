"""
tools/task2_ventilation.py
Executes TASK 2: VENTILATION, RIGHT DESIGN (P_Leh_R3_037 & Jodhpur Positive Control)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import shutil
import pandas as pd
import numpy as np

from src.sim.render import render_building_idf, resolve_epw_path
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

def run_ventilation_study():
    print("=" * 115)
    print("TASK 2 - VENTILATION SENSITIVITY: P_Leh_R3_037 & JODHPUR POSITIVE CONTROL")
    print("=" * 115)
    
    scratch_dir = "data/processed/scratch_task2_vent"
    os.makedirs(scratch_dir, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # PART 1: P_Leh_R3_037 in Leh
    # -------------------------------------------------------------------------
    leh_pareto_csv = "data/processed/active_learning_leh/final_verified_pareto_Leh.csv"
    df_leh = pd.read_csv(leh_pareto_csv)
    p37_row = df_leh[df_leh['design_id'] == 'P_Leh_R3_037'].iloc[0]
    
    p37_params = {
        'building_type': 'shelter_v1',
        'city': 'Leh',
        'roof_insulation_thickness': float(p37_row['roof_insulation_thickness_y']),
        'wall_insulation_thickness': float(p37_row['wall_insulation_thickness_y']),
        'wall_mass_class': str(p37_row['wall_mass_class_y']),
        'roof_solar_absorptance': float(p37_row['roof_solar_absorptance_y']),
        'wwr': float(p37_row['wwr_y']),
        'orientation': float(p37_row['orientation_y']),
        'shading_depth': float(p37_row['shading_depth_y']),
        'ventilation_ach': float(p37_row['ventilation_ach_y'])
    }
    
    epw_leh = resolve_epw_path(city='Leh')
    
    print("\n[PART 1] LEH TEST DESIGN: P_Leh_R3_037")
    print("Design Parameters: roof_ins=0.0m, wall_ins=0.15m, mass=light, abs=0.8786, wwr=0.3533, shade=0.301m")
    
    leh_test_achs = [1.94, 6.0, 13.0]
    leh_results = []
    idf_13_content = ""
    
    for ach in leh_test_achs:
        p = dict(p37_params)
        p['ventilation_ach'] = ach
        
        # 1. Free-running
        rdir_fr = os.path.join(scratch_dir, f"Leh_P37_ACH_{str(ach).replace('.', '_')}_FR")
        os.makedirs(rdir_fr, exist_ok=True)
        idf_fr_path = os.path.join(rdir_fr, "shelter.idf")
        render_building_idf(p, idf_fr_path, building_type='shelter_v1', mode='free_running', epw_path=epw_leh, city='Leh')
        
        if ach == 13.0:
            with open(idf_fr_path, "r", encoding="utf-8") as fp:
                idf_13_content = fp.read()
                
        res_fr = run_single_simulation(idf_fr_path, epw_leh, rdir_fr)
        csv_fr = os.path.join(rdir_fr, "eplusout.csv")
        hdf_fr, _ = parse_simulation_csv(csv_fr)
        top_fr = (hdf_fr['ta'].values + hdf_fr['tr'].values) / 2.0
        med_top = float(np.median(top_fr))
        max_top = float(np.max(top_fr))
        hrs_ge_24 = int(np.sum(top_fr >= 24.0))
        
        # 2. Ideal loads
        rdir_il = os.path.join(scratch_dir, f"Leh_P37_ACH_{str(ach).replace('.', '_')}_IL")
        os.makedirs(rdir_il, exist_ok=True)
        idf_il_path = os.path.join(rdir_il, "shelter.idf")
        render_building_idf(p, idf_il_path, building_type='shelter_v1', mode='ideal_loads', epw_path=epw_leh, city='Leh')
        
        res_il = run_single_simulation(idf_il_path, epw_leh, rdir_il)
        csv_il = os.path.join(rdir_il, "eplusout.csv")
        _, sm_il = parse_simulation_csv(csv_il)
        o2_val = float(sm_il['o2_energy_kwh_per_m2'])
        
        leh_results.append({
            'Design': 'P_Leh_R3_037',
            'City': 'Leh',
            'ACH': ach,
            'O2': o2_val,
            'Top_median': med_top,
            'Top_max': max_top,
            'Hours_ge_24': hrs_ge_24
        })
        
        shutil.rmtree(rdir_fr, ignore_errors=True)
        shutil.rmtree(rdir_il, ignore_errors=True)
        
    print("\nRESULTS TABLE FOR LEH DESIGN P_Leh_R3_037:")
    header = f"{'Design ID':<15} | {'ACH':<6} | {'O2 (kWh/m2)':<14} | {'FR Med Top (C)':<16} | {'FR Max Top (C)':<16} | {'FR Hours Top >= 24C':<20}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in leh_results:
        print(f"{r['Design']:<15} | {r['ACH']:<6.2f} | {r['O2']:<14.2f} | {r['Top_median']:<16.2f} | {r['Top_max']:<16.2f} | {r['Hours_ge_24']:<20}")
    print(sep)
    
    # -------------------------------------------------------------------------
    # PART 2: ZoneVentilation:DesignFlowRate block from ACH=13 run IDF
    # -------------------------------------------------------------------------
    print("\n[PART 2] ZoneVentilation:DesignFlowRate BLOCK FROM IDF (ACH=13.0 RUN):")
    print("-" * 80)
    for line in idf_13_content.splitlines():
        if "ZoneVentilation:DesignFlowRate" in line or "Natural_Ventilation" in line:
            print(line)
    print("-" * 80)
    
    # -------------------------------------------------------------------------
    # PART 3: Positive Control in Jodhpur
    # -------------------------------------------------------------------------
    jod_pareto_csv = "data/processed/active_learning_jodhpur/final_verified_pareto_Jodhpur.csv"
    df_jod = pd.read_csv(jod_pareto_csv)
    j05_row = df_jod.iloc[0]
    
    j05_params = {
        'building_type': 'shelter_v1',
        'city': 'Jodhpur',
        'roof_insulation_thickness': float(j05_row['roof_insulation_thickness']),
        'wall_insulation_thickness': float(j05_row['wall_insulation_thickness']),
        'wall_mass_class': str(j05_row['wall_mass_class']),
        'roof_solar_absorptance': float(j05_row['roof_solar_absorptance']),
        'wwr': float(j05_row['wwr']),
        'orientation': float(j05_row['orientation']),
        'shading_depth': float(j05_row['shading_depth']),
        'ventilation_ach': float(j05_row['ventilation_ach'])
    }
    epw_jod = resolve_epw_path(city='Jodhpur')
    
    print("\n[PART 3] JODHPUR POSITIVE CONTROL DESIGN: P_Jodhpur_R3_005")
    print("Design Parameters: roof_ins=0.15m, wall_ins=0.15m, mass=heavy, abs=0.3044, wwr=0.0501, shade=0.647m")
    
    jod_test_achs = [2.0, 6.0, 13.0]
    jod_results = []
    
    for ach in jod_test_achs:
        p = dict(j05_params)
        p['ventilation_ach'] = ach
        
        # 1. Free-running
        rdir_fr = os.path.join(scratch_dir, f"Jod_P05_ACH_{int(ach)}_FR")
        os.makedirs(rdir_fr, exist_ok=True)
        idf_fr_path = os.path.join(rdir_fr, "shelter.idf")
        render_building_idf(p, idf_fr_path, building_type='shelter_v1', mode='free_running', epw_path=epw_jod, city='Jodhpur')
        
        res_fr = run_single_simulation(idf_fr_path, epw_jod, rdir_fr)
        csv_fr = os.path.join(rdir_fr, "eplusout.csv")
        hdf_fr, _ = parse_simulation_csv(csv_fr)
        top_fr = (hdf_fr['ta'].values + hdf_fr['tr'].values) / 2.0
        med_top = float(np.median(top_fr))
        max_top = float(np.max(top_fr))
        hrs_ge_24 = int(np.sum(top_fr >= 24.0))
        
        # 2. Ideal loads
        rdir_il = os.path.join(scratch_dir, f"Jod_P05_ACH_{int(ach)}_IL")
        os.makedirs(rdir_il, exist_ok=True)
        idf_il_path = os.path.join(rdir_il, "shelter.idf")
        render_building_idf(p, idf_il_path, building_type='shelter_v1', mode='ideal_loads', epw_path=epw_jod, city='Jodhpur')
        
        res_il = run_single_simulation(idf_il_path, epw_jod, rdir_il)
        csv_il = os.path.join(rdir_il, "eplusout.csv")
        _, sm_il = parse_simulation_csv(csv_il)
        o2_val = float(sm_il['o2_energy_kwh_per_m2'])
        
        jod_results.append({
            'Design': 'P_Jodhpur_R3_005',
            'City': 'Jodhpur',
            'ACH': ach,
            'O2': o2_val,
            'Top_median': med_top,
            'Top_max': max_top,
            'Hours_ge_24': hrs_ge_24
        })
        
        shutil.rmtree(rdir_fr, ignore_errors=True)
        shutil.rmtree(rdir_il, ignore_errors=True)
        
    print("\nRESULTS TABLE FOR JODHPUR POSITIVE CONTROL (P_Jodhpur_R3_005):")
    print(sep)
    print(header)
    print(sep)
    for r in jod_results:
        print(f"{r['Design']:<15} | {r['ACH']:<6.2f} | {r['O2']:<14.2f} | {r['Top_median']:<16.2f} | {r['Top_max']:<16.2f} | {r['Hours_ge_24']:<20}")
    print(sep)
    
    # -------------------------------------------------------------------------
    # PART 4: Required Concluding Statement
    # -------------------------------------------------------------------------
    print("\n[PART 4] CONCLUSION:")
    print("ACH matters when Top >= 24 C")

if __name__ == '__main__':
    run_ventilation_study()
