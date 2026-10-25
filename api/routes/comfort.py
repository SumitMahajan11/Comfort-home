"""
api/routes/comfort.py

Endpoints for occupant comfort questionnaire schema and individualized profile evaluation.
Computes Comfort Fit Scores (0-100) and gap analysis against typical local building norms.
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
    QuestionnaireSchemaResponse,
    ProfileEvaluationRequest,
    ProfileEvaluationResponse,
    FitScoreResult
)
from src.comfort.profile import (
    QUESTIONNAIRE_SCHEMA,
    build_user_comfort_profile
)
from src.comfort.fit import compute_comfort_fit_score
from src.costs.packages import select_packages

router = APIRouter(tags=["Comfort Profile & Fit Score"])

def format_questionnaire(lang: str = "en") -> Dict[str, Any]:
    """Formats the questionnaire schema for the requested language (en or hi)."""
    is_hi = lang == "hi"
    questions_out = []
    for q in QUESTIONNAIRE_SCHEMA["questions"]:
        q_copy = {
            "id": q["id"],
            "number": q["number"],
            "title": q["title_hi"] if is_hi else q["title_en"],
            "type": q["type"],
            "default": q.get("default")
        }
        if "options" in q:
            opts = []
            for opt in q["options"]:
                label = opt.get("label_hi" if is_hi else "label_en", str(opt.get("value")))
                opts.append({
                    "value": opt["value"],
                    "label": label,
                    "target_class": opt.get("target_class")
                })
            q_copy["options"] = opts
        elif "min" in q and "max" in q:
            q_copy["min"] = q["min"]
            q_copy["max"] = q["max"]
            q_copy["unit"] = q.get("unit_hi" if is_hi else "unit_en", q.get("unit", ""))
        questions_out.append(q_copy)

    title = "उपयोगकर्ता थर्मल कम्फर्ट प्रोफाइल" if is_hi else "User Thermal Comfort Profile"
    desc = (
        "आपकी प्राथमिकताओं व संवेदनशीलता के आधार पर पैसिव इमारतों का अनुकूलन।"
        if is_hi else
        "Tailors candidate passive building designs to your sensitivity, priorities, and daily occupancy."
    )
    return {
        "language": lang,
        "title": title,
        "description": desc,
        "questions": questions_out
    }

# -----------------------------------------------------------------------------
# GET /questionnaire?lang=en|hi
# -----------------------------------------------------------------------------
@router.get("/questionnaire", response_model=QuestionnaireSchemaResponse)
def get_questionnaire(lang: str = Query("en", description="Language: 'en' or 'hi'")):
    """Returns the bilingual occupant comfort questionnaire schema."""
    store = get_store()
    schema = format_questionnaire(lang)
    return QuestionnaireSchemaResponse(
        confidence_tier="High",
        applicability={"schema_version": "1.0.0", "supported_languages": ["en", "hi"]},
        verification_status="verified",
        limitations=[
            "Questionnaire inputs map to post-hoc weighting multipliers.",
            "Locked baseline simulation assumptions A-001..A-007 are strictly preserved."
        ],
        data_version=store.manifest_checksum,
        language=schema["language"],
        title=schema["title"],
        description=schema["description"],
        questions=schema["questions"]
    )

# -----------------------------------------------------------------------------
# POST /profile/evaluate
# -----------------------------------------------------------------------------
@router.post("/profile/evaluate", response_model=ProfileEvaluationResponse)
def evaluate_profile(req: ProfileEvaluationRequest):
    """
    Evaluates user comfort profile against local typical baseline and 3 candidate packages.
    Returns 0-100 Comfort Fit Scores, comfort gain points, and dual-judge disagreement.
    """
    store = get_store()
    c_key = req.city.replace(" ", "_")
    if c_key not in CITY_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{req.city}' not supported.")

    b_type = req.building_type.lower()
    if b_type not in ALLOWED_BUILDING_TYPES:
        raise HTTPException(status_code=400, detail=f"Building type '{req.building_type}' not supported. Allowed: {ALLOWED_BUILDING_TYPES}")

    scenario = req.scenario.lower()
    if scenario not in ALLOWED_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Scenario '{req.scenario}' not supported. Allowed: {ALLOWED_SCENARIOS}")

    meta = CITY_METADATA[c_key]
    ref_metrics = meta["reference_r2"]

    # 1. Parse User Profile
    user_profile = build_user_comfort_profile(req.answers)

    # 2. Evaluate Typical Local Building (R2) Baseline
    baseline_eval = compute_comfort_fit_score(
        design_metrics=ref_metrics,
        reference_metrics=ref_metrics,
        user_profile=user_profile,
        city=c_key
    )

    typical_building_res = FitScoreResult(
        overall_fit_score=baseline_eval["fit_score"],
        comfort_subscore=baseline_eval["sub_scores"]["comfort_score"],
        energy_subscore=baseline_eval["sub_scores"]["energy_score"],
        cost_subscore=baseline_eval["sub_scores"]["cost_score"],
        comfort_gain_points=0.0,
        discomfort_reduction_pct=0.0,
        dual_judge={
            "ml_champion_o1": baseline_eval["dual_judges"]["O1_ml_champion_pct"],
            "adaptive_90_o1": baseline_eval["dual_judges"]["O1_adaptive_90_pct"],
            "disagreement_pts": baseline_eval["dual_judges"]["judge_disagreement_pts"]
        },
        explanation_en=baseline_eval["explanations"]["en"],
        explanation_hi=baseline_eval["explanations"]["hi"]
    )

    # 3. Load Pareto Designs & Select Packages
    p_designs = store.get_pareto(c_key, b_type)
    if not p_designs:
        raise HTTPException(status_code=500, detail=f"Pareto designs for '{c_key}' ({b_type}) not found in cache.")

    pkg_selection = select_packages(
        pareto_designs=p_designs,
        reference_design=ref_metrics,
        building_type=b_type,
        city=c_key,
        dsr_rates=store.dsr_rates,
        tariffs=store.tariffs
    )

    packages_out: Dict[str, FitScoreResult] = {}
    for p_key, p_data in pkg_selection.get("packages", {}).items():
        design_metrics = p_data.get("performance", {})
        fit_eval = compute_comfort_fit_score(
            design_metrics=design_metrics,
            reference_metrics=ref_metrics,
            user_profile=user_profile,
            city=c_key
        )
        packages_out[p_key] = FitScoreResult(
            overall_fit_score=fit_eval["fit_score"],
            comfort_subscore=fit_eval["sub_scores"]["comfort_score"],
            energy_subscore=fit_eval["sub_scores"]["energy_score"],
            cost_subscore=fit_eval["sub_scores"]["cost_score"],
            comfort_gain_points=fit_eval["comfort_gain_points"],
            discomfort_reduction_pct=fit_eval["discomfort_reduction_pct"],
            dual_judge={
                "ml_champion_o1": fit_eval["dual_judges"]["O1_ml_champion_pct"],
                "adaptive_90_o1": fit_eval["dual_judges"]["O1_adaptive_90_pct"],
                "disagreement_pts": fit_eval["dual_judges"]["judge_disagreement_pts"]
            },
            explanation_en=fit_eval["explanations"]["en"],
            explanation_hi=fit_eval["explanations"]["hi"]
        )

    return ProfileEvaluationResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "Fit Score is an individualized alignment index (0-100) weighting occupied hours inside comfort preferences.",
            "Dual judges: ML Champion argmax classifier and physical ASHRAE 55 Adaptive 90% model.",
            "Locked baseline assumptions A-001..A-007 are preserved in simulation baselines."
        ],
        data_version=store.manifest_checksum,
        city=c_key,
        building_type=b_type,
        scenario=scenario,
        user_profile_summary={
            "sensitivity": user_profile.get("sensitivity", {}),
            "normalized_weights": user_profile.get("normalized_weights", {}),
            "special_needs_flags": user_profile.get("special_needs_flags", [])
        },
        typical_local_building=typical_building_res,
        packages=packages_out
    )
