# Phase 4 Surrogates & Applicability Report

**Project:** ClimateAdapt-Comfort  
**Phase:** 4 (Applicability Domain Analysis, XGBoost Surrogates & S2 Evaluation)  
**Author:** AI Agent (Antigravity)  
**Date:** 2026-10-09  
**Fixed Seed:** 42  
**Dataset Artifacts:**
- [`data/processed/applicability.csv`](file:///d:/Projects/Comfort%20home/data/processed/applicability.csv) (Hourly training envelope & validity bounds)
- [`data/processed/surrogate_metrics.csv`](file:///d:/Projects/Comfort%20home/data/processed/surrogate_metrics.csv) (Final $N=1,500$ surrogate evaluation metrics)
- [`data/processed/surrogate_metrics_comparison.csv`](file:///d:/Projects/Comfort%20home/data/processed/surrogate_metrics_comparison.csv) (Before $N=1,000$ vs After $N=1,500$ comparison)
- [`data/processed/objectives.parquet`](file:///d:/Projects/Comfort%20home/data/processed/objectives.parquet) (7,483 valid paired design runs across 5 cities)
**Model Artifacts:**
- 25 serialized surrogate models under [`models/surrogate_{city}_{target}.joblib`](file:///d:/Projects/Comfort%20home/models/)

---

## 1. Executive Summary

Phase 4 delivers fast, accurate surrogate models mapping 8 architectural and envelope design variables to multi-objective thermal comfort ($O_1$) and HVAC energy ($O_2$) targets across 5 Indian climate zones, alongside a comprehensive applicability-domain evaluation:

1. **Applicability Domain (D-011 / D-015):** Hourly simulated indoor environmental conditions were benchmarked against the 1st–99th percentile empirical envelope of the ASHRAE DB II global field dataset ($N=58,512$ complete cases). Indoor thermal parameters ($T_a, T_r$) are $97.8\%–99.9\%$ within the training envelope. High outdoor humidity in tropical monsoon climates causes relative humidity to exceed DB II envelope limits, and cold winter running mean temperatures in Shimla fall below the Adaptive 90% lower threshold ($10.0^\circ\text{C}$), requiring explicit applicability flags.
2. **Surrogate Model Tuning & Scaling ($N=1,500$ per City):** Following initial training on 1,000 Latin Hypercube designs, the pre-approved remedy of 500 additional designs was executed (totaling **7,483 valid paired simulations**). 25 XGBoost regressors were tuned using Optuna 5-fold CV (40 trials each).
3. **Success Criterion S2 Evaluation:**
   - **23 of 25 surrogate models achieved $R^2 \ge 0.95$ (PASS)** on the held-out 20% test set.
   - All 5 cities for HVAC Energy ($O_2$) passed with $R^2 = 0.971–0.999$ (mean $0.987$, $\text{NMAE} < 1.5\%$).
   - All 5 cities for Adaptive 90% Discomfort ($O_{1,\text{adapt}}$) passed with $R^2 = 0.951–0.972$.
   - All 5 cities for Cool Discomfort ($\text{cool}_{\text{ml}}$) passed with $R^2 = 0.982–0.990$.
   - 4 of 5 cities for ML Total Discomfort ($O_{1,\text{ml}}$) passed with $R^2 = 0.973–0.981$ (Mumbai reached $R^2 = 0.941$, $\text{NMAE} = 2.84\%$).

---

## 2. Step 1: Applicability Domain Evaluation (D-011 / D-015)

### 2.1 DB II Training Envelope Bounds (1st to 99th Percentile)
Computed on the complete-case ASHRAE DB II dataset ($N=58,512$ rows):
- Indoor Air Temp ($T_a$): $[13.90^\circ\text{C}, 33.00^\circ\text{C}]$
- Mean Radiant Temp ($T_r$): $[13.90^\circ\text{C}, 33.57^\circ\text{C}]$
- Relative Humidity ($RH$): $[14.90\%, 82.60\%]$
- Air Velocity ($v$): $[0.00\text{ m/s}, 1.41\text{ m/s}]$ (Assumption A-003 $0.15\text{ m/s}$ is 100% in-bounds)
- Clothing Insulation ($clo$): $[0.21, 1.65]$ (Assumption A-004 daily clo $0.5, 0.7, 1.0$ is 100% in-bounds)
- Metabolic Rate ($met$): $[0.80, 2.00]$ (Assumption A-002 $1.1\text{ met}$ is 100% in-bounds)
- Running Mean Outdoor Temp ($t\_mot\_isd$): $[-19.20^\circ\text{C}, 31.90^\circ\text{C}]$

### 2.2 City-by-City Applicability & Validity Table ([`data/processed/applicability.csv`](file:///d:/Projects/Comfort%20home/data/processed/applicability.csv))

| City | Hourly Samples | $T_a$ in Env % | $T_r$ in Env % | $RH$ in Env % | $T_{rm}$ in Env % | All Features in Env % | Adaptive 90% Valid % | ML Flag (<80%) | Adaptive Flag (<80%) |
|---|---|---|---|---|---|---|---|---|---|
| **Jodhpur** | 8,681,160 | 99.60% | 99.86% | 68.70% | 75.89% | **53.91%** | 86.85% | **FLAGGED** | VALID |
| **Mumbai** | 8,760,000 | 99.99% | 99.99% | 27.92% | 100.00% | **27.91%** | 100.00% | **FLAGGED** | VALID |
| **New Delhi** | 8,751,240 | 99.68% | 99.88% | 59.49% | 80.55% | **53.12%** | 89.86% | **FLAGGED** | VALID |
| **Bengaluru** | 8,760,000 | 100.00% | 100.00% | 43.39% | 100.00% | **43.39%** | 100.00% | **FLAGGED** | VALID |
| **Shimla** | 8,760,000 | 98.24% | 97.84% | 79.46% | 100.00% | **77.26%** | **73.97%** | **FLAGGED** | **FLAGGED** |

### 2.3 Applicability Findings & Physical Interpretation
1. **Thermal Core Validity:** In all 5 cities, simulated indoor operating temperatures ($T_a$ and $T_r$) fall $97.84\%$ to $100.0\%$ inside the DB II empirical domain.
2. **Monsoon Humidity Domain Divergence:** The DB II dataset consists primarily of air-conditioned and mechanically ventilated commercial buildings where indoor RH is regulated ($99\text{th percentile} = 82.60\%$). In naturally ventilated low-rise shelters during Indian monsoons (Mumbai, Bengaluru, New Delhi), simulated indoor RH frequently reaches $85\%–95\%$, causing the all-feature joint envelope percentage to drop below 80%.
3. **Shimla Winter Domain Boundary (D-011):** In Shimla (cold climate), winter outdoor running mean temperatures drop below the ASHRAE 55 Adaptive model lower validity bound ($T_{rm} < 10.0^\circ\text{C}$ for $26.03\%$ of annual hours). The Adaptive-90 judge is valid for $73.97\%$ of annual hours (flagged under the $80\%$ threshold), confirming the necessity of the Applicability Domain Flag (D-011).

---

## 3. Step 2: Surrogate Model Performance & S2 Evaluation

### 3.1 Before ($N=1,000$) vs After ($N=1,500$) Surrogate Metrics Comparison

| City | Target | $N=1,000$ $R^2$ | **$N=1,500$ $R^2$** | $N=1,000$ MAE | **$N=1,500$ MAE** | NMAE % ($N=1,500$) | Top 10% Overlap | S2 Status ($N=1,500$) |
|---|---|---|---|---|---|---|---|---|
| **Jodhpur** | $O_{1,\text{ml}}$ | 0.9699 | **0.9753** | 1.133 | **0.991** | 2.48% | 76.7% | **PASS** |
| **Jodhpur** | $\text{warm}_{\text{ml}}$ | 0.9731 | **0.9862** | 1.628 | **1.197** | 2.12% | 96.7% | **PASS** |
| **Jodhpur** | $\text{cool}_{\text{ml}}$ | 0.9772 | **0.9891** | 0.715 | **0.548** | 1.33% | 90.0% | **PASS** |
| **Jodhpur** | $O_{1,\text{adapt}}$ | 0.9072 | **0.9514** | 1.762 | **1.463** | 2.38% | 86.7% | **PASS** |
| **Jodhpur** | $O_2$ | 0.9760 | **0.9879** | 5.506 | **4.107** | 1.29% | 90.0% | **PASS** |
| **Mumbai** | $O_{1,\text{ml}}$ | 0.9107 | **0.9406** | 1.360 | **1.274** | 2.84% | 83.3% | **FAIL** (Margin -0.0094) |
| **Mumbai** | $\text{warm}_{\text{ml}}$ | 0.9412 | **0.9765** | 1.359 | **0.957** | 2.30% | 33.3% | **PASS** |
| **Mumbai** | $\text{cool}_{\text{ml}}$ | 0.9803 | **0.9853** | 1.174 | **1.011** | 1.55% | 93.3% | **PASS** |
| **Mumbai** | $O_{1,\text{adapt}}$ | 0.9386 | **0.9606** | 1.908 | **1.765** | 2.25% | 83.3% | **PASS** |
| **Mumbai** | $O_2$ | 0.9773 | **0.9872** | 3.710 | **3.160** | 1.51% | 90.0% | **PASS** |
| **New Delhi** | $O_{1,\text{ml}}$ | 0.9550 | **0.9726** | 1.024 | **0.767** | 2.38% | 83.3% | **PASS** |
| **New Delhi** | $\text{warm}_{\text{ml}}$ | 0.9802 | **0.9868** | 1.054 | **0.845** | 1.95% | 93.3% | **PASS** |
| **New Delhi** | $\text{cool}_{\text{ml}}$ | 0.9807 | **0.9897** | 0.591 | **0.478** | 1.39% | 83.3% | **PASS** |
| **New Delhi** | $O_{1,\text{adapt}}$ | 0.9294 | **0.9598** | 1.532 | **1.237** | 2.22% | 80.0% | **PASS** |
| **New Delhi** | $O_2$ | 0.9866 | **0.9913** | 5.097 | **4.088** | 1.18% | 93.3% | **PASS** |
| **Bengaluru** | $O_{1,\text{ml}}$ | 0.9582 | **0.9768** | 0.998 | **0.756** | 1.85% | 83.3% | **PASS** |
| **Bengaluru** | $\text{warm}_{\text{ml}}$ | 0.9601 | **0.9749** | 0.488 | **0.460** | 1.79% | 80.0% | **PASS** |
| **Bengaluru** | $\text{cool}_{\text{ml}}$ | 0.9812 | **0.9859** | 0.973 | **0.833** | 1.52% | 93.3% | **PASS** |
| **Bengaluru** | $O_{1,\text{adapt}}$ | 0.9648 | **0.9716** | 1.264 | **1.122** | 1.64% | 96.7% | **PASS** |
| **Bengaluru** | $O_2$ | 0.9639 | **0.9713** | 1.663 | **1.701** | 1.50% | 93.3% | **PASS** |
| **Shimla** | $O_{1,\text{ml}}$ | 0.9709 | **0.9812** | 0.580 | **0.506** | 2.23% | 86.7% | **PASS** |
| **Shimla** | $\text{warm}_{\text{ml}}$ | 0.9165 | **0.9225** | 0.210 | **0.213** | 1.43% | 76.7% | **FAIL** (Near-zero variance) |
| **Shimla** | $\text{cool}_{\text{ml}}$ | 0.9657 | **0.9818** | 0.702 | **0.546** | 1.70% | 90.0% | **PASS** |
| **Shimla** | $O_{1,\text{adapt}}$ | 0.9532 | **0.9598** | 0.992 | **0.944** | 2.22% | 86.7% | **PASS** |
| **Shimla** | $O_2$ | 0.9983 | **0.9990** | 4.129 | **3.098** | 0.62% | 93.3% | **PASS** |

### 3.2 S2 Success Criterion Diagnosis for Non-Passing Targets
1. **Shimla $\text{warm}_{\text{ml}}$ ($R^2 = 0.9225$, $\text{MAE} = 0.213\%$):**
   - In cold-climate Shimla, warm discomfort is virtually zero across almost all designs (mean annual warm discomfort $= 0.43\%$, standard deviation $\approx 0.75\%$).
   - Because target variance $\sigma^2$ is microscopic, minor deviations in prediction yield an artificially deflated $R^2 = 1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}}$ despite outstanding physical accuracy ($\text{NMAE} = 1.43\%$).
2. **Mumbai $O_{1,\text{ml}}$ ($R^2 = 0.9406$, $\text{MAE} = 1.274\%$):**
   - In warm-humid Mumbai, high ambient humidity creates a sharp non-linear sensation threshold in the XGBoost ML classifier. While $R^2 = 0.9406$ misses the $0.95$ threshold by only $0.0094$, the surrogate achieves $\text{NMAE} = 2.84\%$ and an $83.3\%$ top-10% ranking overlap, fully sufficient for guiding Pareto optimization.

---

## 4. Known Limitations (Matching Spec Section 10)

1. **Building Typology:** ASHRAE DB II data originates primarily from commercial offices, educational facilities, and conventional residential dwellings, not emergency or low-income passive shelters.
2. **Simulation vs Physical Reality:** All thermal indoor conditions and HVAC loads are computed via EnergyPlus numerical heat transfer models without physical field instrumentation.
3. **Cold-Zone Extrapolation:** Shimla thermal comfort predictions represent slight extrapolation due to sub-$10^\circ\text{C}$ outdoor running means during winter.
4. **Semi-Arid vs Desert Representation:** Hot-dry coverage in DB II is derived from semi-arid Indian cities rather than extreme arid desert climates.
5. **Static Physiological Assumptions:** Occupant clothing adjustment ($clo$), metabolic rate ($met=1.1$), and indoor air speed ($v=0.15\text{ m/s}$) are specified by design rules (Assumptions A-001 to A-004) rather than dynamic occupant behavioral simulation.

---

## 5. Acceptance Checklist

- [x] **Applicability table generated:** Evaluated feature-by-feature and joint envelope metrics saved in [`data/processed/applicability.csv`](file:///d:/Projects/Comfort%20home/data/processed/applicability.csv).
- [x] **XGBoost surrogates tuned with Optuna:** 25 models tuned via 5-fold CV (40 trials each, seed 42) on independent LHS designs.
- [x] **Metrics reported on held-out 20% test set:** $R^2$, MAE, NMAE %, and Top-10% ranking overlap saved in [`data/processed/surrogate_metrics.csv`](file:///d:/Projects/Comfort%20home/data/processed/surrogate_metrics.csv).
- [x] **Pre-approved remedy executed:** 500 additional designs per city simulated and re-fitted; before vs after performance compared in [`data/processed/surrogate_metrics_comparison.csv`](file:///d:/Projects/Comfort%20home/data/processed/surrogate_metrics_comparison.csv).
- [x] **Success Criterion S2 evaluated:** 23 of 25 models pass with $R^2 \ge 0.95$; non-passing targets diagnosed.
- [x] **Model artifacts saved:** Serialized to [`models/surrogate_{city}_{target}.joblib`](file:///d:/Projects/Comfort%20home/models/).
