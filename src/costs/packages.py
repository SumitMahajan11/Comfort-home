"""
src/costs/packages.py

Package Selection Engine for ClimateAdapt-Comfort.
Selects three curated packages (Budget, Balanced, Best-Comfort) per city and building type.

Strict Rules:
- Never includes an unverified design when verified designs exist in the Pareto set.
- Dual-judge thermal comfort: evaluates O1 as (O1_ml + O1_adapt) / 2.0.
- Handles missing or null cost rates gracefully, documenting selection rationale.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from src.costs.bom import build_bom
from src.costs.estimate import estimate_cost_range, compare_design_to_reference
from src.costs.carbon import compute_embodied_carbon

CITY_CONFIDENCE_TIERS = {
    "Jodhpur": "Low",
    "Mumbai": "Medium",
    "New_Delhi": "Low",
    "Bengaluru": "Medium",
    "Shimla": "Low"
}

def get_dual_judge_o1(design: Dict[str, Any]) -> float:
    """Returns the average discomfort percentage across ML champion and Adaptive 90 judges."""
    o1_ml = float(design.get("actual_O1_ml", design.get("O1_ml", 0.0)))
    o1_adapt = float(design.get("actual_O1_adapt", design.get("O1_adapt", 0.0)))
    return (o1_ml + o1_adapt) / 2.0

def get_actual_or_pred_o2(design: Dict[str, Any]) -> float:
    """Returns the actual EnergyPlus O2 if verified, else predicted O2."""
    return float(design.get("actual_O2", design.get("O2", 0.0)))

def select_packages(
    pareto_designs: List[Dict[str, Any]],
    reference_design: Dict[str, Any],
    building_type: str,
    city: str,
    floor_area_m2: float = None,
    dsr_rates: Optional[Dict[str, Any]] = None,
    tariffs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Selects Budget, Balanced, and Best-Comfort packages from the Pareto set.

    Args:
        pareto_designs: List of Pareto design dictionaries
        reference_design: Conventional reference building dictionary (e.g. R2)
        building_type: 'shelter_v1', 'house', 'apartment', or 'commercial'
        city: reference city name
        floor_area_m2: optional building floor area
        dsr_rates: optional DSR rates
        tariffs: optional tariffs

    Returns:
        Dictionary with three packages: 'budget', 'balanced', 'best_comfort'
    """
    if not pareto_designs:
        raise ValueError(f"No Pareto designs provided for {city} - {building_type}")

    # GATING RULE: Filter to verified designs if ANY verified design exists
    verified_pool = [d for d in pareto_designs if d.get("verified") is True]
    cand_pool = verified_pool if verified_pool else pareto_designs

    ref_o1 = get_dual_judge_o1(reference_design) if reference_design else 100.0
    ref_o2 = get_actual_or_pred_o2(reference_design) if reference_design else 999.0

    # Compute BOM and Cost Estimates for each candidate
    pool_records = []
    for d in cand_pool:
        bom = build_bom(building_type, d, floor_area_m2=floor_area_m2, city=city)
        cost_est = estimate_cost_range(bom, city=city, dsr_rates=dsr_rates)
        carbon_est = compute_embodied_carbon(bom, floor_area_m2=floor_area_m2 or 50.0)
        
        o1_val = get_dual_judge_o1(d)
        o2_val = get_actual_or_pred_o2(d)
        beats_ref_both = (o1_val <= ref_o1) and (o2_val <= ref_o2)

        # Proxy for envelope intervention if cost rates are null
        # (insulation thickness + shading depth + WWR)
        intervention_proxy = (
            float(d.get("roof_insulation_thickness", 0.0)) * 10.0 +
            float(d.get("wall_insulation_thickness", 0.0)) * 10.0 +
            float(d.get("shading_depth", 0.0)) * 1.5 +
            float(d.get("wwr", 0.20))
        )

        pool_records.append({
            "design": d,
            "bom": bom,
            "cost": cost_est,
            "carbon": carbon_est,
            "o1_dual": o1_val,
            "o2": o2_val,
            "beats_ref_both": beats_ref_both,
            "intervention_proxy": intervention_proxy
        })

    # 1. BEST-COMFORT PACKAGE: Lowest dual-judge average O1
    best_comfort_item = min(pool_records, key=lambda x: (x["o1_dual"], x["o2"]))

    # 2. BUDGET PACKAGE:
    # Lowest cost among designs that beat reference on both O1 and O2
    beaters = [r for r in pool_records if r["beats_ref_both"]]
    budget_candidates = beaters if beaters else pool_records

    # If cost rates are available, sort by cost_inr_mid; otherwise sort by intervention proxy
    sample_cost = budget_candidates[0]["cost"]
    if sample_cost.get("status") == "AVAILABLE":
        budget_item = min(budget_candidates, key=lambda x: (x["cost"]["cost_inr_mid"], x["o1_dual"]))
    else:
        # Rates null: pick lowest intervention proxy that still beats reference
        budget_item = min(budget_candidates, key=lambda x: (x["intervention_proxy"], x["o1_dual"]))

    # 3. BALANCED PACKAGE: Knee point of the Pareto front
    # Min Euclidean distance to normalized utopia (min O1, min O2)
    o1_vals = np.array([r["o1_dual"] for r in pool_records])
    o2_vals = np.array([r["o2"] for r in pool_records])

    o1_range = (np.max(o1_vals) - np.min(o1_vals)) or 1.0
    o2_range = (np.max(o2_vals) - np.min(o2_vals)) or 1.0

    norm_o1 = (o1_vals - np.min(o1_vals)) / o1_range
    norm_o2 = (o2_vals - np.min(o2_vals)) / o2_range
    knee_distances = norm_o1**2 + norm_o2**2

    knee_idx = int(np.argmin(knee_distances))
    balanced_item = pool_records[knee_idx]

    # Package assembly helper
    conf_tier = CITY_CONFIDENCE_TIERS.get(city, "Low")
    ref_bom = build_bom(building_type, reference_design, floor_area_m2=floor_area_m2, city=city) if reference_design else []
    ref_cost = estimate_cost_range(ref_bom, city=city, dsr_rates=dsr_rates) if reference_design else {}

    def format_pkg(pkg_key: str, name: str, desc: str, item: Dict[str, Any]) -> Dict[str, Any]:
        d = item["design"]
        payback_res = compare_design_to_reference(
            design_cost=item["cost"],
            reference_cost=ref_cost,
            o2_design=item["o2"],
            o2_reference=ref_o2,
            floor_area_m2=floor_area_m2 or 50.0,
            city=city,
            tariffs=tariffs
        )
        return {
            "package_id": pkg_key,
            "name": name,
            "description": desc,
            "city": city,
            "building_type": building_type,
            "confidence_tier": conf_tier,
            "pareto_id": d.get("pareto_id", "P_UNKNOWN"),
            "verified": d.get("verified", False),
            "verification_mode": d.get("verification_mode", "unverified"),
            "design_variables": {
                "roof_insulation_thickness": d.get("roof_insulation_thickness"),
                "wall_insulation_thickness": d.get("wall_insulation_thickness"),
                "wall_mass_class": d.get("wall_mass_class"),
                "roof_solar_absorptance": d.get("roof_solar_absorptance"),
                "wwr": d.get("wwr"),
                "orientation": d.get("orientation"),
                "shading_depth": d.get("shading_depth"),
                "ventilation_ach": d.get("ventilation_ach")
            },
            "performance": {
                "O1_dual_judge_pct": round(item["o1_dual"], 2),
                "O1_ml_pct": round(float(d.get("actual_O1_ml", d.get("O1_ml", 0.0))), 2),
                "O1_adapt_pct": round(float(d.get("actual_O1_adapt", d.get("O1_adapt", 0.0))), 2),
                "O2_kwh_per_m2_yr": round(item["o2"], 2),
                "beats_reference_both": item["beats_ref_both"]
            },
            "bom": item["bom"],
            "cost_range": item["cost"],
            "payback": payback_res,
            "embodied_carbon": item["carbon"]
        }

    return {
        "city": city,
        "building_type": building_type,
        "confidence_tier": conf_tier,
        "verified_pool_size": len(verified_pool),
        "total_pareto_size": len(pareto_designs),
        "packages": {
            "budget": format_pkg(
                "pkg_budget",
                "Budget Package",
                "Lowest cost envelope interventions while outperforming baseline on comfort and energy.",
                budget_item
            ),
            "balanced": format_pkg(
                "pkg_balanced",
                "Balanced Package",
                "Knee point of the multi-objective Pareto front providing optimal trade-off between comfort and energy.",
                balanced_item
            ),
            "best_comfort": format_pkg(
                "pkg_best_comfort",
                "Best Comfort Package",
                "Maximum thermal comfort (lowest dual-judge discomfort hours) among verified designs.",
                best_comfort_item
            )
        }
    }
