# CORRECTION NOTE: Surrogate Model Architecture and Implementation Class

**Date:** 2026-11-02  
**Scope:** Phase 4B Surrogate Models & Jodhpur Pilot Pipeline  
**Status:** Official Errata Record (Old evidence files remain untouched per AGENTS.md Rule 1)

---

## 1. Background & Discrepancy Found
In certain pilot discussions, narrative summaries, and high-level progress logs, the fast surrogate estimators were colloquially referred to as "CatBoost" models. 

An exhaustive codebase and artifact audit reveals that this naming was factually inaccurate. No CatBoost package or CatBoostRegressor model exists anywhere in the repository.

---

## 2. Codebase Ground Truth
The entire surrogate pipeline is built strictly on **XGBoost** (`XGBRegressor`):

1. **Model Definition & Training (`src/models/train_surrogates.py:16`):**
   ```python
   from xgboost import XGBRegressor
   ```
   Hyperparameter optimization via Optuna (`tune_surrogate_xgboost`) explicitly tunes XGBoost parameters:
   - `n_estimators`: 100 to 500
   - `max_depth`: 3 to 10
   - `learning_rate`: 0.01 to 0.20
   - `subsample`: 0.6 to 1.0
   - `colsample_bytree`: 0.6 to 1.0
   - `reg_alpha`: 1e-3 to 10.0
   - `reg_lambda`: 1e-3 to 10.0

2. **Pipeline Execution Scripts (`tools/run_jodhpur_pilot.py`, `tools/run_active_learning_jodhpur.py`):**
   Both scripts import and instantiate `XGBRegressor`.

3. **Serialized Artifacts (`models/pilot_jodhpur/*.joblib`, `models/surrogate_*.joblib`):**
   Inspection of the serialized model artifacts confirms:
   - `artifact['model'].__class__.__name__ == 'XGBRegressor'`
   - `artifact['model'].__class__.__module__ == 'xgboost.sklearn'`

---

## 3. Physical & Algorithmic Implication
The negative surrogate predictions observed in unconstrained Pareto optimization (e.g., $O_{1,\text{ml}} < 0\%$ or $O_2 < 0\text{ kWh/m}^2$) were previously described in informal notes as "polynomial extrapolation". 

In reality, because the model is an additive ensemble of gradient boosted trees:
$$\hat{y}(\mathbf{x}) = \text{base\_score} + \sum_{m=1}^M \eta f_m(\mathbf{x})$$
when an optimizer drives design variables into an under-sampled extreme corner (e.g., maximum insulation, minimal WWR, maximum shading, maximum night ventilation), the additive sum of negative gradient steps across hundreds of trees pushes the cumulative sum below zero. Clamping predictions to physical bounds ($[0, 100]$ for comfort discomfort and $[0, \infty)$ for energy) resolves the optimization anomaly.

---

## 4. Preservation of Historical Evidence
Per project rules (AGENTS.md Rule 1: *Never edit existing evidence files*), historical evidence files (e.g. `reports/evidence/jodhpur_pilot_execution_output_ground18.txt`, `reports/evidence/jodhpur_active_learning_report_ground18.txt`) remain completely untouched. This correction note stands as the canonical clarification of model class identity.
