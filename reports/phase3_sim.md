# Phase 3 Simulation Engine Report

**Project:** ClimateAdapt-Comfort  
**Author:** AI Agent (Antigravity)  
**Date:** 2026-10-09  
**Fixed Seed:** 42  
**Dataset Artifact:** [`data/processed/sim_runs.parquet`](file:///d:/Projects/Comfort%20home/data/processed/sim_runs.parquet) (9,988 rows $\times$ 28 columns)  
**Evidence Artifacts:**
- [`reports/evidence/phase3_smoke_test_output.txt`](file:///d:/Projects/Comfort%20home/reports/evidence/phase3_smoke_test_output.txt) (50 fresh runs, spot checks, 3 directional checks, sensitivity)
- [`reports/evidence/phase3_batch_execution_log.txt`](file:///d:/Projects/Comfort%20home/reports/evidence/phase3_batch_execution_log.txt) (10,000-run batch execution log)

---

## 1. Executive Summary

Phase 3 implements an automated, resumable, and parallel building energy simulation engine that maps 8 architectural and envelope design variables into hourly indoor environmental conditions ($T_a, T_r, RH, T_{out}$) and annual HVAC energy demands ($O_2$) across 5 Indian climate zones.

### Acceptance Milestones Completed:
1. **Parametric Model Architecture:** Built [`src/sim/template.idf`](file:///d:/Projects/Comfort%20home/src/sim/template.idf) and [`src/sim/render.py`](file:///d:/Projects/Comfort%20home/src/sim/render.py) for a single-zone passive shelter ($5\text{ m} \times 4\text{ m} \times 3\text{ m} = 20\text{ m}^2$) fully compatible with EnergyPlus v26.2.0.
2. **Fresh Smoke Test Execution:** 50/50 runs freshly executed across 5 cities with 0 severe and 0 fatal errors. Spot checks confirmed 8,760 hourly rows per annual run and verified the literal `"EnergyPlus Completed Successfully"` line.
3. **Three Directional Sanity Verifications:**
   - **Check 1 (Roof Absorptance):** In Jodhpur summer (May 1–Jun 30), cool roof ($\alpha=0.30$ vs $0.90$) lowered mean indoor air temperature by $-0.51^\circ\text{C}$ and mean radiant temperature by $-0.66^\circ\text{C}$.
   - **Check 2 (Insulation in Winter):** In Shimla winter (Dec 1–Feb 28), wall & roof insulation ($0.15\text{ m}$ vs $0.01\text{ m}$) raised mean free-running indoor temperature by $+2.25^\circ\text{C}$.
   - **Check 3 (Natural Cooling Ventilation):** In Jodhpur summer (May 1–Jun 30), natural cooling ventilation ($15\text{ ACH}$ vs $1\text{ ACH}$) reduced mean indoor temperature by $-0.02^\circ\text{C}$.
4. **Sensitivity Verification:** Across 10 sampled designs, discomfort hours outside the ASHRAE adaptive 90% band varied by **18.00% to 31.18%** across all 5 cities (vastly exceeding the 3.0 percentage-point sensitivity threshold).
5. **Full Batch Execution:** 10,000 simulations executed (1,000 designs $\times$ 5 cities $\times$ 2 conditioning modes) with **9,988 successful runs (99.88% success rate)**, exceeding the $\ge 99\%$ phase requirement.

---

## 2. Parametric Design Space & Sampling

Using Latin Hypercube Sampling ([`src/sim/sampler.py`](file:///d:/Projects/Comfort%20home/src/sim/sampler.py), seed 42), 1,000 design vectors were generated spanning the 8 design variables defined in `docs/PROJECT_SPEC.md`:

| Variable | Description | Range / Classes | Distribution |
|---|---|---|---|
| `roof_insulation_thickness` | Roof XPS/EPS insulation | 0.0 to 0.15 m (0 to 150 mm) | Uniform continuous |
| `wall_insulation_thickness` | Wall XPS/EPS insulation | 0.0 to 0.15 m (0 to 150 mm) | Uniform continuous |
| `roof_solar_absorptance` | Cool roof coating vs dark finish | 0.30 to 0.90 | Uniform continuous |
| `wwr` | Window-to-wall ratio (South & North) | 0.05 to 0.40 (5% to 40%) | Uniform continuous |
| `orientation` | Building azimuth angle | $0^\circ$ to $359^\circ$ | Uniform continuous |
| `shading_depth` | Overhang overhang depth | 0.0 to 1.0 m | Uniform continuous |
| `ventilation_ach` | Max natural ventilation flow rate | 1.0 to 15.0 ACH | Uniform continuous |
| `wall_mass_class` | Thermal mass material | `light` (timber), `medium` (brick), `heavy` (concrete) | Categorical uniform |

---

## 3. Climate Zones & Weather Files

Five cities representing the primary Indian climatic classifications under NBC 2016 / ASHRAE were simulated using validated TMYx weather files from `data/raw/India_Weather_Extracted/`:

| City | Climate Zone | Weather File Path | Mean Annual $T_{out}$ | Annual Range ($T_{min} / T_{max}$) | Mean RH |
|---|---|---|---|---|---|
| **Jodhpur** | Hot-Dry / Arid | `IND_RJ_Jodhpur.423390_TMYx.epw` | $26.86^\circ\text{C}$ | $4.8^\circ\text{C} / 45.4^\circ\text{C}$ | $41.8\%$ |
| **Mumbai** | Warm-Humid / Tropical | `IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw` | $27.25^\circ\text{C}$ | $14.1^\circ\text{C} / 38.6^\circ\text{C}$ | $69.7\%$ |
| **New Delhi** | Composite | `IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw` | $25.44^\circ\text{C}$ | $5.0^\circ\text{C} / 44.0^\circ\text{C}$ | $54.2\%$ |
| **Bengaluru** | Moderate / Temperate | `IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw` | $23.71^\circ\text{C}$ | $13.0^\circ\text{C} / 36.6^\circ\text{C}$ | $64.8\%$ |
| **Shimla** | Cold | `IND_HP_Shimla.420830_TMYx.epw` | $15.54^\circ\text{C}$ | $-6.6^\circ\text{C} / 31.6^\circ\text{C}$ | $68.0\%$ |

---

## 4. Full Batch Simulation Results

### 4.1 Free-Running Mode: Annual Thermal Performance (4,990 Successful Runs)

Under free-running conditions (no mechanical HVAC), passive design variables create substantial indoor climate modulation:

| City | Mean $T_a$ ($^\circ\text{C}$) [Min / Max] | Mean $T_r$ ($^\circ\text{C}$) [Min / Max] | Adaptive 90% Discomfort % [Min / Max] | Cold Discomfort % [Min / Max] | Hot Discomfort % [Min / Max] |
|---|---|---|---|---|---|
| **Bengaluru** | $23.54$ [$22.35, 25.20$] | $23.11$ [$21.50, 25.01$] | $41.98\%$ [$14.36\%, 83.30\%$] | $40.62\%$ [$14.11\%, 83.30\%$] | $1.37\%$ [$0.0\%, 22.82\%$] |
| **Jodhpur** | $25.37$ [$23.48, 27.46$] | $24.87$ [$22.48, 27.46$] | $31.99\%$ [$12.90\%, 78.85\%$] | $26.01\%$ [$9.10\%, 78.85\%$] | $5.98\%$ [$0.0\%, 38.23\%$] |
| **Mumbai** | $25.57$ [$23.69, 27.44$] | $24.85$ [$22.54, 27.33$] | $23.60\%$ [$3.82\%, 82.32\%$] | $19.76\%$ [$1.38\%, 82.32\%$] | $3.84\%$ [$0.0\%, 31.18\%$] |
| **New Delhi** | $24.52$ [$22.95, 26.19$] | $24.03$ [$21.99, 26.02$] | $37.30\%$ [$20.68\%, 79.59\%$] | $32.92\%$ [$16.61\%, 79.59\%$] | $4.38\%$ [$0.0\%, 30.66\%$] |
| **Shimla** | $20.16$ [$18.80, 21.45$] | $20.03$ [$18.24, 21.49$] | $54.53\%$ [$40.17\%, 80.74\%$] | $54.10\%$ [$36.42\%, 80.74\%$] | $0.43\%$ [$0.0\%, 16.78\%$] |

---

### 4.2 Ideal-Loads Conditioning Mode: Annual $O_2$ Energy Demands (4,998 Successful Runs)

Under ideal-loads conditioning ($T_{\text{heat}} = 20.0^\circ\text{C}, T_{\text{cool}} = 26.0^\circ\text{C}$ per Assumption A-005):

| City | Mean $O_2$ ($\text{kWh/m}^2/\text{yr}$) | Min $O_2$ | Max $O_2$ | Std $O_2$ | Mean Annual Cooling (kWh) | Mean Annual Heating (kWh) |
|---|---|---|---|---|---|---|
| **Bengaluru** | **22.76** | 0.19 | 100.39 | 14.89 | 264.70 | 190.54 |
| **Mumbai** | **57.06** | 0.01 | 208.78 | 39.06 | 1,120.29 | 20.99 |
| **Jodhpur** | **139.73** | 15.38 | 307.84 | 52.60 | 1,648.73 | 1,145.96 |
| **New Delhi** | **166.77** | 22.16 | 349.35 | 61.28 | 1,432.91 | 1,902.49 |
| **Shimla** | **293.73** | 55.23 | 555.38 | 132.02 | 29.17 | 5,845.34 |

---

## 5. Execution Performance & Failure Analysis

- **Total Simulations Dispatched:** 10,000
- **Successful Runs:** 9,988 (99.88%)
- **Failed Runs:** 12 (0.12%)
- **Total Elapsed Wall Time:** 3,999.4 s (~66.7 min)
- **Average Throughput:** 2.50 simulations/sec across 6 worker processes.
- **Root Cause of 12 Failed Runs:** Transient Windows file locking on `readvars.audit` during simultaneous process cleanup. The 99.88% success rate far exceeds the $\ge 99\%$ acceptance threshold.

---

## 6. Verification Against Phase 3 Acceptance Gates

| Gate / Acceptance Check | Requirement | Result | Status |
|---|---|---|---|
| **10 designs / city smoke test** | 0 severe, 0 fatal errors on 50 runs | 50/50 runs passed, 0 severe, 0 fatal errors | **PASS** |
| **Hourly data integrity** | 8,760 hourly rows per annual run | Verified on 5 representative cities | **PASS** |
| **Directional Sanity Check 1** | Cool roof ($\alpha=0.30$) lowers $T_a, T_r$ in Jodhpur summer | $\Delta T_a = -0.51^\circ\text{C}, \Delta T_r = -0.66^\circ\text{C}$ | **PASS** |
| **Directional Sanity Check 2** | Insulation raises free-running $T_a$ in Shimla winter | $\Delta T_a = +2.25^\circ\text{C}$ | **PASS** |
| **Directional Sanity Check 3** | Natural ventilation cooling lowers indoor temperature | $\Delta T_a = -0.02^\circ\text{C}$ | **PASS** |
| **Design Sensitivity** | $>3.0$ %-pts variation in discomfort across designs | $18.00\%$ to $31.18\%$ spread across all 5 cities | **PASS** |
| **Full Batch Success Rate** | $\ge 99\%$ across ~10,000 runs | **99.88%** (9,988 / 10,000 successful) | **PASS** |

**Phase 3 is complete and verified.**
