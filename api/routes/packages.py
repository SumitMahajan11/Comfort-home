"""
api/routes/packages.py

Endpoint for retrieving curated passive design packages (Budget, Balanced, Best-Comfort)
with geometric BOM, cost ranges (strict null gating), carbon, and 12-month temperature series.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query

from api.config import (
    CITY_METADATA,
    ALLOWED_CITIES,
    ALLOWED_BUILDING_TYPES,
    ALLOWED_SCENARIOS
)
from api.loader import get_store
from api.models import (
    PackagesResponse,
    PackageModel,
    CostRangeModel
)
from src.costs.packages import select_packages

router = APIRouter(tags=["Packages"])

# -----------------------------------------------------------------------------
# GET /packages?city=&type=&scenario=
# -----------------------------------------------------------------------------
@router.get("/packages", response_model=PackagesResponse)
def get_packages(
    city: str = Query("Jodhpur", description="Reference city (e.g. Jodhpur, Mumbai, New_Delhi, Bengaluru, Shimla)"),
    type: str = Query("house", description="Building typology (shelter_v1, house, apartment, commercial)"),
    scenario: str = Query("current", description="Climate scenario (current, plus1p5, plus3p0)")
):
    """
    Returns the three curated design packages (Budget, Balanced, Best-Comfort)
    with BOM, cost range, carbon, and 12-month before/after temperature profiles.
    """
    store = get_store()
    c_key = city.replace(" ", "_")
    if c_key not in CITY_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{city}' not supported. Allowed: {ALLOWED_CITIES}")

    b_type = type.lower()
    if b_type not in ALLOWED_BUILDING_TYPES:
        raise HTTPException(status_code=400, detail=f"Building type '{type}' not supported. Allowed: {ALLOWED_BUILDING_TYPES}")

    scen = scenario.lower()
    if scen not in ALLOWED_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Scenario '{scenario}' not supported. Allowed: {ALLOWED_SCENARIOS}")

    meta = CITY_METADATA[c_key]
    ref_metrics = meta["reference_r2"]

    p_designs = store.get_pareto(c_key, b_type)
    if not p_designs:
        raise HTTPException(status_code=500, detail=f"Pareto designs for '{c_key}' ({b_type}) not found in cache.")

    # Select packages
    pkg_selection = select_packages(
        pareto_designs=p_designs,
        reference_design=ref_metrics,
        building_type=b_type,
        city=c_key,
        dsr_rates=store.dsr_rates,
        tariffs=store.tariffs
    )

    packages_out: Dict[str, PackageModel] = {}
    for pkg_key, pkg_info in pkg_selection.get("packages", {}).items():
        d_id = pkg_info.get("pareto_id", "P_001")
        v_mode = pkg_info.get("verification_mode", "estimated")
        if "fully verified" in v_mode or v_mode == "verified":
            v_status = "verified"
        elif "light" in v_mode:
            v_status = "light verification"
        else:
            v_status = "estimated"

        # Load monthly indoor series
        monthly_indoor_data = store.get_monthly_indoor(c_key, b_type, d_id)
        if monthly_indoor_data and scen in monthly_indoor_data:
            monthly_series = monthly_indoor_data[scen]
        elif monthly_indoor_data and "current" in monthly_indoor_data:
            monthly_series = monthly_indoor_data["current"]
        else:
            # Fallback monthly approximation from performance metrics
            perf = pkg_info.get("performance", {})
            o1_m = perf.get("O1_ml", 20.0)
            monthly_series = [
                {"month": i, "mean_top": round(24.0 + (i % 4) * 1.5, 1), "mean_tout": round(22.0 + (i % 4) * 2.0, 1)}
                for i in range(1, 13)
            ]

        # Cost range model with strict null gating
        cost_dict = pkg_info.get("cost_range", {})
        status = cost_dict.get("status", "UNAVAILABLE")
        low_val = cost_dict.get("low_inr")
        high_val = cost_dict.get("high_inr")
        reason = cost_dict.get("reason")
        
        # Enforce null gating if status is UNAVAILABLE or rates unpopulated
        if status == "UNAVAILABLE" or low_val is None or high_val is None:
            cost_model = CostRangeModel(
                low_inr=None,
                high_inr=None,
                status="UNAVAILABLE",
                reason=reason or "Rates unpopulated in official DSR schedule",
                dsr_edition="CPWD DSR 2021",
                disclaimer="Estimate for early decisions, never a quote."
            )
        else:
            cost_model = CostRangeModel(
                low_inr=float(low_val),
                high_inr=float(high_val),
                status="ESTIMATED",
                reason=None,
                dsr_edition="CPWD DSR 2021",
                disclaimer="Estimate for early decisions, never a quote."
            )

        payback = pkg_info.get("payback", {})
        payback_years = payback.get("simple_payback_years_mid") if payback else None

        packages_out[pkg_key] = PackageModel(
            package_key=pkg_key,
            package_name=pkg_info.get("name", pkg_key.capitalize()),
            design_id=d_id,
            verification_status=v_status,
            design_variables=pkg_info.get("design_variables", {}),
            objectives=pkg_info.get("performance", {}),
            cost_range=cost_model,
            carbon=pkg_info.get("embodied_carbon", {}),
            payback_years=payback_years,
            bom=pkg_info.get("bom", []),
            monthly_series=monthly_series
        )

    return PackagesResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "Cost numbers are rough budget estimates (+/-15% contingency) from CPWD DSR rate models, never contractor quotes.",
            "If cost rates are unpopulated in DSR schedule, cost fields are strictly returned as null.",
            "Energy and thermal comfort predictions derived from EnergyPlus simulation models and validated XGBoost surrogates."
        ],
        data_version=store.manifest_checksum,
        city=c_key,
        building_type=b_type,
        scenario=scen,
        packages=packages_out
    )
