"""
tests/test_costs.py

Automated test suite for ClimateAdapt-Comfort Materials and Cost Engine.
Verifies:
1. BOM quantity mathematics on hand-calculated reference shelter example.
2. Cost range ordering (cost_low <= cost_mid <= cost_high) and strict null gating.
3. Validator fails loudly when rates are null/unfilled.
4. Curated packages never select an unverified design when verified designs exist.
"""

import pytest
import os
import subprocess
import sys

from src.costs.bom import build_bom
from src.costs.estimate import estimate_cost_range, compare_design_to_reference
from src.costs.carbon import compute_embodied_carbon
from src.costs.packages import select_packages
from tools.validate_costs import validate_cost_rates

def test_bom_quantity_math_hand_calculated_example():
    """
    Hand-calculated reference example:
    Building type: shelter_v1 (4.5m x 4.5m, height 3.0m)
    Gross wall area: 18.0m * 3.0m = 54.0 m2
    Roof area: 20.25 m2
    WWR: 0.20
    Roof insulation: 0.05 m (50 mm)
    Wall insulation: 0.05 m (50 mm)
    Wall mass: medium (clay brick)
    Roof absorptance: 0.30 (Cool roof coating)
    Shading depth: 0.50 m
    Ventilation: 7.5 ACH
    """
    design_vars = {
        "wall_mass_class": "medium",
        "wwr": 0.20,
        "roof_insulation_thickness": 0.05,
        "wall_insulation_thickness": 0.05,
        "roof_solar_absorptance": 0.30,
        "shading_depth": 0.50,
        "ventilation_ach": 7.5
    }

    bom = build_bom(
        building_type="shelter_v1",
        design_variables=design_vars,
        floor_area_m2=20.25,
        city="Jodhpur"
    )

    items_dict = {item["item_id"]: item for item in bom}

    # 1. Window area = 54.0 * 0.20 = 10.80 m2
    assert "window_glazing_standard" in items_dict
    assert pytest.approx(items_dict["window_glazing_standard"]["quantity"], rel=1e-3) == 10.80

    # 2. Net wall area = 54.0 - 10.80 = 43.20 m2
    assert "wall_medium_brick" in items_dict
    assert pytest.approx(items_dict["wall_medium_brick"]["quantity"], rel=1e-3) == 43.20

    # 3. Wall insulation volume = 43.20 * 0.05 = 2.16 m3
    assert "wall_insulation_eps" in items_dict
    assert pytest.approx(items_dict["wall_insulation_eps"]["quantity"], rel=1e-3) == 2.160

    # 4. Roof slab = 20.25 m2
    assert "roof_slab_rcc" in items_dict
    assert pytest.approx(items_dict["roof_slab_rcc"]["quantity"], rel=1e-3) == 20.25

    # 5. Roof insulation volume = 20.25 * 0.05 = 1.0125 m3
    assert "roof_insulation_eps" in items_dict
    assert pytest.approx(items_dict["roof_insulation_eps"]["quantity"], rel=1e-3) == 1.0125

    # 6. Roof finish: absorptance 0.30 <= 0.45 -> Cool roof coating = 20.25 m2
    assert "roof_cool_coating" in items_dict
    assert pytest.approx(items_dict["roof_cool_coating"]["quantity"], rel=1e-3) == 20.25
    assert "roof_standard_finish" not in items_dict

    # 7. Shading projection area = (10.80 m2 / 1.2 m) * 0.50 m = 9.0 m * 0.50 m = 4.50 m2
    assert "shading_overhang_cantilever" in items_dict
    assert pytest.approx(items_dict["shading_overhang_cantilever"]["quantity"], rel=1e-3) == 4.50

    # 8. Ventilation louvers = 10.80 * (7.5 / 15.0 * 0.50) = 10.80 * 0.25 = 2.70 m2
    assert "ventilation_louvers" in items_dict
    assert pytest.approx(items_dict["ventilation_louvers"]["quantity"], rel=1e-3) == 2.70

def test_cost_range_ordering_and_strict_null_gating():
    """
    Verifies that when rates are loaded, cost_low <= cost_mid <= cost_high,
    and when rates are null, returns status UNAVAILABLE with null costs.
    """
    design_vars = {
        "wall_mass_class": "medium",
        "wwr": 0.20,
        "roof_insulation_thickness": 0.05,
        "wall_insulation_thickness": 0.05,
        "roof_solar_absorptance": 0.30,
        "shading_depth": 0.50,
        "ventilation_ach": 7.5
    }
    bom = build_bom("shelter_v1", design_vars)

    # 1. Null rates test (repository default)
    null_est = estimate_cost_range(bom, city="Jodhpur")
    assert null_est["status"] == "UNAVAILABLE"
    assert null_est["cost_inr_low"] is None
    assert null_est["cost_inr_mid"] is None
    assert null_est["cost_inr_high"] is None
    assert "rates not yet loaded" in null_est["message"]

    # 2. Populated rates test
    mock_rates = {
        "wall_medium_brick": {"rate_inr_low": 1000.0, "rate_inr_high": 1200.0, "city_cost_index": {"Jodhpur": 1.0}},
        "wall_insulation_eps": {"rate_inr_low": 4000.0, "rate_inr_high": 5000.0, "city_cost_index": {"Jodhpur": 1.0}},
        "roof_slab_rcc": {"rate_inr_low": 1500.0, "rate_inr_high": 1800.0, "city_cost_index": {"Jodhpur": 1.0}},
        "roof_insulation_eps": {"rate_inr_low": 4000.0, "rate_inr_high": 5000.0, "city_cost_index": {"Jodhpur": 1.0}},
        "roof_cool_coating": {"rate_inr_low": 200.0, "rate_inr_high": 280.0, "city_cost_index": {"Jodhpur": 1.0}},
        "roof_standard_finish": {"rate_inr_low": 120.0, "rate_inr_high": 180.0, "city_cost_index": {"Jodhpur": 1.0}},
        "window_glazing_standard": {"rate_inr_low": 3500.0, "rate_inr_high": 4200.0, "city_cost_index": {"Jodhpur": 1.0}},
        "shading_overhang_cantilever": {"rate_inr_low": 1000.0, "rate_inr_high": 1400.0, "city_cost_index": {"Jodhpur": 1.0}},
        "ventilation_louvers": {"rate_inr_low": 1400.0, "rate_inr_high": 1800.0, "city_cost_index": {"Jodhpur": 1.0}}
    }

    valid_est = estimate_cost_range(bom, city="Jodhpur", dsr_rates=mock_rates, contingency_pct=15.0)
    assert valid_est["status"] == "AVAILABLE"
    assert valid_est["cost_inr_low"] > 0
    assert valid_est["cost_inr_mid"] > 0
    assert valid_est["cost_inr_high"] > 0
    assert valid_est["cost_inr_low"] <= valid_est["cost_inr_mid"] <= valid_est["cost_inr_high"]
    assert pytest.approx(valid_est["cost_inr_mid"], rel=1e-2) == (valid_est["cost_inr_low"] + valid_est["cost_inr_high"]) / 2.0

def test_validator_fails_when_rate_is_null():
    """
    Validates that tools/validate_costs.py fails loudly (returns False / exits non-zero)
    when data/costs/dsr_rates.json has null rates.
    """
    is_valid, unfilled = validate_cost_rates("data/costs/dsr_rates.json")
    assert is_valid is False
    assert len(unfilled) >= 10
    assert any(u["item_id"] == "wall_medium_brick" for u in unfilled)
    assert any(u["reason"] == "RATE_IS_NULL" for u in unfilled)

    # CLI process validation
    res = subprocess.run([sys.executable, "tools/validate_costs.py"], capture_output=True, text=True)
    assert res.returncode == 1
    assert "VALIDATION FAILED" in res.stdout or "VALIDATION FAILED" in res.stderr

def test_packages_never_include_unverified_design_when_verified_exist():
    """
    Verifies that package selection strictly filters to verified designs
    whenever verified designs exist in the Pareto set.
    """
    # Create candidate pool with 3 verified designs and 3 unverified designs
    # Unverified design P_UNVER_0 has artificially "better" O1 and lower energy
    pool = [
        # Unverified "bait" designs
        {
            "pareto_id": "P_UNVER_0",
            "verified": False,
            "verification_mode": "unverified",
            "O1_ml": 5.0,
            "O1_adapt": 5.0,
            "O2": 2.0,
            "roof_insulation_thickness": 0.05,
            "wall_insulation_thickness": 0.05,
            "wall_mass_class": "medium",
            "roof_solar_absorptance": 0.30,
            "wwr": 0.15,
            "shading_depth": 0.4,
            "ventilation_ach": 5.0
        },
        # Verified designs
        {
            "pareto_id": "P_VER_1",
            "verified": True,
            "verification_mode": "fully verified",
            "actual_O1_ml": 18.0,
            "actual_O1_adapt": 16.0,
            "actual_O2": 15.0,
            "roof_insulation_thickness": 0.05,
            "wall_insulation_thickness": 0.05,
            "wall_mass_class": "medium",
            "roof_solar_absorptance": 0.30,
            "wwr": 0.20,
            "shading_depth": 0.5,
            "ventilation_ach": 7.0
        },
        {
            "pareto_id": "P_VER_2",
            "verified": True,
            "verification_mode": "fully verified",
            "actual_O1_ml": 12.0,
            "actual_O1_adapt": 14.0,
            "actual_O2": 22.0,
            "roof_insulation_thickness": 0.10,
            "wall_insulation_thickness": 0.08,
            "wall_mass_class": "heavy",
            "roof_solar_absorptance": 0.30,
            "wwr": 0.25,
            "shading_depth": 0.6,
            "ventilation_ach": 8.0
        },
        {
            "pareto_id": "P_VER_3",
            "verified": True,
            "verification_mode": "fully verified",
            "actual_O1_ml": 25.0,
            "actual_O1_adapt": 22.0,
            "actual_O2": 10.0,
            "roof_insulation_thickness": 0.02,
            "wall_insulation_thickness": 0.02,
            "wall_mass_class": "light",
            "roof_solar_absorptance": 0.40,
            "wwr": 0.15,
            "shading_depth": 0.3,
            "ventilation_ach": 5.0
        }
    ]

    ref_design = {
        "reference_name": "R2_Conventional",
        "O1_ml": 30.0,
        "O1_adapt": 28.0,
        "O2": 35.0,
        "wall_mass_class": "medium",
        "roof_insulation_thickness": 0.0,
        "wall_insulation_thickness": 0.0,
        "roof_solar_absorptance": 0.60,
        "wwr": 0.20,
        "shading_depth": 0.0,
        "ventilation_ach": 5.0
    }

    result = select_packages(
        pareto_designs=pool,
        reference_design=ref_design,
        building_type="house",
        city="Jodhpur"
    )

    pkgs = result["packages"]
    for pkg_name in ["budget", "balanced", "best_comfort"]:
        pkg = pkgs[pkg_name]
        assert pkg["verified"] is True, f"Package {pkg_name} selected unverified design!"
        assert pkg["pareto_id"] != "P_UNVER_0", f"Package {pkg_name} selected unverified 'bait' design!"
        assert pkg["pareto_id"] in ["P_VER_1", "P_VER_2", "P_VER_3"]
