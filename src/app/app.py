"""
ClimateAdapt-Comfort: Decision-Support Dashboard
Streamlit Web Application for Passive Shelter Design Optimization and Thermal Comfort Evaluation.

Author: Antigravity AI & Research Team
Project: ClimateAdapt-Comfort
Repo Root: D:/Projects/Comfort home
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Add repo root to sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.models.explain import get_top_drivers, FEATURE_NAME_MAP

# ---------------------------------------------------------
# Application Configuration & Constants
# ---------------------------------------------------------
st.set_page_config(
    page_title="ClimateAdapt-Comfort | Shelter Decision-Support",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

CITIES_METADATA = {
    "Jodhpur": {
        "zone": "Hot-Dry",
        "koppen": "BWh (Arid Desert)",
        "epw": "IND_RJ_Jodhpur.423390_TMYx.epw",
        "flag": "LOW_CONFIDENCE (DB II training envelope bounds; high daytime extreme drybulb temperatures)",
        "adaptive_validity": "86.85% valid hours"
    },
    "Mumbai": {
        "zone": "Warm-Humid",
        "koppen": "Aw (Tropical Savanna)",
        "epw": "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
        "flag": "LOW_CONFIDENCE (High monsoon relative humidity envelope bounds)",
        "adaptive_validity": "100.0% valid hours"
    },
    "New_Delhi": {
        "zone": "Composite",
        "koppen": "Cwa (Monsoon Subtropical)",
        "epw": "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
        "flag": "LOW_CONFIDENCE (High monsoon humidity & extreme seasonal diurnal swings)",
        "adaptive_validity": "89.86% valid hours"
    },
    "Bengaluru": {
        "zone": "Temperate",
        "koppen": "Aw / Cwa (Tropical Moderate Upland)",
        "epw": "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
        "flag": "LOW_CONFIDENCE (DB II envelope boundaries)",
        "adaptive_validity": "100.0% valid hours"
    },
    "Shimla": {
        "zone": "Cold",
        "koppen": "Cwb (Subtropical Highland / Alpine)",
        "epw": "IND_HP_Shimla.420830_TMYx.epw",
        "flag": "LOW_CONFIDENCE (D-011: Zero labelled sensation votes in DB II; 26.03% winter running mean < 10°C outside standard Adaptive 90% boundary)",
        "adaptive_validity": "73.97% valid hours (Severe winter extrapolation)"
    }
}

# ---------------------------------------------------------
# Cached Data Loading (Strictly Read-Only on Saved Artifacts)
# ---------------------------------------------------------
@st.cache_data
def load_reference_results():
    path = os.path.join(REPO_ROOT, "data/processed/reference_results.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_applicability_data():
    path = os.path.join(REPO_ROOT, "data/processed/applicability.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_pareto_front(city_name):
    path = os.path.join(REPO_ROOT, f"data/processed/pareto_{city_name}.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()

@st.cache_data
def load_verified_results():
    path = os.path.join(REPO_ROOT, "data/processed/pareto_verification_results.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_s3_results():
    path = os.path.join(REPO_ROOT, "data/processed/s3_evaluation_results.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_data
def load_surrogate_metrics():
    path = os.path.join(REPO_ROOT, "data/processed/surrogate_metrics.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

@st.cache_resource
def load_surrogate_model(city_name, target):
    path = os.path.join(REPO_ROOT, f"models/surrogate_{city_name}_{target}.joblib")
    if os.path.exists(path):
        return joblib.load(path)
    return None

# ---------------------------------------------------------
# UI Layout & Navigation
# ---------------------------------------------------------
st.sidebar.title("ClimateAdapt-Comfort")
st.sidebar.caption("Passive Shelter Decision-Support System")

nav_choice = st.sidebar.radio(
    "Navigation",
    ["1. Overview", "2. Evaluate a Design", "3. Recommend", "4. Explain", "5. About"],
    index=0
)

city_selected = st.sidebar.selectbox(
    "Select Climate Zone / City",
    list(CITIES_METADATA.keys()),
    index=0
)

city_meta = CITIES_METADATA[city_selected]
st.sidebar.markdown(f"**Zone:** {city_meta['zone']}")
st.sidebar.markdown(f"**Climate Class:** {city_meta['koppen']}")
st.sidebar.caption(f"Weather: `{city_meta['epw']}`")

# ---------------------------------------------------------
# PAGE 1: OVERVIEW
# ---------------------------------------------------------
if nav_choice == "1. Overview":
    st.title("ClimateAdapt-Comfort: Shelter Decision Support System")
    st.markdown("### Decision-Support System for Passive Shelter Design Across Indian Climate Zones")
    
    # Applicability Warning Banner (D-015 / D-011)
    if "Shimla" in city_selected:
        st.error(
            f"⚠️ **Applicability Domain Warning (Cold Zone - Shimla | D-011):**\n"
            f"- **ML Comfort Model:** DB II has 0 labelled sensation votes for Shimla (460 rows, all TSV missing). Predictions represent model extrapolation.\n"
            f"- **Adaptive 90% Model:** {city_meta['adaptive_validity']} ({city_meta['flag']}). Thermal comfort predictions in winter operate outside the calibrated comfort envelope."
        )
    else:
        st.warning(
            f"ℹ️ **Applicability Domain Notice ({city_selected} | D-015):**\n"
            f"- **Status:** `{city_meta['flag']}`\n"
            f"- **Adaptive 90% Validity:** {city_meta['adaptive_validity']}"
        )

    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Selected Station", city_selected)
    with col2:
        st.metric("Climate Classification", city_meta["zone"])
    with col3:
        st.metric("Adaptive 90% Validity Share", city_meta["adaptive_validity"].split()[0])
        
    st.subheader("1. Reference Shelter Baseline Performance")
    st.markdown(
        "EnergyPlus baseline simulations for **R1 (Lightweight Shelter)** and **R2 (Conventional Clay Brick Shelter)**. "
        "Every optimized design is benchmarked against beating both baselines simultaneously."
    )
    
    df_refs = load_reference_results()
    if not df_refs.empty:
        city_refs = df_refs[df_refs['city'] == city_selected].copy()
        display_cols = ['reference_name', 'wall_mass_class', 'roof_solar_absorptance', 'mean_ta', 'O1_ml', 'warm_ml', 'cool_ml', 'O1_adapt', 'O2']
        rename_dict = {
            'reference_name': 'Shelter Benchmark',
            'wall_mass_class': 'Wall Mass',
            'roof_solar_absorptance': 'Roof Absorptance',
            'mean_ta': 'Mean Indoor Ta (°C)',
            'O1_ml': 'O1 ML Discomfort (%)',
            'warm_ml': 'Warm ML (%)',
            'cool_ml': 'Cool ML (%)',
            'O1_adapt': 'O1 Adaptive 90% (%)',
            'O2': 'O2 Energy (kWh/m²/yr)'
        }
        st.dataframe(city_refs[display_cols].rename(columns=rename_dict).set_index('Shelter Benchmark'), use_container_width=True)
    else:
        st.warning("Reference shelter results not found at `data/processed/reference_results.csv`.")
        
    st.subheader("2. Applicability Domain & Confidence Tiers (D-015, D-017)")
    st.info(
        "⚠️ **ML Comfort Envelope Coverage Notice:** Across all five simulated Indian climate zones, the ML Champion comfort model operates below the 80% training envelope threshold (27.91% to 77.26% of hours inside the DB II 1st–99th percentile feature envelope), driven primarily by extreme monsoon relative humidity and dry desert conditions."
    )
    
    conf_table = pd.DataFrame([
        {"City": "Mumbai", "Climate Zone": "Warm-Humid", "DB II Envelope Inside (%)": "27.91%", "Adaptive 90% Valid (%)": "100.00%", "Dual-Judge Spearman (rs)": "0.945", "Confidence Tier (D-017)": "Medium"},
        {"City": "Bengaluru", "Climate Zone": "Temperate", "DB II Envelope Inside (%)": "43.39%", "Adaptive 90% Valid (%)": "100.00%", "Dual-Judge Spearman (rs)": "0.943", "Confidence Tier (D-017)": "Medium"},
        {"City": "Shimla", "Climate Zone": "Cold", "DB II Envelope Inside (%)": "77.26%", "Adaptive 90% Valid (%)": "73.97%", "Dual-Judge Spearman (rs)": "0.868", "Confidence Tier (D-017)": "Low (Winter < 10°C)"},
        {"City": "New_Delhi", "Climate Zone": "Composite", "DB II Envelope Inside (%)": "53.12%", "Adaptive 90% Valid (%)": "89.86%", "Dual-Judge Spearman (rs)": "0.195", "Confidence Tier (D-017)": "Low (Judge Disagreement)"},
        {"City": "Jodhpur", "Climate Zone": "Hot-Dry", "DB II Envelope Inside (%)": "53.91%", "Adaptive 90% Valid (%)": "86.85%", "Dual-Judge Spearman (rs)": "0.109", "Confidence Tier (D-017)": "Low (Judge Disagreement)"}
    ])
    st.dataframe(conf_table.set_index("City"), use_container_width=True)
    
    st.markdown("**Detailed Feature Envelope Breakdown:**")
    df_app = load_applicability_data()
    if not df_app.empty:
        st.dataframe(df_app, use_container_width=True)
        
    st.subheader("3. Optimization Objectives & Formulation")
    st.markdown("""
    - **O1_ml (Minimize):** Annual occupied hours (%) predicted non-neutral by the calibrated ML Champion model (`Ablation_A3_OutdoorTemp` with running-mean outdoor temperature t_mot_isd).
    - **O1_adapt (Minimize):** Annual occupied hours (%) outside the physical Adaptive 90% comfort envelope (T_cmf = 17.8 + 0.31 * T_rm ± 2.5°C).
    - **O2 (Minimize):** Annual ideal-loads HVAC energy intensity (kWh/m²/yr) with cooling setpoint 26°C and heating setpoint 20°C.
    """)

# ---------------------------------------------------------
# PAGE 2: EVALUATE A DESIGN
# ---------------------------------------------------------
elif nav_choice == "2. Evaluate a Design":
    st.title("Evaluate a Custom Shelter Design")
    st.markdown(f"Adjust design variables below to evaluate instant surrogate predictions for **{city_selected}** ({city_meta['zone']}).")
    
    st.subheader("Design Variables (Envelope & Passive Parameters)")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        roof_ins_mm = st.slider("Roof Insulation Thickness (mm)", min_value=0.0, max_value=150.0, value=100.0, step=5.0)
        wall_ins_mm = st.slider("Wall Insulation Thickness (mm)", min_value=0.0, max_value=150.0, value=50.0, step=5.0)
    with c2:
        roof_abs = st.slider("Roof Solar Absorptance", min_value=0.30, max_value=0.90, value=0.60, step=0.01)
        wwr_pct = st.slider("Window-to-Wall Ratio (WWR %)", min_value=5.0, max_value=40.0, value=15.0, step=1.0)
    with c3:
        orientation_deg = st.slider("Orientation (° from North)", min_value=0.0, max_value=359.0, value=180.0, step=1.0)
        shading_m = st.slider("Shading Overhang Depth (m)", min_value=0.0, max_value=1.0, value=0.50, step=0.05)
    with c4:
        vent_ach = st.slider("Natural Ventilation (ACH)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
        wall_mass = st.selectbox("Wall Construction Class", ["light", "medium", "heavy"], index=1)
        
    design_input = {
        'roof_insulation_thickness': roof_ins_mm / 1000.0,
        'wall_insulation_thickness': wall_ins_mm / 1000.0,
        'roof_solar_absorptance': roof_abs,
        'wwr': wwr_pct / 100.0,
        'orientation': orientation_deg,
        'shading_depth': shading_m,
        'ventilation_ach': vent_ach,
        'wall_mass_heavy': 1.0 if wall_mass == 'heavy' else 0.0,
        'wall_mass_light': 1.0 if wall_mass == 'light' else 0.0,
        'wall_mass_medium': 1.0 if wall_mass == 'medium' else 0.0
    }
    
    df_feat = pd.DataFrame([design_input])
    feature_cols = ['roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach', 'wall_mass_heavy', 'wall_mass_light', 'wall_mass_medium']
    X_input = df_feat[feature_cols]
    
    # Predict using surrogates
    m_o1_ml = load_surrogate_model(city_selected, "O1_ml")
    m_warm_ml = load_surrogate_model(city_selected, "warm_ml")
    m_cool_ml = load_surrogate_model(city_selected, "cool_ml")
    m_o1_adapt = load_surrogate_model(city_selected, "O1_adapt")
    m_o2 = load_surrogate_model(city_selected, "O2")
    
    if all([m_o1_ml, m_warm_ml, m_cool_ml, m_o1_adapt, m_o2]):
        pred_o1_ml = float(m_o1_ml['model'].predict(X_input)[0])
        pred_warm_ml = float(m_warm_ml['model'].predict(X_input)[0])
        pred_cool_ml = float(m_cool_ml['model'].predict(X_input)[0])
        pred_o1_adapt = float(m_o1_adapt['model'].predict(X_input)[0])
        pred_o2 = max(0.0, float(m_o2['model'].predict(X_input)[0]))
        
        st.subheader("Predicted Objective Performance")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("O1 ML Discomfort Hours", f"{pred_o1_ml:.2f}%", help="Predicted non-neutral comfort probability")
            st.caption(f"Breakdown: {pred_warm_ml:.1f}% Warm | {pred_cool_ml:.1f}% Cool")
        with col_m2:
            st.metric("O1 Adaptive 90% Discomfort", f"{pred_o1_adapt:.2f}%", help="Predicted hours outside Adaptive 90% envelope")
        with col_m3:
            st.metric("O2 Annual HVAC Energy", f"{pred_o2:.2f} kWh/m²", help="Annual ideal-loads heating & cooling energy intensity")
            
        # Comparison with R1 and R2 baselines
        df_refs = load_reference_results()
        if not df_refs.empty:
            c_refs = df_refs[df_refs['city'] == city_selected]
            r1_row = c_refs[c_refs['reference_name'].str.contains("R1")].iloc[0]
            r2_row = c_refs[c_refs['reference_name'].str.contains("R2")].iloc[0]
            
            st.markdown("#### Side-by-Side Comparison with Reference Baselines")
            comp_table = pd.DataFrame([
                {
                    "Design": "Current Evaluated Design",
                    "O1 ML Discomfort (%)": f"{pred_o1_ml:.2f}%",
                    "O1 Adapt 90% (%)": f"{pred_o1_adapt:.2f}%",
                    "O2 Energy (kWh/m²/yr)": f"{pred_o2:.2f}",
                    "Status vs R1": "Beats R1" if (pred_o1_ml < r1_row['O1_ml'] and pred_o1_adapt < r1_row['O1_adapt'] and pred_o2 < r1_row['O2']) else "Worse than R1 on some metrics",
                    "Status vs R2": "Beats R2" if (pred_o1_ml < r2_row['O1_ml'] and pred_o1_adapt < r2_row['O1_adapt'] and pred_o2 < r2_row['O2']) else "Worse than R2 on some metrics"
                },
                {
                    "Design": "R1 Lightweight Reference (A-006)",
                    "O1 ML Discomfort (%)": f"{r1_row['O1_ml']:.2f}%",
                    "O1 Adapt 90% (%)": f"{r1_row['O1_adapt']:.2f}%",
                    "O2 Energy (kWh/m²/yr)": f"{r1_row['O2']:.2f}",
                    "Status vs R1": "Baseline",
                    "Status vs R2": "-"
                },
                {
                    "Design": "R2 Conventional Reference (A-007)",
                    "O1 ML Discomfort (%)": f"{r2_row['O1_ml']:.2f}%",
                    "O1 Adapt 90% (%)": f"{r2_row['O1_adapt']:.2f}%",
                    "O2 Energy (kWh/m²/yr)": f"{r2_row['O2']:.2f}",
                    "Status vs R1": "-",
                    "Status vs R2": "Baseline"
                }
            ])
            st.dataframe(comp_table.set_index("Design"), use_container_width=True)
    else:
        st.error(f"Surrogate models for {city_selected} could not be loaded from `models/`.")

# ---------------------------------------------------------
# PAGE 3: RECOMMEND (PARETO EXPLORER)
# ---------------------------------------------------------
elif nav_choice == "3. Recommend":
    st.title("Recommend: Multi-Objective Pareto Explorer")
    st.markdown(
        f"Explore the 100 non-dominated Pareto designs derived for **{city_selected}** ({city_meta['zone']}). "
        "Adjust priority weights below to identify the optimal shelter configuration matching your stakeholder goals."
    )
    
    df_pareto = load_pareto_front(city_selected)
    df_ver = load_verified_results()
    
    if not df_pareto.empty:
        st.subheader("1. Stakeholder Preference Weights")
        pw1, pw2, pw3 = st.columns(3)
        with pw1:
            w_ml = st.slider("Weight: O1 ML Comfort", min_value=0.0, max_value=1.0, value=0.40, step=0.05)
        with pw2:
            w_adapt = st.slider("Weight: O1 Adaptive 90% Comfort", min_value=0.0, max_value=1.0, value=0.30, step=0.05)
        with pw3:
            w_o2 = st.slider("Weight: O2 HVAC Energy Efficiency", min_value=0.0, max_value=1.0, value=0.30, step=0.05)
            
        w_sum = w_ml + w_adapt + w_o2
        if w_sum == 0:
            w_norm_ml, w_norm_adapt, w_norm_o2 = 0.333, 0.333, 0.334
        else:
            w_norm_ml, w_norm_adapt, w_norm_o2 = w_ml / w_sum, w_adapt / w_sum, w_o2 / w_sum
            
        # Compute normalized weighted score
        min_ml, max_ml = df_pareto['pred_O1_ml'].min(), df_pareto['pred_O1_ml'].max()
        min_ad, max_ad = df_pareto['pred_O1_adapt'].min(), df_pareto['pred_O1_adapt'].max()
        min_e, max_e = df_pareto['pred_O2'].min(), df_pareto['pred_O2'].max()
        
        denom_ml = (max_ml - min_ml) if max_ml > min_ml else 1.0
        denom_ad = (max_ad - min_ad) if max_ad > min_ad else 1.0
        denom_e = (max_e - min_e) if max_e > min_e else 1.0
        
        df_pareto['norm_O1_ml'] = (df_pareto['pred_O1_ml'] - min_ml) / denom_ml
        df_pareto['norm_O1_adapt'] = (df_pareto['pred_O1_adapt'] - min_ad) / denom_ad
        df_pareto['norm_O2'] = (df_pareto['pred_O2'] - min_e) / denom_e
        
        df_pareto['weighted_score'] = (
            w_norm_ml * df_pareto['norm_O1_ml'] +
            w_norm_adapt * df_pareto['norm_O1_adapt'] +
            w_norm_o2 * df_pareto['norm_O2']
        )
        
        best_rec = df_pareto.sort_values(by='weighted_score').iloc[0]
        
        st.success(
            f"🎯 **Recommended Design for Current Weights:** `{best_rec['pareto_id']}`\n"
            f"- **Predicted O1_ml:** {best_rec['pred_O1_ml']:.2f}% | "
            f"**Predicted O1_adapt:** {best_rec['pred_O1_adapt']:.2f}% | "
            f"**Predicted O2:** {best_rec['pred_O2']:.2f} kWh/m²\n"
            f"- **Envelope Specification:** Roof Ins={best_rec['roof_insulation_thickness']*1000:.1f} mm, "
            f"Wall Ins={best_rec['wall_insulation_thickness']*1000:.1f} mm, "
            f"Wall Mass={best_rec['wall_mass_class']}, "
            f"Roof Abs={best_rec['roof_solar_absorptance']:.2f}, "
            f"WWR={best_rec['wwr']*100:.1f}%, "
            f"Orientation={best_rec['orientation']:.0f}°, "
            f"Shading={best_rec['shading_depth']:.2f} m, "
            f"Vent={best_rec['ventilation_ach']:.1f} ACH."
        )
        
        st.subheader("2. Interactive Pareto Frontier Visualization")
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=120)
        
        # Plot 1: O1_ml vs O2
        ax1 = axes[0]
        ax1.scatter(df_pareto['pred_O1_ml'], df_pareto['pred_O2'], c=df_pareto['weighted_score'], cmap='viridis_r', s=45, label='Pareto Front (Predicted)')
        ax1.scatter(best_rec['pred_O1_ml'], best_rec['pred_O2'], c='gold', marker='*', s=250, edgecolors='black', label=f'Best Match ({best_rec["pareto_id"]})')
        
        # Overlay verified points if available
        if not df_ver.empty:
            c_ver = df_ver[df_ver['city'] == city_selected]
            ax1.scatter(c_ver['actual_O1_ml'], c_ver['actual_O2'], c='red', marker='x', s=70, label='Direct EnergyPlus Verified')
            
        ax1.set_xlabel('O1 (ML Champion Discomfort %)')
        ax1.set_ylabel('O2 (Annual Energy kWh/m²)')
        ax1.set_title(f'{city_selected} - ML Comfort vs Energy')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend()
        
        # Plot 2: O1_adapt vs O2
        ax2 = axes[1]
        ax2.scatter(df_pareto['pred_O1_adapt'], df_pareto['pred_O2'], c=df_pareto['weighted_score'], cmap='viridis_r', s=45, label='Pareto Front (Predicted)')
        ax2.scatter(best_rec['pred_O1_adapt'], best_rec['pred_O2'], c='gold', marker='*', s=250, edgecolors='black', label=f'Best Match ({best_rec["pareto_id"]})')
        
        if not df_ver.empty:
            c_ver = df_ver[df_ver['city'] == city_selected]
            ax2.scatter(c_ver['actual_O1_adapt'], c_ver['actual_O2'], c='red', marker='x', s=70, label='Direct EnergyPlus Verified')
            
        ax2.set_xlabel('O1 (Adaptive 90% Discomfort %)')
        ax2.set_ylabel('O2 (Annual Energy kWh/m²)')
        ax2.set_title(f'{city_selected} - Adaptive 90% Comfort vs Energy')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend()
        
        st.pyplot(fig)
        plt.close()
        
        st.subheader("3. Direct EnergyPlus Verification Table (10 Verified Designs)")
        if not df_ver.empty:
            c_ver = df_ver[df_ver['city'] == city_selected].copy()
            v_cols = ['pareto_id', 'selection_role', 'pred_O1_ml', 'actual_O1_ml', 'abs_err_O1_ml', 'pred_O1_adapt', 'actual_O1_adapt', 'abs_err_O1_adapt', 'pred_O2', 'actual_O2', 'abs_err_O2']
            rename_v = {
                'pareto_id': 'Pareto ID',
                'selection_role': 'Selection Role',
                'pred_O1_ml': 'Pred O1 ML (%)',
                'actual_O1_ml': 'Actual E+ O1 ML (%)',
                'abs_err_O1_ml': 'Err ML',
                'pred_O1_adapt': 'Pred O1 Adapt (%)',
                'actual_O1_adapt': 'Actual E+ O1 Adapt (%)',
                'abs_err_O1_adapt': 'Err Adapt',
                'pred_O2': 'Pred O2',
                'actual_O2': 'Actual E+ O2 (kWh/m²)',
                'abs_err_O2': 'Err O2'
            }
            st.dataframe(c_ver[v_cols].rename(columns=rename_v).set_index('Pareto ID'), use_container_width=True)
            
    else:
        st.error(f"Pareto parquet file not found for {city_selected} at `data/processed/pareto_{city_selected}.parquet`.")

# ---------------------------------------------------------
# PAGE 4: EXPLAIN (SHAP ATTRIBUTION)
# ---------------------------------------------------------
elif nav_choice == "4. Explain":
    st.title("Explain: SHAP Attribution & Model Drivers")
    st.markdown(
        f"Explain model predictions for **{city_selected}** ({city_meta['zone']}) using exact TreeExplainer Shapley values. "
        "Understand why specific passive envelope features improve or degrade comfort and energy."
    )
    
    st.subheader("1. Local Design Explainability (Top 3 Feature Drivers)")
    
    t_choice = st.selectbox("Select Target Objective to Explain", ["O1_ml", "O1_adapt", "O2"], index=0)
    
    # Sliders for test design
    c1, c2, c3 = st.columns(3)
    with c1:
        r_ins = st.slider("Roof Insulation (mm)", 0.0, 150.0, 100.0, 5.0, key="exp_r_ins")
        w_ins = st.slider("Wall Insulation (mm)", 0.0, 150.0, 50.0, 5.0, key="exp_w_ins")
        r_abs = st.slider("Roof Solar Absorptance", 0.30, 0.90, 0.45, 0.01, key="exp_r_abs")
    with c2:
        wwr_val = st.slider("Window-to-Wall Ratio (%)", 5.0, 40.0, 15.0, 1.0, key="exp_wwr")
        orient_val = st.slider("Orientation (°)", 0.0, 359.0, 180.0, 1.0, key="exp_orient")
        shad_val = st.slider("Shading Depth (m)", 0.0, 1.0, 0.50, 0.05, key="exp_shad")
    with c3:
        v_ach = st.slider("Ventilation (ACH)", 1.0, 15.0, 3.0, 0.5, key="exp_vent")
        w_mass = st.selectbox("Wall Mass", ["light", "medium", "heavy"], index=1, key="exp_mass")
        
    custom_design = {
        'roof_insulation_thickness': r_ins / 1000.0,
        'wall_insulation_thickness': w_ins / 1000.0,
        'roof_solar_absorptance': r_abs,
        'wwr': wwr_val / 100.0,
        'orientation': orient_val,
        'shading_depth': shad_val,
        'ventilation_ach': v_ach,
        'wall_mass_class': w_mass
    }
    
    try:
        top_drivers = get_top_drivers(city_selected, custom_design, target=t_choice, top_k=3)
        st.markdown(f"#### Top 3 Impact Drivers for `{t_choice}` in **{city_selected}**:")
        
        for i, d in enumerate(top_drivers, 1):
            is_pos = d['shap_value'] > 0
            box_type = st.warning if is_pos else st.success
            sign_str = f"+{d['shap_value']:.2f}" if is_pos else f"{d['shap_value']:.2f}"
            unit = "%" if "O1" in t_choice else "kWh/m²"
            
            st.markdown(
                f"**{i}. {d['feature_name']} = `{d['input_value']}`**  \n"
                f"- **Attribution Effect:** `{sign_str} {unit}` ({d['direction']})  \n"
                f"- **Base Rate (Dataset Average):** `{d['base_value']:.2f} {unit}` ➔ **Model Predicted Value:** `{d['predicted_value']:.2f} {unit}`"
            )
    except Exception as e:
        st.error(f"Error computing local SHAP drivers: {e}")
        
    st.subheader("2. Global Feature Importance Plots")
    
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"**Surrogate Feature Importance ({city_selected} - {t_choice})**")
        fig_surr = os.path.join(REPO_ROOT, f"reports/figures/shap_surrogate_{city_selected}_{t_choice}.png")
        if os.path.exists(fig_surr):
            st.image(fig_surr, use_column_width=True)
        else:
            st.info("Surrogate importance plot not found.")
            
    with g2:
        st.markdown("**ML Champion Global Feature Attributions (ASHRAE DB II)**")
        fig_champ = os.path.join(REPO_ROOT, "reports/figures/shap_champion_db2.png")
        if os.path.exists(fig_champ):
            st.image(fig_champ, use_column_width=True)
        else:
            st.info("Champion DB II SHAP plot not found.")

# ---------------------------------------------------------
# PAGE 5: ABOUT
# ---------------------------------------------------------
elif nav_choice == "5. About":
    st.title("About ClimateAdapt-Comfort & Research Audit")
    
    st.subheader("1. Success Criteria Ledger (S1 to S4)")
    
    s_table = pd.DataFrame([
        {
            "Criterion": "S1: ML Champion vs Adaptive Baseline",
            "Target Threshold": "Macro-F1 lead >= +0.05 on identical rows",
            "Result": "FAIL (Negative Result)",
            "Literal Value / Margin": "ML Champion 0.4785 vs Adaptive 90% 0.4939 (Margin: -0.0154)",
            "Status": "❌ Reported honestly as negative result"
        },
        {
            "Criterion": "S2: Surrogate Model Accuracy",
            "Target Threshold": "R² >= 0.95 on held-out test designs",
            "Result": "PARTIAL",
            "Literal Value / Margin": "23/25 models passed R² >= 0.95 (Failures: Mumbai O1_ml R²=0.9406, Shimla warm_ml R²=0.9225); Mean R² on O2 = 0.987",
            "Status": "⚠️ PARTIAL (23/25 verified)"
        },
        {
            "Criterion": "S3: Direct EnergyPlus Optimization Verification",
            "Target Threshold": "Verified Pareto design beats BOTH R1 & R2 on all 3 objectives",
            "Result": "PASS",
            "Literal Value / Margin": "Passed in all 5 climate zones (Jodhpur 7/10, Mumbai 7/10, New Delhi 6/10, Bengaluru 8/10, Shimla 8/10; 36/50 verified designs). Note: Optimizer used unclipped O2 surrogates (59/500 negative); S3 is unaffected because it rests on direct simulations.",
            "Status": "✅ Verified"
        },
        {
            "Criterion": "S4: Standalone Local Decision-Support Dashboard",
            "Target Threshold": "Runs locally with 1 command, read-only on saved artifacts, zero external APIs",
            "Result": "PASS",
            "Literal Value / Margin": "Streamlit app starts offline with automated AppTest verification across all 5 pages",
            "Status": "✅ Verified"
        }
    ])
    st.dataframe(s_table.set_index("Criterion"), use_container_width=True)
    
    st.subheader("2. Dual Comfort Judges Side-by-Side Comparison")
    st.markdown(r"""
    | Comfort Judge | Mathematical Formulation | Primary Strengths | Limitations & Implementation Notes |
    |---|---|---|---|
    | **ML Champion (`Ablation_A3_OutdoorTemp`)** | Discrete argmax class $\hat{y}_t = \arg\max P(\text{class} \mid \mathbf{x}_t) \in \{0=\text{cool}, 1=\text{neutral}, 2=\text{warm}\}$ (`model.predict()`), evaluating $O_{1,\text{ml}} = \frac{100}{N}\sum \mathbf{1}(\hat{y}_t \ne 1)$ | Captures complex non-linear multi-variable interactions (e.g. radiant vs air temperature deltas, humidity coupling) | Trained on DB II; extrapolates in extreme monsoons/deserts. **Deviation Note:** Uses discrete argmax prediction rather than continuous probability summation $\sum(1-P(\text{neutral}))$. |
    | **Physical Adaptive 90%** | $T_{cmf} = 17.8 + 0.31 T_{rm} \pm 2.5^\circ\text{C}$ on valid hours $10.0^\circ\text{C} \le T_{rm} \le 33.5^\circ\text{C}$ (ASHRAE Standard 55) | Grounded in empirical field adaptation physics; highly interpretable | Strictly defined only for running mean $10.0^\circ\text{C} \le T_{rm} \le 33.5^\circ\text{C}$; invalid during cold mountain winters (Shimla) |
    """)
    
    st.subheader("3. Known Project Limitations (PROJECT_SPEC §10)")
    st.markdown("""
    1. **DB II Training Representation:** ASHRAE DB II consists predominantly of offices, university classrooms, and standard housing, not temporary or emergency shelter typologies.
    2. **Simulated vs Measured Reality:** All envelope performance, temperature dynamics, and energy figures are derived from EnergyPlus 26.2.0 numerical simulations without physical sensor measurements.
    3. **Cold-Zone Extrapolation (Shimla):** The cold-climate sensation predictions from the ML model and Adaptive 90% comfort envelope operate outside standard validation bounds during severe winter conditions.
    4. **Hot-Dry Semi-Arid Representation:** Hot-dry coverage in DB II originates mostly from semi-arid Indian field studies; true arid desert classes have few buildings.
    5. **Behavioral Design Assumptions:** Clothing insulation schedule (A-004), metabolic rate ($\text{met}=1.1$, A-002), and indoor air velocity ($\text{vel}=0.15\text{ m/s}$, A-003) are assumed design constants rather than dynamic occupant behaviors.
    """)

# ---------------------------------------------------------
# Application Footer
# ---------------------------------------------------------
st.markdown("---")
st.caption("ClimateAdapt-Comfort Decision Support System | Generated for Research & Engineering Audit | Phase 6")
