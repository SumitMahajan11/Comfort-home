"""
src/models/explain.py

SHAP explainability module for ClimateAdapt-Comfort.
Computes global SHAP attributions for the ML Champion comfort model and XGBoost surrogates,
generates explainability figures, exports mean |SHAP| tables, and provides local design attribution helpers.
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath("."))

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]
TARGETS = ["O1_ml", "O1_adapt", "O2", "warm_ml", "cool_ml"]

FEATURE_NAME_MAP = {
    'roof_insulation_thickness': 'Roof Insulation (m)',
    'wall_insulation_thickness': 'Wall Insulation (m)',
    'roof_solar_absorptance': 'Roof Solar Absorptance',
    'wwr': 'Window-to-Wall Ratio (WWR)',
    'orientation': 'Orientation (deg)',
    'shading_depth': 'Shading Depth (m)',
    'ventilation_ach': 'Ventilation (ACH)',
    'wall_mass_heavy': 'Wall Mass: Heavy (Concrete)',
    'wall_mass_light': 'Wall Mass: Light (Sheet)',
    'wall_mass_medium': 'Wall Mass: Medium (Clay Brick)',
    'ta': 'Indoor Air Temp Ta (°C)',
    'tr': 'Mean Radiant Temp Tr (°C)',
    'rh': 'Relative Humidity RH (%)',
    'vel': 'Air Velocity (m/s)',
    'clo': 'Clothing Insulation (clo)',
    'met': 'Metabolic Rate (met)',
    't_outdoor': 'Running Mean Outdoor Temp (°C)'
}

def run_champion_shap_analysis(sample_size=2000, seed=42):
    """
    Step 1a: Global SHAP for ML Champion comfort model on DB II test set and simulated hourly conditions.
    """
    print("\n" + "="*80)
    print("STEP 1A: SHAP ANALYSIS FOR ML CHAMPION COMFORT MODEL")
    print("="*80)
    
    os.makedirs("reports/figures", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    champ_dict = joblib.load("models/champion_comfort_model.joblib")
    model = champ_dict['model']
    features = champ_dict['features']
    
    # 1. DB II test data
    clean_df = pd.read_parquet("data/processed/comfort_clean.parquet")
    # Prepare complete features
    df_db2 = clean_df.dropna(subset=['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_mot_isd']).copy()
    df_db2['t_outdoor'] = df_db2['t_mot_isd']
    X_db2 = df_db2[features]
    
    if len(X_db2) > sample_size:
        X_db2_sample = X_db2.sample(n=sample_size, random_state=seed)
    else:
        X_db2_sample = X_db2
        
    explainer = shap.TreeExplainer(model)
    shap_values_db2 = explainer.shap_values(X_db2_sample)
    
    # Check shape: for multi-class, shap_values is array (N, features, 3) or list of 3 (N, features)
    if isinstance(shap_values_db2, list):
        # list of 3 classes: 0=cool, 1=neutral, 2=warm
        mean_abs_cool = np.mean(np.abs(shap_values_db2[0]), axis=0)
        mean_abs_neutral = np.mean(np.abs(shap_values_db2[1]), axis=0)
        mean_abs_warm = np.mean(np.abs(shap_values_db2[2]), axis=0)
    else:
        # numpy 3D array (N, features, 3)
        mean_abs_cool = np.mean(np.abs(shap_values_db2[:, :, 0]), axis=0)
        mean_abs_neutral = np.mean(np.abs(shap_values_db2[:, :, 1]), axis=0)
        mean_abs_warm = np.mean(np.abs(shap_values_db2[:, :, 2]), axis=0)
        
    mean_abs_overall = (mean_abs_cool + mean_abs_neutral + mean_abs_warm) / 3.0
    
    df_shap_db2 = pd.DataFrame({
        'feature': features,
        'feature_name': [FEATURE_NAME_MAP.get(f, f) for f in features],
        'mean_abs_shap_cool': mean_abs_cool,
        'mean_abs_shap_neutral': mean_abs_neutral,
        'mean_abs_shap_warm': mean_abs_warm,
        'mean_abs_shap_overall': mean_abs_overall
    }).sort_values(by='mean_abs_shap_overall', ascending=False)
    
    df_shap_db2.to_csv("data/processed/shap_champion_db2.csv", index=False)
    print("  -> Saved DB II SHAP metrics to data/processed/shap_champion_db2.csv")
    print(df_shap_db2.to_string(index=False))
    
    # Plot DB II SHAP summary
    plt.figure(figsize=(10, 5), dpi=150)
    indices = np.arange(len(df_shap_db2))
    width = 0.25
    plt.barh(indices + width, df_shap_db2['mean_abs_shap_cool'], width, label='Cool Sensation', color='#3498db')
    plt.barh(indices, df_shap_db2['mean_abs_shap_neutral'], width, label='Neutral (Comfort)', color='#2ecc71')
    plt.barh(indices - width, df_shap_db2['mean_abs_shap_warm'], width, label='Warm Sensation', color='#e74c3c')
    plt.yticks(indices, df_shap_db2['feature_name'])
    plt.xlabel('Mean |SHAP Value| (Impact on Class Sensation Probability)')
    plt.title('ML Champion Comfort Model - Global Feature Attributions (ASHRAE DB II)')
    plt.gca().invert_yaxis()
    plt.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig("reports/figures/shap_champion_db2.png")
    plt.close()
    print("  -> Saved figure reports/figures/shap_champion_db2.png")
    
    # 2. Simulated indoor hours per city
    sim_shap_records = []
    from src.optimize.coupling import (
        calculate_daily_mean_series,
        compute_running_mean_outdoor_temperature_db2,
        compute_clo_schedule_a004
    )
    
    for city in CITIES:
        hourly_file = f"data/processed/hourly_fr_{city}.parquet"
        if os.path.exists(hourly_file):
            df_hourly = pd.read_parquet(hourly_file)
            # Sample hourly records from first 5 designs to ensure full 8760 sequence for tout
            sample_designs = df_hourly['design_id'].unique()[:5]
            df_sub = df_hourly[df_hourly['design_id'].isin(sample_designs)].copy()
            
            # Compute running mean tout and clo for 8760 hours
            t_out_8760 = df_sub.iloc[:8760]['t_out'].values
            daily_means = calculate_daily_mean_series(t_out_8760)
            t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_means)
            t_rm_hourly = np.repeat(t_rm_daily, 24)
            clo_hourly = compute_clo_schedule_a004(daily_means)
            
            # Tile across the sample designs
            n_reps = len(df_sub) // 8760
            df_sub['t_outdoor'] = np.tile(t_rm_hourly, n_reps)
            df_sub['clo'] = np.tile(clo_hourly, n_reps)
            df_sub['vel'] = 0.15
            df_sub['met'] = 1.1
            
            df_h_sample = df_sub.sample(n=min(len(df_sub), sample_size), random_state=seed)
            X_sim = df_h_sample[features]
            
            shap_sim = explainer.shap_values(X_sim)
            if isinstance(shap_sim, list):
                m_neutral = np.mean(np.abs(shap_sim[1]), axis=0)
            else:
                m_neutral = np.mean(np.abs(shap_sim[:, :, 1]), axis=0)
                
            for feat, val in zip(features, m_neutral):
                sim_shap_records.append({
                    'city': city,
                    'feature': feat,
                    'feature_name': FEATURE_NAME_MAP.get(feat, feat),
                    'mean_abs_shap_neutral': val
                })
                
    if sim_shap_records:
        df_sim_shap = pd.DataFrame(sim_shap_records)
        df_sim_shap.to_csv("data/processed/shap_champion_sim_cities.csv", index=False)
        print("  -> Saved simulated hours SHAP to data/processed/shap_champion_sim_cities.csv")
        
        # Plot city comparison for champion model
        plt.figure(figsize=(12, 6), dpi=150)
        pvt = df_sim_shap.pivot(index='feature_name', columns='city', values='mean_abs_shap_neutral')
        pvt.plot(kind='barh', figsize=(12, 6), colormap='viridis')
        plt.xlabel('Mean |SHAP Value| on Comfort Probability')
        plt.title('ML Champion Feature Importance Across 5 Simulated Climate Zones')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig("reports/figures/shap_champion_sim_cities.png")
        plt.close()
        print("  -> Saved figure reports/figures/shap_champion_sim_cities.png")
        
    return df_shap_db2

def run_surrogates_shap_analysis(sample_size=1000, seed=42):
    """
    Step 1b: SHAP analysis per city and surrogate objective.
    """
    print("\n" + "="*80)
    print("STEP 1B: SHAP ANALYSIS FOR SURROGATE MODELS (5 Cities x 5 Targets)")
    print("="*80)
    
    # Load dataset features from objectives.parquet
    df_objs = pd.read_parquet("data/processed/objectives.parquet")
    
    surrogate_shap_summary = []
    
    for city in CITIES:
        city_objs = df_objs[df_objs['city'] == city]
        
        # Prepare one-hot features
        feat_df = city_objs[['roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach']].copy()
        feat_df['wall_mass_heavy'] = (city_objs['wall_mass_class'] == 'heavy').astype(float)
        feat_df['wall_mass_light'] = (city_objs['wall_mass_class'] == 'light').astype(float)
        feat_df['wall_mass_medium'] = (city_objs['wall_mass_class'] == 'medium').astype(float)
        
        feature_cols = ['roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach', 'wall_mass_heavy', 'wall_mass_light', 'wall_mass_medium']
        X_city = feat_df[feature_cols]
        if len(X_city) > sample_size:
            X_city_sample = X_city.sample(n=sample_size, random_state=seed)
        else:
            X_city_sample = X_city
            
        for target in TARGETS:
            model_path = f"models/surrogate_{city}_{target}.joblib"
            if not os.path.exists(model_path):
                continue
            
            s_dict = joblib.load(model_path)
            model = s_dict['model']
            
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_city_sample)
            
            mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
            
            for feat, val in zip(feature_cols, mean_abs_shap):
                surrogate_shap_summary.append({
                    'city': city,
                    'target': target,
                    'feature': feat,
                    'feature_name': FEATURE_NAME_MAP.get(feat, feat),
                    'mean_abs_shap': val
                })
                
            # Create a beeswarm/bar plot for primary objectives
            if target in ['O1_ml', 'O1_adapt', 'O2']:
                plt.figure(figsize=(9, 5), dpi=150)
                # Plot bar of mean |SHAP|
                sort_idx = np.argsort(mean_abs_shap)
                plt.barh([FEATURE_NAME_MAP.get(feature_cols[i], feature_cols[i]) for i in sort_idx],
                         mean_abs_shap[sort_idx], color='teal' if target=='O1_adapt' else ('steelblue' if target=='O1_ml' else 'coral'))
                plt.xlabel('Mean |SHAP Value| (Impact on Objective)')
                plt.title(f'{city} - {target} Surrogate Feature Importance')
                plt.tight_layout()
                fig_name = f"reports/figures/shap_surrogate_{city}_{target}.png"
                plt.savefig(fig_name)
                plt.close()
                
    df_surr_shap = pd.DataFrame(surrogate_shap_summary)
    df_surr_shap.to_csv("data/processed/shap_surrogates_summary.csv", index=False)
    print(f"  -> Saved all surrogate SHAP metrics to data/processed/shap_surrogates_summary.csv ({len(df_surr_shap)} rows)")
    
    # Create global aggregated surrogate importance plot
    plt.figure(figsize=(14, 8), dpi=150)
    agg = df_surr_shap[df_surr_shap['target'].isin(['O1_ml', 'O1_adapt', 'O2'])].groupby(['target', 'feature_name'])['mean_abs_shap'].mean().unstack(level=0)
    agg.plot(kind='barh', figsize=(12, 7), colormap='tab10')
    plt.xlabel('Cross-City Mean |SHAP Value|')
    plt.title('Global Surrogate Design Variable Importance (O1_ml vs O1_adapt vs O2)')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig("reports/figures/shap_surrogates_global.png")
    plt.close()
    print("  -> Saved global figure reports/figures/shap_surrogates_global.png")
    
    return df_surr_shap

def get_top_drivers(city, design_dict, target='O1_ml', top_k=3):
    """
    Helper function to explain any specific shelter design for a given city and target objective.
    Returns the top K drivers (features, signed SHAP value, direction, magnitude, and interpretation).
    
    Parameters:
    - city: string (e.g. 'Jodhpur', 'Mumbai', 'New_Delhi', 'Bengaluru', 'Shimla')
    - design_dict: dict with 8 design variables
    - target: string ('O1_ml', 'O1_adapt', 'O2', 'warm_ml', 'cool_ml')
    - top_k: int, number of top drivers to return (default 3)
    
    Returns:
    - list of dicts with keys: ['feature', 'feature_name', 'input_value', 'shap_value', 'abs_shap', 'direction', 'effect_desc', 'base_value', 'predicted_value']
    """
    model_path = f"models/surrogate_{city}_{target}.joblib"
    if not os.path.exists(model_path):
        csv_path = "data/processed/shap_surrogates_summary.csv"
        if os.path.exists(csv_path):
            df_s = pd.read_csv(csv_path)
            sub = df_s[(df_s['city'] == city) & (df_s['target'] == target)].sort_values('mean_abs_shap', ascending=False)
            drivers = []
            for _, r in sub.head(top_k).iterrows():
                feat = r['feature']
                val = design_dict.get(feat, 0.0)
                mean_shap = float(r['mean_abs_shap'])
                drivers.append({
                    'feature': feat,
                    'feature_name': r['feature_name'],
                    'input_value': val,
                    'shap_value': mean_shap,
                    'abs_shap': mean_shap,
                    'direction': 'increases',
                    'effect_desc': f"{r['feature_name']} has precomputed mean |SHAP| impact of {mean_shap:.3f}",
                    'base_value': 0.0,
                    'predicted_value': 0.0
                })
            return drivers
        raise FileNotFoundError(f"Surrogate model not found: {model_path}")
        
    s_dict = joblib.load(model_path)
    model = s_dict['model']
    feature_names = s_dict['feature_names']
    
    # Process wall mass class
    mass = str(design_dict.get('wall_mass_class', 'medium')).lower()
    
    row_dict = {
        'roof_insulation_thickness': float(design_dict['roof_insulation_thickness']),
        'wall_insulation_thickness': float(design_dict['wall_insulation_thickness']),
        'roof_solar_absorptance': float(design_dict['roof_solar_absorptance']),
        'wwr': float(design_dict['wwr']),
        'orientation': float(design_dict['orientation']),
        'shading_depth': float(design_dict['shading_depth']),
        'ventilation_ach': float(design_dict['ventilation_ach']),
        'wall_mass_heavy': 1.0 if mass == 'heavy' or mass == '0' or mass == 0 else 0.0,
        'wall_mass_light': 1.0 if mass == 'light' or mass == '1' or mass == 1 else 0.0,
        'wall_mass_medium': 1.0 if mass == 'medium' or mass == '2' or mass == 2 else 0.0
    }
    
    X_single = pd.DataFrame([row_dict])[feature_names]
    
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_single)[0]
    base_val = float(explainer.expected_value) if hasattr(explainer, 'expected_value') else float(np.mean(shap_vals))
    pred_val = max(0.0, float(model.predict(X_single)[0])) if target == 'O2' else float(model.predict(X_single)[0])
    
    drivers = []
    for f_col, s_val in zip(feature_names, shap_vals):
        val = row_dict[f_col]
        abs_s = abs(s_val)
        
        # Unit formatting
        if 'insulation' in f_col:
            val_str = f"{val*1000:.1f} mm"
        elif 'wwr' in f_col:
            val_str = f"{val*100:.1f}%"
        elif 'orientation' in f_col:
            val_str = f"{val:.0f}°"
        elif 'shading' in f_col:
            val_str = f"{val:.2f} m"
        elif 'ventilation' in f_col:
            val_str = f"{val:.1f} ACH"
        elif 'wall_mass' in f_col:
            val_str = "Active" if val == 1.0 else "Inactive"
        else:
            val_str = f"{val:.2f}"
            
        unit_target = "% Discomfort" if "O1" in target or "ml" in target else "kWh/m²"
        direction = "Increases (Worsens)" if s_val > 0 else "Decreases (Improves)"
        effect_desc = f"{direction} {target} by {abs(s_val):.2f} {unit_target}"
        
        drivers.append({
            'feature': f_col,
            'feature_name': FEATURE_NAME_MAP.get(f_col, f_col),
            'input_value': val_str,
            'shap_value': float(s_val),
            'abs_shap': float(abs_s),
            'direction': direction,
            'effect_desc': effect_desc,
            'base_value': base_val,
            'predicted_value': pred_val
        })
        
    drivers_sorted = sorted(drivers, key=lambda d: d['abs_shap'], reverse=True)
    return drivers_sorted[:top_k]

def run_full_explainability_pipeline():
    df_db2_shap = run_champion_shap_analysis()
    df_surr_shap = run_surrogates_shap_analysis()
    
    # Test top drivers helper on a sample design
    test_design = {
        'roof_insulation_thickness': 0.10,
        'wall_insulation_thickness': 0.05,
        'roof_solar_absorptance': 0.35,
        'wwr': 0.15,
        'orientation': 180.0,
        'shading_depth': 0.50,
        'ventilation_ach': 5.0,
        'wall_mass_class': 'medium'
    }
    top_3 = get_top_drivers('Jodhpur', test_design, target='O1_ml', top_k=3)
    print("\n" + "="*80)
    print("SAMPLE LOCAL SHAP EXPLANATION (Jodhpur, O1_ml):")
    print("="*80)
    for i, d in enumerate(top_3, 1):
        print(f"{i}. {d['feature_name']} = {d['input_value']}: {d['effect_desc']} (SHAP: {d['shap_value']:+.3f})")
        
    # Save evidence file
    evidence_txt = "reports/evidence/phase6_shap_output.txt"
    with open(evidence_txt, "w", encoding="utf-8") as f:
        f.write("PHASE 6 SHAP EXPLAINABILITY EVIDENCE OUTPUT\n")
        f.write("="*80 + "\n\n")
        f.write("ML CHAMPION DB II SHAP IMPORTANCE:\n")
        f.write(df_db2_shap.to_string(index=False) + "\n\n")
        f.write("SURROGATE SHAP TOP DRIVERS SUMMARY (Head):\n")
        f.write(df_surr_shap.head(30).to_string(index=False) + "\n\n")
        f.write("SAMPLE LOCAL DRIVER OUTPUT (Jodhpur):\n")
        for i, d in enumerate(top_3, 1):
            f.write(f"  {i}. {d['feature_name']} = {d['input_value']}: {d['effect_desc']} (SHAP: {d['shap_value']:+.3f})\n")
            
    print(f"\nSaved Phase 6 SHAP evidence to {evidence_txt}")

if __name__ == "__main__":
    run_full_explainability_pipeline()
