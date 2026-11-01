# Data, Targets & Models Reference

This document catalogs the datasets, target variables, surrogate models, and verified accuracy metrics utilized in the `ClimateAdapt-Comfort` project. All tables and numerical metrics are directly extracted from verified repository data artifacts without manual estimation.

---

## 1. Datasets

### A. ASHRAE Global Thermal Comfort Database II (v2.1.0)
- **Source:** Center for the Built Environment (CBE), UC Berkeley (`docs/PROJECT_SPEC.md`).
- **Total Ingested Records:** 109,033 rows x 53 columns (`data/raw/ashrae_db_ii/db_metadata.csv`, `reports/phase1_eda.md:14`).
- **Complete-Case Analysis Subset:** 58,512 records containing complete thermal comfort sensation (`thermal_sensation`), air temperature (`ta`), radiant temperature (`tr`), relative humidity (`rh`), outdoor temperature (`t_out`), air velocity (`vel`), clothing insulation (`clo`), and metabolic rate (`met`) (`data/processed/comfort_clean.parquet`, `reports/evidence/phase2_cleaning_log.txt:7`).
- **India Field Survey Observations:** 6,700 rows (`data/processed/applicability.csv`, `reports/phase1_eda.md:46`).
- **Group-Aware Splitting:** 5-fold GroupKFold by `building_id` (422 unique buildings) and 4-fold Leave-One-Köppen-Group-Out (LOGO) cross-validation across Tropical (A), Arid (B), Temperate (C), and Continental (D) zones (`data/processed/splits.json`, `reports/evidence/splits_assertion_test.txt:28`).

### B. Indian Weather Stations (TMYx 2011–2025)
- **Source:** Climate.OneBuilding.org (`docs/PROJECT_SPEC.md:27`, `reports/climate_onebuilding_india_file_list.txt`).
- **Total Valid Indian Stations Cataloged:** 443 unique weather stations (`reports/station_registry.csv`).
- **Batch Scaling Coverage:** 435 stations cataloged after excluding the 5 original development cities and 3 benchmarks (`tools/run_batch.py`, `reports/station_registry.csv`).

---

## 2. Target Variables & Optimization Objectives

| Objective / Target | Name | Definition & Formulation | Target Variable Units | Source Code Reference |
| :--- | :--- | :--- | :---: | :--- |
| **Objective 1 (ML)** | `O1_ml` | Total annual occupant discomfort hours (%) scored by ML Champion (`Ablation_A3_OutdoorTemp`) | % (0–100) | `src/optimize/coupling.py:126` |
| **Component Target** | `warm_ml` | Annual fraction of hours where occupant feels warm/hot (Thermal Sensation > +0.5) | % (0–100) | `src/optimize/coupling.py:127` |
| **Component Target** | `cool_ml` | Annual fraction of hours where occupant feels cool/cold (Thermal Sensation < -0.5) | % (0–100) | `src/optimize/coupling.py:128` |
| **Objective 1 (Adaptive)** | `O1_adapt` | Total annual occupant discomfort hours (%) scored by ASHRAE 55 Adaptive 90% | % (0–100) | `src/optimize/coupling.py:64` |
| **Objective 2 (Energy)** | `O2` | Annual HVAC cooling & heating operational energy demand (kWh/m²/yr) | kWh/m²/yr | `src/sim/parse.py:72` |

---

## 3. Thermal Comfort Classifier Baseline vs ML Results

Evaluated on complete-case records (58,512 rows) across GroupKFold (GKF) and Leave-One-Köppen-Group-Out (LOGO) evaluations (`data/processed/baseline_results.json`, `data/processed/model_results.json`):

| Model / Baseline | Model Type | GKF Mean Macro-F1 | Mean Holdout (A+B) | LOGO Macro-F1 (Holdouts A, B, C, D) | 95% Confidence Interval (Holdouts A & B) | Result File |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Fanger PMV (ISO 7730)** | Physical Baseline | 0.4347 | 0.4681 | A (Trop): 0.4598, B (Arid): 0.4765, C (Temp): 0.4212, D (Cont): 0.3866 | N/A | `data/processed/baseline_results.json` |
| **Adaptive 80%** | Physical Baseline | 0.3900 | 0.4899 | A (Trop): 0.4174, B (Arid): 0.5625, C (Temp): 0.3450, D (Cont): 0.3342 | N/A | `data/processed/baseline_results.json` |
| **Adaptive 90% (Best Physical)** | Physical Baseline | 0.4390 | **0.4939** | A (Trop): 0.4565, B (Arid): 0.5313, C (Temp): 0.4060, D (Cont): 0.4066 | N/A | `data/processed/baseline_results.json` |
| LogisticRegression | Empirical ML | 0.4357 | 0.4274 | A (Trop): 0.4178, B (Arid): 0.4371, C (Temp): 0.4329, D (Cont): 0.3658 | A: [0.3781, 0.4426], B: [0.3598, 0.5179] | `data/processed/model_results.json` |
| RandomForest | Empirical ML | 0.4614 | 0.4501 | A (Trop): 0.4381, B (Arid): 0.4621, C (Temp): 0.4072, D (Cont): 0.3554 | A: [0.4006, 0.4622], B: [0.3870, 0.5323] | `data/processed/model_results.json` |
| XGBoost_CC | Empirical ML | 0.4649 | 0.4517 | A (Trop): 0.4304, B (Arid): 0.4730, C (Temp): 0.4190, D (Cont): 0.3603 | A: [0.3939, 0.4562], B: [0.4013, 0.5393] | `data/processed/model_results.json` |
| MLP | Empirical ML | 0.4538 | 0.4408 | A (Trop): 0.3479, B (Arid): 0.5338, C (Temp): 0.4134, D (Cont): 0.3477 | A: [0.3106, 0.3646], B: [0.4411, 0.6009] | `data/processed/model_results.json` |
| XGBoost_NaN_Tolerant_D004a | Empirical ML | 0.4580 | 0.4402 | A (Trop): 0.4252, B (Arid): 0.4552, C (Temp): 0.4111, D (Cont): 0.3547 | A: [0.3893, 0.4457], B: [0.3874, 0.5209] | `data/processed/model_results.json` |
| Ablation_A1_NoTr | Empirical ML | 0.4564 | 0.4473 | A (Trop): 0.4235, B (Arid): 0.4711, C (Temp): 0.4086, D (Cont): 0.3507 | A: [0.3792, 0.4587], B: [0.4015, 0.5336] | `data/processed/model_results.json` |
| Ablation_A2_CoolingType | Empirical ML | 0.4724 | 0.4706 | A (Trop): 0.4588, B (Arid): 0.4824, C (Temp): 0.4006, D (Cont): 0.3909 | A: [0.4136, 0.4895], B: [0.4107, 0.5487] | `data/processed/model_results.json` |
| **Ablation_A3_OutdoorTemp (ML Champion)** | Empirical ML | 0.4733 | **0.4785** | A (Trop): 0.4741, B (Arid): 0.4829, C (Temp): 0.3915, D (Cont): 0.4055 | A: [0.4247, 0.5103], B: [0.4075, 0.5533] | `data/processed/model_results.json` |

### Baseline vs ML Nuance & Evaluation Splits:
- **Primary Holdout A+B (Tropical & Arid climates):** Adaptive 90% achieves Macro-F1 = **0.4939**, outperforming ML Champion (`Ablation_A3_OutdoorTemp`, Macro-F1 = **0.4785**) by +0.0154. This constitutes the negative result reported in Criterion S1.
- **Confidence Interval Overlap:** On Holdout A, ML Champion is 0.4741 (95% CI: [0.4247, 0.5103]) vs Adaptive 90% 0.4565. On Holdout B, ML Champion is 0.4829 (95% CI: [0.4075, 0.5533]) vs Adaptive 90% 0.5313. Due to substantial variance across building clusters, individual fold confidence intervals exhibit overlap.
- **GroupKFold (Random Building Partitioning across all Köppen zones):** ML Champion achieves Macro-F1 = **0.4733**, leading Adaptive 90% (**0.4390**) by +0.0343.
- **Holdouts C (Temperate) & D (Continental / Cold):** Both models exhibit comparable performance (Holdout C: Adaptive 90% 0.4060 vs ML 0.3915; Holdout D: Adaptive 90% 0.4066 vs ML 0.4055).

---

## 4. XGBoost Surrogate Model Metrics & Comparison Table

Surrogate models trained across 5 development cities (5 targets per city = 25 models total). Evaluation conducted on held-out 20% test designs across baseline (initial design space) and augmented datasets (`data/processed/surrogate_metrics_comparison.csv`):

| City | designs in pool (base D_ / augmented total) | Target | Baseline R² | Baseline MAE | Baseline Top-10% Overlap | Baseline S2 Status | Augmented R² | Augmented MAE | Augmented Top-10% Overlap | Augmented S2 Status | S2 Threshold |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Jodhpur** | 990 / 1,485 | `O1_ml` | 0.9699 | 1.133 | 75.0% | **PASS** | 0.9753 | 0.991 | 76.7% | **PASS** | R² >= 0.95 |
| **Jodhpur** | 990 / 1,485 | `warm_ml` | 0.9731 | 1.628 | 80.0% | **PASS** | 0.9862 | 1.197 | 96.7% | **PASS** | R² >= 0.95 |
| **Jodhpur** | 990 / 1,485 | `cool_ml` | 0.9772 | 0.715 | 80.0% | **PASS** | 0.9891 | 0.548 | 90.0% | **PASS** | R² >= 0.95 |
| **Jodhpur** | 990 / 1,485 | `O1_adapt` | 0.9072 | 1.762 | 75.0% | **FAIL** | 0.9514 | 1.463 | 86.7% | **PASS** | R² >= 0.95 |
| **Jodhpur** | 990 / 1,485 | `O2` | 0.9760 | 5.506 | 85.0% | **PASS** | 0.9879 | 4.107 | 90.0% | **PASS** | R² >= 0.95 |
| **Mumbai** | 1,000 / 1,500 | `O1_ml` | 0.9107 | 1.360 | 75.0% | **FAIL** | 0.9406 | 1.274 | 83.3% | **FAIL** | R² >= 0.95 |
| **Mumbai** | 1,000 / 1,500 | `warm_ml` | 0.9412 | 1.359 | 50.0% | **FAIL** | 0.9765 | 0.957 | 33.3% | **PASS** | R² >= 0.95 |
| **Mumbai** | 1,000 / 1,500 | `cool_ml` | 0.9803 | 1.174 | 80.0% | **PASS** | 0.9853 | 1.011 | 93.3% | **PASS** | R² >= 0.95 |
| **Mumbai** | 1,000 / 1,500 | `O1_adapt` | 0.9386 | 1.908 | 90.0% | **FAIL** | 0.9606 | 1.765 | 83.3% | **PASS** | R² >= 0.95 |
| **Mumbai** | 1,000 / 1,500 | `O2` | 0.9773 | 3.710 | 95.0% | **PASS** | 0.9872 | 3.160 | 90.0% | **PASS** | R² >= 0.95 |
| **New_Delhi** | 999 / 1,499 | `O1_ml` | 0.9550 | 1.024 | 80.0% | **PASS** | 0.9726 | 0.767 | 83.3% | **PASS** | R² >= 0.95 |
| **New_Delhi** | 999 / 1,499 | `warm_ml` | 0.9802 | 1.054 | 100.0% | **PASS** | 0.9868 | 0.845 | 93.3% | **PASS** | R² >= 0.95 |
| **New_Delhi** | 999 / 1,499 | `cool_ml` | 0.9807 | 0.591 | 95.0% | **PASS** | 0.9897 | 0.478 | 83.3% | **PASS** | R² >= 0.95 |
| **New_Delhi** | 999 / 1,499 | `O1_adapt` | 0.9294 | 1.532 | 85.0% | **FAIL** | 0.9598 | 1.237 | 80.0% | **PASS** | R² >= 0.95 |
| **New_Delhi** | 999 / 1,499 | `O2` | 0.9866 | 5.097 | 90.0% | **PASS** | 0.9913 | 4.088 | 93.3% | **PASS** | R² >= 0.95 |
| **Bengaluru** | 999 / 1,499 | `O1_ml` | 0.9582 | 0.998 | 80.0% | **PASS** | 0.9768 | 0.756 | 83.3% | **PASS** | R² >= 0.95 |
| **Bengaluru** | 999 / 1,499 | `warm_ml` | 0.9601 | 0.488 | 85.0% | **PASS** | 0.9749 | 0.460 | 80.0% | **PASS** | R² >= 0.95 |
| **Bengaluru** | 999 / 1,499 | `cool_ml` | 0.9812 | 0.973 | 85.0% | **PASS** | 0.9859 | 0.833 | 93.3% | **PASS** | R² >= 0.95 |
| **Bengaluru** | 999 / 1,499 | `O1_adapt` | 0.9648 | 1.264 | 85.0% | **PASS** | 0.9716 | 1.122 | 96.7% | **PASS** | R² >= 0.95 |
| **Bengaluru** | 999 / 1,499 | `O2` | 0.9639 | 1.663 | 90.0% | **PASS** | 0.9713 | 1.701 | 93.3% | **PASS** | R² >= 0.95 |
| **Shimla** | 1,000 / 1,500 | `O1_ml` | 0.9709 | 0.580 | 90.0% | **PASS** | 0.9812 | 0.506 | 86.7% | **PASS** | R² >= 0.95 |
| **Shimla** | 1,000 / 1,500 | `warm_ml` | 0.9165 | 0.210 | 75.0% | **FAIL** | 0.9225 | 0.213 | 76.7% | **FAIL** | R² >= 0.95 |
| **Shimla** | 1,000 / 1,500 | `cool_ml` | 0.9657 | 0.702 | 85.0% | **PASS** | 0.9818 | 0.546 | 90.0% | **PASS** | R² >= 0.95 |
| **Shimla** | 1,000 / 1,500 | `O1_adapt` | 0.9532 | 0.992 | 85.0% | **PASS** | 0.9598 | 0.944 | 86.7% | **PASS** | R² >= 0.95 |
| **Shimla** | 1,000 / 1,500 | `O2` | 0.9983 | 4.129 | 100.0% | **PASS** | 0.9990 | 3.098 | 93.3% | **PASS** | R² >= 0.95 |

*\*Note on S2 Pass Criteria:* Success Criterion S2 is judged strictly on the statistical fit threshold ($R^2 \ge 0.95$) on held-out test designs. Top-10% overlap is a diagnostic ranking fidelity metric reported alongside $R^2$; models with $R^2 \ge 0.95$ (such as `Mumbai warm_ml` with $R^2 = 0.9765$ and $33.3\%$ overlap) satisfy the S2 pass criterion.

### S2 Success Criteria Reconciliation & Provenance:
- **S2 Criteria:** R² >= 0.95 on held-out test designs across all 25 surrogate models.
- **Initial Baseline Status (initial D_ design pool per city):** **19/25 Passed (PARTIAL)**.
  - *6 Initial Failures under 0.95:* `Jodhpur O1_adapt` (R² = 0.9072), `Mumbai O1_ml` (R² = 0.9107), `Mumbai warm_ml` (R² = 0.9412), `Mumbai O1_adapt` (R² = 0.9386), `New_Delhi O1_adapt` (R² = 0.9294), `Shimla warm_ml` (R² = 0.9165).
- **Augmented Retraining Status (augmented total design pool per city):** **23/25 Passed (PARTIAL)**.
  - *2 Remaining Failures under 0.95:* `Mumbai O1_ml` (R² = 0.9406), `Shimla warm_ml` (R² = 0.9225).
  - *4 Models Improved to PASS via Augmentation:* `Jodhpur O1_adapt` (0.9072 -> 0.9514), `Mumbai warm_ml` (0.9412 -> 0.9765), `Mumbai O1_adapt` (0.9386 -> 0.9606), `New_Delhi O1_adapt` (0.9294 -> 0.9598).
- **Provenance of `surrogate_metrics.csv` vs `claims_audit.py`:**
  - `data/processed/surrogate_metrics.csv` contains the active augmented state (23/25 pass).
  - `tools/claims_audit.py` reads `data/processed/surrogate_metrics.csv` directly, verifying 23/25 passed models and reporting PARTIAL status in exact alignment with the augmented metrics.