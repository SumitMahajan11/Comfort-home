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
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw",
    "Leh": "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
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

# R3 Code-Compliant Baseline per Indian Climate Zone
# Primary Reference: Eco-Niwas Samhita 2024 (Residential Buildings Code)
# Secondary Reference: Energy Conservation Building Code (ECBC 2017, Commercial Buildings)
#
# Conservatism Note:
# The R3 baseline envelope is sized to satisfy the stricter commercial ECBC 2017 U-limits
# (e.g., U_roof <= 0.33 W/m2·K vs residential ENS U_roof <= 1.20 W/m2·K, and U_wall <= 0.40 W/m2·K),
# thereby comfortably exceeding the residential ENS minimum requirements as a conservative,
# climate-responsive reference benchmark.
#
# Sources & Literal Citations:
# 1. Primary: Bureau of Energy Efficiency (BEE), Ministry of Power, Govt. of India:
#    "Eco-Niwas Samhita (ENS) 2024 (Part I: Building Envelope)" (PDF: data/docs/ENS_2024.pdf):
#    - Section 5.2.1.3 (Page 34): "Thermal transmittance of the roof shall comply with the maximum Uroof value of 1.2 W/m2·K as prescribed in section 9.4"
#    - Section 5.2.1.4 (Page 34): "The RETV for the building envelope (except the roof) for four climate zones... shall comply with the maximum RETV value of 15 W/m2"
#    - Section 5.2.1.5 (Page 34): "thermal transmittance of the building envelope (except the roof) for the cold climate shall comply with the maximum value of 1.8 W/m2·K"
#
# 2. Secondary: Bureau of Energy Efficiency (BEE), Ministry of Power, Govt. of India:
#    "Energy Conservation Building Code 2017" (ECBC 2017, Commercial) (PDF: data/docs/ECBC_2017.pdf):
#    - Table 4-4 (Page 59): "All building types, except below Composite 0.33 Hot-dry 0.33 Warm-humid 0.33 Temperate 0.33 Cold 0.28"
#    - Table 4-7 (Page 60): "All building types, except below Composite 0.40 Hot-dry 0.40 Warm-humid 0.40 Temperate 0.55 Cold 0.34"
#    - Section 4.3.1.1(a) (Page 59): "roofs with slopes less than 20° shall have an initial solar reflectance of no less than 0.70" (solar absorptance <= 0.30)
#
# Unprescribed Geometry / Operation Assumptions (Labelled ASSUMPTION):
# - ASSUMPTION A-008: External overhang depth = 0.30 m (Step 4 lower bound applied as baseline geometry; ENS specifies no fixed depth in meters).
# - ASSUMPTION A-009: Infiltration/ventilation rate = 5.0 ACH (Standard baseline default consistent across all 5 cities; no code-mandated ACH for unconditioned single-zone shelters).
# - ASSUMPTION A-010: Window-to-Wall Ratio = 0.15 (Standard baseline shelter fenestration ratio, compliant with ECBC Table 4-10 maximum 0.40).

REFERENCE_R3_PER_CITY = {
    'Jodhpur': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Hot and Dry',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.4 (RETV <= 15 W/m2; RETV not evaluated, walls sized to ECBC commercial U-limits)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (Reflectance>=0.70, Absorptance<=0.30)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.33,
        'target_u_wall_ecbc': 0.40,
        'computed_u_roof': 0.276,            # 125 mm XPS: R_total=3.621 -> U=0.276 W/m2-K (Meets ENS 1.20 & ECBC 0.33)
        'computed_u_wall': 0.326,            # 100 mm XPS: R_total=3.068 -> U=0.326 W/m2-K (Meets ECBC 0.40 commercial limit; ENS RETV not evaluated)
        'roof_insulation_thickness': 0.125,  # 125 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.100,  # 100 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # ECBC Cool Roof initial solar reflectance >= 0.70
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default
    },
    'Mumbai': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Warm and Humid',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.4 (RETV <= 15 W/m2; RETV not evaluated, walls sized to ECBC commercial U-limits)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (Reflectance>=0.70, Absorptance<=0.30)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.33,
        'target_u_wall_ecbc': 0.40,
        'computed_u_roof': 0.276,            # 125 mm XPS: R_total=3.621 -> U=0.276 W/m2-K (Meets ENS 1.20 & ECBC 0.33)
        'computed_u_wall': 0.326,            # 100 mm XPS: R_total=3.068 -> U=0.326 W/m2-K (Meets ECBC 0.40 commercial limit; ENS RETV not evaluated)
        'roof_insulation_thickness': 0.125,  # 125 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.100,  # 100 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # ECBC Cool Roof initial solar reflectance >= 0.70
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default
    },
    'New_Delhi': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Composite',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.4 (RETV <= 15 W/m2; RETV not evaluated, walls sized to ECBC commercial U-limits)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Roof U<=0.33), Table 4-7 (Wall U<=0.40), Sec 4.3.1.1 (Reflectance>=0.70, Absorptance<=0.30)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.33,
        'target_u_wall_ecbc': 0.40,
        'computed_u_roof': 0.276,            # 125 mm XPS: R_total=3.621 -> U=0.276 W/m2-K (Meets ENS 1.20 & ECBC 0.33)
        'computed_u_wall': 0.326,            # 100 mm XPS: R_total=3.068 -> U=0.326 W/m2-K (Meets ECBC 0.40 commercial limit; ENS RETV not evaluated)
        'roof_insulation_thickness': 0.125,  # 125 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.100,  # 100 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.30,      # ECBC Cool Roof initial solar reflectance >= 0.70
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default
    },
    'Bengaluru': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Temperate',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.4 (RETV <= 15 W/m2; RETV not evaluated, walls sized to ECBC commercial U-limits)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Roof U<=0.33), Table 4-7 (Temperate Wall U<=0.55)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.33,
        'target_u_wall_ecbc': 0.55,
        'computed_u_roof': 0.276,            # 125 mm XPS: R_total=3.621 -> U=0.276 W/m2-K (Meets ENS 1.20 & ECBC 0.33)
        'computed_u_wall': 0.415,            # 75 mm XPS: R_total=2.410 -> U=0.415 W/m2-K (Meets ECBC 0.55 commercial limit; ENS RETV not evaluated)
        'roof_insulation_thickness': 0.125,  # 125 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.075,  # 75 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.60,      # ASSUMPTION: Standard conventional absorptance (no cool roof mandate in temperate)
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default
    },
    'Shimla': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Cold',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.5 (U_envelope,cold <= 1.80 W/m2-K)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Cold Roof U<=0.28), Table 4-7 (Cold Wall U<=0.34)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.28,
        'target_u_wall_ens': 1.80,
        'target_u_wall_ecbc': 0.34,
        'computed_u_roof': 0.238,            # 150 mm XPS: R_total=4.209 -> U=0.238 W/m2-K (Meets ENS 1.20 & ECBC 0.28)
        'computed_u_wall': 0.326,            # 100 mm XPS: R_total=3.068 -> U=0.326 W/m2-K (Meets ECBC 0.34 & ENS 1.80)
        'roof_insulation_thickness': 0.150,  # 150 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.100,  # 100 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.60,      # ASSUMPTION: Standard conventional absorptance (passive-solar 0.70 tuning removed)
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default (2.0 ACH tuning removed)
    },
    'Leh': {
        'name': 'R3_Code_Compliant',
        'climate_zone': 'Cold',
        'primary_standard': 'Eco-Niwas Samhita 2024 (Residential)',
        'primary_clause': 'ENS Section 5.2.1.3 (U_roof <= 1.2 W/m2-K), Section 5.2.1.5 (U_envelope,cold <= 1.80 W/m2-K)',
        'secondary_standard': 'ECBC 2017 (Commercial)',
        'secondary_clause': 'ECBC Table 4-4 (Cold Roof U<=0.28), Table 4-7 (Cold Wall U<=0.34)',
        'citation_pdf_primary': 'data/docs/ENS_2024.pdf (p. 34)',
        'citation_pdf_secondary': 'data/docs/ECBC_2017.pdf (pp. 59-60)',
        'citation_url': 'https://beeindia.gov.in',
        'target_u_roof_ens': 1.20,
        'target_u_roof_ecbc': 0.28,
        'target_u_wall_ens': 1.80,
        'target_u_wall_ecbc': 0.34,
        'computed_u_roof': 0.238,            # 150 mm XPS: R_total=4.209 -> U=0.238 W/m2-K (Meets ENS 1.20 & ECBC 0.28)
        'computed_u_wall': 0.326,            # 100 mm XPS: R_total=3.068 -> U=0.326 W/m2-K (Meets ECBC 0.34 & ENS 1.80)
        'roof_insulation_thickness': 0.150,  # 150 mm XPS (25 mm step)
        'wall_insulation_thickness': 0.100,  # 100 mm XPS (25 mm step)
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.60,      # ASSUMPTION: Standard conventional absorptance
        'wwr': 0.15,                         # ASSUMPTION: Baseline fenestration ratio (ECBC Table 4-10 max <= 0.40)
        'orientation': 0.0,
        'shading_depth': 0.30,               # ASSUMPTION: Step 4 overhang lower bound (>= 0.30 m)
        'ventilation_ach': 5.0               # ASSUMPTION: Standard baseline infiltration default
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
