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

## Phase 7: Packaging and reporting
Deliverables: README with one-command reproduction, `reports/final_results.md` built only from the tracker's evidence ledger, a limitations section matching the spec. Slides and write-ups come after this phase.
