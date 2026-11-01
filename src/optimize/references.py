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

# R3 Code-Compliant Baseline per Indian Climate Zone (ECBC 2017 & Eco-Niwas Samhita 2018)
# Sources:
# 1. Bureau of Energy Efficiency (BEE), Ministry of Power, Govt. of India:
#    "Energy Conservation Building Code 2017" (ECBC 2017), Section 4.3 Prescriptive Requirements:
#    - Table 4-4: Roof Assembly Maximum U-factor (W/m2-K):
#        Composite: 0.33, Hot-Dry: 0.33, Warm-Humid: 0.33, Temperate: 0.33, Cold: 0.28
#    - Table 4-7: Opaque Assembly Maximum U-factor (Walls, W/m2-K):
#        Composite: 0.40, Hot-Dry: 0.40, Warm-Humid: 0.40, Temperate: 0.55, Cold: 0.34
#    - Section 4.3.1.1: Cool Roof Solar Reflectance >= 0.70 (Solar Absorptance <= 0.30) for non-cold climates
#    URL: https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc
#
# 2. Bureau of Energy Efficiency (BEE), Ministry of Power, Govt. of India:
#    "Eco-Niwas Samhita 2018 (Part I: Building Envelope)" (ENS 2018):
#    - Section 3.1 & Table 1: Thermal Transmittance of Roof (U_roof) <= 1.20 W/m2-K (all climate zones)
#    - Section 3.2: Maximum RETV <= 15.0 W/m2 (Cooling zones) / U_envelope <= 1.80 W/m2-K (Cold zone Table 2)
#    - Section 3.3 & Table 3: Minimum external shading overhang >= 0.30 m, openable window ratio WFR_op >= 10%
#    URL: https://beeindia.gov.in/en/energy-conservation-building-code-residential-eco-niwas-samhita
#
# Physical Derivation:
# XPS/EPS Insulation conductivity k = 0.038 W/m-K (render.py Material:Wall_Insulation & Material:Roof_Insulation).
# Base uninsulated roof (100mm RCC + 15mm plaster + 10mm finish + air films): R_base = 0.332 m2-K/W.
#   - U <= 0.33 W/m2-K requires R_total >= 3.030 m2-K/W -> t_ins >= (3.030 - 0.332) * 0.038 = 0.1025 m -> 0.100 m (100 mm).
#   - Cold U <= 0.28 W/m2-K requires R_total >= 3.571 m2-K/W -> t_ins >= (3.571 - 0.332) * 0.038 = 0.1231 m -> 0.125 m (125 mm).
# Base uninsulated wall (200mm brick + 30mm plaster + air films): R_base = 0.489 m2-K/W.
#   - U <= 0.40 W/m2-K requires R_total >= 2.500 m2-K/W -> t_ins >= (2.500 - 0.489) * 0.038 = 0.0764 m -> 0.075 m (75 mm).
#   - Temperate U <= 0.55 W/m2-K requires R_total >= 1.818 m2-K/W -> t_ins >= (1.818 - 0.489) * 0.038 = 0.0505 m -> 0.050 m (50 mm).
#   - Cold U <= 0.34 W/m2-K requires R_total >= 2.941 m2-K/W -> t_ins >= (2.941 - 0.489) * 0.038 = 0.0932 m -> 0.100 m (100 mm).

REFERENCE_R3_PER_CITY = {
    'Jodhpur': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Hot and Dry',
        'code_standard': 'ECBC 2017 & ENS 2018',
        'citation_source': 'ECBC 2017 Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (SRI>=78); ENS 2018 Sec 3.1 & 3.3',
        'citation_url': 'https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc',
        'target_u_roof': 0.33,
        'target_u_wall': 0.40,
        'roof_insulation_thickness': 0.100,  # 100 mm XPS
        'wall_insulation_thickness': 0.075,  # 75 mm XPS
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # Cool Roof SRI >= 78 compliant
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,               # ENS 2018 Table 3 minimum permanent overhang
        'ventilation_ach': 5.0
    },
    'Mumbai': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Warm and Humid',
        'code_standard': 'ECBC 2017 & ENS 2018',
        'citation_source': 'ECBC 2017 Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (SRI>=78); ENS 2018 Sec 3.1 & 3.3',
        'citation_url': 'https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc',
        'target_u_roof': 0.33,
        'target_u_wall': 0.40,
        'roof_insulation_thickness': 0.100,  # 100 mm XPS
        'wall_insulation_thickness': 0.075,  # 75 mm XPS
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # Cool Roof SRI >= 78 compliant
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    },
    'New_Delhi': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Composite',
        'code_standard': 'ECBC 2017 & ENS 2018',
        'citation_source': 'ECBC 2017 Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (SRI>=78); ENS 2018 Sec 3.1 & 3.3',
        'citation_url': 'https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc',
        'target_u_roof': 0.33,
        'target_u_wall': 0.40,
        'roof_insulation_thickness': 0.100,  # 100 mm XPS
        'wall_insulation_thickness': 0.075,  # 75 mm XPS
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # Cool Roof SRI >= 78 compliant
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    },
    'Bengaluru': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Temperate',
        'code_standard': 'ECBC 2017 & ENS 2018',
        'citation_source': 'ECBC 2017 Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.55 for Temperate); ENS 2018 Sec 3.1 & 3.3',
        'citation_url': 'https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc',
        'target_u_roof': 0.33,
        'target_u_wall': 0.55,
        'roof_insulation_thickness': 0.100,  # 100 mm XPS
        'wall_insulation_thickness': 0.050,  # 50 mm XPS
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.60,      # Standard temperate absorptance
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.30,
        'ventilation_ach': 5.0
    },
    'Shimla': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Cold',
        'code_standard': 'ECBC 2017 & ENS 2018',
        'citation_source': 'ECBC 2017 Table 4-4 (Cold Roof U<=0.28), Table 4-7 (Cold Wall U<=0.34); ENS 2018 Table 2 (U_env<=1.80)',
        'citation_url': 'https://beeindia.gov.in/en/programmes/energy-conservation-building-code-ecbc',
        'target_u_roof': 0.28,
        'target_u_wall': 0.34,
        'roof_insulation_thickness': 0.125,  # 125 mm XPS
        'wall_insulation_thickness': 0.100,  # 100 mm XPS
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.70,      # Solar absorptive roof for winter passive solar heat gain
        'wwr': 0.15,
        'orientation': 0.0,
        'shading_depth': 0.00,               # Unshaded in cold climate to maximize passive solar winter gain
        'ventilation_ach': 2.0               # Restricted ventilation to prevent severe cold-air infiltration
    }
}

def get_reference_r3(city_name: str) -> dict:
    """Returns the climate-specific R3 ECBC/ENS code-compliant reference design."""
    if city_name not in REFERENCE_R3_PER_CITY:
        raise ValueError(f"Unknown city {city_name}. Must be one of {list(REFERENCE_R3_PER_CITY.keys())}")
    return REFERENCE_R3_PER_CITY[city_name]

def get_city_references(city_name: str) -> list:
    """Returns R1 Lightweight, R2 Conventional, and R3 Code-Compliant for a city."""
    return [REFERENCE_R1, REFERENCE_R2, get_reference_r3(city_name)]

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
