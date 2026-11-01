# How to Run ClimateAdapt-Comfort

This document provides exact, runnable commands to execute the pipeline stages, run single weather stations, execute batch scaling, and launch the decision dashboard.

---

## Prerequisites & Setup

1. **Python Environment (Python 3.13 / 3.11+):**
```powershell
pip install -r requirements.txt
```

2. **EnergyPlus Building Simulation Engine (v26.2.0):**
- Install EnergyPlus v26.2.0 to `C:\EnergyPlusV26-2-0\energyplus.exe` (or specify path via `--eplus-exe`).

3. **Verify Environment via Automated Tests:**
```powershell
python -m pytest tests/ -v
```

---

## 1. Running a Single Weather Station Pipeline

To run the complete 5-stage simulation, surrogate modeling, Pareto optimization, and direct verification for a single station:

```powershell
# Syntax: python tools/run_station_pipeline.py <station_name> <epw_path> [output_dir]
python tools/run_station_pipeline.py "Jodhpur" "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"
```

### What happens during a station run:
1. **Stage 1 (Physics Simulations):** Samples 1,000 Latin Hypercube envelope designs (`seed=42`) and runs 2,000 EnergyPlus simulations (free-running and ideal-loads) in parallel.
2. **Stage 2 (Dual Comfort Judge Coupling):** Scores all 8,760 hours against ASHRAE 55 Adaptive 90% and ML Champion (`Ablation_A3`), saving `objectives_<station>.parquet`.
3. **Stage 3 (Surrogate Training):** Trains 5 XGBoost surrogate models using Optuna 5-fold cross-validation (40 trials, `seed=42`) in parallel.
4. **Stage 4 (NSGA-II Optimization):** Evolves a population of 100 designs across 200 generations (`seed=42`) to produce Pareto frontier `pareto_<station>.parquet`.
5. **Stage 5 (Direct EnergyPlus Verification):** Simulates 10 representative Pareto designs (20 runs) in EnergyPlus to verify surrogate predictions against physical ground truth.
6. **Stage 6 (Archiving & Cleanup):** Compresses run directories into `archive_<station>.zip` and removes transient simulation folders.

---

## 2. Running Batch Scaling Across All India Stations

The batch runner processes stations sequentially from `reports/station_registry.csv` (excluding the 5 original cities and 3 benchmarks, leaving 435 stations):

```powershell
# 1. Dry Run (inspect station list and exit without running)
python -u tools/run_batch.py --dry-run

# 2. Single Station Test (processes 1 station, enforces memory/disk gates)
python -u tools/run_batch.py --limit 1 --max-hours 1 --max-sim-workers 8

# 3. Full Production Batch Session (up to 10 hours)
python -u tools/run_batch.py --max-hours 10 --max-sim-workers 8
```

### Safety Features of the Batch Runner:
- **Unique Output Keying:** All station outputs are keyed on `{name}_{wmo}` (e.g. `Madurai_433590` vs `Madurai_433600`) to eliminate overwrite collisions.
- **Memory Headroom Gate:** Requires $\ge 5.0\text{ GB}$ available RAM before starting each station (retries every 60 s up to 5 times).
- **Disk Safety Guard:** Aborts immediately if free disk space on D: drops below $5.0\text{ GB}$.
- **Circuit Breaker:** Automatically halts execution if 2 consecutive stations fail.
- **Automatic Resume:** Skips stations whose objective parquet, Pareto parquet, verification CSV, surrogate models, and archive zip already exist.

---

## 3. Running Augmentation & Surrogate Re-fitting

To sample additional Latin Hypercube designs, simulate both modes, and re-fit surrogate models:

```powershell
# Runs 500 additional designs per city (seed=1042) and re-fits 25 surrogate models
python src/models/augment_and_refit.py
```

---

## 4. Running the Interactive Decision-Support Dashboard

To launch the local interactive Streamlit dashboard:

```powershell
streamlit run src/app/app.py
```

---

## 5. Running the Automated Evidence Claims Audit

To verify all numerical claims against literal saved evidence files:

```powershell
python tools/claims_audit.py
```
