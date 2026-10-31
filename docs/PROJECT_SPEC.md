# PROJECT_SPEC: ClimateAdapt-Comfort
Status: FINALIZED
Finalized: 2026-10-25

Single source of truth. Changes only through the decision log in `TRACKER.md`.

## 1. Purpose and research question

Build a decision-support system for passive shelter design across Indian climate zones.

> Does a thermal-comfort model trained on global field data, coupled to building simulation, recommend shelter designs that reduce discomfort hours and energy demand, and does it beat PMV and adaptive-model baselines?

Contribution claimed: integration of comfort prediction, simulation, multi-objective optimization, and explanation in one pipeline. Nothing here is a proven result until verified in the tracker's evidence ledger. Results are simulation-based; there is no physical validation.

## 2. Scope

- One single-zone, low-rise passive shelter (fixed footprint, fixed occupancy), simulated in EnergyPlus.
- Five cities, one per Indian climate zone.
- Comfort model: classification of thermal sensation, trained on ASHRAE DB II.
- Optimization: NSGA-II over design variables, using a surrogate model, with final designs verified in EnergyPlus.
- Out of scope: personalized comfort models, cyclone work, physical measurements, multi-zone buildings, paid tools.

## 3. Data sources (all under `data/raw/`, immutable)

| Item | Path / location |
|---|---|
| DB II measurements | `ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz` (109,033 rows x 53 cols) |
| DB II metadata | `ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv` (809 rows), merge on `building_id` |
| DB II Dryad copy | `ashrae_db_ii_dryad_backup/`: backup only, do not use |
| Weather | `India_Weather_Extracted/` (1,760 EPW files, 476 stations) |
| ICE embodied carbon | `ice_database/ICE DB Educational V5.0 - Jun 2026.xlsx`, parsed table at `data/processed/ice_materials_extracted.csv` |
| EnergyPlus | `C:\EnergyPlusV26-2-0\energyplus.exe`, version 26.2.0-4bd7a1f26f |

Key DB II columns: `ta, tr, rh, vel, clo, met, thermal_sensation, t_out, t_out_isd, t_mot_isd, climate, country, building_type, cooling_type, building_id, record_id`.

## 4. Locked decisions

| ID | Decision |
|---|---|
| D-001 | Shelter: single zone, passive, free-running baseline. |
| D-002 | Cities and EPW files: Jodhpur `IND_RJ_Jodhpur.423390_ISHRAE2014.epw` (hot-dry); Mumbai `IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw` (warm-humid); New Delhi `IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw` (composite); Bengaluru `IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw` (temperate); Shimla `IND_HP_Shimla.420830_TMYx.epw` (cold). Use a TMYx file for Jodhpur if one exists; otherwise record the source difference. |
| D-003 | Target: 3 classes from `thermal_sensation`: cool (TSV < -0.5), neutral (-0.5 to 0.5), warm (TSV > 0.5). Rows with missing TSV are dropped. |
| D-004 | Primary features: `ta, tr, rh, vel, clo, met` (complete cases, 58,512 rows). Ablations: A1 without `tr` (82,789 rows); A2 add `cooling_type`; A3 add `t_out` or `t_mot_isd` (about 40k rows). |
| D-005 | Never impute `tr = ta`. Radiant temperature is exactly what roof and wall design changes; imputing it removes the effect the project optimizes. |
| D-006 | Evaluation: GroupKFold by `building_id`, plus leave-one-Köppen-major-group-out (A tropical, B arid, C temperate, D continental) after normalizing the 31 raw `climate` labels via a reviewed mapping file. 12 of 31 raw classes have fewer than 3 buildings, so raw-class holdout is invalid. |
| D-007 | Baselines (PMV, adaptive 80% and 90%) are scored on the identical rows as the ML models in every split. Phase 1 baseline numbers used different row subsets and are reference only. |
| D-008 | Simulation: text-templated IDF derived from the installed example files; no eppy. About 1,000 Latin-hypercube designs per city, two modes (free-running, ideal-loads), about 10,000 runs. |
| D-009 | Objectives: O1 = % occupied hours predicted non-neutral (also report warm% and cool% separately). O2 = annual ideal-loads energy, kWh/m2. Stretch O3 = embodied carbon from ICE (thermal properties come from the EnergyPlus material library, not ICE). |
| D-010 | Stack: Python, pandas, scikit-learn, XGBoost, Optuna, pymoo, SHAP, Streamlit. All free, all local. |
| D-011 | DB II has no labelled sensation votes for the Shimla building (460 rows, all TSV missing). Shimla results must carry an applicability-domain flag. |
| D-012 | Champion comfort model selection based on 5-fold GroupKFold CV macro-F1 on complete-case rows (`Ablation_A3_OutdoorTemp` achieves 0.4733 CV mean, 0.4785 Holdout mean). |
| D-013 | Retain both ML Champion (score 0.4785) and Physical Adaptive 90% (score 0.4939) as dual comfort judges for simulation coupling and optimization. |
| D-014 | Strict paired-run completeness: drop a (city, design) pair if either free-running or ideal-loads simulation mode fails. |
| D-015 | Applicability domain defined by 1st-99th percentile of DB II training features; flag cities under 80% validity threshold. |
| D-016 | Rank design variable sensitivity by XGBoost gain / permutation importance per climate zone. |
| D-017 | Decision-support confidence tiers: Medium confidence requires dual-judge Spearman $r_s \ge 0.8$ AND Adaptive 90% validity $\ge 80\%$; all other cities assigned Low confidence. |
| D-018 | Dual comfort judge hourly coupling: discrete argmax prediction $\hat{y}_t \in \{0=\text{cool}, 1=\text{neutral}, 2=\text{warm}\}$ for $O_{1,\text{ml}}$ alongside ASHRAE 55 Adaptive 90% comfort band for $O_{1,\text{adapt}}$. |
| D-019 | Running mean outdoor temperature ($t\_mot\_isd$) computed from EPW using exact ASHRAE 55 / DB II 7-day exponential formula ($\alpha=0.8$). |
| D-020 | CPWD DSR Rate Schedule & Cost Engine: envelope cost ranges derived strictly from verified CPWD Delhi Schedule of Rates (DSR 2021/2023) items with +/-15% contingency; never presented as contractor quotes. |
| D-021 | ClimateAdapt-Comfort v2 decoupled architecture: Next.js frontend + FastAPI backend serving PRECOMPUTED simulation artifacts only; zero runtime EnergyPlus calls; 5-step user flow. |
| D-022 | Multi-Building Typology Templates: parameterized EnergyPlus text-templated IDFs for House (60 m2, 3 zones), Apartment (55 m2, 2 zones, adiabatic party boundaries), and Commercial (80 m2, internal plug loads). |
| D-023 | Future-Climate EPW Morphing: monthly mean dry-bulb temperature shifting (+1.5C and +3.0C) with Magnus-Tetens psychrometric proportional humidity conservation. |
| D-024 | Precomputed API Export Schema (`data/export/`): all Pareto designs, references, monthly profiles, and SHAP drivers serialized with cryptographic `manifest.json` SHA-256 checksums. |
| D-025 | Strict Null-Gating Policy for Cost Rates: unpopulated CPWD DSR items remain explicitly `null` with status `"UNAVAILABLE"`; system blocks startup unless explicitly run with `-AllowUnfilledCosts`. |
| D-026 | Area Comfort Norms & User Comfort Fit Scoring Engine (`src/comfort/`): regional EPW summaries, reference discomfort profiles, and DB II occupant preference distributions by Koppen group. |
| D-027 | Read-Only FastAPI Production Service (`api/`): startup SHA-256 manifest validation, versioned `/api/v1` routes, Pydantic v2 schemas, and ReportLab builder-ready vector PDF generation. |
| D-028 | ClimateAdapt-Comfort v2 Web Client (`web/`): Next.js 16 (App Router) + TypeScript + Tailwind CSS with 5-step guided wizard, expert architectural studio, bilingual English/Hindi localization, and honest-labelling badges. |

## 5. Scenario assumptions (change only via decision log)

- A-001 Occupancy: 24 h/day (shelter). A-002 `met` = 1.1. A-003 `vel` = 0.15 m/s.
- A-004 `clo` rule from daily mean outdoor temperature: 0.5 if >= 25 C; 0.7 if 15 to 25 C; 1.0 if < 15 C.
- A-005 Ideal-loads setpoints for O2: cooling 26 C, heating 20 C.

## 6. Design variables (initial ranges; adjustable via decision log)

| Variable | Range |
|---|---|
| Roof insulation thickness | 0 to 150 mm |
| Wall insulation thickness | 0 to 150 mm |
| Wall mass class | light / medium (clay brick) / heavy (concrete) |
| Roof solar absorptance | 0.3 to 0.9 |
| Window-to-wall ratio | 5% to 40% |
| Orientation | 0 to 359 degrees |
| Shading depth | 0 to 1.0 m |
| Natural ventilation | 1 to 15 air changes/hour |

## 7. Pipeline

```
DB II -> clean -> comfort model (calibrated) ---------------+
                                                            v
design vars + EPW -> EnergyPlus (2 modes) -> hourly indoor conditions
                                                            v
        hourly class probabilities -> O1 (discomfort hours), O2 (energy)
                                                            v
                  surrogate models -> NSGA-II -> Pareto designs
                                                            v
          verify in EnergyPlus -> SHAP -> Streamlit dashboard
```

## 8. Repo layout

```
AGENTS.md
docs/            PROJECT_SPEC.md  PHASES.md  TRACKER.md
data/raw/        immutable
data/processed/  derived data, splits, sim results
src/             data/  models/  sim/  optimize/  app/
models/          trained artifacts
reports/         phaseN_*.md, evidence/
tests/
```

## 9. Success criteria (reported honestly, pass or fail)

- S1: Best ML model beats the best baseline by at least 0.05 macro-F1 on identical rows under group-held-out evaluation. If not met, report as a negative result.
- S2: Surrogates reach R2 >= 0.95 on held-out designs; MAE reported per city.
- S3: At least one verified Pareto design per city beats both reference shelters on O1 and O2, confirmed by direct EnergyPlus runs.
- S4: Dashboard runs locally with one command and shows an applicability flag per city.

## 10. Known limitations (state in every final report)

- DB II is mostly offices, classrooms, and housing, not shelters.
- Results are simulated, not measured.
- Cold-zone (Shimla) comfort predictions are partly extrapolation.
- Hot-dry coverage in DB II comes mostly from semi-arid Indian data; desert classes have 2 buildings each.
- `clo`, `met`, and `vel` at design time are assumptions, not predictions.
