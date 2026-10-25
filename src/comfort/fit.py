"""
src/comfort/fit.py

Comfort Fit Score (0-100) and Area Gap Calculation Engine.
Evaluates how closely a candidate building design (or typical local baseline)
satisfies the specific occupant's comfort preferences, sensitivity, and priorities.

Key Principles:
- Uses dual judges (ML Champion + Physical Adaptive 90%) and transparently reports disagreement.
- Fully deterministic: Plain-language explanations are generated from templates (EN/HI),
  never from an external LLM, ensuring 100% reproducibility.
- Returns both the final score and full mathematical step breakdown for UI expert mode.
"""

from typing import Dict, Any, List, Optional
import numpy as np

def compute_comfort_fit_score(
    design_metrics: Dict[str, Any],
    reference_metrics: Dict[str, Any],
    user_profile: Dict[str, Any],
    cost_estimate: Optional[Dict[str, Any]] = None,
    city: str = "Jodhpur"
) -> Dict[str, Any]:
    """
    Computes the 0-100 Comfort Fit Score for a building design against user preferences.

    Args:
        design_metrics: dict with O1_ml, warm_ml, cool_ml, O1_adapt, O2
        reference_metrics: conventional reference building (R2) metrics
        user_profile: parsed profile from src/comfort/profile.py
        cost_estimate: optional cost range dict from src/costs/estimate.py
        city: city name

    Returns:
        Dictionary containing overall fit score, sub-scores, gap vs reference,
        dual judge disagreement, and bilingual explanation strings.
    """
    # 1. Extract performance metrics
    o1_ml = float(design_metrics.get("actual_O1_ml", design_metrics.get("O1_ml", 0.0)))
    warm_ml = float(design_metrics.get("actual_warm_ml", design_metrics.get("warm_ml", 0.0)))
    cool_ml = float(design_metrics.get("actual_cool_ml", design_metrics.get("cool_ml", 0.0)))
    o1_adapt = float(design_metrics.get("actual_O1_adapt", design_metrics.get("O1_adapt", 0.0)))
    o2 = float(design_metrics.get("actual_O2", design_metrics.get("O2", 0.0)))

    ref_o1_ml = float(reference_metrics.get("O1_ml", 35.0))
    ref_warm_ml = float(reference_metrics.get("warm_ml", 25.0))
    ref_cool_ml = float(reference_metrics.get("cool_ml", 10.0))
    ref_o1_adapt = float(reference_metrics.get("O1_adapt", 30.0))
    ref_o2 = float(reference_metrics.get("O2", 30.0))

    # 2. Dual judge consensus & disagreement
    o1_dual = (o1_ml + o1_adapt) / 2.0
    ref_o1_dual = (ref_o1_ml + ref_o1_adapt) / 2.0
    judge_disagreement = abs(o1_ml - o1_adapt)
    ref_judge_disagreement = abs(ref_o1_ml - ref_o1_adapt)

    # 3. User sensitivity penalties
    sens = user_profile.get("sensitivity", {})
    w_warm = float(sens.get("warm_discomfort_penalty", 1.0))
    w_cool = float(sens.get("cool_discomfort_penalty", 1.0))
    avg_w = (w_warm + w_cool) / 2.0

    # User-weighted discomfort calculation
    weighted_discomfort_ml = (w_warm * warm_ml) + (w_cool * cool_ml)
    weighted_discomfort_adapt = o1_adapt * avg_w
    weighted_discomfort_dual = 0.5 * weighted_discomfort_ml + 0.5 * weighted_discomfort_adapt

    # Reference weighted discomfort
    ref_weighted_ml = (w_warm * ref_warm_ml) + (w_cool * ref_cool_ml)
    ref_weighted_adapt = ref_o1_adapt * avg_w
    ref_weighted_dual = 0.5 * ref_weighted_ml + 0.5 * ref_weighted_adapt

    # 4. Component Sub-scores (0 to 100)
    # Comfort sub-score
    s_comfort = max(0.0, min(100.0, 100.0 - weighted_discomfort_dual))
    ref_s_comfort = max(0.0, min(100.0, 100.0 - ref_weighted_dual))

    # Energy sub-score (benchmark against reference building)
    if ref_o2 > 0:
        rel_energy_ratio = o2 / ref_o2
        if rel_energy_ratio <= 1.0:
            s_energy = min(100.0, 50.0 + 50.0 * (1.0 - rel_energy_ratio))
        else:
            s_energy = max(0.0, 50.0 - 50.0 * (rel_energy_ratio - 1.0))
    else:
        s_energy = 80.0
    ref_s_energy = 50.0 # reference baseline scores 50 on energy

    # Cost sub-score
    # If cost available: reward lower extra cost; if unavailable: neutral 70.0
    s_cost = 70.0
    ref_s_cost = 70.0
    if cost_estimate and cost_estimate.get("status") == "AVAILABLE":
        cost_mid = cost_estimate.get("cost_inr_mid", 0.0)
        # Higher cost marginally reduces score (10 pts per 100k INR above reference)
        s_cost = max(30.0, min(95.0, 80.0 - (cost_mid / 50000.0)))

    # 5. Priority weights
    weights = user_profile.get("normalized_weights", {
        "weight_comfort": 0.50,
        "weight_energy": 0.30,
        "weight_cost": 0.20
    })
    wc = float(weights.get("weight_comfort", 0.50))
    we = float(weights.get("weight_energy", 0.30))
    wt = float(weights.get("weight_cost", 0.20))

    # Overall Fit Score
    fit_score = round(wc * s_comfort + we * s_energy + wt * s_cost, 1)
    ref_fit_score = round(wc * ref_s_comfort + we * ref_s_energy + wt * ref_s_cost, 1)

    comfort_gain = round(fit_score - ref_fit_score, 1)
    discomfort_reduction = round(ref_o1_dual - o1_dual, 1)

    # 6. Deterministic Plain-Language Explanations (EN / HI)
    explanation_en, explanation_hi = _generate_explanation_strings(
        fit_score=fit_score,
        ref_fit_score=ref_fit_score,
        comfort_gain=comfort_gain,
        o1_dual=o1_dual,
        ref_o1_dual=ref_o1_dual,
        warm_ml=warm_ml,
        cool_ml=cool_ml,
        w_warm=w_warm,
        w_cool=w_cool,
        judge_disagreement=judge_disagreement,
        city=city
    )

    return {
        "fit_score": fit_score,
        "reference_fit_score": ref_fit_score,
        "comfort_gain_points": comfort_gain,
        "discomfort_reduction_pct": discomfort_reduction,
        "sub_scores": {
            "comfort_score": round(s_comfort, 1),
            "energy_score": round(s_energy, 1),
            "cost_score": round(s_cost, 1)
        },
        "dual_judges": {
            "O1_dual_judge_pct": round(o1_dual, 1),
            "O1_ml_champion_pct": round(o1_ml, 1),
            "O1_adaptive_90_pct": round(o1_adapt, 1),
            "warm_discomfort_ml_pct": round(warm_ml, 1),
            "cool_discomfort_ml_pct": round(cool_ml, 1),
            "judge_disagreement_pts": round(judge_disagreement, 1),
            "judges_agree": judge_disagreement <= 5.0
        },
        "reference_baseline_dual_judges": {
            "O1_dual_judge_pct": round(ref_o1_dual, 1),
            "O1_ml_champion_pct": round(ref_o1_ml, 1),
            "O1_adaptive_90_pct": round(ref_o1_adapt, 1),
            "judge_disagreement_pts": round(ref_judge_disagreement, 1)
        },
        "user_weighted_inputs": {
            "warm_penalty": round(w_warm, 2),
            "cool_penalty": round(w_cool, 2),
            "weights": {"comfort": wc, "energy": we, "cost": wt}
        },
        "explanations": {
            "en": explanation_en,
            "hi": explanation_hi
        }
    }

def _generate_explanation_strings(
    fit_score: float,
    ref_fit_score: float,
    comfort_gain: float,
    o1_dual: float,
    ref_o1_dual: float,
    warm_ml: float,
    cool_ml: float,
    w_warm: float,
    w_cool: float,
    judge_disagreement: float,
    city: str
) -> (str, str):
    """Generates deterministic, template-based explanation strings in English and Hindi."""
    primary_concern = "overheating" if w_warm > w_cool else ("chills/cold" if w_cool > w_warm else "both heat and cold")
    primary_concern_hi = "अत्यधिक गर्मी" if w_warm > w_cool else ("अत्यधिक ठंड" if w_cool > w_warm else "गर्मी और ठंड दोनों")

    if comfort_gain >= 10.0:
        perf_summary_en = f"This package achieves a strong Comfort Fit Score of {fit_score}/100, outperforming the local typical building by +{comfort_gain} points."
        perf_summary_hi = f"यह पैकेज {fit_score}/100 का मजबूत कम्फर्ट फिट स्कोर प्रदान करता है, जो स्थानीय सामान्य इमारत से +{comfort_gain} अंक बेहतर है।"
    elif comfort_gain > 0:
        perf_summary_en = f"This package achieves a Comfort Fit Score of {fit_score}/100, providing an improvement of +{comfort_gain} points over the area baseline."
        perf_summary_hi = f"यह पैकेज {fit_score}/100 का कम्फर्ट फिट स्कोर देता है, जो क्षेत्र के सामान्य स्तर से +{comfort_gain} अंक सुधार प्रदान करता है।"
    else:
        perf_summary_en = f"This design achieves a Comfort Fit Score of {fit_score}/100, performing comparably to the local conventional building ({ref_fit_score}/100)."
        perf_summary_hi = f"यह डिजाइन {fit_score}/100 का कम्फर्ट फिट स्कोर देता है, जो स्थानीय सामान्य इमारत ({ref_fit_score}/100) के समकक्ष है।"

    discomfort_en = f"Annual discomfort is reduced from {ref_o1_dual:.1f}% down to {o1_dual:.1f}%. Given your sensitivity to {primary_concern}, envelope passive cooling features are strongly aligned with your priorities."
    discomfort_hi = f"वार्षिक असुविधा समय {ref_o1_dual:.1f}% से घटकर {o1_dual:.1f}% रह जाता है। आपकी {primary_concern_hi} के प्रति संवेदनशीलता को देखते हुए, पैसिव डिज़ाइन आपकी प्राथमिकताओं के अनुकूल है।"

    if judge_disagreement > 6.0:
        judge_note_en = f" Dual-Judge Note: The empirical ML comfort model and physical Adaptive 90% model differ by {judge_disagreement:.1f} percentage points in {city}, reflecting climate humidity or boundary conditions."
        judge_note_hi = f" दोहरा मॉडल मूल्यांकन नोट: {city} में अनुभवजन्य एमएल मॉडल और भौतिक अनुकूली मॉडल के बीच {judge_disagreement:.1f}% का अंतर है, जो जलवायु की उमस व सीमा स्थिति को दर्शाता है।"
    else:
        judge_note_en = f" Dual-Judge Note: Both the empirical ML model and physical Adaptive 90% model agree closely (within {judge_disagreement:.1f} pts)."
        judge_note_hi = f" दोहरा मॉडल मूल्यांकन नोट: अनुभवजन्य एमएल मॉडल और भौतिक अनुकूली मॉडल दोनों अत्यधिक सहमत हैं ({judge_disagreement:.1f}% अंतर)।"

    full_en = f"{perf_summary_en} {discomfort_en}{judge_note_en}"
    full_hi = f"{perf_summary_hi} {discomfort_hi}{judge_note_hi}"

    return full_en, full_hi
