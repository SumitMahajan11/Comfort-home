"""
tools/export_web_data.py

Exports all ClimateAdapt-Comfort pipeline outputs (parquets, CSVs, JSONs)
into clean, static, typed JSON artifacts for the Next.js frontend in `web/public/data/`.
Can be re-run whenever new simulation or optimization results are produced.
"""

import os
import json
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data", "processed")
WEB_DATA_DIR = os.path.join(REPO_ROOT, "web", "public", "data")

os.makedirs(WEB_DATA_DIR, exist_ok=True)

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]

CITY_DISPLAY = {
    "Jodhpur": {"name": "Jodhpur", "zone": "Hot-Dry (BWh)", "epw": "IND_RJ_Jodhpur.423390_TMYx.epw", "confidence": "Low", "spearman": 0.109, "coordinates": [26.2389, 73.0243]},
    "Mumbai": {"name": "Mumbai", "zone": "Warm-Humid (Aw)", "epw": "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw", "confidence": "Medium", "spearman": 0.945, "coordinates": [19.0760, 72.8777]},
    "New_Delhi": {"name": "New Delhi", "zone": "Composite (Cwa)", "epw": "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw", "confidence": "Low", "spearman": 0.195, "coordinates": [28.6139, 77.2090]},
    "Bengaluru": {"name": "Bengaluru", "zone": "Temperate (Aw/Cwb)", "epw": "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw", "confidence": "Medium", "spearman": 0.943, "coordinates": [12.9716, 77.5946]},
    "Shimla": {"name": "Shimla", "zone": "Cold (Cwb)", "epw": "IND_HP_Shimla.420830_TMYx.epw", "confidence": "Low", "spearman": 0.868, "coordinates": [31.1048, 77.1734]}
}

def export_all():
    print("=" * 80)
    print("Exporting ClimateAdapt-Comfort Pipeline Data to Web JSON")
    print(f"Source: {DATA_DIR}")
    print(f"Target: {WEB_DATA_DIR}")
    print("=" * 80)

    # 1. Applicability
    app_csv = os.path.join(DATA_DIR, "applicability.csv")
    if os.path.exists(app_csv):
        df_app = pd.read_csv(app_csv)
        records = df_app.to_dict(orient="records")
        for r in records:
            c = r["city"]
            if c in CITY_DISPLAY:
                r["display_name"] = CITY_DISPLAY[c]["name"]
                r["zone"] = CITY_DISPLAY[c]["zone"]
                r["confidence"] = CITY_DISPLAY[c]["confidence"]
                r["spearman"] = CITY_DISPLAY[c]["spearman"]
                r["coordinates"] = CITY_DISPLAY[c]["coordinates"]
        with open(os.path.join(WEB_DATA_DIR, "applicability.json"), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(" [OK] applicability.json")

    # 2. Surrogate Metrics
    surr_csv = os.path.join(DATA_DIR, "surrogate_metrics.csv")
    if os.path.exists(surr_csv):
        df_surr = pd.read_csv(surr_csv)
        records = df_surr.to_dict(orient="records")
        with open(os.path.join(WEB_DATA_DIR, "surrogate_metrics.json"), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(" [OK] surrogate_metrics.json")

    # 3. References
    ref_csv = os.path.join(DATA_DIR, "reference_results.csv")
    if os.path.exists(ref_csv):
        df_ref = pd.read_csv(ref_csv)
        records = df_ref.to_dict(orient="records")
        with open(os.path.join(WEB_DATA_DIR, "reference_results.json"), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(" [OK] reference_results.json")

    # 4. S3 Evaluation
    s3_csv = os.path.join(DATA_DIR, "s3_evaluation_results.csv")
    if os.path.exists(s3_csv):
        df_s3 = pd.read_csv(s3_csv)
        records = df_s3.to_dict(orient="records")
        with open(os.path.join(WEB_DATA_DIR, "s3_evaluation.json"), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        print(" [OK] s3_evaluation.json")

    # 5. Verified Pareto Designs
    ver_csv = os.path.join(DATA_DIR, "pareto_verification_results.csv")
    df_ver = pd.read_csv(ver_csv) if os.path.exists(ver_csv) else pd.DataFrame()

    # 6. Per-City Pareto Sets
    for city in CITIES:
        parquet_file = os.path.join(DATA_DIR, f"pareto_{city}.parquet")
        if os.path.exists(parquet_file):
            df_p = pd.read_parquet(parquet_file)
            # Clip negative surrogate energy predictions physically to 0 (per Decision D-017 / Release v1.1)
            df_p["O2"] = df_p["O2"].clip(lower=0.0)
            
            # Merge verification info
            if not df_ver.empty:
                ver_city = df_ver[df_ver["city"] == city]
                ver_dict = {r["pareto_id"]: r.to_dict() for _, r in ver_city.iterrows()}
            else:
                ver_dict = {}

            records = []
            for _, row in df_p.iterrows():
                r = row.to_dict()
                pid = r.get("pareto_id", "")
                r["is_verified"] = pid in ver_dict
                if r["is_verified"]:
                    v = ver_dict[pid]
                    r["verified_O1_ml"] = v.get("actual_O1_ml")
                    r["verified_O1_adapt"] = v.get("actual_O1_adapt")
                    r["verified_O2"] = v.get("actual_O2")
                    r["rel_error_O1_ml"] = v.get("rel_error_O1_ml")
                    r["rel_error_O1_adapt"] = v.get("rel_error_O1_adapt")
                    r["rel_error_O2"] = v.get("rel_error_O2")
                records.append(r)

            with open(os.path.join(WEB_DATA_DIR, f"pareto_{city}.json"), "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            print(f" [OK] pareto_{city}.json ({len(records)} designs)")

    # 7. SHAP Summary
    shap_summary = {}
    shap_db2_csv = os.path.join(DATA_DIR, "shap_champion_db2.csv")
    if os.path.exists(shap_db2_csv):
        shap_summary["champion_db2"] = pd.read_csv(shap_db2_csv).to_dict(orient="records")
    shap_sim_csv = os.path.join(DATA_DIR, "shap_champion_sim_cities.csv")
    if os.path.exists(shap_sim_csv):
        shap_summary["champion_sim_cities"] = pd.read_csv(shap_sim_csv).to_dict(orient="records")
    shap_surr_csv = os.path.join(DATA_DIR, "shap_surrogates_summary.csv")
    if os.path.exists(shap_surr_csv):
        shap_summary["surrogates"] = pd.read_csv(shap_surr_csv).to_dict(orient="records")

    with open(os.path.join(WEB_DATA_DIR, "shap_summary.json"), "w", encoding="utf-8") as f:
        json.dump(shap_summary, f, indent=2)
    print(" [OK] shap_summary.json")

    # 8. Models Leaderboard & Criteria Metadata
    models_meta = {}
    mod_res_json = os.path.join(DATA_DIR, "model_results.json")
    if os.path.exists(mod_res_json):
        with open(mod_res_json, "r") as f:
            models_meta["ml_models"] = json.load(f)
    base_res_json = os.path.join(DATA_DIR, "baseline_results.json")
    if os.path.exists(base_res_json):
        with open(base_res_json, "r") as f:
            models_meta["baselines"] = json.load(f)

    with open(os.path.join(WEB_DATA_DIR, "models_leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(models_meta, f, indent=2)
    print(" [OK] models_leaderboard.json")

    # 9. Project Metadata, Success Criteria & Assumptions
    meta = {
        "kpis": {
            "survey_records": 109033,
            "clean_complete_case": 58512,
            "total_simulations": 10000,
            "valid_paired_designs": 4988,
            "surrogate_models": 25,
            "pareto_designs": 500,
            "verified_in_energyplus": 50
        },
        "success_criteria": [
            {
                "id": "S1",
                "name": "Comfort Model Generalization vs Baseline",
                "threshold": "Best ML model beats best baseline by >= +0.05 macro-F1 on identical complete-case test rows (58,512 rows) under Leave-One-Köppen-Group-Out CV",
                "status": "FAIL",
                "ml_score": 0.4785,
                "baseline_score": 0.4939,
                "margin": -0.0154,
                "evidence": "E-012",
                "explanation": "Reported honestly as a negative result: the ML champion (Ablation A3 with outdoor temperature) achieved 0.4785 macro-F1, falling short of physical Adaptive 90% (0.4939). Dual comfort judges are therefore retained throughout coupling and optimization to avoid single-model bias."
            },
            {
                "id": "S2",
                "name": "XGBoost Surrogate Model Accuracy",
                "threshold": "Surrogates reach R2 >= 0.95 on held-out 20% test designs across all 25 models",
                "status": "PARTIAL",
                "passing_models": 23,
                "total_models": 25,
                "mean_o2_r2": 0.987,
                "evidence": "E-019",
                "explanation": "23 of 25 surrogate models exceeded R2 >= 0.95. Two targets marginally missed the strict threshold: Mumbai O1_ml (R2 = 0.9406) and Shimla warm_ml (R2 = 0.9225). Annual HVAC energy (O2) achieved high fidelity with mean R2 = 0.987 across all 5 climate zones."
            },
            {
                "id": "S3",
                "name": "Direct EnergyPlus Simulation Verification",
                "threshold": "At least 1 verified Pareto design per city beats BOTH R1 (Lightweight) and R2 (Conventional) reference shelters across all three objectives (O1_ml, O1_adapt, and O2)",
                "status": "PASS",
                "passing_cities": 5,
                "total_cities": 5,
                "verified_beating_both": "36 / 50",
                "evidence": "E-020",
                "explanation": "Verified in all 5 climate zones by 100 direct EnergyPlus physical simulation runs. Pareto designs beat both reference shelters simultaneously in Jodhpur (7/10), Mumbai (7/10), New Delhi (6/10), Bengaluru (8/10), and Shimla (8/10)."
            },
            {
                "id": "S4",
                "name": "Decision-Support Application Usability",
                "threshold": "Dashboard runs locally with one command, operates strictly read-only on saved artifacts, with zero external network or paid API dependencies, displaying applicability flags",
                "status": "PASS",
                "evidence": "E-021",
                "explanation": "Full application operates completely client-side and offline on precomputed simulation and surrogate artifacts. All test cases passed with zero exceptions."
            }
        ],
        "assumptions": [
            {"id": "A-001", "name": "Continuous Occupancy", "value": "24 hours/day occupancy reflecting emergency/passive shelter use."},
            {"id": "A-002", "name": "Metabolic Rate", "value": "Constant 1.1 met (light seated resting activity)."},
            {"id": "A-003", "name": "Indoor Air Velocity", "value": "Constant 0.15 m/s still indoor baseline air speed."},
            {"id": "A-004", "name": "Dynamic Clothing Model", "value": "0.5 clo if Daily Mean Ta >= 25°C; 0.7 clo if 15°C <= Ta < 25°C; 1.0 clo if Ta < 15°C."},
            {"id": "A-005", "name": "Ideal-Loads HVAC Setpoints", "value": "Cooling setpoint 26°C, heating setpoint 20°C for objective O2."},
            {"id": "A-006", "name": "Reference R1 Lightweight", "value": "No insulation (roof=0, wall=0), light mass, solar absorptance 0.85, WWR 0.15, shading 0.0 m, 5 ACH."},
            {"id": "A-007", "name": "Reference R2 Conventional", "value": "No insulation (roof=0, wall=0), medium clay brick mass, solar absorptance 0.60, WWR 0.15, shading 0.0 m, 5 ACH."}
        ],
        "decisions": [
            {"id": "D-001", "title": "Single-zone shelter baseline", "description": "Single-zone, low-rise shelter simulated in EnergyPlus across 5 Indian climate zones."},
            {"id": "D-002", "title": "Representative Climate Stations", "description": "Jodhpur (hot-dry), Mumbai (warm-humid), New Delhi (composite), Bengaluru (temperate), Shimla (cold)."},
            {"id": "D-004a", "title": "NaN-tolerant training, complete-case evaluation", "description": "Model learns from 18,061 Indian rows while preserving 100% identical-row complete-case evaluation."},
            {"id": "D-005", "title": "Never impute tr = ta", "description": "Radiant temperature is the primary physics altered by envelope design; imputing removes optimization leverage."},
            {"id": "D-011", "title": "Shimla applicability warning", "description": "Shimla has no labelled votes in DB II; cold winter hours carry explicit extrapolation flag."},
            {"id": "D-013", "title": "Dual comfort judges", "description": "Retain both ML Champion and Physical Adaptive 90% as dual judges to prevent single-model bias."},
            {"id": "D-017", "title": "Decision-support confidence tiers", "description": "Medium confidence requires Spearman rs >= 0.8 AND Adaptive 90% validity >= 80%; otherwise Low confidence."}
        ],
        "design_variables": [
            {"id": "roof_insulation_thickness", "name": "Roof Insulation", "unit": "mm", "min": 0, "max": 150, "step": 5, "default": 50, "description": "Expanded polystyrene roof insulation thickness."},
            {"id": "wall_insulation_thickness", "name": "Wall Insulation", "unit": "mm", "min": 0, "max": 150, "step": 5, "default": 40, "description": "Mineral wool wall insulation thickness."},
            {"id": "wall_mass_class", "name": "Wall Mass Class", "unit": "", "type": "categorical", "options": ["light", "medium", "heavy"], "default": "medium", "description": "Thermal mass: Light (timber/sheet), Medium (clay brick), Heavy (concrete block)."},
            {"id": "roof_solar_absorptance", "name": "Roof Solar Absorptance", "unit": "", "min": 0.3, "max": 0.9, "step": 0.05, "default": 0.5, "description": "Fraction of solar radiation absorbed by the roof (lower = cool white roof)."},
            {"id": "wwr", "name": "Window-to-Wall Ratio", "unit": "%", "min": 5, "max": 40, "step": 1, "default": 15, "description": "Glazing area as percentage of external wall area."},
            {"id": "orientation", "name": "Orientation", "unit": "deg", "min": 0, "max": 359, "step": 5, "default": 0, "description": "Azimuth angle (0° = North, 90° = East, 180° = South, 270° = West)."},
            {"id": "shading_depth", "name": "Overhang Shading Depth", "unit": "m", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.4, "description": "Horizontal overhang projection over windows."},
            {"id": "ventilation_ach", "name": "Natural Ventilation", "unit": "ACH", "min": 1.0, "max": 15.0, "step": 0.5, "default": 5.0, "description": "Air changes per hour provided by passive cross-ventilation."}
        ]
    }

    with open(os.path.join(WEB_DATA_DIR, "project_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(" [OK] project_meta.json")

    print("\n[SUCCESS] All data exported successfully to web/public/data/")

if __name__ == "__main__":
    export_all()
