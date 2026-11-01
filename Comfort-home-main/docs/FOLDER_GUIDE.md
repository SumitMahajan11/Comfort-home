# Repository Folder Guide

This guide describes the organization and contents of each folder in the `ClimateAdapt-Comfort` repository to help collaborators navigate and contribute effectively.

---

## High-Level Layout

| Directory / File | Category | Purpose / Description | Git Tracking Status |
| :--- | :--- | :--- | :--- |
| `src/` | **Core Code** | Core computational physics, ML modeling, and optimization library | Tracked |
| `tools/` | **Core Code / Runners** | Operational CLI tools, batch scaling runner, and audit scripts | Tracked |
| `tests/` | **Core Code / Tests** | Automated pytest suite for splits, comfort coupling, and UI | Tracked |
| `docs/` | **Documentation** | Specifications, phase gates, decision tracker, and guides | Tracked |
| `reports/` | **Results & Evidence** | Phase reports, evidence logs, figures, and station registry | Tracked (except bulky telemetry) |
| `data/processed/` | **Results & Data** | Processed datasets, split definitions, metrics, and Pareto parquets | Summary CSVs/JSONs + core parquets tracked |
| `data/raw/` | **Generated / Bulky** | Raw immutable weather files (TMYx), ASHRAE DB II, and ICE DB | Gitignored (Re-downloadable / Restricted) |
| `models/` | **Generated / Bulky** | ML champion comfort model (`champion_comfort_model.joblib`) and surrogates | Champion model tracked; surrogates ignored |
| `scratch/` | **Scratch / Temporary** | Ad-hoc debugging, inspection, and temporary audit scripts | Gitignored |

---

## Detailed Directory Breakdown

### 1. `src/` (Core Library)
Contains the modular, functional building blocks of the project.
- `src/data/`: Data ingestion, complete-case filtering, Köppen group mapping, and group-aware train/test splitting (`make_splits.py`).
- `src/models/`: Baseline evaluations (PMV, Adaptive 80%/90%, IMAC), ML comfort classifier training (`train.py`), XGBoost surrogate training (`train_surrogates.py`), and SHAP explainability (`explain.py`).
- `src/sim/`: EnergyPlus envelope IDF rendering (`render.py`), Latin Hypercube design sampling (`sampler.py`), simulation execution (`runner.py`), and CSV/ESO parsing (`parse.py`).
- `src/optimize/`: Dual comfort judge coupling (`coupling.py`), reference shelter baselines (`references.py`), and NSGA-II multi-objective optimization (`nsga2.py`).
- `src/app/`: Interactive Streamlit decision-support dashboard (`app.py`) and survey question mapping (`answer_mapping.py`).

### 2. `tools/` (Pipeline Runners & Utilities)
Contains execution scripts invoked from the command line:
- `tools/run_station_pipeline.py`: Full 5-stage pipeline for a single weather station (2,000 EnergyPlus runs, surrogate training, Pareto optimization, and direct verification).
- `tools/run_batch.py`: Batch runner that sequentially processes stations across India with telemetry logging, memory start guards, and circuit breakers.
- `tools/build_station_registry.py`: Scans weather folders and compiles `reports/station_registry.csv` (443 total stations, 435 batch stations).
- `tools/check_station_quality.py`: Audits EPW weather data quality and validity across all stations.
- `tools/claims_audit.py`: Automated audit verifying all numerical claims against literal files in `reports/evidence/`.
- `tools/mem_watch.py`: Real-time system RAM and Windows commit limit telemetry logger.

> **Station Naming Convention:** The 8 protected reference stations (`Jodhpur`, `Mumbai`, `New_Delhi`, `Bengaluru`, `Shimla`, `Ahmedabad`, `Chennai`, `Leh`) use plain city names. All batch-scaled stations use unique `{name}_{wmo}` keying (e.g. `Madurai_433590`) to prevent collisions across multiple stations in the same administrative city.

### 3. `docs/` (Architecture & Project Governance)
- `docs/PROJECT_SPEC.md`: Single source of truth containing locked decisions, envelope parameter ranges, and mathematical definitions.
- `docs/PHASES.md`: Deliverables, verification criteria, and acceptance gates for all phases.
- `docs/TRACKER.md`: Execution tracker, evidence ledger, decision log, and risk register.
- `docs/FOLDER_GUIDE.md`: This layout and folder navigation document.
- `docs/HOW_TO_RUN.md`: Step-by-step instructions for running single stations, batch scaling, and tests.
- `docs/DATA_AND_MODELS.md`: Comprehensive breakdown of datasets, target variables, and verified model accuracy tables.

### 4. `reports/` (Reports, Evidence & Visualizations)
- `reports/evidence/`: Command execution outputs and verification logs (`phase1_eda_calc_output.txt`, `phase7_claims_audit_output.txt`, etc.).
- `reports/figures/`: SHAP summary plots, Pareto frontier charts, and dashboard UI screenshots.
- `reports/*.md`: Phase completion synthesis reports (`phase1_eda.md` through `final_results.md`).
- `reports/station_registry.csv`: Catalog of all 443 extracted Indian weather stations.
