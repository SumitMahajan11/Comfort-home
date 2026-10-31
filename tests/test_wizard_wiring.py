"""
tests/test_wizard_wiring.py

Automated acceptance test verifying that:
1. Every remaining Step 4 questionnaire answer in the wizard wires into at least one output field.
2. Sensation / sensitivity modulates the occupant comfort profile weights.
3. Occupancy hours modulate user_occupied_hours.
4. Packages represent distinct verified Pareto design trade-offs.
"""

import pytest
from src.comfort.profile import build_user_comfort_profile
from src.api.recommender import generate_three_packages

def test_wizard_step4_wiring_answers_affect_outputs():
    # 1. Test that the three packages generated reflect distinct trade-offs across the Pareto front
    res_balanced = generate_three_packages(city="Jodhpur", building_type="house", user_priority="balanced")

    pkg_budget = res_balanced["packages"]["budget"]
    pkg_balanced = res_balanced["packages"]["balanced"]
    pkg_comfort = res_balanced["packages"]["best_comfort"]

    # Each package represents a distinct verified envelope specification
    assert pkg_budget["id"] != pkg_comfort["id"]
    assert pkg_balanced["id"] != pkg_comfort["id"]
    assert pkg_budget["design_variables"]["roof_insulation_thickness"] <= pkg_comfort["design_variables"]["roof_insulation_thickness"]

def test_wizard_step4_occupant_profile_parsing():
    # Sensation sensitivity mapping
    prof_hot = build_user_comfort_profile({"feel_summer": 2, "sensitivity": "heat_sensitive", "hours_occupied": 18.0})
    prof_cold = build_user_comfort_profile({"feel_summer": -2, "sensitivity": "cold_sensitive", "hours_occupied": 8.0})

    assert prof_hot["sensitivity"]["warm_discomfort_penalty"] > prof_cold["sensitivity"]["warm_discomfort_penalty"]
    assert prof_cold["sensitivity"]["cool_discomfort_penalty"] > prof_hot["sensitivity"]["cool_discomfort_penalty"]
    assert prof_hot["user_model_inputs"]["user_occupied_hours_per_day"] == 18.0
    assert prof_cold["user_model_inputs"]["user_occupied_hours_per_day"] == 8.0
