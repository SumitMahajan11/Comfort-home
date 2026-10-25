"""
tools/generate_comfort_fit_examples.py

Computes worked Comfort Fit Score examples across all 5 reference cities
(Jodhpur, Mumbai, New Delhi, Bengaluru, Shimla) using real precomputed simulation
data and user comfort profile scenarios.

Saves verified evidence to: reports/evidence/comfort_fit_worked_examples.txt
"""

import os
import sys
import json

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.comfort.profile import build_user_comfort_profile
from src.comfort.fit import compute_comfort_fit_score

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]

# City-tailored typical user response profiles
USER_SCENARIOS = {
    "Jodhpur": {
        "scenario_name": "Hot-Dry Desert Resident (Extreme Heat Sensitivity)",
        "responses": {
            "feel_summer": 3, # Hot (+3)
            "feel_winter": 0, # Neutral
            "feel_monsoon": 1, # Slightly warm
            "sensitivity": "heat_sensitive",
            "clothing_summer": "light",
            "clothing_winter": "normal",
            "activity_level": "light_active",
            "hours_occupied": 20,
            "cooling_equipment": "cooler",
            "cooling_willingness": "moderate",
            "priorities": {"weight_comfort": 60, "weight_energy": 25, "weight_cost": 15},
            "special_needs": ["elderly"]
        }
    },
    "Mumbai": {
        "scenario_name": "Coastal Humid Urban Resident (Ceiling Fan Reliance)",
        "responses": {
            "feel_summer": 2, # Warm (+2)
            "feel_winter": 0, # Neutral
            "feel_monsoon": 3, # Hot & muggy (+3)
            "sensitivity": "heat_sensitive",
            "clothing_summer": "light",
            "clothing_winter": "light",
            "activity_level": "light_active",
            "hours_occupied": 16,
            "cooling_equipment": "fan",
            "cooling_willingness": "frequent",
            "priorities": {"weight_comfort": 50, "weight_energy": 35, "weight_cost": 15},
            "special_needs": ["work_from_home"]
        }
    },
    "New_Delhi": {
        "scenario_name": "Composite Climate Resident (Dual Season Sensitivity)",
        "responses": {
            "feel_summer": 3, # Hot (+3)
            "feel_winter": -2, # Cool (-2)
            "feel_monsoon": 2, # Warm (+2)
            "sensitivity": "balanced",
            "clothing_summer": "light",
            "clothing_winter": "heavy",
            "activity_level": "light_active",
            "hours_occupied": 18,
            "cooling_equipment": "ac",
            "cooling_willingness": "moderate",
            "priorities": {"weight_comfort": 45, "weight_energy": 35, "weight_cost": 20},
            "special_needs": []
        }
    },
    "Bengaluru": {
        "scenario_name": "Temperate Plateau Resident (Moderate Preferences)",
        "responses": {
            "feel_summer": 1, # Slightly warm
            "feel_winter": 0, # Neutral
            "feel_monsoon": 0, # Neutral
            "sensitivity": "balanced",
            "clothing_summer": "normal",
            "clothing_winter": "normal",
            "activity_level": "sedentary",
            "hours_occupied": 16,
            "cooling_equipment": "fan",
            "cooling_willingness": "minimal",
            "priorities": {"weight_comfort": 40, "weight_energy": 40, "weight_cost": 20},
            "special_needs": []
        }
    },
    "Shimla": {
        "scenario_name": "Cold Montane Resident (Severe Cold Sensitivity)",
        "responses": {
            "feel_summer": 0, # Neutral
            "feel_winter": -3, # Cold (-3)
            "feel_monsoon": -1, # Slightly cool
            "sensitivity": "cold_sensitive",
            "clothing_summer": "normal",
            "clothing_winter": "heavy",
            "activity_level": "light_active",
            "hours_occupied": 20,
            "cooling_equipment": "none",
            "cooling_willingness": "minimal",
            "priorities": {"weight_comfort": 55, "weight_energy": 30, "weight_cost": 15},
            "special_needs": ["elderly"]
        }
    }
}

def main():
    lines = []
    def log(msg=""):
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        lines.append(msg)

    log("=" * 80)
    log("CLIMATEADAPT-COMFORT V2: WORKED COMFORT FIT SCORE EXAMPLES")
    log("=" * 80)
    log("Demonstrates steps 3 & 4 of product flow across all 5 reference stations.")
    log("Evaluates candidate Pareto designs vs conventional local baseline (R2).")
    log("Dual judges (ML Champion + Physical Adaptive 90%) evaluated with transparent disagreement.")
    log()

    # Load city norms
    with open("data/export/city_comfort_norms.json", "r", encoding="utf-8") as f:
        city_norms = json.load(f)

    for city in CITIES:
        log("-" * 80)
        log(f"CITY: {city.upper()} ({city_norms[city]['applicability']['confidence_tier']} Confidence)")
        log("-" * 80)

        norm = city_norms[city]
        pref = norm["occupant_preferences_db2"]
        log(f"Climate Description: {pref['climate_description']}")
        log(f"DB II Sample: {pref['n_rows']} rows across {pref['n_buildings']} buildings ({pref['sample_scope']})")
        if pref['has_labelled_votes']:
            tsv = pref['tsv_distribution_pct']
            log(f"Typical Occupant Votes: Cool {tsv['cool']}%, Neutral {tsv['neutral']}%, Warm {tsv['warm']}% | Median Neutral: {pref['median_neutral_temp_c']} C")
        else:
            log(f"Typical Occupant Votes: {pref['notes']}")

        scenario = USER_SCENARIOS[city]
        log(f"\nUser Profile Scenario: {scenario['scenario_name']}")
        profile = build_user_comfort_profile(scenario["responses"])
        log(f"  Warm Discomfort Penalty: {profile['sensitivity']['warm_discomfort_penalty']}x")
        log(f"  Cool Discomfort Penalty: {profile['sensitivity']['cool_discomfort_penalty']}x")
        log(f"  Priority Weights: Comfort {profile['normalized_weights']['weight_comfort']*100:.0f}%, Energy {profile['normalized_weights']['weight_energy']*100:.0f}%, Cost {profile['normalized_weights']['weight_cost']*100:.0f}%")

        # Load reference and Pareto designs
        ref_path = f"data/export/reference_{city}_house.json"
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_r2 = json.load(f).get("R2", {})

        pareto_path = f"data/export/pareto_{city}_house.json"
        with open(pareto_path, "r", encoding="utf-8") as f:
            pareto_list = json.load(f)

        # Pick top verified design
        verified_candidates = [d for d in pareto_list if d.get("verified")]
        top_design = verified_candidates[0] if verified_candidates else pareto_list[0]

        fit_res = compute_comfort_fit_score(
            design_metrics=top_design,
            reference_metrics=ref_r2,
            user_profile=profile,
            city=city
        )

        log(f"\n[FIT SCORE EVALUATION]")
        log(f"  Typical Local Building (R2 Baseline) Fit Score : {fit_res['reference_fit_score']} / 100")
        log(f"  Recommended Design ({top_design['pareto_id']}) Fit Score : {fit_res['fit_score']} / 100")
        log(f"  Comfort Gain Points                            : +{fit_res['comfort_gain_points']} pts")
        log(f"  Discomfort Hours Reduction                     : -{fit_res['discomfort_reduction_pct']}% of year")
        log(f"  Sub-Scores (Comfort / Energy / Cost)          : {fit_res['sub_scores']['comfort_score']} / {fit_res['sub_scores']['energy_score']} / {fit_res['sub_scores']['cost_score']}")
        log(f"  Dual Judges (ML Champion / Adaptive 90%)       : {fit_res['dual_judges']['O1_ml_champion_pct']}% vs {fit_res['dual_judges']['O1_adaptive_90_pct']}% (Disagreement: {fit_res['dual_judges']['judge_disagreement_pts']} pts)")
        log(f"\nExplanation (EN):")
        log(f"  \"{fit_res['explanations']['en']}\"")
        log(f"Explanation (HI):")
        log(f"  \"{fit_res['explanations']['hi']}\"")
        log()

    out_file = "reports/evidence/comfort_fit_worked_examples.txt"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nLiteral worked examples saved to: {out_file}")

if __name__ == "__main__":
    main()
