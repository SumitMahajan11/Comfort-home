# Final Synthesis Report: ClimateAdapt-Comfort

**Project:** ClimateAdapt-Comfort  
**Phase:** 7 (Packaging and Final Reporting)  
**Date:** 2026-10-09  
**Status:** COMPLETE & FROZEN (v1.1)  
**Master Evidence Files:** [`reports/evidence/`](file:///d:/Projects/Comfort%20home/reports/evidence/)  
**Tracker Reference:** [`docs/TRACKER.md`](file:///d:/Projects/Comfort%20home/docs/TRACKER.md)

---

## 1. Executive Summary & Success Criteria Ledger

The ClimateAdapt-Comfort project built and verified an end-to-end computational decision-support system for passive shelter design across 5 major Indian climate zones (Jodhpur, Mumbai, New Delhi, Bengaluru, Shimla). The pipeline integrates empirical thermal comfort models trained on the ASHRAE Global Thermal Comfort Database II (109,033 measurement rows `[E-001]`), 10,000 EnergyPlus 26.2.0 building simulations `[E-017]`, 25 gradient-boosted XGBoost surrogate regressors `[E-019]`, NSGA-II multi-objective optimization `[E-020]`, SHAP explainability `[E-021]`, and a standalone interactive Streamlit web application `[E-021]`.

### Success Criteria Summary Table

| Criterion | Target Requirement | Evaluation Split / Baseline | Achieved Literal Score | Target vs Achieved Margin | Verdict | Evidence ID |
|---|---|---|---|---|---|---|
| **S1: Comfort Model Accuracy** | ML model beats best physical baseline by $\ge +0.05$ macro-F1 | Leave-One-Köppen-Group-Out (LOGO) cross-validation on 58,512 complete-case test rows | Best ML: **0.4785** (`Ablation_A3_OutdoorTemp`) vs Best Baseline: **0.4939** (Adaptive 90%) | **-0.0154** (Best baseline leads by +0.0154) | **FAIL** (Reported honestly as negative result) | `[E-012]` |
| **S2: Surrogate Model Accuracy** | $R^2 \ge 0.95$ on held-out 20% test designs | Held-out 20% independent Latin-hypercube test split (7,483 valid designs total) | 23 of 25 models achieved $R^2 \ge 0.95$; Two failures: Mumbai $O_{1,\text{ml}}$ ($R^2 = 0.9406$) and Shimla $\text{warm\_ml}$ ($R^2 = 0.9225$); Mean $R^2$ on $O_2 = \mathbf{0.987}$ | 23/25 pass; Mean $R^2$ on $O_2$ exceeds 0.95 threshold by **+0.037** | **PARTIAL** (23/25 verified) | `[E-019]` |
| **S3: Direct Simulation Verification** | At least 1 verified Pareto design beats BOTH R1 and R2 reference shelters on $O_{1,\text{ml}}$, $O_{1,\text{adapt}}$, and $O_2$ | Direct EnergyPlus simulations (100 runs: 10 verified Pareto designs per city) vs R1 & R2 | Verified Pareto designs beat both reference shelters on all 3 objectives in **all 5 climate zones**: Jodhpur (7/10), Mumbai (7/10), New Delhi (6/10), Bengaluru (8/10), Shimla (8/10); 36/50 total | Substantial multi-objective gains (up to **-39.08%** discomfort and **-240.47 kWh/m²** energy) | **PASS** | `[E-020]` |
| **S4: Local Decision-Support Dashboard** | Runs locally with 1 command, completely offline, zero external/paid APIs, showing applicability flags | Streamlit application (`src/app/app.py`) verified via automated `AppTest` pytest suite (`tests/test_app.py`) | 6 of 6 automated UI tests passed in **5.38 seconds** with 0 errors; full read-only artifact execution | Zero runtime simulation overhead, 100% offline | **PASS** | `[E-021]` |

---

## 2. Comfort Modeling & Negative Result (Success Criterion S1)

### A. Data Cleaning & Complete-Case Filtering
- Raw ASHRAE DB II measurements: **109,033 rows** $\times$ **53 columns** across **809 buildings** `[E-001]`.
- Target Thermal Sensation Vote (TSV) 3-class balance: **48.74% neutral** (51,749 rows), **26.17% cool** (27,789 rows), and **25.08% warm** (26,633 rows) across **106,171 valid TSV rows** `[E-004]`.
- Complete-case filtering ($T_a, T_r, \text{RH}, \text{vel}, \text{clo}, \text{met}$ present): retained **58,512 rows** $\times$ **83 columns** across **617 buildings** (Set A) `[E-008]`. Set B without $T_r$ retained **82,789 rows** `[E-005]`.
- Clean complete-case dataset saved to `data/processed/comfort_clean.parquet` `[E-008]`.
- Cross-validation splits: 5-fold GroupKFold and 4 Leave-One-Köppen-Group-Out (LOGO) splits constructed over all 106,171 TSV rows with complete-case test sets (58,512 rows) and zero building leakage (`data/processed/splits.json`) `[E-010]`.

### B. Baseline vs Machine Learning Head-to-Head Comparison (Identical Rows)
All physical baselines and machine learning models were evaluated on 100% identical test rows across all splits with 1,000 bootstrap iterations for 95% confidence intervals `[E-011]`, `[E-012]`:

| Model / Baseline | Category | 5-Fold GroupKFold Macro-F1 (Mean ± Std) | 4-Fold LOGO Holdout A/B Macro-F1 (95% CI) | Evidence ID |
|---|---|---|---|---|
| **Adaptive 90% (ASHRAE 55)** | Physical Baseline | 0.4397 ± 0.0163 | **0.4939** [0.4907, 0.4971] | `[E-011]` |
| **Adaptive 80% (ASHRAE 55)** | Physical Baseline | 0.3900 ± 0.0177 | 0.4899 [0.4868, 0.4931] | `[E-011]` |
| **IMAC MM 90% (India Model)** | Physical Baseline | 0.3941 ± 0.0162 | 0.4820 [0.4788, 0.4853] | `[E-011]` |
| **IMAC NV 90% (India Model)** | Physical Baseline | 0.4312 ± 0.0175 | 0.4775 [0.4742, 0.4807] | `[E-011]` |
| **PMV (Fanger ISO 7730)** | Physical Baseline | 0.4332 ± 0.0152 | 0.4681 [0.4649, 0.4713] | `[E-011]` |
| **Ablation A3 (+ Running Mean Tout)** | ML Model (Champion) | **0.4733 ± 0.0194** | **0.4785** [0.4754, 0.4816] | `[E-012]` |
| **Ablation A2 (+ Cooling Type)** | ML Model | 0.4724 ± 0.0189 | 0.4706 [0.4674, 0.4737] | `[E-012]` |
| **XGBoost (Complete Cases)** | ML Model | 0.4665 ± 0.0199 | 0.4685 [0.4653, 0.4716] | `[E-012]` |
| **Random Forest** | ML Model | 0.4645 ± 0.0190 | 0.4697 [0.4665, 0.4729] | `[E-012]` |
| **Multilayer Perceptron (MLP)** | ML Model | 0.4571 ± 0.0185 | 0.4668 [0.4636, 0.4700] | `[E-012]` |
| **Ablation A1 (Without Tr)** | ML Model | 0.4580 ± 0.0196 | 0.4562 [0.4530, 0.4594] | `[E-012]` |
| **Logistic Regression** | ML Model | 0.4287 ± 0.0186 | 0.4443 [0.4411, 0.4474] | `[E-012]` |

### C. Analysis of the S1 Negative Result
1. **The Physical Adaptive Baseline Leads:** The physical Adaptive 90% comfort model achieved the highest out-of-distribution holdout performance (**0.4939** macro-F1), outperforming the ML Champion (**0.4785** macro-F1) by **+0.0154**.
2. **Why ML Failed to Beat Adaptive Physics on Climate Holdouts:** Field survey comfort votes in ASHRAE DB II exhibit high subjective variance across buildings and socio-cultural contexts. While tree-based ML captures complex indoor air-radiant interactions, the physical adaptive model's linear running-mean formulation ($T_{cmf} = 17.8 + 0.31 T_{rm}$) provides stronger inductive bias when extrapolating to entirely unseen Köppen climate zones.
3. **Dual Comfort Judge Solution (Decisions D-013, D-018):** Rather than discarding either model, both the probability-calibrated ML Champion (`models/champion_comfort_model.joblib` `[E-014]`) and the Physical Adaptive 90% model were retained as dual objective comfort judges throughout Phases 4, 5, and 6 `[E-018]`, `[E-020]`.

---

## 3. Applicability Envelope, Confidence Tiers & Judge Disagreement Analysis

### A. Per-City Applicability & Confidence Table (Decisions D-015, D-017)
Across all five simulated Indian climate zones, the ML Champion comfort model operates **below the 80% training envelope threshold** (27.91% to 77.26% of hours inside the DB II 1st–99th percentile feature envelope `[E-019]`), driven primarily by extreme monsoon relative humidity and dry desert conditions:

| City | Climate Zone | DB II Ta In-Envelope (%) | DB II RH In-Envelope (%) | All Features In-Envelope (%) | Adaptive 90% Valid Hours (%) | Dual-Judge Spearman ($r_s$) | Confidence Tier (D-017) |
|---|---|---|---|---|---|---|---|
| **Mumbai** | Warm-Humid | 99.99% | 27.92% | **27.91%** | **100.00%** | **0.945** | **Medium** ($r_s \ge 0.8$, Adapt $\ge 80\%$) |
| **Bengaluru** | Temperate | 100.00% | 43.39% | **43.39%** | **100.00%** | **0.943** | **Medium** ($r_s \ge 0.8$, Adapt $\ge 80\%$) |
| **Shimla** | Cold | 98.24% | 79.46% | **77.26%** | **73.97%** | **0.868** | **Low** (Adaptive valid $< 80\%$ in winter) |
| **New Delhi** | Composite | 99.68% | 59.49% | **53.12%** | **89.86%** | **0.195** | **Low** (Dual-judge rank disagreement) |
| **Jodhpur** | Hot-Dry | 99.60% | 68.70% | **53.91%** | **86.85%** | **0.109** | **Low** (Dual-judge rank disagreement) |

> **Mumbai Envelope Note:** In Mumbai, the ML Champion comfort model covers only **27.91%** of conditions (27.9%) due to intense coastal monsoon relative humidity exceeding the DB II 99th percentile training envelope boundary.

### B. Dual Comfort Judge Disagreement Analysis (Jodhpur and New Delhi)

#### 1. Literal Evidence:
- **Cold-Side Rank Agreement (~0.97):** Across both semi-arid and composite climates, the ML and Adaptive models agree strongly on cool/cold discomfort ranking. In Jodhpur, `cool_ml` (mean 30.32%) correlates with `cold_adapt` (mean 28.91%) with Pearson correlation **0.9676** (~0.97). In New Delhi, `cool_ml` (mean 36.88%) correlates with `cold_adapt` (mean 34.68%) with Pearson correlation **0.9765** (~0.97).
- **Warm-Side Discrepancy (0.83 to 0.88, 3.5 to 4x hours):** On the warm/hot discomfort side, the models diverge. In Jodhpur, `warm_ml` (mean 22.62%) is **4.08 times higher** (~4x) than `hot_adapt` (mean 5.54%), with Pearson correlation **0.8348** (0.83 to 0.88). In New Delhi, `warm_ml` (mean 14.29%) is **3.55 times higher** (~3.5x) than `hot_adapt` (mean 4.02%), with Pearson correlation **0.8787** (0.83 to 0.88).

#### 2. Clearly Labelled Hypotheses & Untested Mechanisms:
- **Hypothesis 1 (Adaptive Temperature Band Widening):** The physical Adaptive 90% model ($T_{cmf} = 17.8 + 0.31 T_{rm} \pm 2.5^\circ\text{C}$) expands the acceptable indoor operative temperature boundary up to 31°C during hot weather, categorizing the vast majority of daytime hours as comfortable.
- **Hypothesis 2 (Multi-Variable Physiological Sensitivity):** The ML Champion evaluates multi-variable physiological interactions (indoor drybulb, mean radiant temperature, air velocity, and dynamic clothing), penalizing extreme radiant loads during hot afternoons.
- **Hypothesis 3 (Humidity Penalty - UNTESTED):** In composite climates (New Delhi monsoon), elevated indoor relative humidity (>70% RH) may shift ML predicted probabilities toward the warm class. **Note on Humidity Hypothesis:** *This mechanism remains untested in the current pipeline* because ASHRAE DB II features are correlated in complete cases, and no isolated single-variable humidity ablation was executed on the hourly simulation time-series.
- **Ranking Consequence:** Because total discomfort $O_{1,\text{ml}} = \text{warm} + \text{cool}$ combines two seasonally opposing components with a substantial warm contribution, the overall design ranking diverges from $O_{1,\text{adapt}} = \text{hot} + \text{cold}$ (which is dominated almost purely by winter cold hours).

---

## 4. Simulation, Surrogates & Optimization (Phases 3, 4, 5)

### A. EnergyPlus Simulation Batch Execution `[E-017]`
- Single-zone passive shelter template parameterized in `src/sim/template.idf` and rendered via `src/sim/render.py` across 8 design variables `[E-016]`.
- Dispatched **10,000 EnergyPlus 26.2.0 simulation runs** (1,000 Latin-hypercube designs $\times$ 5 cities $\times$ 2 conditioning modes: free-running and ideal-loads HVAC) `[E-017]`.
- Batch completed in **3,999.4 seconds (66.7 minutes)** with **9,988 successful runs (99.88% completion rate)** and 0 severe or fatal simulation errors `[E-017]`.
- Filtered **4,988 strictly valid paired designs** (`data/processed/sim_runs.parquet`) `[E-018]`.

### B. Surrogate Model Accuracy (Success Criterion S2: PARTIAL) `[E-019]`
- Trained **25 XGBoost surrogate regressors** with Optuna 5-fold cross-validation (40 trials each, seed 42) on 7,483 valid designs (including pre-approved 500-design augmentation) `[E-019]`.
- **23 of 25 surrogate models met the $R^2 \ge 0.95$ threshold** (`data/processed/surrogate_metrics.csv`):
  - **Two Failures under $R^2 \ge 0.95$:**
    1. `Mumbai O1_ml`: test $R^2 = \mathbf{0.9406}$ (MAE = 1.27%)
    2. `Shimla warm_ml`: test $R^2 = \mathbf{0.9225}$ (MAE = 0.21%)
  - **Energy Surrogate Accuracy:** Mean $R^2$ on $O_2$ reached **0.987** across all 5 cities (Jodhpur 0.988, Mumbai 0.987, New Delhi 0.991, Bengaluru 0.971, Shimla 0.999).

### C. NSGA-II Optimization & Direct EnergyPlus Verification (Success Criterion S3: PASS) `[E-020]`
Two reference shelter baselines were parameterized in `src/optimize/references.py` (Assumptions A-006 R1 Lightweight, A-007 R2 Conventional) and directly simulated in EnergyPlus across all 5 cities `[E-020]`:
- **R1 Lightweight Reference (A-006):** No insulation ($0\text{ mm}$), light sheet wall mass, roof absorptance $0.85$, WWR $0.15$, shading $0.0\text{ m}$, ventilation $5.0\text{ ACH}$, orientation $0^\circ$ `[E-020]`.
- **R2 Conventional Reference (A-007):** Medium clay brick wall mass, no insulation ($0\text{ mm}$), roof absorptance $0.60$, WWR $0.15$, shading $0.0\text{ m}$, ventilation $5.0\text{ ACH}$, orientation $0^\circ$ `[E-020]`.

NSGA-II derived 100 non-dominated Pareto designs per city (`data/processed/pareto_{city}.parquet`) `[E-020]`. Ten representative designs per city (50 designs total) were re-simulated directly in EnergyPlus (100 physical runs) to evaluate S3 `[E-020]`:

#### Literal S3 Evaluation Results Table ([`data/processed/s3_evaluation_results.csv`](file:///d:/Projects/Comfort%20home/data/processed/s3_evaluation_results.csv)):

| City | Climate Zone | S3 Status | Verified Designs Beating Both R1 & R2 | Benchmark to Beat: $\min(\text{R1, R2})$ $[O_{1,\text{ml}}\% / O_{1,\text{ad}}\% / O_2]$ | Best Verified Pareto Design ID | Best Verified Actual $[O_{1,\text{ml}}\% / O_{1,\text{ad}}\% / O_2]$ | Actual Improvement Margins $[\Delta O_{1,\text{ml}} / \Delta O_{1,\text{ad}} / \Delta O_2]$ |
|---|---|---|---|---|---|---|---|
| **Jodhpur** | Hot-Dry (BWh) | **PASS** | **7 / 10** | $75.72\% \,/\, 49.89\% \,/\, 281.88\text{ kWh/m}^2$ | `P_Jodhpur_001` | $36.64\% \,/\, 30.94\% \,/\, 41.40\text{ kWh/m}^2$ | **-39.08% / -18.95% / -240.47 kWh/m²** `[E-020]` |
| **Mumbai** | Warm-Humid (Aw) | **PASS** | **7 / 10** | $65.95\% \,/\, 34.16\% \,/\, 199.99\text{ kWh/m}^2$ | `P_Mumbai_001` | $41.97\% \,/\, 4.99\% \,/\, 102.94\text{ kWh/m}^2$ | **-23.97% / -29.17% / -97.05 kWh/m²** `[E-020]` |
| **New Delhi** | Composite (Cwa) | **PASS** | **6 / 10** | $70.40\% \,/\, 50.76\% \,/\, 279.40\text{ kWh/m}^2$ | `P_New_Delhi_002` | $39.35\% \,/\, 31.91\% \,/\, 50.40\text{ kWh/m}^2$ | **-31.05% / -18.85% / -229.00 kWh/m²** `[E-020]` |
| **Bengaluru** | Temperate (Aw/Cwa) | **PASS** | **8 / 10** | $59.93\% \,/\, 39.27\% \,/\, 66.94\text{ kWh/m}^2$ | `P_Bengaluru_002` | $45.74\% \,/\, 14.89\% \,/\, 36.61\text{ kWh/m}^2$ | **-14.19% / -24.38% / -30.33 kWh/m²** `[E-020]` |
| **Shimla** | Cold (Cwb) | **PASS** | **8 / 10** | $77.36\% \,/\, 51.45\% \,/\, 279.54\text{ kWh/m}^2$ | `P_Shimla_001` | $67.95\% \,/\, 40.69\% \,/\, 74.08\text{ kWh/m}^2$ | **-9.42% / -10.76% / -205.46 kWh/m²** `[E-020]` |

### D. Direct Verification Error & Negative Energy Analysis
Examining the 50 directly verified Pareto designs in [`data/processed/pareto_verification_results.csv`](file:///d:/Projects/Comfort%20home/data/processed/pareto_verification_results.csv) against the 10% relative-error threshold:

1. **$O_{1,\text{ml}}$ Relative Error:** **50 of 50 designs (100.0%)** fell within $\le 10\%$ relative error:
   - Jodhpur: Mean Abs Err = $1.75\%$, Mean Rel Err = $3.46\%$ (10/10 within $\le 10\%$)
   - Mumbai: Mean Abs Err = $1.97\%$, Mean Rel Err = $3.74\%$ (10/10 within $\le 10\%$)
   - New Delhi: Mean Abs Err = $1.37\%$, Mean Rel Err = $2.50\%$ (10/10 within $\le 10\%$)
   - Bengaluru: Mean Abs Err = $1.68\%$, Mean Rel Err = $3.39\%$ (10/10 within $\le 10\%$)
   - Shimla: Mean Abs Err = $1.12\%$, Mean Rel Err = $1.48\%$ (10/10 within $\le 10\%$)
2. **$O_{1,\text{adapt}}$ Relative Error:**
   - Jodhpur: Mean Abs Err = $3.76\%$, Mean Rel Err = $12.38\%$ (5/10 within $\le 10\%$)
   - Mumbai: Mean Abs Err = $1.95\%$, Mean Rel Err = $31.48\%$ (4/10 within $\le 10\%$; high relative % due to low base actual discomfort $\sim 4.2\%$)
   - New Delhi: Mean Abs Err = $2.86\%$, Mean Rel Err = $6.72\%$ (10/10 within $\le 10\%$)
   - Bengaluru: Mean Abs Err = $1.97\%$, Mean Rel Err = $11.82\%$ (4/10 within $\le 10\%$)
   - Shimla: Mean Abs Err = $1.57\%$, Mean Rel Err = $4.50\%$ (8/10 within $\le 10\%$)
3. **$O_2$ Energy Relative Error & Negative Predictions:**
   - Jodhpur: Mean Abs Err = $2.97\text{ kWh/m}^2$, Mean Rel Err = $12.68\%$ (6/10 within $\le 10\%$)
   - Mumbai: Mean Abs Err = $6.81\text{ kWh/m}^2$, Mean Rel Err = $269.40\%$ (4/10 within $\le 10\%$; relative error inflated by actual near-zero energy $0.69\text{ kWh/m}^2$)
   - New Delhi: Mean Abs Err = $2.67\text{ kWh/m}^2$, Mean Rel Err = $7.16\%$ (7/10 within $\le 10\%$)
   - Bengaluru: Mean Abs Err = $4.35\text{ kWh/m}^2$, Mean Rel Err = $120.23\%$ (0/10 within $\le 10\%$; actual energy near-zero $0.74\text{ to }2.29\text{ kWh/m}^2$)
   - Shimla: Mean Abs Err = $6.08\text{ kWh/m}^2$, Mean Rel Err = $10.10\%$ (5/10 within $\le 10\%$)
4. **Optimizer Unclipped Surrogates & S3 Direct Simulation Independence:** On the unconstrained raw Pareto sets, **59 negative energy predictions** occurred out of 500 designs (32 in Mumbai, min $-9.36\text{ kWh/m}^2$; 27 in Bengaluru, min $-2.80\text{ kWh/m}^2$; 0 in Jodhpur, New Delhi, Shimla) because the NSGA-II optimizer evaluated raw, unclipped $O_2$ surrogate regressors. **Success Criterion S3 is completely unaffected by surrogate under-prediction or negative values**, because S3 evaluation rests entirely on direct, physical EnergyPlus simulations (where verified actual energy is strictly non-negative). Non-negative physical clipping at $0.0\text{ kWh/m}^2$ is enforced in user-facing surrogate wrappers (`src/models/explain.py`, `src/app/app.py`).

---

## 5. Explainability & Streamlit Dashboard (Phases 6 & 7)

### A. SHAP Global & Local Attribution `[E-021]`
- Computed global TreeExplainer SHAP values across DB II (`data/processed/shap_champion_db2.csv` `[E-021]`), simulated hours (`data/processed/shap_champion_sim_cities.csv` `[E-021]`), and 25 surrogate models (`data/processed/shap_surrogates_summary.csv` `[E-021]`).
- Implemented `get_top_drivers` in `src/models/explain.py`, providing local feature contributions and interpretations `[E-021]`.

### B. Interactive Dashboard (`src/app/app.py`) `[E-021]`
- Built a 5-page Streamlit web application operating strictly read-only on saved artifacts with zero external network or EnergyPlus runtime dependencies `[E-021]`.
- Automated test suite (`tests/test_app.py`) executed via `streamlit.testing.v1.AppTest`, passing all 6 tests in **5.38 seconds** with zero exceptions (`reports/evidence/phase6_apptest_output.txt`) `[E-021]`.

---

## 6. Complete Figures Index

| Figure | Description | File Path |
|---|---|---|
| **Pareto Frontier - Jodhpur** | Multi-objective Pareto front with EnergyPlus verified points & R1/R2 baselines | [`reports/figures/pareto_Jodhpur.png`](file:///d:/Projects/Comfort%20home/reports/figures/pareto_Jodhpur.png) |
| **Pareto Frontier - Mumbai** | Multi-objective Pareto front with EnergyPlus verified points & R1/R2 baselines | [`reports/figures/pareto_Mumbai.png`](file:///d:/Projects/Comfort%20home/reports/figures/pareto_Mumbai.png) |
| **Pareto Frontier - New Delhi** | Multi-objective Pareto front with EnergyPlus verified points & R1/R2 baselines | [`reports/figures/pareto_New_Delhi.png`](file:///d:/Projects/Comfort%20home/reports/figures/pareto_New_Delhi.png) |
| **Pareto Frontier - Bengaluru** | Multi-objective Pareto front with EnergyPlus verified points & R1/R2 baselines | [`reports/figures/pareto_Bengaluru.png`](file:///d:/Projects/Comfort%20home/reports/figures/pareto_Bengaluru.png) |
| **Pareto Frontier - Shimla** | Multi-objective Pareto front with EnergyPlus verified points & R1/R2 baselines | [`reports/figures/pareto_Shimla.png`](file:///d:/Projects/Comfort%20home/reports/figures/pareto_Shimla.png) |
| **ML Champion SHAP (DB II)** | Global feature importance on ASHRAE DB II complete cases | [`reports/figures/shap_champion_db2.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_champion_db2.png) |
| **ML Champion SHAP (Sim Cities)**| Global feature importance across 5 simulated Indian climate zones | [`reports/figures/shap_champion_sim_cities.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_champion_sim_cities.png) |
| **Surrogates SHAP (Global)** | Cross-city design variable importance for $O_{1,\text{ml}}$, $O_{1,\text{adapt}}$, and $O_2$ | [`reports/figures/shap_surrogates_global.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_surrogates_global.png) |

---

## 7. Known Limitations (PROJECT_SPEC §10)

1. **DB II Training Representation:** ASHRAE DB II consists predominantly of commercial offices, university classrooms, and permanent dwellings, not temporary or emergency shelter typologies.
2. **Simulation vs Physical Reality:** All envelope performance, temperature dynamics, and energy figures are derived from EnergyPlus 26.2.0 numerical simulations without physical on-site sensor validation.
3. **Cold-Zone Extrapolation (Shimla):** The cold-climate comfort predictions from the ML model and Adaptive 90% envelope operate outside standard validation bounds during severe winter conditions ($26.03\%$ running mean hours $< 10^\circ\text{C}$, 0 labelled sensation votes in DB II).
4. **Hot-Dry Semi-Arid Representation:** Hot-dry coverage in DB II originates mostly from semi-arid Indian field studies; true arid desert classes have few buildings.
5. **Behavioral Design Assumptions:** Clothing insulation schedule (A-004), metabolic rate ($\text{met}=1.1$, A-002), and indoor air velocity ($\text{vel}=0.15\text{ m/s}$, A-003) are assumed design constants rather than dynamic occupant behaviors.
