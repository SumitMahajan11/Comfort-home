# ClimateAdapt-Comfort

Decision-Support System for Passive Shelter Design Across Indian Climate Zones.

---

## 1. Purpose & Research Question

The ClimateAdapt-Comfort project investigates whether empirical thermal comfort models trained on global field survey data, coupled to building thermal simulation and multi-objective optimization, can recommend passive shelter designs that minimize occupant discomfort hours and annual HVAC energy demand across distinct Indian climate zones.

> **Research Question:** Does a thermal-comfort model trained on global field data, coupled to building simulation, recommend shelter designs that reduce discomfort hours and energy demand, and does it beat PMV and adaptive-model baselines?

---

## 2. Headline Results (Evidence-Gated)

All numbers are grounded strictly in literal command outputs recorded in [`docs/TRACKER.md`](docs/TRACKER.md) and [`reports/evidence/`](reports/evidence/):

- **Success Criterion S1 (Comfort Model vs Adaptive Baseline): `FAIL`** `[E-012]`
  - *Target:* Best ML model beats best baseline by $\ge +0.05$ macro-F1 on identical complete-case test rows (58,512 rows) under Leave-One-Köppen-Group-Out cross-validation.
  - *Result:* Physical Adaptive 90% achieved macro-F1 **0.4939** (95% CI: [0.4907, 0.4971]); ML Champion (`Ablation_A3_OutdoorTemp`) achieved macro-F1 **0.4785** (95% CI: [0.4754, 0.4816]).
  - *Margin:* **-0.0154** (reported honestly as a negative result; ML model did not beat the physical adaptive baseline on group-held-out validation).
- **Success Criterion S2 (Surrogate Model Accuracy): `PASS`** `[E-019]`
  - *Target:* XGBoost surrogate regressors reach $R^2 \ge 0.95$ on held-out 20% test designs.
  - *Result:* 23 of 25 surrogate models achieved $R^2 \ge 0.95$; mean $R^2$ on annual HVAC energy ($O_2$) reached **0.987** across all 5 climate zones.
- **Success Criterion S3 (Direct EnergyPlus Verification vs Reference Shelters): `PASS`** `[E-020]`
  - *Target:* At least one verified Pareto design per city beats BOTH R1 (Lightweight) and R2 (Conventional) reference shelters across all three objectives ($O_{1,\text{ml}}$, $O_{1,\text{adapt}}$, and $O_2$), confirmed by direct EnergyPlus runs.
  - *Result:* **Passed in all 5 climate zones** (60% to 80% of verified designs beat both baselines):
    - **Jodhpur (Hot-Dry):** Discomfort reduced from $75.72\%$ to **$36.64\%$** ($\Delta -39.08\%$), energy reduced from $281.88$ to **$41.40\text{ kWh/m}^2/\text{yr}$** ($\Delta -240.47\text{ kWh/m}^2$).
    - **Mumbai (Warm-Humid):** Discomfort reduced from $65.95\%$ to **$41.97\%$** ($\Delta -23.97\%$), energy reduced from $199.99$ to **$102.94\text{ kWh/m}^2/\text{yr}$** ($\Delta -97.05\text{ kWh/m}^2$).
    - **New Delhi (Composite):** Discomfort reduced from $70.40\%$ to **$39.35\%$** ($\Delta -31.05\%$), energy reduced from $279.40$ to **$50.40\text{ kWh/m}^2/\text{yr}$** ($\Delta -229.00\text{ kWh/m}^2$).
    - **Bengaluru (Temperate):** Discomfort reduced from $59.93\%$ to **$45.74\%$** ($\Delta -14.19\%$), energy reduced from $66.94$ to **$36.61\text{ kWh/m}^2/\text{yr}$** ($\Delta -30.33\text{ kWh/m}^2$).
    - **Shimla (Cold):** Discomfort reduced from $77.36\%$ to **$67.95\%$** ($\Delta -9.42\%$), energy reduced from $279.54$ to **$74.08\text{ kWh/m}^2/\text{yr}$** ($\Delta -205.46\text{ kWh/m}^2$).
- **Success Criterion S4 (Decision-Support Dashboard): `PASS`** `[E-021]`
  - *Target:* Streamlit dashboard runs locally with one command, read-only on saved artifacts, with zero external network or paid API dependencies, displaying applicability flags.
  - *Result:* Web application starts instantly via `streamlit run src/app/app.py`; automated pytest test suite (`tests/test_app.py`) passed all 6 UI tests in **5.38 seconds** with 0 errors.

---

## 3. Environment Setup & Installation (Windows PowerShell)

### Prerequisites
- **Operating System:** Windows 10/11 x64 (PowerShell 5.1 / 7.x)
- **Python Version:** Python 3.13.7 (or $\ge 3.11$)
- **EnergyPlus Engine:** EnergyPlus Version 26.2.0 (Installed to `C:\EnergyPlusV26-2-0\energyplus.exe` or set via `$env:ENERGYPLUS_EXE`)

### Installation Steps
```powershell
# 1. Clone repository and navigate to root
cd "D:\Projects\Comfort home"

# 2. Install required Python packages
pip install -r requirements.txt

# 3. Verify unit tests
python -m pytest tests/ -v

# 4. Launch the local interactive decision-support dashboard
streamlit run src/app/app.py
```

---

## 4. How to Obtain Raw Datasets (`data/raw/` is gitignored)

All derived files under `data/processed/` are generated deterministically. The raw source datasets must be placed in `data/raw/`:

1. **ASHRAE Global Thermal Comfort Database II (v2.1.0):**
   - *Source:* [ASHRAE Database II GitHub Repository](https://github.com/CenterForTheBuiltEnvironment/ashrae-db-II)
   - *File Placement:* `data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz` (109,033 rows $\times$ 53 cols) and `db_metadata.csv` (809 rows $\times$ 23 cols).
2. **Indian Climate EPW Weather Files (TMYx / ISHRAE):**
   - *Source:* [Climate.OneBuilding.org](https://climate.onebuilding.org/)
   - *File Placement:* `data/raw/India_Weather_Extracted/` containing subfolders for Jodhpur (`IND_RJ_Jodhpur.423390_TMYx.epw`), Mumbai (`IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw`), New Delhi (`IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw`), Bengaluru (`IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw`), and Shimla (`IND_HP_Shimla.420830_TMYx.epw`).
3. **ICE Database Educational Version 5.0 (Embodied Carbon):**
   - *Source:* [Circular Ecology Inventory of Carbon and Energy](https://circularecology.com/embodied-carbon-footprint-database.html)
   - *File Placement:* `data/raw/ice_database/ICE DB Educational V5.0 - Jun 2026.xlsx`.

---

## 5. Measured Pipeline Stage Runtimes

| Stage | Script / Module | Description | Measured Runtime |
|---|---|---|---|
| **Clean & Splits** | `src/data/build_building_group_map.py`, `src/data/make_splits.py` | Complete-case filtering (58,512 rows) and 5-fold GroupKFold + 4-fold LOGO splits | **14.2 s** |
| **Physical Baselines** | `src/models/baselines.py` | PMV, Adaptive 80%/90%, IMAC NV/MM evaluation on identical rows (1,000 bootstrap CIs) | **82.5 s** |
| **ML Comfort Models** | `src/models/train.py` | Training LogReg, RF, MLP, XGBoost, and Ablations A1–A3; Champion calibration | **48.1 s** |
| **Simulation Batch** | `src/sim/batch.py` | 10,000 EnergyPlus runs (1,000 LHS designs $\times$ 5 cities $\times$ 2 modes) with 16 parallel workers | **3,999.4 s (66.7 min)** |
| **Coupling & Series** | `src/optimize/run_phase4a.py` | Hourly extraction (43.69M records), running mean outdoor temperature, dual judge scoring | **162.3 s** |
| **Surrogates Tuning** | `src/models/train_surrogates.py` | Optuna 5-fold CV hyperparameter optimization (40 trials $\times$ 25 models, 7,483 valid designs) | **640.8 s (10.7 min)** |
| **Optimization & Verify** | `src/optimize/nsga2.py` | NSGA-II optimization (Pop=100, Gen=200, 5 cities) and 50 direct EnergyPlus verification runs | **124.6 s (2.1 min)** |
| **SHAP Explainability** | `src/models/explain.py` | TreeExplainer global and local attributions across DB II, simulated hours, and 25 surrogates | **38.4 s** |
| **Smoke Test Pipeline** | `python src/run_all.py --smoke` | Micro-sample end-to-end execution of all pipeline stages | **140.3 s (2.3 min)** |

---

## 6. Licensing & Educational Terms

- **ASHRAE Global Thermal Comfort Database II:** Distributed under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/) and Open Data Commons Attribution License (ODC-By v1.0). Commercial and academic research use permitted with attribution to the authors and CBE UC Berkeley.
- **Darjeeling / Indian Comfort Field Datasets:** Field measurements contributed to DB II by Indian research institutions under standard academic research attribution terms.
- **ICE Database Educational Version 5.0:** Distributed by Circular Ecology Ltd under **Educational / Non-Commercial Use Only** terms. The data may be used for academic, educational, and research projects; commercial use requires a licensed version from Circular Ecology.
- **EnergyPlus Engine:** Distributed by the United States Department of Energy (DOE) and National Renewable Energy Laboratory (NREL) under an open-source modified BSD licence.

---

## 7. Repo Architecture

```
ClimateAdapt-Comfort/
├── AGENTS.md                 # Universal project rules and evidence gating contract
├── requirements.txt          # Pinned Python package dependencies (Python 3.13)
├── run_all.ps1               # Windows PowerShell orchestrator script
├── docs/
│   ├── PROJECT_SPEC.md       # Project single source of truth and locked decisions
│   ├── PHASES.md             # Detailed phase requirements and acceptance gates
│   └── TRACKER.md            # Evidence ledger, decision log, and status checklist
├── data/
│   ├── raw/                  # Immutable raw source datasets (gitignored)
│   └── processed/            # Derived parquets, splits, surrogates, metrics, and Pareto sets
├── models/                   # Serialized champion comfort model and 25 XGBoost surrogates
├── reports/
│   ├── figures/              # Generated Pareto scatter plots and SHAP importance figures
│   ├── evidence/             # Literal command execution logs backing every claim
│   ├── data_audit.md         # Phase 0 data audit report
│   ├── phase1_eda.md         # Phase 1 EDA and baselines report
│   ├── phase2_models.md      # Phase 2 ML comfort modeling report
│   ├── phase3_sim.md         # Phase 3 EnergyPlus simulation engine report
│   ├── phase4a_coupling.md   # Phase 4A dual judge coupling report
│   ├── phase4_surrogates.md  # Phase 4B XGBoost surrogate modeling report
│   ├── phase5_optimization.md# Phase 5 NSGA-II optimization & verification report
│   ├── phase6_dashboard.md   # Phase 6 SHAP explainability & Streamlit dashboard report
│   └── final_results.md      # Final comprehensive synthesis report
├── src/
│   ├── app/app.py            # 5-page interactive decision-support dashboard
│   ├── data/                 # Data cleaning, group mapping, and split generation
│   ├── models/               # Model training, baseline evaluation, surrogates, and SHAP
│   ├── optimize/             # Coupling engine, reference shelters, and NSGA-II optimizer
│   ├── sim/                  # IDF rendering, LHS sampling, runner, and output parser
│   └── run_all.py            # Master end-to-end Python pipeline orchestrator
├── tests/
│   ├── test_app.py           # Automated Streamlit AppTest unit test suite
│   ├── test_coupling.py      # Comfort judge coupling and running mean unit tests
│   └── test_splits.py        # Group split integrity and building leakage tests
└── tools/
    └── claims_audit.py       # Automated evidence audit verification script
```
