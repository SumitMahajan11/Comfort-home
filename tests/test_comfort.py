"""
tests/test_comfort.py

Automated test suite for City Comfort Norms, User Comfort Profile, and Comfort Fit Score Engine.
Verifies:
1. Empirical city comfort norms integrity and Shimla D-011 zero-fabrication assertion.
2. User comfort profile mapping and user override mode integrity.
3. Comfort Fit Score formula mathematics, bounds, and dual-judge disagreement reporting.
4. Deterministic bilingual template explanations (EN/HI).
"""

import pytest
import os
import json

from src.comfort.profile import (
    build_user_comfort_profile,
    map_tsv_to_target_class,
    QUESTIONNAIRE_SCHEMA
)
from src.comfort.fit import compute_comfort_fit_score

def test_city_comfort_norms_integrity_and_d011_shimla_gating():
    """Verifies city comfort norms data structure and strict null gating on Shimla votes."""
    norms_path = "data/export/city_comfort_norms.json"
    assert os.path.exists(norms_path), "city_comfort_norms.json missing from data/export/"

    with open(norms_path, "r", encoding="utf-8") as f:
        norms = json.load(f)

    assert len(norms) == 5
    for city in ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]:
        assert city in norms
        c_data = norms[city]
        assert len(c_data["monthly_climate_summary"]) == 12
        assert "confidence_tier" in c_data["applicability"]
        assert "occupant_preferences_db2" in c_data

    # Decision D-011 assertion: Shimla has NO labelled votes in DB II; must not be fabricated
    shimla_pref = norms["Shimla"]["occupant_preferences_db2"]
    assert shimla_pref["has_labelled_votes"] is False
    assert shimla_pref["tsv_distribution_pct"] is None
    assert shimla_pref["median_neutral_temp_c"] is None
    assert "Decision D-011" in shimla_pref["notes"]
    assert shimla_pref["flag_missing_votes"] is True

    # Bengaluru check: Medium confidence, valid votes present
    blr_pref = norms["Bengaluru"]["occupant_preferences_db2"]
    assert blr_pref["has_labelled_votes"] is True
    assert blr_pref["tsv_distribution_pct"]["neutral"] > 40.0
    assert pytest.approx(blr_pref["median_neutral_temp_c"], rel=1e-1) == 24.8
    assert norms["Bengaluru"]["applicability"]["confidence_tier"] == "Medium"

def test_questionnaire_schema_and_profile_parser():
    """Verifies bilingual questionnaire schema and user override mapping."""
    assert len(QUESTIONNAIRE_SCHEMA["questions"]) >= 6

    # Test 7-point scale mapping to 3-class target
    assert map_tsv_to_target_class(-3) == "cool"
    assert map_tsv_to_target_class(-1) == "cool"
    assert map_tsv_to_target_class(0) == "neutral"
    assert map_tsv_to_target_class(1) == "warm"
    assert map_tsv_to_target_class(3) == "warm"

    # Test user profile parser with heat sensitive response
    user_resp = {
        "feel_summer": 3,
        "feel_winter": 0,
        "feel_monsoon": 2,
        "sensitivity": "heat_sensitive",
        "clothing_summer": "light",
        "clothing_winter": "normal",
        "activity_level": "light_active",
        "hours_occupied": 18,
        "cooling_equipment": "cooler",
        "cooling_willingness": "moderate",
        "priorities": {"weight_comfort": 60, "weight_energy": 25, "weight_cost": 15},
        "special_needs": ["elderly"]
    }

    profile = build_user_comfort_profile(user_resp)
    assert profile["status"] == "VALID_PROFILE"
    assert profile["user_overrides_active"] is True
    assert profile["seasonal_feel"]["summer"]["target_class"] == "warm"
    assert profile["seasonal_feel"]["winter"]["target_class"] == "neutral"

    # Heat sensitive penalty check: warm penalty must be higher than base 1.0
    assert profile["sensitivity"]["warm_discomfort_penalty"] >= 1.35
    # Elderly special needs increases cool protection
    assert profile["sensitivity"]["cool_discomfort_penalty"] > 0.75

    # Priority weights normalization check
    weights = profile["normalized_weights"]
    total_w = weights["weight_comfort"] + weights["weight_energy"] + weights["weight_cost"]
    assert pytest.approx(total_w, rel=1e-3) == 1.0

def test_comfort_fit_score_formula_and_bounds():
    """
    Tests exact mathematics of the Comfort Fit Score formula:
    - Dual-judge consensus and disagreement calculation.
    - Sub-score bounds [0, 100].
    - Comfort gain positive when design outperforms reference.
    """
    user_profile = {
        "sensitivity": {
            "warm_discomfort_penalty": 1.35,
            "cool_discomfort_penalty": 0.85
        },
        "normalized_weights": {
            "weight_comfort": 0.50,
            "weight_energy": 0.30,
            "weight_cost": 0.20
        }
    }

    ref_metrics = {
        "O1_ml": 40.0,
        "warm_ml": 30.0,
        "cool_ml": 10.0,
        "O1_adapt": 36.0,
        "O2": 35.0
    }

    design_metrics = {
        "actual_O1_ml": 15.0,
        "actual_warm_ml": 10.0,
        "actual_cool_ml": 5.0,
        "actual_O1_adapt": 18.0,
        "actual_O2": 12.0
    }

    fit_res = compute_comfort_fit_score(
        design_metrics=design_metrics,
        reference_metrics=ref_metrics,
        user_profile=user_profile,
        city="Jodhpur"
    )

    # 1. Dual judge calculations
    # Design dual judge = (15.0 + 18.0) / 2 = 16.5
    assert pytest.approx(fit_res["dual_judges"]["O1_dual_judge_pct"], rel=1e-2) == 16.5
    # Judge disagreement = |15.0 - 18.0| = 3.0 pts
    assert pytest.approx(fit_res["dual_judges"]["judge_disagreement_pts"], rel=1e-2) == 3.0

    # 2. Score bounds [0, 100]
    assert 0.0 <= fit_res["fit_score"] <= 100.0
    assert 0.0 <= fit_res["reference_fit_score"] <= 100.0
    assert 0.0 <= fit_res["sub_scores"]["comfort_score"] <= 100.0
    assert 0.0 <= fit_res["sub_scores"]["energy_score"] <= 100.0
    assert 0.0 <= fit_res["sub_scores"]["cost_score"] <= 100.0

    # 3. Comfort gain points: design significantly beats reference
    assert fit_res["comfort_gain_points"] > 20.0
    assert fit_res["fit_score"] > fit_res["reference_fit_score"]
    assert fit_res["discomfort_reduction_pct"] > 0.0

    # 4. Explanation strings deterministic and present in both EN and HI
    assert len(fit_res["explanations"]["en"]) > 50
    assert len(fit_res["explanations"]["hi"]) > 50
    assert "Comfort Fit Score" in fit_res["explanations"]["en"]
    assert "कम्फर्ट फिट स्कोर" in fit_res["explanations"]["hi"]
    assert "Dual-Judge Note" in fit_res["explanations"]["en"]
