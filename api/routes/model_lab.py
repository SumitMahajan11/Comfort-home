"""
api/routes/model_lab.py

Endpoint for research auditability, S1-S4 success criteria scorecard,
comfort-model leaderboard, surrogate accuracy matrices, and phase evidence timeline.
"""

from typing import Dict, Any, List
from fastapi import APIRouter

from api.loader import get_store
from api.models import ModelLabResponse

router = APIRouter(tags=["Model Lab & Audit"])

@router.get("/model-lab", response_model=ModelLabResponse)
def get_model_lab():
    """
    Returns full research scorecard (S1-S4), comfort model leaderboard with 95% bootstrap CIs,
    surrogate accuracy matrices per typology, and chronological phase evidence links.
    """
    store = get_store()

    scorecard = {
        "S1": {
            "name": "ML Comfort Model vs Physical Adaptive 90% Baseline",
            "threshold": "ML macro-F1 must beat Adaptive 90% by >= 0.05 on group-held-out evaluation",
            "literal_result": "Champion Ablation_A3 achieved 0.4785 vs Adaptive 90% at 0.4939 (delta: -0.0154)",
            "status": "FAIL",
            "evidence_file": "reports/evidence/phase2_models_output.txt"
        },
        "S2": {
            "name": "Surrogate Model Accuracy",
            "threshold": "R2 >= 0.95 on held-out test designs across all 25 models",
            "literal_result": "23 of 25 targets passed R2 >= 0.95 (2 failures: Mumbai O1_ml R2=0.9406, Shimla warm_ml R2=0.9225; mean O2 R2=0.987)",
            "status": "PARTIAL",
            "evidence_file": "reports/evidence/phase4_surrogates_output.txt"
        },
        "S3": {
            "name": "Optimization vs Reference Baselines",
            "threshold": "Verified Pareto designs must beat BOTH R1 and R2 across all 3 objectives",
            "literal_result": "36 of 50 verified Pareto designs beat BOTH R1 and R2 across all 3 objectives (Jodhpur 7/10, Mumbai 7/10, New Delhi 6/10, Bengaluru 8/10, Shimla 8/10)",
            "status": "PASS",
            "evidence_file": "reports/evidence/phase5_optimization_output.txt"
        },
        "S4": {
            "name": "Interactive Dashboard & API Integration",
            "threshold": "Zero runtime EnergyPlus execution, verified automated test suite, response < 2s",
            "literal_result": "FastAPI + Next.js web application operating strictly on precomputed artifacts with 100% test pass rate",
            "status": "PASS",
            "evidence_file": "reports/evidence/phase6_apptest_output.txt"
        }
    }

    comfort_leaderboard = [
        {"model": "Adaptive 90% (Physical Baseline)", "macro_f1": 0.4939, "ci_95": "N/A (deterministic)", "rank": 1},
        {"model": "Ablation_A3_OutdoorTemp (ML Champion)", "macro_f1": 0.4785, "ci_95": "[0.4705, 0.4862]", "rank": 2},
        {"model": "XGBoost CC", "macro_f1": 0.4688, "ci_95": "[0.4608, 0.4764]", "rank": 3},
        {"model": "Random Forest", "macro_f1": 0.4651, "ci_95": "[0.4571, 0.4730]", "rank": 4},
        {"model": "Multi-Layer Perceptron (MLP)", "macro_f1": 0.4623, "ci_95": "[0.4542, 0.4701]", "rank": 5},
        {"model": "Logistic Regression", "macro_f1": 0.4410, "ci_95": "[0.4330, 0.4489]", "rank": 6}
    ]

    surrogate_matrices = {
        "house": store.get_surrogate_metrics("house") or {},
        "apartment": store.get_surrogate_metrics("apartment") or {},
        "commercial": store.get_surrogate_metrics("commercial") or {}
    }

    phase_timeline = [
        {"phase": 0, "name": "Data Audit", "status": "DONE", "evidence": "reports/data_audit.md"},
        {"phase": 1, "name": "EDA & Reference Baselines", "status": "DONE", "evidence": "reports/evidence/phase1_eda_calc_output.txt"},
        {"phase": 2, "name": "Clean Data & ML Comfort Models", "status": "DONE", "evidence": "reports/evidence/phase2_models_output.txt"},
        {"phase": 3, "name": "EnergyPlus Simulation Engine", "status": "DONE", "evidence": "reports/evidence/phase3_batch_execution_log.txt"},
        {"phase": 4, "name": "Coupling & XGBoost Surrogates", "status": "DONE", "evidence": "reports/evidence/phase4_surrogates_output.txt"},
        {"phase": 5, "name": "Multi-Objective NSGA-II Optimization", "status": "DONE", "evidence": "reports/evidence/phase5_optimization_output.txt"},
        {"phase": 6, "name": "SHAP Explainability & Dashboard", "status": "DONE", "evidence": "reports/evidence/phase6_shap_output.txt"},
        {"phase": 7, "name": "Packaging & Claims Audit", "status": "DONE", "evidence": "reports/evidence/phase7_claims_audit_output.txt"},
        {"phase": 8, "name": "Multi-Typologies, Future Climate & Norms", "status": "DONE", "evidence": "reports/evidence/phase8_pipeline_output.txt"}
    ]

    return ModelLabResponse(
        confidence_tier="High",
        applicability={"verified_criteria_count": 4, "tracked_models_count": len(comfort_leaderboard)},
        verification_status="verified",
        limitations=[
            "All metrics trace to literal command outputs saved in reports/evidence/.",
            "S1 failure is prominently reported and led to dual-judge architecture (Decision D-013)."
        ],
        data_version=store.manifest_checksum,
        scorecard_s1_s4=scorecard,
        comfort_model_leaderboard=comfort_leaderboard,
        surrogate_matrices=surrogate_matrices,
        phase_timeline=phase_timeline
    )
