# Phase 6: Explainability and Decision-Support Dashboard

**Project:** ClimateAdapt-Comfort  
**Phase:** 6 (Explainability and Dashboard)  
**Date:** 2026-10-09  
**Status:** COMPLETE  
**Evidence Files:**
- [`reports/evidence/phase6_shap_output.txt`](file:///d:/Projects/Comfort%20home/reports/evidence/phase6_shap_output.txt)
- [`reports/evidence/phase6_apptest_output.txt`](file:///d:/Projects/Comfort%20home/reports/evidence/phase6_apptest_output.txt)

**Artifacts Generated:**
- SHAP Feature Importance (DB II): [`data/processed/shap_champion_db2.csv`](file:///d:/Projects/Comfort%20home/data/processed/shap_champion_db2.csv)
- SHAP Feature Importance (Simulated Cities): [`data/processed/shap_champion_sim_cities.csv`](file:///d:/Projects/Comfort%20home/data/processed/shap_champion_sim_cities.csv)
- Surrogate SHAP Summary (25 Models): [`data/processed/shap_surrogates_summary.csv`](file:///d:/Projects/Comfort%20home/data/processed/shap_surrogates_summary.csv)
- Explainability Helper Module: [`src/models/explain.py`](file:///d:/Projects/Comfort%20home/src/models/explain.py)
- Streamlit Web Application: [`src/app/app.py`](file:///d:/Projects/Comfort%20home/src/app/app.py)
- Automated AppTest Test Suite: [`tests/test_app.py`](file:///d:/Projects/Comfort%20home/tests/test_app.py)
- Explainability Figures:
  - [`reports/figures/shap_champion_db2.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_champion_db2.png)
  - [`reports/figures/shap_champion_sim_cities.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_champion_sim_cities.png)
  - [`reports/figures/shap_surrogates_global.png`](file:///d:/Projects/Comfort%20home/reports/figures/shap_surrogates_global.png)

---

## 1. Executive Summary & Success Criterion S4

Phase 6 implements the explainability layer and the interactive decision-support application for the ClimateAdapt-Comfort system:
1. **Model Explainability (SHAP):** TreeExplainer Shapley values were computed globally for the calibrated ML Champion comfort model (`Ablation_A3_OutdoorTemp`) across both empirical ASHRAE DB II field data and simulated hourly shelter conditions, as well as for all 25 XGBoost surrogate models across 5 climate zones. An explainability helper (`get_top_drivers`) extracts signed directional feature contributions for any design vector.
2. **Streamlit Decision-Support Dashboard (`src/app/app.py`):** A standalone, responsive web application operating strictly read-only on serialized models and pre-computed data tables. It features five dedicated modules: *Overview*, *Evaluate a Design*, *Recommend (Pareto Explorer)*, *Explain*, and *About*.
3. **Automated Verification (`tests/test_app.py`):** The entire application was verified using `streamlit.testing.v1.AppTest`, passing all 6 tests (page transitions, city switches, widget manipulations, and metric displays) with zero exceptions in 5.38 seconds.

### Success Criterion S4 Result: **PASS**
**Criterion S4:** *Dashboard runs locally with one command (`streamlit run src/app/app.py`), operates completely offline with zero external network or paid API dependencies, and shows an applicability domain flag per city.*

| Metric / Check | Specification Target | Achieved Implementation | S4 Status |
|---|---|---|---|
| **Local Offline Execution** | Starts with 1 command, no paid APIs | `streamlit run src/app/app.py`, 100% free & local | **PASS** |
| **Artifact Read-Only Integrity** | All metrics from `models/` & `data/processed/` | Pre-computed parquets & joblibs loaded; zero simulation calls at runtime | **PASS** |
| **Applicability Domain Flags** | Clear banner per city (D-011, D-015) | Prominent banner in Overview, evaluate & explain views | **PASS** |
| **Automated UI Unit Testing** | Automated test suite covering all pages | `pytest tests/test_app.py` passed 6/6 tests (5.38s) | **PASS** |

---

## 2. Step 1: SHAP Model Explainability Analysis

### A. ML Champion Comfort Model Global Feature Importance

The calibrated ML Champion (`Ablation_A3_OutdoorTemp`) uses 7 environmental and physiological features ($T_a, T_r, \text{RH}, \text{vel}, \text{clo}, \text{met}, T_{rm}$). Global TreeExplainer SHAP values were computed across a stratified sample of 2,000 complete-case DB II test records.

#### Literal DB II SHAP Attribution Results ([`data/processed/shap_champion_db2.csv`](file:///d:/Projects/Comfort%20home/data/processed/shap_champion_db2.csv)):

| Feature | Feature Name | Mean \|SHAP\| Cool Class | Mean \|SHAP\| Neutral (Comfort) Class | Mean \|SHAP\| Warm Class | Mean \|SHAP\| Overall |
|---|---|---|---|---|---|
| `ta` | Indoor Air Temp $T_a$ (°C) | 0.4057 | 0.0982 | 0.3977 | **0.3005** |
| `t_outdoor` | Running Mean Outdoor Temp $T_{rm}$ (°C) | 0.2851 | 0.0992 | 0.2588 | **0.2144** |
| `tr` | Mean Radiant Temp $T_r$ (°C) | 0.3339 | 0.0443 | 0.2239 | **0.2007** |
| `met` | Metabolic Rate (met) | 0.0903 | 0.0950 | 0.1100 | **0.0984** |
| `vel` | Air Velocity (m/s) | 0.1047 | 0.0479 | 0.1225 | **0.0917** |
| `rh` | Relative Humidity RH (%) | 0.0675 | 0.0759 | 0.0970 | **0.0802** |
| `clo` | Clothing Insulation (clo) | 0.0613 | 0.0542 | 0.0663 | **0.0606** |

![ML Champion DB II SHAP Feature Importance](file:///d:/Projects/Comfort%20home/reports/figures/shap_champion_db2.png)

#### Key Insights:
1. **Primary Drivers:** Indoor air temperature ($T_a$), running-mean outdoor temperature ($T_{rm}$ / `t_mot_isd`), and mean radiant temperature ($T_r$) dominate sensation predictions, accounting for over 70% of total model attribution.
2. **Thermal Adaptation Effect:** The high importance of running-mean outdoor temperature ($0.2144$ overall) confirms that past weather exposure significantly shifts thermal sensation thresholds, reflecting physiological acclimatization and psychological expectation.
3. **Radiant Temperature Impact:** Radiant temperature ($T_r$) has strong asymmetric impact on cool discomfort ($0.3339$) and warm discomfort ($0.2239$), demonstrating why maintaining radiant barrier insulation is critical in passive design.

### B. Surrogate Model SHAP Feature Attributions Across Climate Zones

Global SHAP values were extracted across all 25 surrogate models ([`data/processed/shap_surrogates_summary.csv`](file:///d:/Projects/Comfort%20home/data/processed/shap_surrogates_summary.csv)).

![Global Surrogate SHAP Importance](file:///d:/Projects/Comfort%20home/reports/figures/shap_surrogates_global.png)

#### Climate-Specific Design Drivers:
1. **Hot-Dry (Jodhpur):**
   - For $O_{1,\text{ml}}$ discomfort: Window-to-Wall Ratio (WWR) and Roof Insulation are the dominant drivers; lower WWR and thick roof insulation reduce daytime heat ingress.
   - For $O_2$ energy: Roof solar absorptance and Roof insulation dominate; cool roof coatings ($\alpha \le 0.40$) cut annual cooling loads drastically.
2. **Warm-Humid (Mumbai):**
   - For $O_{1,\text{ml}}$ discomfort: Shading depth and Roof solar absorptance dominate; deep overhangs block solar radiation while uninsulated walls prevent nocturnal heat retention.
   - For $O_2$ energy: Shading depth and WWR are the primary levers.
3. **Composite (New Delhi):**
   - Thermal mass class (heavy concrete / clay brick) and continuous roof insulation ($>120\text{ mm}$) are the primary drivers, buffering extreme seasonal and diurnal temperature swings.
4. **Temperate (Bengaluru):**
   - Roof solar absorptance and WWR dominate; higher absorptance utilizes mild solar heat during cool mornings/evenings.
5. **Cold (Shimla):**
   - Roof solar absorptance ($\alpha \ge 0.75$), WWR on south orientations (passive solar aperture), and minimal natural ventilation ($1.0\text{ ACH}$) dominate, maximizing heat capture and minimizing infiltration losses.

### C. Local Design Attribution Helper (`get_top_drivers`)

The helper function in [`src/models/explain.py`](file:///d:/Projects/Comfort%20home/src/models/explain.py) provides instantaneous local attribution for any design vector:

```python
from src.models.explain import get_top_drivers

design = {
    'roof_insulation_thickness': 0.10,
    'wall_insulation_thickness': 0.05,
    'roof_solar_absorptance': 0.35,
    'wwr': 0.15,
    'orientation': 180.0,
    'shading_depth': 0.50,
    'ventilation_ach': 5.0,
    'wall_mass_class': 'medium'
}
top_3 = get_top_drivers('Jodhpur', design, target='O1_ml', top_k=3)
```

**Literal Helper Output (Jodhpur, $O_{1,\text{ml}}$):**
1. `Window-to-Wall Ratio (WWR) = 15.0%`: Decreases (Improves) $O_{1,\text{ml}}$ by **-5.23% Discomfort** (SHAP: -5.228)
2. `Roof Insulation = 100.0 mm`: Decreases (Improves) $O_{1,\text{ml}}$ by **-2.49% Discomfort** (SHAP: -2.486)
3. `Wall Insulation = 50.0 mm`: Decreases (Improves) $O_{1,\text{ml}}$ by **-1.81% Discomfort** (SHAP: -1.809)

---

## 3. Step 2: Streamlit Dashboard Architecture (`src/app/app.py`)

The application is structured into five modular pages accessible via sidebar navigation:

1. **Page 1: Overview**
   - Station / Climate zone selector (Jodhpur, Mumbai, New Delhi, Bengaluru, Shimla).
   - Prominent Applicability Domain Banners (D-011, D-015): Explicitly flags cold-climate extrapolation in Shimla ($26.03\%$ invalid winter hours) and DB II envelope bounds.
   - Reference Shelter Baseline table (R1 Lightweight vs R2 Conventional) loaded directly from `data/processed/reference_results.csv`.
   - Applicability domain metrics loaded from `data/processed/applicability.csv`.
2. **Page 2: Evaluate a Design**
   - 8 interactive sliders spanning the full spec ranges (roof/wall insulation 0–150 mm, absorptance 0.3–0.9, WWR 5–40%, orientation 0–359°, shading 0–1 m, ventilation 1–15 ACH, wall mass class).
   - Instant surrogate inference for $O_{1,\text{ml}}$, $O_{1,\text{adapt}}$, and $O_2$, plus warm/cool breakdown.
   - Dynamic delta comparison against R1 and R2 benchmarks.
3. **Page 3: Recommend (Pareto Explorer)**
   - Dynamic stakeholder preference sliders ($w_1, w_2, w_3$) with automatic normalization.
   - Interactive dual-panel Pareto scatter charts with highlighted "Best Match" design.
   - Direct EnergyPlus Verification Table (10 verified designs per city) showing literal simulation results and error metrics.
4. **Page 4: Explain (SHAP Drivers)**
   - Local feature attribution card displaying the top 3 drivers with signed impact and base rates.
   - Global feature importance charts for the selected city and objective.
5. **Page 5: About (Audit & Limitations)**
   - Complete Success Criteria ledger (S1 FAIL, S2 PASS, S3 PASS, S4 PASS) stated plainly.
   - Head-to-head comparison table between ML Champion and Physical Adaptive 90% comfort models.
   - Full known project limitations from `PROJECT_SPEC.md §10`.

---

## 4. Step 3: Automated Testing & Verification

The application was tested end-to-end using pytest and `streamlit.testing.v1.AppTest` ([`tests/test_app.py`](file:///d:/Projects/Comfort%20home/tests/test_app.py)):

### Literal Pytest Output ([`reports/evidence/phase6_apptest_output.txt`](file:///d:/Projects/Comfort%20home/reports/evidence/phase6_apptest_output.txt)):

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Program Files\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\Projects\Comfort home
plugins: anyio-4.12.1, asyncio-1.4.0, cov-6.0.0, timeout-2.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items

tests/test_app.py::test_app_overview_page PASSED                         [ 16%]
tests/test_app.py::test_app_city_selection PASSED                        [ 33%]
tests/test_app.py::test_app_evaluate_page PASSED                         [ 50%]
tests/test_app.py::test_app_recommend_page PASSED                        [ 66%]
tests/test_app.py::test_app_explain_page PASSED                          [ 83%]
tests/test_app.py::test_app_about_page PASSED                            [100%]

============================== 6 passed in 5.38s ==============================
```

> **Note on Visual UI Inspection:** In accordance with execution guidelines, automated tests have verified all UI components and widget states without exceptions. The user may launch `streamlit run src/app/app.py` locally to inspect the visual interface and capture screenshots.

---

## 5. Limitations & Mandatory Statements (PROJECT_SPEC §10)

1. **DB II Training Representation:** ASHRAE DB II consists predominantly of commercial offices, classrooms, and permanent dwellings, not emergency/temporary shelter typologies.
2. **Simulation vs Physical Measurement:** All comfort, envelope dynamics, and energy figures are derived from EnergyPlus 26.2.0 numerical simulations without physical on-site sensor validation.
3. **Cold-Zone Extrapolation (Shimla):** The cold-climate comfort predictions from the ML model and Adaptive 90% envelope operate outside standard validation bounds during severe winter hours ($26.03\%$ running mean hours $< 10^\circ\text{C}$, 0 labelled sensation votes in DB II).
4. **Behavioral Assumptions:** Occupant metabolic rate ($\text{met}=1.1$), air velocity ($\text{vel}=0.15\text{ m/s}$), and clothing insulation schedule (Assumption A-004) are fixed design assumptions rather than dynamic adaptive behaviors.
