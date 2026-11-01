"""
Reference Shelter Definitions and Direct EnergyPlus Evaluation for ClimateAdapt-Comfort.
Phase 5, Step 1:
- R1 Lightweight (Assumption A-006): no insulation, light wall mass, roof absorptance 0.85, WWR 0.15, shading 0, ventilation 5 ACH, orientation 0.
- R2 Conventional (Assumption A-007): medium (clay brick) mass, no insulation, roof absorptance 0.6, WWR 0.15, shading 0, ventilation 5 ACH, orientation 0.
Simulates R1 and R2 across all 5 cities in both modes, applies dual comfort judges, and outputs data/processed/reference_results.csv.
"""

import os
import sys
import shutil
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

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

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

# Assumption A-006: R1 Lightweight reference shelter
REFERENCE_R1 = {
    'name': 'R1_Lightweight',
    'roof_insulation_thickness': 0.0,
    'wall_insulation_thickness': 0.0,
    'wall_mass_class': 'light',
    'roof_solar_absorptance': 0.85,
    'wwr': 0.15,
    'orientation': 0.0,
    'shading_depth': 0.0,
    'ventilation_ach': 5.0
}

# Assumption A-007: R2 Conventional medium-mass reference shelter
REFERENCE_R2 = {
    'name': 'R2_Conventional',
    'roof_insulation_thickness': 0.0,
    'wall_insulation_thickness': 0.0,
    'wall_mass_class': 'medium',
    'roof_solar_absorptance': 0.60,
    'wwr': 0.15,
    'orientation': 0.0,
    'shading_depth': 0.0,
    'ventilation_ach': 5.0
}

REFERENCES = [REFERENCE_R1, REFERENCE_R2]

def run_reference_simulations(output_csv="data/processed/reference_results.csv"):
    print("="*80)
    print("RUNNING DIRECT ENERGYPLUS SIMULATIONS FOR REFERENCE SHELTERS (R1 & R2)")
    print("="*80)
    
    temp_dir = "data/processed/temp_reference_sims"
    os.makedirs(temp_dir, exist_ok=True)
    
    model = load_champion_model()
    records = []
    
    for city, epw in CITIES_EPW.items():
        print(f"\nCity: {city}")
        for ref in REFERENCES:
            ref_name = ref['name']
            p = {k: v for k, v in ref.items() if k != 'name'}
            
            run_dir = os.path.join(temp_dir, f"{city}_{ref_name}")
            dir_fr = os.path.join(run_dir, "fr")
            dir_il = os.path.join(run_dir, "il")
            os.makedirs(dir_fr, exist_ok=True)
            os.makedirs(dir_il, exist_ok=True)
            
            # 1. Free running
            idf_fr = os.path.join(dir_fr, "shelter.idf")
            render_shelter_idf(p, idf_fr, mode='free_running')
            res_fr = run_single_simulation(idf_fr, epw, dir_fr)
            if res_fr['status'] != 'SUCCESS':
                raise RuntimeError(f"Failed free-running simulation for {city} {ref_name}: {res_fr.get('error_summary')}")
                
            csv_fr = os.path.join(dir_fr, "eplusout.csv")
            hdf_fr, sm_fr = parse_simulation_csv(csv_fr)
            
            ta = hdf_fr['ta'].values.astype(np.float32)
            tr = hdf_fr['tr'].values.astype(np.float32)
            rh = hdf_fr['rh'].values.astype(np.float32)
            tout = hdf_fr['t_out'].values.astype(np.float32)
            
            # 2. Ideal loads
            idf_il = os.path.join(dir_il, "shelter.idf")
            render_shelter_idf(p, idf_il, mode='ideal_loads')
            res_il = run_single_simulation(idf_il, epw, dir_il)
            if res_il['status'] != 'SUCCESS':
                raise RuntimeError(f"Failed ideal-loads simulation for {city} {ref_name}: {res_il.get('error_summary')}")
                
            csv_il = os.path.join(dir_il, "eplusout.csv")
            hdf_il, sm_il = parse_simulation_csv(csv_il)
            o2_energy = float(sm_il['o2_energy_kwh_per_m2'])
            
            # Coupling
            daily_tout = calculate_daily_mean_series(tout)
            t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
            t_rm_hourly = np.repeat(t_rm_daily, 24)
            clo_hourly = compute_clo_schedule_a004(daily_tout)
            
            adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
            ml_res = evaluate_ml_champion_comfort(
                model=model, ta=ta, tr=tr, rh=rh,
                t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
                met=1.1, vel=0.15
            )
            
            rec = {
                'city': city,
                'reference_name': ref_name,
                **p,
                'mean_ta': float(sm_fr['mean_ta']),
                'max_ta': float(sm_fr['max_ta']),
                'min_ta': float(sm_fr['min_ta']),
                'mean_tr': float(sm_fr['mean_tr']),
                'O1_ml': ml_res['O1_ml'],
                'warm_ml': ml_res['warm_ml'],
                'cool_ml': ml_res['cool_ml'],
                'O1_adapt': adapt_res['O1_adapt'],
                'hot_adapt': adapt_res['hot_adapt'],
                'cold_adapt': adapt_res['cold_adapt'],
                'invalid_share_adapt': adapt_res['invalid_share_adapt'],
                'O2': o2_energy
            }
            records.append(rec)
            print(f"  {ref_name:16s} | O1_ml: {ml_res['O1_ml']:5.2f}% | O1_adapt: {adapt_res['O1_adapt']:5.2f}% | O2: {o2_energy:6.2f} kWh/m2")
            
    # Clean up temp dir
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    df_refs = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_refs.to_csv(output_csv, index=False)
    print(f"\nSaved reference results ({len(df_refs)} rows) to {output_csv}")
    
    print("\n" + "="*80)
    print("REFERENCE SHELTER RESULTS TABLE (Direct EnergyPlus Simulations)")
    print("="*80)
    cols_show = ['city', 'reference_name', 'O1_ml', 'warm_ml', 'cool_ml', 'O1_adapt', 'O2', 'mean_ta', 'mean_tr']
    print(df_refs[cols_show].to_string(index=False))
    return df_refs

if __name__ == "__main__":
    run_reference_simulations()
