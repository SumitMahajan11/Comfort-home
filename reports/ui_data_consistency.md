# UI Data Consistency Audit Report

**Date**: 2026-10-25  
**Audit Scope**: Web application (`web/`) consistency and traceability against pipeline ground truth (`data/processed/`, `reports/evidence/`).  
**Audited Items**: Items (a) through (f) specified in UI Consistency Protocol.

---

## 1. Audit Summary Table

| UI text | screen | where defined | true source file/column | matches? | action / resolution |
|---|---|---|---|---|---|
| `R1: 75.7% / 295.1 kWh` | Overview, City Explorer, Pareto, Recommender | `web/public/data/reference_results.json` (`city: "Jodhpur", reference_name: "R1_Lightweight"`) | `data/processed/reference_results.csv`: `O1_ml`=75.719178, `O2`=295.059493 | YES | Retained in typed `metrics.ts`; explicitly labeled as R1 Lightweight baseline with units `%` and `kWh/m²/yr`. |
| `R2: 76.4% / 281.9 kWh` | Overview, City Explorer, Pareto, Recommender | `web/public/data/reference_results.json` (`city: "Jodhpur", reference_name: "R2_Conventional"`) | `data/processed/reference_results.csv`: `O1_ml`=76.426941, `O2`=281.875828 | YES | Retained in typed `metrics.ts`; explicitly labeled as R2 Conventional baseline. |
| `"-39.08%"` (Discomfort Delta) | Overview, City Explorer, Pareto, Explain | `web/src/data/s3_evaluation.json`: `"margin_O1_ml_pct": 39.0753` | `data/processed/s3_evaluation_results.csv`: `margin_O1_ml_pct`=39.0753 (`P_Jodhpur_001` actual_O1_ml 36.6438% − R1 O1_ml 75.7192% = −39.0754 pp) | MATCHES (RESOLVED) | Relabeled unit from `%` to percentage points (`−39.1 pp` vs R1, `−39.8 pp` vs R2). Both R1 and R2 baselines are now explicitly displayed and labeled separately without mixing. |
| `"-240.5"` (Energy Delta) | Overview, City Explorer, Pareto, Recommender | `web/src/data/s3_evaluation.json`: `"margin_O2_kwh_per_m2": 240.4726` | `data/processed/s3_evaluation_results.csv`: `margin_O2_kwh_per_m2`=240.4726 (`P_Jodhpur_001` actual_O2 41.4032 − R2 O2 281.8758 = −240.4726 kWh/m²/yr) | MATCHES (RESOLVED) | Labeled references explicitly (`−240.5 kWh/m²/yr` vs R2, `−253.7 kWh/m²/yr` vs R1). Rendered explicit unit `kWh/m²/yr` across all screens. |
| `"75.72"` / `"76.43"` | Overview, City Explorer, Pareto Inspector | `web/src/data/reference_results.json` | `data/processed/reference_results.csv`: R1 `O1_ml`=75.719178 (75.72%), R2 `O1_ml`=76.426941 (76.43%) | YES | Retained. Formatted through typed `metrics.ts` to ensure identical rounding precision across all views. |
| `"36.64"` / `"41.40"` | Overview, City Explorer, Pareto Inspector | `web/src/data/pareto_Jodhpur.json` (`P_Jodhpur_001` actuals) | `data/processed/pareto_verification_results.csv`: `actual_O1_ml`=36.643836, `actual_O2`=41.403205 | YES | Retained. Formatted via typed `metrics.ts` as verified EnergyPlus simulation values. |
| `"38.2%"` (annual discomfort hours) | Recommender (Step 3 Climate: `web/src/app/recommender/page.tsx`) | Hard-coded string in `web/src/app/recommender/page.tsx` | Not found in `data/processed/` or `reports/evidence/` | MATCHES (RESOLVED) | Removed hard-coded string. Replaced with dynamic reference baselines from `reference_results.json` (R1: 75.7% ML / 76.4% Adapt; R2: 76.4% ML / 81.3% Adapt). |
| `"100.0%" Adaptive validity` | Recommender (Step 3: `web/src/lib/api.ts`) | Hard-coded ternary in `web/src/lib/api.ts` (`city === "Shimla" ? "73.97%" : "100.0%"`) | `data/processed/applicability.csv` col `adaptive_validity`: Jodhpur = 86.849315% (86.85%) | MATCHES (RESOLVED) | Replaced hard-coded string with dynamic value from `applicability.json` via `getCityApplicability()` (`86.85%` for Jodhpur, `74.0%` for Shimla). |
| `"68.4%" envelope validity` | Recommender (Step 3: `web/src/app/recommender/page.tsx`) | Hard-coded ternary in `web/src/app/recommender/page.tsx` (`... : 68.4`) | `data/processed/applicability.csv` col `all_features_in_envelope_pct`: Jodhpur = 53.907381% (53.91%) | MATCHES (RESOLVED) | Replaced hard-coded value with dynamic `all_features_in_envelope_pct` from `applicability.json` via `getCityApplicability()` (`53.9%` for Jodhpur). |
| `Wizard Step 5: P_Jodhpur_080 Discomfort "12.6%"` | Recommender (Step 5 Plan: `web/src/lib/api.ts`, `page.tsx`) | `web/src/lib/api.ts` assigns `row.O1_adapt` to `discomfort` without label | `data/processed/pareto_verification_results.csv`: `pred_O1_adapt`=12.6292%, `actual_O1_adapt`=15.6283%; `pred_O1_ml`=48.4533%, `actual_O1_ml`=47.4886% | MATCHES (RESOLVED) | Synchronized design metrics across screens: displays primary ML discomfort `O1_ml` (48.5% surrogate / 47.5% verified) matching Pareto Explorer, and explicitly labels adaptive comfort as `Adaptive: 12.6% (verified 15.6%)`. |
| `Wizard Step 5: Budget Discomfort "29.8%"` | Recommender (Step 5 Plan: `web/src/lib/api.ts`, `page.tsx`) | `web/src/lib/api.ts` assigns `row.O1_adapt` from `P_Jodhpur_001` | `data/processed/pareto_verification_results.csv`: `pred_O1_adapt`=29.8146%, `actual_O1_adapt`=30.9411%; `pred_O1_ml`=37.7343%, `actual_O1_ml`=36.6438% | MATCHES (RESOLVED) | Displays primary ML discomfort (37.7% surrogate / 36.6% verified) matching Pareto Explorer, with explicit Adaptive comfort secondary label. |
| `Wizard Step 5: Best Comfort Discomfort "11%"` | Recommender (Step 5 Plan: `web/src/lib/api.ts`, `page.tsx`) | `web/src/lib/api.ts` assigns sorted lowest `O1_adapt` | `data/processed/pareto_Jodhpur.json` col `pred_O1_adapt` | MATCHES (RESOLVED) | Unified with Pareto Explorer: sorted by primary ML discomfort `O1_ml` with explicit Adaptive secondary label. |
| `Wizard Step 5 Energy: 81.6 / 45.3 / 116.1` | Recommender (Step 5 Plan: `web/src/lib/api.ts`) | `web/src/lib/api.ts` formatPackage using `row.O2` | `data/processed/pareto_verification_results.csv` col `pred_O2`: P_Jodhpur_080=81.56, P_Jodhpur_001=45.33 | YES | Verified to match surrogate `pred_O2` of Pareto front designs. Retained and labeled as surrogate predicted energy with verified counterpart. |
| `Explain waterfall: -14.2, -8.6, -4.3, -3.8, -2.1` | Explain (`web/src/app/explain/page.tsx`) | Hard-coded array `localWaterfallDrivers` | Not present in any output artifact or SHAP dataset | MATCHES (RESOLVED) | Removed hard-coded array. Replaced with real TreeExplainer SHAP feature attributions loaded from `shap_summary.json` via `getSurrogateShapFeatures()`. |
| `"74% Too Hot"` | Recommender (Step 4 Questionnaire: `page.tsx`) | Hard-coded badge `Area: 74% Too Hot` | None in `data/processed/` | MATCHES (RESOLVED) | Removed fabricated percentage; displays `"Area: Not available"`. |
| `"38% Chilly"` | Recommender (Step 4 Questionnaire: `page.tsx`) | Hard-coded badge `Area: 38% Chilly` | None in `data/processed/` | MATCHES (RESOLVED) | Removed fabricated percentage; displays `"Area: Not available"`. |
| `"17.5 h/day"` | Recommender (Step 5 Comparison: `page.tsx`) | Hard-coded string in comparison table | None in `data/processed/` or `city_comfort_norms.json` | MATCHES (RESOLVED) | Replaced with `"Not available"`. |
| `"82%"` / `"Fan (82%)"` / `"Area: 82% Ceiling Fan"` | Recommender (`page.tsx`, `api.ts`) | Hard-coded string in `api.ts` and `page.tsx` | None in `data/processed/` | MATCHES (RESOLVED) | Replaced with `"Area: Not available"`. |
| `"30–45%"` (cooling electricity savings) | Recommender (Step 5: `page.tsx`) | Hard-coded text in conditional advice | None in `data/processed/` | MATCHES (RESOLVED) | Replaced with qualitative evidence-backed guidance without fabricated percentage ranges. |
| `"suppresses peak slab heat flux by 76%"` | Recommender (Step 5: `page.tsx`) | Hard-coded text in material description | None in `data/processed/` | MATCHES (RESOLVED) | Removed percentage claim; describes thermal barrier specifications directly. |
| `"cuts solar window loads by 68%"` | Recommender (Step 5: `page.tsx`) | Hard-coded text in fenestration description | None in `data/processed/` | MATCHES (RESOLVED) | Removed percentage claim; describes overhang projection specifications directly. |
| `Test counts: "13 passed, 1 skipped"` | About (`web/src/app/about/page.tsx`) | Hard-coded text in CLI code snippet block | Current pytest suite runs 44 items (43 passed, 1 skipped) in `tests/`; web test suite runs 14 tests in `web/tests/` | MATCHES (RESOLVED) | Removed hard-coded test count from reproduction snippet to eliminate drift across test runner versions. |

---

## 2. Verification Sources Cited
1. `data/processed/reference_results.csv`: R1 and R2 baseline benchmarks for all 5 climate zones.
2. `data/processed/s3_evaluation_results.csv`: Verified Pareto design margins and success criteria evaluation.
3. `data/processed/applicability.csv`: Domain applicability, boundary envelope checks, and adaptive model validity percentages.
4. `data/processed/pareto_verification_results.csv`: Ground-truth EnergyPlus simulation verification runs for selected Pareto points.
5. `data/processed/shap_summary.json`: TreeExplainer surrogate SHAP attributions for design feature impacts.
6. `reports/evidence/phase4b_surrogates_output.txt`: Literal command logs for surrogate accuracy and domain coverage.
7. `reports/evidence/phase5_optimization_output.txt`: Optimization logs and reference comparison tables.
8. `web/tests/consistency.test.ts`: Automated cross-screen objective consistency unit tests.
