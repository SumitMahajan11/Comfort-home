"""
api/routes/pareto.py

Endpoints for exploring the 100 non-dominated Pareto designs (with filtering and pagination)
and retrieving SHAP feature attributions with deterministic bilingual explanations.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query

from api.config import (
    CITY_METADATA,
    ALLOWED_CITIES,
    ALLOWED_BUILDING_TYPES
)
from api.loader import get_store
from api.models import (
    ParetoDesignsResponse,
    ParetoDesign,
    DesignExplainResponse
)

router = APIRouter(tags=["Pareto & Explainability"])

# -----------------------------------------------------------------------------
# GET /designs/pareto?city=&type=
# -----------------------------------------------------------------------------
@router.get("/designs/pareto", response_model=ParetoDesignsResponse)
def get_pareto_designs(
    city: str = Query("Jodhpur", description="Reference climate city"),
    type: str = Query("house", description="Building typology (shelter_v1, house, apartment, commercial)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    min_o1: Optional[float] = Query(None, description="Minimum discomfort hours % (O1_ml)"),
    max_o1: Optional[float] = Query(None, description="Maximum discomfort hours % (O1_ml)"),
    min_o2: Optional[float] = Query(None, description="Minimum HVAC energy kWh/m2/yr (O2)"),
    max_o2: Optional[float] = Query(None, description="Maximum HVAC energy kWh/m2/yr (O2)"),
    verified_only: bool = Query(False, description="Filter for EnergyPlus physically verified designs only"),
    min_wwr: Optional[float] = Query(None, description="Minimum window-to-wall ratio fraction"),
    max_wwr: Optional[float] = Query(None, description="Maximum window-to-wall ratio fraction")
):
    """
    Returns the 100 Pareto-optimal designs for a given city and building typology,
    with flexible multi-objective range filters and pagination.
    """
    store = get_store()
    c_key = city.replace(" ", "_")
    if c_key not in CITY_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found.")

    b_type = type.lower()
    if b_type not in ALLOWED_BUILDING_TYPES:
        raise HTTPException(status_code=400, detail=f"Building type '{type}' not supported.")

    raw_designs = store.get_pareto(c_key, b_type)
    if not raw_designs:
        raise HTTPException(status_code=500, detail=f"Pareto designs for '{c_key}' ({b_type}) not found in cache.")

    # Apply filters
    filtered: List[Dict[str, Any]] = []
    for d in raw_designs:
        o1 = d.get("O1_ml", 0.0)
        o2 = d.get("O2", 0.0)
        wwr = d.get("wwr", 0.15)
        is_ver = d.get("verified", False)

        if min_o1 is not None and o1 < min_o1:
            continue
        if max_o1 is not None and o1 > max_o1:
            continue
        if min_o2 is not None and o2 < min_o2:
            continue
        if max_o2 is not None and o2 > max_o2:
            continue
        if min_wwr is not None and wwr < min_wwr:
            continue
        if max_wwr is not None and wwr > max_wwr:
            continue
        if verified_only and not is_ver:
            continue

        filtered.append(d)

    total_count = len(filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged = filtered[start_idx:end_idx]

    designs_out = [ParetoDesign(**item) for item in paged]
    meta = CITY_METADATA[c_key]

    return ParetoDesignsResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "Pareto front generated via NSGA-II optimization (pop=100, gen=200, seed=42).",
            "Top knee-point and representative designs verified with direct EnergyPlus simulations."
        ],
        data_version=store.manifest_checksum,
        city=c_key,
        building_type=b_type,
        total_count=total_count,
        page=page,
        page_size=page_size,
        designs=designs_out
    )

# -----------------------------------------------------------------------------
# GET /designs/{id}/explain
# -----------------------------------------------------------------------------
@router.get("/designs/{id}/explain", response_model=DesignExplainResponse)
def explain_design(
    id: str,
    city: Optional[str] = Query(None, description="Optional city name"),
    type: Optional[str] = Query(None, description="Optional building typology")
):
    """
    Returns SHAP feature drivers and plain-language explanation templates (EN/HI)
    for a specific Pareto design.
    """
    store = get_store()

    # Infer city and type from ID if not provided
    c_key = city.replace(" ", "_") if city else None
    b_type = type.lower() if type else None

    if not c_key or not b_type:
        parts = id.split("_")
        if len(parts) >= 4 and parts[0] == "P":
            # e.g. P_Jodhpur_house_063 or P_New_Delhi_house_082
            if parts[1] == "New" and parts[2] == "Delhi":
                c_key = c_key or "New_Delhi"
                b_type = b_type or parts[3]
            else:
                c_key = c_key or parts[1]
                b_type = b_type or parts[2]

    c_key = c_key or "Jodhpur"
    b_type = b_type or "house"

    if c_key not in CITY_METADATA:
        c_key = "Jodhpur"
    if b_type not in ALLOWED_BUILDING_TYPES:
        b_type = "house"

    shap_data = store.get_shap(c_key, b_type)
    if not shap_data:
        raise HTTPException(status_code=404, detail=f"SHAP explanation data for '{c_key}' ({b_type}) not found.")

    # Find design variables if present in Pareto set
    p_designs = store.get_pareto(c_key, b_type) or []
    target_design = next((d for d in p_designs if d.get("pareto_id") == id), None)

    # Global/local SHAP drivers
    o1_shap = shap_data.get("O1_ml", {})
    sorted_drivers = sorted(o1_shap.items(), key=lambda kv: abs(kv[1]), reverse=True)

    top_drivers = []
    sentences_en = []
    sentences_hi = []

    friendly_names_en = {
        "roof_insulation_thickness": "Roof Insulation",
        "wall_insulation_thickness": "Wall Insulation",
        "roof_solar_absorptance": "Roof Cool Coating / Solar Absorptance",
        "wwr": "Window-to-Wall Ratio",
        "orientation": "Orientation",
        "shading_depth": "Overhang Shading Depth",
        "ventilation_ach": "Natural Ventilation Rate",
        "wall_mass_heavy": "Heavy Concrete Thermal Mass",
        "wall_mass_medium": "Medium Clay Brick Mass",
        "wall_mass_light": "Lightweight Wall Assembly"
    }

    friendly_names_hi = {
        "roof_insulation_thickness": "छत का थर्मल इन्सुलेशन",
        "wall_insulation_thickness": "दीवार का थर्मल इन्सुलेशन",
        "roof_solar_absorptance": "कूल-रूफ कोटिंग / सौर अवशोषण",
        "wwr": "खिड़की-से-दीवार अनुपात (WWR)",
        "orientation": "भवन की दिशा (ओरिएंटेशन)",
        "shading_depth": "छज्जा शेडिंग की गहराई",
        "ventilation_ach": "प्राकृतिक वेंटिलेशन दर",
        "wall_mass_heavy": "भारी कंक्रीट थर्मल मास",
        "wall_mass_medium": "मध्यम ईंट थर्मल मास",
        "wall_mass_light": "हल्की दीवार संरचना"
    }

    for feat_name, importance in sorted_drivers[:4]:
        name_en = friendly_names_en.get(feat_name, feat_name)
        name_hi = friendly_names_hi.get(feat_name, feat_name)
        val = target_design.get(feat_name) if target_design else None

        driver_info = {
            "feature": feat_name,
            "display_name_en": name_en,
            "display_name_hi": name_hi,
            "importance": round(importance, 4),
            "design_value": val
        }
        top_drivers.append(driver_info)

        if val is not None:
            sentences_en.append(f"{name_en} (value: {val}) is a primary driver, reducing thermal discomfort by {importance*100:.1f}%.")
            sentences_hi.append(f"{name_hi} (मान: {val}) एक प्रमुख कारक है, जो थर्मल असुविधा को {importance*100:.1f}% तक कम करता है।")
        else:
            sentences_en.append(f"{name_en} is a primary driver with relative importance {importance*100:.1f}%.")
            sentences_hi.append(f"{name_hi} एक प्राथमिक कारक है जिसका सापेक्ष प्रभाव {importance*100:.1f}% है।")

    meta = CITY_METADATA[c_key]
    return DesignExplainResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "SHAP values reflect TreeExplainer marginal contributions on surrogate XGBoost models.",
            "Attribution is predictive within surrogate parameter bounds, not guaranteed causal physics."
        ],
        data_version=store.manifest_checksum,
        design_id=id,
        city=c_key,
        building_type=b_type,
        top_drivers=top_drivers,
        sentences_en=sentences_en,
        sentences_hi=sentences_hi
    )
