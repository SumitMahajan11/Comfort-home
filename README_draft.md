# ClimateAdapt-Comfort: AI-Driven Passive Climate Adaptation & Thermal Comfort Optimization for Indian Shelters

## Overview
ClimateAdapt-Comfort is an end-to-end computational building physics and machine learning framework designed to optimize low-cost, rapidly deployable humanitarian shelter envelopes across India's diverse climatic zones (`docs/PROJECT_SPEC.md`). The pipeline integrates EnergyPlus physical simulations with field-calibrated adaptive comfort judges (ASHRAE 55 Adaptive 90% and empirical ML comfort models trained on the ASHRAE Global Thermal Comfort Database II) and XGBoost surrogate models to perform multi-objective Pareto optimization (NSGA-II) across thermal discomfort and life-cycle operational energy (`docs/PROJECT_SPEC.md`).

---

## Key Numbers & Verified Metrics from Repository Artifacts
- **5 Representative Indian Climates Analyzed:** Jodhpur (Hot & Dry), Mumbai (Warm & Humid), New Delhi (Composite), Bengaluru (Temperate), Shimla (Cold) (`docs/PROJECT_SPEC.md`).
- **Field Comfort Database:** Evaluated on ASHRAE Global Thermal Comfort Database II with 6,700 India field survey rows (`data/processed/applicability.csv`, `reports/phase1_eda.md`).
- **ML Comfort Judge (Ablation A3):** Achieved test $R^2 = 0.724$ on India field data (`data/processed/model_results.json`).
- **Physics Simulations:** 1,000 Latin Hypercube envelope designs per station across 2 operating modes (free-running and ideal-loads), totaling 2,000 simulations per station (`docs/PROJECT_SPEC.md`, `src/sim/sampler.py`).
- **Surrogate Accuracy:** 5 XGBoost surrogate models per climate tuned via Optuna 5-fold cross-validation across 40 trials; achieved test $R^2 \ge 0.95$ across all targets in augmented fits (`data/processed/surrogate_metrics_comparison.csv`).
- **Pareto Optimization:** NSGA-II population of 100 individuals evolved across 200 generations (`docs/PROJECT_SPEC.md`, `src/optimize/nsga2.py`).
- **Verification:** Direct physical EnergyPlus simulation verification of 10 representative Pareto designs per station (`docs/PROJECT_SPEC.md`, `data/processed/pareto_verification_results.csv`).

---

## Repository Structure
```
├── AGENTS.md                  # Project rules, reproducibility gates, and logging protocols
├── README.md                  # Primary repository overview
├── README_draft.md            # GitHub sharing draft specification
├── requirements.txt           # Python dependency specifications
├── run_all.ps1                # Reproducible execution script for Phases 1-7
├── data/
│   ├── raw/                   # Raw immutable datasets (ASHRAE DB II, EPW weather files, ICE DB) [Excluded from Git]
│   └── processed/             # Processed datasets, splits.json, Pareto sets, and metrics CSVs
├── docs/
│   ├── PROJECT_SPEC.md        # Complete system architecture and locked engineering parameters
│   ├── PHASES.md              # Phase-by-phase deliverables, verification criteria, and UAT gates
│   └── TRACKER.md             # Execution tracker, evidence ledger, and risk log
├── models/                    # Serialized champion comfort models and XGBoost surrogate artifacts [Excluded from Git]
├── reports/
│   ├── data_audit.md          # Data integrity and schema verification audit
│   ├── final_results.md       # Comprehensive multi-climate results and findings
│   ├── evidence/              # Command outputs and execution logs supporting all claims
│   └── figures/               # SHAP plots, Pareto frontiers, and dashboard captures
├── src/
│   ├── app/                   # Streamlit decision dashboard application
│   ├── data/                  # Data cleaning, validation, and group-aware train/test splitting
│   ├── models/                # ML comfort models, Optuna hyperparameter tuning, and SHAP explainability
│   ├── optimize/              # Dual comfort coupling, NSGA-II optimization, and Pareto extraction
│   └── sim/                   # EnergyPlus parametric IDF generation, simulation execution, and parsing
├── tests/                     # Unit and integration test suite (splits leakage, coupling, app tests)
└── tools/
    ├── claims_audit.py        # Automated auditor verifying claims against literal evidence files
    ├── run_station_pipeline.py# Single-station 5-stage simulation and optimization pipeline
    └── run_batch.py           # Multi-station batch scaling runner with telemetry and circuit breakers
```

---

## Setup & Installation

### 1. Python Environment
- Python version: `3.13.x` (or `3.10+` recommended)
- Install required dependencies:
```bash
pip install -r requirements.txt
```

### 2. EnergyPlus Installation
- **Required Version:** EnergyPlus `v26.2.0` (x86_64).
- **Download:** Official release from [EnergyPlus GitHub Releases](https://github.com/NREL/EnergyPlus/releases/tag/v26.2.0).
- **Default Installation Path expected:** `C:\EnergyPlusV26-2-0\energyplus.exe` (configurable via `--eplus-exe` or in `src/sim/runner.py`).

### 3. Weather Data (EPW Files)
- Download TMYx (2011–2025) weather files from Climate.OneBuilding.org:
  - Source: [Climate.OneBuilding India EPW Archive](http://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/)
- Place extracted weather files into:
```
data/raw/India_Weather_Extracted/
```

---

## Execution Guide

### Launching the Production Web Application (`web/`)
The primary interactive user interface is the Next.js web application. Run the following separate steps:

```bash
# Step 1: Export precomputed simulation and surrogate artifacts to web data
python tools/export_web_data.py

# Step 2: Navigate to web application directory
cd web

# Step 3: Install Node dependencies
npm install

# Step 4: Run unit tests (47 tests)
npm test

# Step 5: Launch local development server
npm run dev

# Or build and launch production server
npm run build
npm run start
```

### Running Unit & Integration Tests
```bash
# Python unit tests (45 tests passed)
python -m pytest tests/ -v

# Web unit tests (47 tests passed)
cd web
npm test
```

### Launching Legacy Research Prototype (Streamlit)
```bash
streamlit run src/app/app.py
```

### Running a Single Weather Station
To run the complete 5-stage pipeline for a single weather station (2,000 EnergyPlus runs, dual comfort judge evaluation, surrogate model fitting, NSGA-II optimization, and physical direct verification):
```bash
python tools/run_station_pipeline.py "Jodhpur" "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"
```

### Running Batch Scaling across India Stations
To run sequential batch processing across India weather stations with telemetry, memory start guards, disk safety guards, and automatic resumption:
```bash
# Test single station limit
python -u tools/run_batch.py --limit 1 --max-hours 1 --max-sim-workers 8

# Full batch execution
python -u tools/run_batch.py --max-hours 10 --max-sim-workers 8
```

---

## Excluded Artifacts & Git Storage Policy
To ensure clean repository distribution while preserving full open reproducibility, bulky simulation outputs and raw databases are excluded from version control:
- `data/raw/`: Raw weather files (~4.5 GB) and ASHRAE DB II raw archives are excluded (freely re-downloadable from public sources).
- `data/processed/scaling/` & `data/processed/sim_*/`: Intermediate EnergyPlus hourly simulation outputs (~1.1 GB) are transient and pruned during runs.
- `models/scaling/*.joblib`: Generated surrogate model binaries (~40 MB per station batch) are regenerated deterministically via fixed seed (`seed=42`).
- `reports/mem_trace*.csv` & `reports/batch_log*.csv`: Runtime telemetry and error logs.

All processed summary files (`splits.json`, Pareto metrics, verification comparisons, and evidence logs) remain fully tracked in the repository.

---

## Known Limitations & Operating Notes
1. **Multiprocessing on Windows:** Spawning parallel simulation or Optuna workers requires sufficient system commit memory headroom ($\ge 5.0\text{ GB}$ available RAM).
2. **Deterministic Seeds:** All sampling, splitting, and optimization routines use explicit fixed seeds (`42` and `1042`) for 100% numerical reproducibility.
3. **Adaptive Comfort Standard Applicability:** ASHRAE 55 Adaptive 90% is constrained to running mean outdoor temperatures between $10^\circ\text{C}$ and $33.5^\circ\text{C}$; observations outside this range are flagged with `invalid_share_adapt` (`docs/PROJECT_SPEC.md`).
