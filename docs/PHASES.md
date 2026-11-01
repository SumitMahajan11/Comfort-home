# PHASES

A phase is complete only when every acceptance check has been run and its literal output saved in `reports/evidence/`. Status lives in `TRACKER.md`.

## Phase 0: Data audit (DONE)
Delivered: `reports/data_audit.md`, workspace split into `data/raw`, `data/processed`, `reports`, EnergyPlus smoke test passed.

## Phase 1: EDA and reference baselines (DONE, one follow-up)
Delivered: `reports/phase1_eda.md`. Follow-up: baselines were scored on different row subsets; re-scored on identical rows in Phase 2 (D-007).

## Phase 2: Clean data and comfort models
**Goal:** a calibrated comfort classifier, evaluated honestly against PMV and adaptive baselines.

Deliverables:
- `src/data/clean.py` produces `data/processed/comfort_clean.parquet` plus a cleaning log with the row count after each rule. Rules: drop rows missing any primary feature or TSV; drop `rh == 0` (1 row) and `clo == 0` (6 rows); keep high-`vel` and high-`met` rows but flag them.
- `data/processed/koppen_group_map.csv`: maps the 31 raw climate labels to groups A/B/C/D. **Human reviews this file before modeling continues.**
- `data/processed/splits.json`: GroupKFold by `building_id` and leave-one-group-out folds.
- `src/models/baselines.py`: PMV and adaptive (80% and 90%) on the same rows as the ML models.
- `src/models/train.py`: logistic regression, Random Forest, XGBoost, small MLP. Optuna tuning inside training folds only. Probability calibration. Class weights.
- Ablations A1, A2, A3 (see spec D-004).
- `reports/phase2_models.md` with per-split tables: macro-F1, per-class recall, confusion matrices, and an explicit S1 pass/fail.

Acceptance checks:
- Test asserts no `building_id` overlap between train and test for every split (output saved).
- Baselines and ML models show identical row counts per split.
- Re-running with seed 42 reproduces the macro-F1 values.

## Phase 3: Simulation engine
**Goal:** a robust, resumable batch pipeline that turns design variables into hourly indoor conditions.

Deliverables:
- `src/sim/template.idf` (single-zone shelter, parametrized by the spec's design variables) and a renderer.
- Free-running and ideal-loads modes (assumption A-005 for setpoints).
- `src/sim/sampler.py` (Latin hypercube, seed 42), `src/sim/runner.py` (parallel, resumable, skips completed runs, logs failures), `src/sim/parse.py` (hourly air temp, radiant temp, RH, loads).
- `data/processed/sim_runs.parquet` and `reports/phase3_sim.md`.

Acceptance checks:
- 10 random designs per city run with 0 severe and 0 fatal errors (`eplusout.err` summaries saved).
- Directional sanity: lower roof absorptance lowers mean free-running indoor temperature in Jodhpur, May to June.
- Full batch (about 10,000 runs) completes with at least 99% success; failures listed.

## Phase 4: Coupling and surrogates
**Goal:** objectives O1 and O2 computed for every simulated design, plus fast surrogates.

Deliverables:
- `src/optimize/coupling.py`: applies the best comfort model to hourly conditions (assumptions A-001 to A-004) and outputs O1 with warm/cool split.
- Applicability-domain check: share of simulated hours inside the comfort model's training envelope, per city (flags Shimla, D-011).
- Per-city XGBoost surrogates for O1, warm%, cool%, O2. Stretch: one global surrogate with leave-one-city-out.
- `reports/phase4_surrogates.md`.

Acceptance checks:
- Surrogate R2 and MAE on held-out designs per city (S2 pass/fail).
- Applicability table for all five cities.

## Phase 5: Optimization
**Goal:** Pareto-optimal designs per city, verified in EnergyPlus.

Deliverables:
- `src/optimize/nsga2.py` (pymoo, initial population 100, 200 generations, adjustable).
- Two reference shelters: R1 lightweight, uninsulated, high roof absorptance; R2 conventional medium-mass, uninsulated.
- Verification: top 10 Pareto designs per city re-simulated directly; surrogate versus actual objectives compared.
- Stretch: O3 embodied carbon (ICE factor x mass per m2 from EnergyPlus densities and thicknesses).
- `reports/phase5_optimization.md` with Pareto plots.

Acceptance checks:
- S3 pass/fail per city, from direct EnergyPlus results.
- Surrogate-to-actual error on verified designs reported.

## Phase 6: Explainability and dashboard
Deliverables: SHAP for the comfort model and the surrogates; Streamlit app (`src/app/app.py`) with city selection, design input or recommendation, Pareto view, warm/cool split, energy, top drivers, and applicability flag.

Acceptance checks: `streamlit run src/app/app.py` starts offline; screenshot saved in `reports/evidence/`; S4 pass/fail.

## Phase 7: Packaging and reporting (DONE, FROZEN v1.1)
Deliverables: README with one-command reproduction, `reports/final_results.md` built only from the tracker's evidence ledger, a limitations section matching the spec. Slides and write-ups come after this phase.

## Phase 8: Multi-Building Typologies & Future Climate (DONE)
**Goal:** Expand simulation and optimization pipeline beyond single-room shelters to House, Apartment, and Commercial typologies, plus morphed future-climate scenarios (+1.5C and +3.0C).

Deliverables:
- Parameterized EnergyPlus 26.2.0 text-templated IDFs (`src/sim/templates/{house,apartment,commercial}.idf`) with zoning and adiabatic party boundary conditions.
- Psychrometric climate morphing engine (`src/sim/morph_weather.py`) generating +1.5C and +3.0C warmer EPWs using the Belcher et al. method.
- Multi-typology smoke test (150/150 passed with 0 severe and 0 fatal errors, `reports/evidence/phase8_smoke_test_output.txt`).
- 3 directional sanity checks verified: roof absorptance in Jodhpur, wall insulation in Shimla, and apartment floor position excess cooling load (+8.64 kWh/m2).
- Precomputed Pareto frontiers across 45 parameter combinations (5 cities x 3 typologies x 3 climate scenarios).
- Cryptographic artifact export (`tools/export_artifacts.py` -> `data/export/manifest.json`, 160 files with SHA-256 checksums).

Acceptance checks:
- 150/150 smoke test simulations succeed without errors.
- Directional sanity checks pass physically.
- Manifest checksums pass validation.

## Phase 9: Materials & Cost-Range Engine (DONE)
**Goal:** Map optimized building envelope parameters to a physical Bill of Materials (BOM) with rough cost ranges derived from official CPWD Delhi Schedule of Rates (DSR), enforcing strict academic honesty.

Deliverables:
- `data/costs/materials.json`: 10 architectural assemblies with thermal properties, density, and embodied carbon coefficients from the Bath ICE database.
- `data/costs/dsr_rates.json`: CPWD DSR rate schedule with strict "TO BE FILLED" placeholder registry and null-gated enforcement (Decision D-025).
- Geometric Bill of Materials engine (`src/costs/bom.py`) and cost estimation engine (`src/costs/estimate.py`) with +/-15% contingency band (A-012).
- Validation auditor (`tools/validate_costs.py`) exiting with loud error code 1 if uncertified rates are present.
- Automated test suite (`tests/test_costs.py`, 4/4 passed).

Acceptance checks:
- Test suite passes all hand-calculated BOM geometric math.
- Validator blocks release and returns code 1 on unfilled rates.
- Packages return `status: "UNAVAILABLE"` with `null` INR values when rates are unpopulated.

## Phase 10: Comfort Fit Engine, Questionnaire & Area Norms (DONE)
**Goal:** Individualize decision-support through an occupant preference survey, comparing user preferences against empirical ASHRAE DB II regional norms to produce a Comfort Fit Score (0-100).

Deliverables:
- City comfort norms generator (`src/comfort/city_norms.py` -> `data/export/city_comfort_norms.json`): monthly EPW climate summaries, conventional reference building discomfort, and DB II occupant vote distributions by Koppen group (with explicit D-011 zero-vote disclosure for Shimla).
- Bilingual English/Hindi questionnaire schema and profile engine (`src/comfort/profile.py`).
- Comfort Fit Score engine (`src/comfort/fit.py`): deterministic 0-100 score combining discomfort reduction, energy savings vs R2, and occupant sensitivity weights (A-013, A-014).
- Worked examples across all 5 reference stations (`tools/generate_comfort_fit_examples.py`, `reports/evidence/comfort_fit_worked_examples.txt`).
- Automated test suite (`tests/test_comfort.py`, 3/3 passed).

Acceptance checks:
- Questionnaire choices correctly adjust user sensitivity multipliers without modifying simulation baselines.
- Comfort Fit Score is bounded within [0, 100].
- Shimla zero-vote limitation is transparently disclosed.

## Phase 11: Final Product Integration, E2E Verification & Thesis Compendium (DONE)
**Goal:** Deliver the complete ClimateAdapt-Comfort v2 web platform, audit all empirical research claims, and compile thesis defence documentation.

Deliverables:
- Read-only FastAPI service (`api/main.py`) with startup SHA-256 manifest validation and ReportLab builder PDF generator (`tests/test_api_v1.py`, 13/13 passed).
- Next.js 16 web application (`web/`) with 5-step guided wizard, expert studio, honest-labelling badges, and Playwright visual evidence screenshots (`web/tests/`, 10/10 passed).
- One-command startup script (`scripts/run_product.ps1` and `.sh`) verifying checksums, running cost validator, and launching services.
- Comprehensive End-to-End grid evaluation across all 45 combinations (`tests/test_e2e_product.py`, 135 packages audited, 100% null-gated costs verified, `reports/evidence/e2e_tests_output.txt`).
- Automated evidence claims audit (`tools/claims_audit.py` -> `reports/evidence/claims_audit_v2_output.txt`, 375/375 numerical claims 100% verified).
- Synthesis report (`reports/final_results_v2.md`) covering S1-S4 across typologies, fully vs lightly verified models, dual-judge divergence, future-climate limits, and prohibited uses.
- Thesis artefacts compendium (`docs/THESIS_ARTEFACTS.md`) with Mermaid architecture, data-flow, user-flow diagrams, master evidence table, and 2-page reproduction guide.

Acceptance checks:
- All 45 combinations tested; 100% of packages have valid verification status, confidence tier, and null-gated costs.
- 100% of numerical claims in thesis reports verified against literal evidence files.
- Startup script halts with loud error if cost rates are unverified unless run with `-AllowUnfilledCosts`.
