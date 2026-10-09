"""
Phase 4A: Dual Comfort Judge Coupling, Sensitivity Analysis, and Objectives Generation.
Executes Step 1, Step 2, Step 3, Step 4 of Phase 4A:
- Evaluates simulation batch integrity and paired completeness
- Performs one-factor ventilation sensitivity checks
- Computes Adaptive-90 and O2 spreads across all 5 climate zones
- Ranks design variables via XGBoost gain / permutation importance (D-016)
- Evaluates dual comfort judges (ML champion & Adaptive 90%) on hourly simulation series
- Computes Spearman rank correlation between ML and Adaptive judges per city
- Computes sensitivity between running mean outdoor temperature vs raw drybulb
- Outputs data/processed/objectives.parquet and evidence artifacts
"""

import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRegressor, XGBClassifier

sys.path.insert(0, os.path.abspath("."))

from src.sim.sampler import sample_designs
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

DESIGN_VARS = [
    'roof_insulation_thickness',
    'wall_insulation_thickness',
    'wall_mass_class',
    'roof_solar_absorptance',
    'wwr',
    'orientation',
    'shading_depth',
    'ventilation_ach'
]

def load_sim_runs_data():
    """Loads Phase 3 sim_runs.parquet and extracts paired valid designs."""
    sim_path = "data/processed/sim_runs.parquet"
    if not os.path.exists(sim_path):
        raise FileNotFoundError(f"Missing {sim_path}")
    df_sim = pd.read_parquet(sim_path)
    
    # Filter for SUCCESS runs
    df_success = df_sim[df_sim['status'] == 'SUCCESS'].copy()
    
    # Check pair completeness: must have both free_running and ideal_loads
    piv = df_success.pivot_table(
        index=['city', 'design_id'],
        columns='mode',
        values='status',
        aggfunc='first'
    )
    valid_pairs = piv[piv['free_running'].notna() & piv['ideal_loads'].notna()].index
    
    # Filter both modes for valid pairs
    df_fr = df_success[
        (df_success['mode'] == 'free_running') &
        df_success.set_index(['city', 'design_id']).index.isin(valid_pairs)
    ].copy()
    
    df_il = df_success[
        (df_success['mode'] == 'ideal_loads') &
        df_success.set_index(['city', 'design_id']).index.isin(valid_pairs)
    ].copy()
    
    return df_sim, df_fr, df_il, valid_pairs

def compute_variable_importances(df_data, target_col, city_name):
    """
    Ranks design variables by XGBoost gain importance for a target objective.
    Encodes categorical wall_mass_class into numerical format.
    """
    X = df_data[DESIGN_VARS].copy()
    # Map wall_mass_class
    mass_map = {'light': 0, 'medium': 1, 'heavy': 2}
    X['wall_mass_class'] = X['wall_mass_class'].map(mass_map)
    y = df_data[target_col].values
    
    model = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X, y)
    
    # Extract feature importances (gain)
    importances = model.feature_importances_
    imp_series = pd.Series(importances, index=DESIGN_VARS).sort_values(ascending=False)
    return imp_series

def run_coupling_and_objectives():
    print("="*80)
    print("PHASE 4A: DUAL COMFORT JUDGE COUPLING & OBJECTIVES PIPELINE")
    print("="*80)
    
    # 1. Batch Integrity
    df_sim, df_fr, df_il, valid_pairs = load_sim_runs_data()
    print(f"\n[STEP 1] Batch Integrity:")
    print(f"Total simulations recorded: {len(df_sim):,}")
    print(f"Total valid paired designs (both modes SUCCESS): {len(valid_pairs):,}")
    for city in CITIES_EPW.keys():
        n_c = len([p for p in valid_pairs if p[0] == city])
        print(f"  - {city:12s}: {n_c:,} valid designs")
        
    # Merge O2 energy from ideal_loads into design dataframe
    il_energy_map = df_il.set_index(['city', 'design_id'])['o2_energy_kwh_per_m2'].to_dict()
    
    # 2. Load ML Champion model
    model = load_champion_model("models/champion_comfort_model.joblib")
    print("\nLoaded calibrated ML Champion comfort model (Ablation_A3_OutdoorTemp).")
    
    # 3. Process each city's hourly data and evaluate judges
    records = []
    sens_records = []
    
    # Sample designs table for design variable values
    df_samples = sample_designs(n_samples=1000, seed=42).set_index('design_id')
    
    for city_name in CITIES_EPW.keys():
        print(f"\nEvaluating comfort judges for {city_name}...")
        hourly_file = f"data/processed/hourly_fr_{city_name}.parquet"
        if not os.path.exists(hourly_file):
            raise FileNotFoundError(f"Hourly simulation file not found: {hourly_file}. Please wait for simulation extraction to finish.")
            
        df_hourly = pd.read_parquet(hourly_file)
        # Group by design_id
        grouped = df_hourly.groupby('design_id', observed=True)
        
        for d_id, group in grouped:
            pair_key = (city_name, d_id)
            if pair_key not in valid_pairs:
                continue # Skip dropped incomplete designs
                
            group_sorted = group.sort_values('hour')
            ta = group_sorted['ta'].values
            tr = group_sorted['tr'].values
            rh = group_sorted['rh'].values
            tout = group_sorted['t_out'].values
            
            # Daily outdoor mean and running mean (t_mot_isd)
            daily_tout = calculate_daily_mean_series(tout)
            t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
            t_rm_hourly = np.repeat(t_rm_daily, 24)
            
            # Clo schedule (Assumption A-004)
            clo_hourly = compute_clo_schedule_a004(daily_tout)
            
            # Judge 1: Adaptive 90%
            adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
            
            # Judge 2: ML Champion (using running mean outdoor temperature)
            ml_res = evaluate_ml_champion_comfort(
                model=model,
                ta=ta,
                tr=tr,
                rh=rh,
                t_outdoor_hourly=t_rm_hourly,
                clo_hourly=clo_hourly,
                met=1.1,
                vel=0.15
            )
            
            # Sensitivity: ML Champion using raw hourly tout
            ml_sens_res = evaluate_ml_champion_comfort(
                model=model,
                ta=ta,
                tr=tr,
                rh=rh,
                t_outdoor_hourly=tout,
                clo_hourly=clo_hourly,
                met=1.1,
                vel=0.15
            )
            
            # Retrieve design variables & O2 energy
            d_params = df_samples.loc[d_id].to_dict()
            o2_val = il_energy_map.get(pair_key, np.nan)
            
            rec = {
                "city": city_name,
                "design_id": d_id,
                **d_params,
                "O1_ml": ml_res['O1_ml'],
                "warm_ml": ml_res['warm_ml'],
                "cool_ml": ml_res['cool_ml'],
                "O1_adapt": adapt_res['O1_adapt'],
                "hot_adapt": adapt_res['hot_adapt'],
                "cold_adapt": adapt_res['cold_adapt'],
                "invalid_share_adapt": adapt_res['invalid_share_adapt'],
                "O2": o2_val
            }
            records.append(rec)
            
            sens_records.append({
                "city": city_name,
                "design_id": d_id,
                "O1_ml_running_mean": ml_res['O1_ml'],
                "O1_ml_raw_tout": ml_sens_res['O1_ml'],
                "diff_O1_ml": ml_res['O1_ml'] - ml_sens_res['O1_ml']
            })
            
    df_objectives = pd.DataFrame(records)
    df_sens = pd.DataFrame(sens_records)
    
    # Save objectives.parquet
    out_obj_path = "data/processed/objectives.parquet"
    df_objectives.to_parquet(out_obj_path, index=False)
    print(f"\nSaved consolidated objectives dataset ({len(df_objectives):,} rows x {len(df_objectives.columns)} cols) to {out_obj_path}")
    
    # Step 3 Analysis: Sensitivity & Spread
    print("\n" + "="*80)
    print("STEP 3: SENSITIVITY AND SPREAD ACROSS FULL BATCH")
    print("="*80)
    
    spread_summary = []
    spearman_summary = []
    
    for city_name in CITIES_EPW.keys():
        c_df = df_objectives[df_objectives['city'] == city_name]
        
        # Adaptive 90% spread
        ad_min = c_df['O1_adapt'].min()
        ad_med = c_df['O1_adapt'].median()
        ad_max = c_df['O1_adapt'].max()
        ad_spread = ad_max - ad_min
        
        # ML Champion spread
        ml_min = c_df['O1_ml'].min()
        ml_med = c_df['O1_ml'].median()
        ml_max = c_df['O1_ml'].max()
        ml_spread = ml_max - ml_min
        
        # O2 energy spread
        o2_min = c_df['O2'].min()
        o2_med = c_df['O2'].median()
        o2_max = c_df['O2'].max()
        o2_spread = o2_max - o2_min
        
        # Spearman correlation between O1_ml and O1_adapt
        valid_both = c_df.dropna(subset=['O1_ml', 'O1_adapt'])
        if len(valid_both) > 10 and not np.isnan(valid_both['O1_adapt'].iloc[0]):
            r_s, p_val = spearmanr(valid_both['O1_ml'], valid_both['O1_adapt'])
        else:
            r_s, p_val = np.nan, np.nan
            
        spread_summary.append({
            "City": city_name,
            "Adapt90_Min": ad_min,
            "Adapt90_Med": ad_med,
            "Adapt90_Max": ad_max,
            "Adapt90_Spread": ad_spread,
            "ML_Min": ml_min,
            "ML_Med": ml_med,
            "ML_Max": ml_max,
            "ML_Spread": ml_spread,
            "O2_Min": o2_min,
            "O2_Med": o2_med,
            "O2_Max": o2_max,
            "O2_Spread": o2_spread,
            "Spearman_O1_ML_vs_Adapt": r_s,
            "Spearman_p_val": p_val
        })
        
    df_spread = pd.DataFrame(spread_summary)
    print("\nSpread & Correlation Summary:")
    print(df_spread.to_string(index=False))
    
    # Variable Importance Ranking
    print("\n" + "="*80)
    print("VARIABLE IMPORTANCE RANKING (XGBoost Gain)")
    print("="*80)
    importance_dict = {}
    for city_name in CITIES_EPW.keys():
        c_df = df_objectives[df_objectives['city'] == city_name]
        imp_o1_adapt = compute_variable_importances(c_df, 'O1_adapt', city_name) if not c_df['O1_adapt'].isna().all() else None
        imp_o1_ml = compute_variable_importances(c_df, 'O1_ml', city_name)
        imp_o2 = compute_variable_importances(c_df, 'O2', city_name)
        
        importance_dict[city_name] = {
            "O1_adapt": imp_o1_adapt.to_dict() if imp_o1_adapt is not None else "All Invalid",
            "O1_ml": imp_o1_ml.to_dict(),
            "O2": imp_o2.to_dict()
        }
        print(f"\n--- {city_name} Top Drivers ---")
        print("O1 (ML Champion):", ", ".join([f"{k} ({v:.3f})" for k, v in imp_o1_ml.head(3).items()]))
        if imp_o1_adapt is not None:
            print("O1 (Adaptive 90%):", ", ".join([f"{k} ({v:.3f})" for k, v in imp_o1_adapt.head(3).items()]))
        print("O2 (Energy):      ", ", ".join([f"{k} ({v:.3f})" for k, v in imp_o2.head(3).items()]))
        
    # Sensitivity: Running Mean vs Raw Tout
    print("\n" + "="*80)
    print("SENSITIVITY: RUNNING MEAN OUTDOOR TEMP VS RAW DRYBULB")
    print("="*80)
    sens_summary = df_sens.groupby('city')['diff_O1_ml'].agg(['mean', 'std', 'min', 'max']).reset_index()
    print(sens_summary.to_string(index=False))
    
    # Save Evidence Artifacts
    os.makedirs("reports/evidence", exist_ok=True)
    evidence_txt = "reports/evidence/phase4a_coupling_output.txt"
    with open(evidence_txt, "w", encoding="utf-8") as f:
        f.write("PHASE 4A COUPLING & OBJECTIVES EVIDENCE OUTPUT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Total Valid Designs: {len(df_objectives)}\n\n")
        f.write("SPREAD & SPEARMAN CORRELATION TABLE:\n")
        f.write(df_spread.to_string(index=False) + "\n\n")
        f.write("VARIABLE IMPORTANCE BY CITY (XGBoost Gain):\n")
        f.write(json.dumps(importance_dict, indent=2) + "\n\n")
        f.write("SENSITIVITY (O1_ml running mean vs raw tout):\n")
        f.write(sens_summary.to_string(index=False) + "\n")
        
    print(f"\nSaved Phase 4A evidence to {evidence_txt}")
    return df_objectives, df_spread, importance_dict, sens_summary

if __name__ == "__main__":
    run_coupling_and_objectives()
