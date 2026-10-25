# Phase 0 Data Audit Report

**Generated Date:** 2026-10-09  
**Workspace Root:** `D:\Projects\Comfort home`  
**Execution Environment:** Windows PowerShell, Python 3.13.7, pandas 2.3.2, openpyxl 3.1.5, EnergyPlus 26.2.0  
**Data Segregation Policy:** Raw downloads stored in `data/raw/` (immutable); generated outputs stored in `data/processed/` and `reports/`.

---

## 1. Directory Reorganization & Clean-Up Summary

The project workspace was reorganized into strict raw/processed splits to protect source integrity:

```
D:\Projects\Comfort home\
├── data/
│   ├── raw/
│   │   ├── ashrae_db_ii/                      # Single Source of Truth for ASHRAE Global Thermal Comfort Database II (GitHub v2.1.0)
│   │   │   ├── ashrae-db-II-master/v2.1.0/    # db_measurements_v2.1.0.csv.gz, db_metadata.csv, main.py
│   │   │   └── db_measurements_v2.1.0.csv/    # Extracted db_measurements_v2.1.0.csv
│   │   ├── ashrae_db_ii_dryad_backup/         # Dryad v20220609 copy (retained as backup only, not active source)
│   │   ├── ice_database/                      # Inventory of Carbon and Energy (ICE V5.0 Excel & PDF documentation)
│   │   └── India_Weather_Extracted/           # 1,760 EPW & companion weather files across 476 Indian stations
│   └── processed/
│       ├── smoke_test/                        # Output files from EnergyPlus 26.2.0 baseline simulation
│       └── ice_materials_extracted.csv        # Structured tabular extraction of ICE material embodied carbon
└── reports/
    ├── data_audit.md                          # This Phase 0 audit report
    ├── audit_db_and_weather.py                # Automated audit extraction script for DB II and EPWs
    └── audit_ice_database.py                  # Automated audit extraction script for ICE DB V5.0
```

*Note on root cleanup:* Stray `IND_WB_Uluberia.428050_TMYx.*` files in the workspace root were verified against `India_Weather_Extracted/IND_WB_Uluberia.428050_TMYx/` and cleaned up to prevent directory pollution.

---

## 2. ASHRAE DB II Measurements & Metadata Audit

### 2.1 File Paths and Dimensions

| Attribute | Literal Verified Value |
| :--- | :--- |
| **Primary Source Path (GZ)** | `data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz` |
| **Primary Source Path (Extracted CSV)** | `data/raw/ashrae_db_ii/db_measurements_v2.1.0.csv/db_measurements_v2.1.0.csv` |
| **Backup Path (Dryad)** | `data/raw/ashrae_db_ii_dryad_backup/db_measurements_v2.1.0.csv.gz` |
| **Metadata Path** | `data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv` |
| **Measurements File Size (GZ)** | 3,033,632 bytes (2.89 MB) |
| **Measurements File Size (CSV)** | 22,608,936 bytes (21.56 MB) |
| **Metadata File Size** | 226,093 bytes (220.79 KB) |
| **Measurements Dimensions** | **109,033 rows × 53 columns** |
| **Metadata Dimensions** | **809 rows × 23 columns** |
| **Merged Dataset Dimensions (`building_id`)** | **109,033 rows × 75 columns** |

### 2.2 Missingness Analysis for Key Physical & Comfort Columns

*Literal output from pandas command:*

| Column Name | Description | Non-Null Count | Null Count | Missing % | Data Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `building_id` | Building Identifier | 109,033 | 0 | 0.00% | int64 |
| `ta` | Air Temperature (°C) [Primary] | 109,033 | 0 | 0.00% | float64 |
| `ta_h` | Air Temperature (Head Level, 1.1m/1.7m) | 28,711 | 80,322 | 73.67% | float64 |
| `ta_m` | Air Temperature (Middle Level, 0.6m) | 33,187 | 75,846 | 69.56% | float64 |
| `ta_l` | Air Temperature (Ankle Level, 0.1m) | 10,398 | 98,635 | 90.46% | float64 |
| `top` | Operative Temperature (°C) | 42,157 | 66,876 | 61.34% | float64 |
| `tr` | Mean Radiant Temperature (°C) | 71,043 | 37,990 | 34.84% | float64 |
| `tg` | Globe Temperature (°C) | 35,511 | 73,522 | 67.43% | float64 |
| `rh` | Relative Humidity (%) | 102,234 | 6,799 | 6.24% | float64 |
| `vel` | Air Speed (m/s) [Primary] | 93,515 | 15,518 | 14.23% | float64 |
| `vel_h` | Air Speed (Head Level) | 21,933 | 87,100 | 79.88% | float64 |
| `vel_m` | Air Speed (Middle Level) | 30,351 | 78,682 | 72.16% | float64 |
| `vel_l` | Air Speed (Ankle Level) | 10,220 | 98,813 | 90.63% | float64 |
| `clo` | Clothing Insulation (clo) | 102,085 | 6,948 | 6.37% | float64 |
| `met` | Metabolic Rate (met) | 94,346 | 14,687 | 13.47% | float64 |
| `thermal_sensation` | Thermal Sensation Vote (-3 to +3) | 106,171 | 2,862 | 2.62% | float64 |
| `thermal_acceptability` | Thermal Acceptability (0/1) | 59,203 | 49,830 | 45.70% | float64 |
| `thermal_preference` | Thermal Preference (cooler/no change/warmer) | 83,169 | 25,864 | 23.72% | object |
| `thermal_comfort` | Thermal Comfort (6-point scale) | 38,154 | 70,879 | 65.01% | float64 |
| `t_out` | Outdoor Temperature (°C) [Logged/Local] | 69,307 | 39,726 | 36.43% | float64 |
| `t_out_monthly` | Monthly Mean Outdoor Temperature (°C) | 51,582 | 57,451 | 52.69% | float64 |
| `t_out_isd` | Outdoor Temp from NOAA ISD Station (°C) | 65,834 | 43,199 | 39.62% | float64 |
| `t_mot_isd` | Running Mean Outdoor Temp from NOAA ISD (°C) | 64,505 | 44,528 | 40.84% | float64 |
| `climate` | Köppen-Geiger Climate Classification | 109,033 | 0 | 0.00% | object |
| `country` | Country Name | 109,033 | 0 | 0.00% | object |
| `building_type` | Building Typology | 109,033 | 0 | 0.00% | object |
| `cooling_type` | Ventilation & Cooling Strategy | 107,507 | 1,526 | 1.40% | object |

---

## 3. Climate, Geographic, Typology & Ventilation Breakdowns

### 3.1 Global Rows by Köppen Climate Class (31 Classes)

*Literal output from command:*

| Climate Class (Köppen) | Row Count | Percentage of DB II |
| :--- | :--- | :--- |
| hot-summer mediterranean | 21,722 | 19.92% |
| humid subtropical | 15,257 | 13.99% |
| hot semi-arid | 8,642 | 7.93% |
| tropical wet savanna | 8,383 | 7.69% |
| tropical savanna | 6,980 | 6.40% |
| warm-summer mediterranean | 5,773 | 5.30% |
| mediterranean | 4,584 | 4.20% |
| temperate oceanic | 4,422 | 4.06% |
| monsoon-influenced hot-summer humid continental | 3,739 | 3.43% |
| warm-summer humid continental | 2,990 | 2.74% |
| tropical monsoon | 2,101 | 1.93% |
| hot desert | 2,083 | 1.91% |
| desert (hot arid) | 2,011 | 1.84% |
| humid midlatitude | 1,944 | 1.78% |
| monsoon-influenced humid subtropical | 1,786 | 1.64% |
| temperate | 1,760 | 1.61% |
| tropical | 1,594 | 1.46% |
| west coast marine | 1,490 | 1.37% |
| wet equatorial | 1,414 | 1.30% |
| cool-summer mediterranean | 1,406 | 1.29% |
| subtropical highland | 1,406 | 1.29% |
| tropical rainforest | 1,350 | 1.24% |
| hot arid | 1,229 | 1.13% |
| semi arid high altitude | 1,072 | 0.98% |
| semi arid midlatitude | 1,066 | 0.98% |
| temperature marine | 1,065 | 0.98% |
| continental subarctic | 869 | 0.80% |
| monsoon-influenced temperate oceanic | 460 | 0.42% |
| cold semi-arid | 242 | 0.22% |
| tropical dry savanna | 152 | 0.14% |
| subtropical hot and dry | 41 | 0.04% |
| **Total Global Rows** | **109,033** | **100.00%** |

### 3.2 Global Rows by Country (29 Countries)

*Literal output from command:*

| Country | Row Count | Percentage |
| :--- | :--- | :--- |
| **UK** | 25,447 | 23.34% |
| **India** | **18,714** | **17.16%** |
| **USA** | 15,021 | 13.78% |
| Australia | 8,002 | 7.34% |
| Brazil | 7,389 | 6.78% |
| China | 6,246 | 5.73% |
| Pakistan | 4,149 | 3.81% |
| Canada | 2,728 | 2.50% |
| Malaysia | 2,299 | 2.11% |
| Iran | 1,971 | 1.81% |
| Greece | 1,940 | 1.78% |
| Tunisia | 1,581 | 1.45% |
| Portugal | 1,558 | 1.43% |
| Italy | 1,554 | 1.43% |
| Mexico | 1,417 | 1.30% |
| Japan | 1,275 | 1.17% |
| Thailand | 1,160 | 1.06% |
| Singapore | 1,090 | 1.00% |
| Germany | 1,049 | 0.96% |
| Indonesia | 996 | 0.91% |
| Sweden | 939 | 0.86% |
| South Korea | 530 | 0.49% |
| France | 480 | 0.44% |
| Nigeria | 468 | 0.43% |
| Slovakia | 457 | 0.42% |
| Philippines | 277 | 0.25% |
| Denmark | 170 | 0.16% |
| Belgium | 85 | 0.08% |
| Cyprus | 41 | 0.04% |
| **Total** | **109,033** | **100.00%** |

### 3.3 India-Specific Dataset Audit (18,714 Rows)

India represents the **second largest single-country dataset** in ASHRAE DB II (18,714 records, 17.16% of global data).

#### A. India Rows by Climate Class
* hot semi-arid: **8,251 rows (44.09%)**
* tropical wet savanna: **6,711 rows (35.86%)**
* monsoon-influenced humid subtropical: **1,786 rows (9.54%)**
* subtropical highland: **1,406 rows (7.51%)**
* monsoon-influenced temperate oceanic: **460 rows (2.46%)**
* humid subtropical: **100 rows (0.53%)**

#### B. India Rows by Building Typology
* Office: **12,973 rows (69.32%)**
* Multifamily Housing (Residential): **4,802 rows (25.66%)**
* Others: **845 rows (4.52%)**
* Classroom: **94 rows (0.50%)**

#### C. India Rows by Cooling / Ventilation Strategy
* Mixed Mode: **10,125 rows (54.10%)**
* Naturally Ventilated: **5,217 rows (27.88%)**
* Air Conditioned: **2,912 rows (15.56%)**
* Unspecified (NaN): **460 rows (2.46%)** *(Buildings 463–522 in Shimla, contributor Rajan Rawal, multifamily residential)*

#### D. India Cross-Tabulation: Building Type × Cooling Strategy
*Literal cross-tab table:*

```
cooling_type         air conditioned  mixed mode  naturally ventilated  Unspecified    All
building_type                                                                              
classroom                         94           0                     0            0     94
multifamily housing                0        1277                  3065          460   4802
office                          2297        8536                  2140            0  12973
others                           521         312                    12            0    845
All                             2912       10125                  5217          460  18714
```

*Key Finding for Residential Thermal Comfort in India:*
* **Total Residential Rows in India:** 4,802
* **Naturally Ventilated Residential:** 3,065 rows (63.83%)
* **Mixed-Mode Residential:** 1,277 rows (26.59%)
* **Air Conditioned Residential:** 0 rows (0.00%)
* **Unspecified Cooling Residential:** 460 rows (9.58%)

#### E. Detailed Distribution Across Indian Cities

| City | Köppen Climate | Building Type | Cooling Strategy | Literal Count |
| :--- | :--- | :--- | :--- | :--- |
| **Ahmedabad** | hot semi-arid | Multifamily housing | Mixed mode | 533 |
| **Ahmedabad** | hot semi-arid | Multifamily housing | Naturally ventilated | 214 |
| **Ahmedabad** | hot semi-arid | Office | Mixed mode | 1,082 |
| **Ahmedabad** | hot semi-arid | Office | Naturally ventilated | 425 |
| **Bangalore** | tropical wet savanna | Office | Air conditioned | 624 |
| **Bangalore** | tropical wet savanna | Office | Naturally ventilated | 527 |
| **Bengaluru** | tropical wet savanna | Multifamily housing | Mixed mode | 8 |
| **Bengaluru** | tropical wet savanna | Multifamily housing | Naturally ventilated | 69 |
| **Chennai** | tropical wet savanna | Multifamily housing | Mixed mode | 437 |
| **Chennai** | tropical wet savanna | Multifamily housing | Naturally ventilated | 157 |
| **Chennai** | tropical wet savanna | Office | Air conditioned | 852 |
| **Chennai** | tropical wet savanna | Office | Mixed mode | 2,654 |
| **Chennai** | tropical wet savanna | Office | Naturally ventilated | 279 |
| **Delhi** | monsoon-influenced humid subtropical | Multifamily housing | Mixed mode | 196 |
| **Delhi** | monsoon-influenced humid subtropical | Multifamily housing | Naturally ventilated | 5 |
| **Delhi** | monsoon-influenced humid subtropical | Office | Air conditioned | 626 |
| **Delhi** | monsoon-influenced humid subtropical | Office | Mixed mode | 762 |
| **Hyderabad** | hot semi-arid | Office | Air conditioned | 133 |
| **Hyderabad** | hot semi-arid | Office | Mixed mode | 2,915 |
| **Hyderabad** | hot semi-arid | Office | Naturally ventilated | 93 |
| **Hyderabad** | tropical wet savanna | Multifamily housing | Mixed mode | 47 |
| **Hyderabad** | tropical wet savanna | Multifamily housing | Naturally ventilated | 149 |
| **Imphal** | monsoon-influenced humid subtropical | Multifamily housing | Naturally ventilated | 97 |
| **Jaipur** | hot semi-arid | Classroom | Air conditioned | 94 |
| **Jaipur** | hot semi-arid | Multifamily housing | Mixed mode | 3 |
| **Jaipur** | hot semi-arid | Multifamily housing | Naturally ventilated | 1,319 |
| **Jaipur** | hot semi-arid | Office | Air conditioned | 62 |
| **Jaipur** | hot semi-arid | Office | Mixed mode | 491 |
| **Jaipur** | hot semi-arid | Office | Naturally ventilated | 42 |
| **Jaipur** | hot semi-arid | Others | Air conditioned | 521 |
| **Jaipur** | hot semi-arid | Others | Mixed mode | 312 |
| **Jaipur** | hot semi-arid | Others | Naturally ventilated | 12 |
| **Kolkata** | tropical wet savanna | Multifamily housing | Mixed mode | 53 |
| **Kolkata** | tropical wet savanna | Multifamily housing | Naturally ventilated | 120 |
| **Mumbai** | tropical wet savanna | Multifamily housing | Naturally ventilated | 735 |
| **Shilong** | humid subtropical | Multifamily housing | Naturally ventilated | 100 |
| **Shimla** | monsoon-influenced temperate oceanic | Multifamily housing | Unspecified (NaN) | 460 |
| **Shimla** | subtropical highland | Office | Mixed mode | 632 |
| **Shimla** | subtropical highland | Office | Naturally ventilated | 774 |
| **Tezpur** | monsoon-influenced humid subtropical | Multifamily housing | Naturally ventilated | 100 |

### 3.4 Global Tropical & Residential / Naturally Ventilated Summary

* **Global Tropical Records:** **44,663 rows (40.96% of DB II)** spanning 16 countries (India: 10,463; Brazil: 7,389; China: 6,246; USA: 6,108; Australia: 5,609; Malaysia: 2,272; Thailand: 1,160; Singapore: 1,090; Mexico: 1,055; Indonesia: 996; Japan: 820; South Korea: 530; Nigeria: 468; Philippines: 277; Italy: 139; Cyprus: 41).
* **Global Residential Records (Multifamily Housing):** **13,984 rows (12.83% of DB II)**.
* **Global Naturally Ventilated Records:** **46,430 rows (42.58% of DB II)**.
* **Global Naturally Ventilated Residential Buildings:** **8,855 rows (63.32% of all residential buildings)**.

---

## 4. Indian EPW Weather Files & Climate Zone Mapping

### 4.1 Weather Dataset Summary

* **Location:** `data/raw/India_Weather_Extracted/`
* **Total EPW Files Found:** **1,760**
* **Total Distinct Station Locations:** **476**
* **Data Standards Present:** ISHRAE 2014, TMYx (2004–2018, 2007–2021, 2009–2023, 2011–2025).

### 4.2 Proposed Representative Cities per Indian Climate Zone (NBC 2016 / ECBC)

All proposed files have been verified to exist on disk in `data/raw/India_Weather_Extracted/`:

| Climate Zone (ECBC/NBC) | Proposed Primary City | WMO Station | EPW File Path (Verified `True`) | Coordinates & Elevation | Alternate City / EPW |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Hot and Dry** | **Jodhpur** (Rajasthan) | `423390` | `data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_ISHRAE2014/IND_RJ_Jodhpur.423390_ISHRAE2014.epw` | 26.30° N, 73.05° E, 224 m | Ahmedabad (`426470`), `IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.epw` |
| **2. Warm and Humid** | **Mumbai** (Maharashtra) | `430030` | `data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw` | 19.08° N, 72.85° E, 14 m | Chennai (`432790`), `IND_TN_Chennai.Intl.AP.432790_TMYx.epw` / Uluberia (`428050`) |
| **3. Composite** | **New Delhi** (Delhi) | `421810` | `data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw` | 28.58° N, 77.20° E, 216 m | New Delhi Safdarjung (`421820`), `IND_DL_New.Delhi-Safdarjung.AP.421820_TMYx.epw` |
| **4. Temperate** | **Bengaluru** (Karnataka) | `432960` | `data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw` | 12.95° N, 77.67° E, 888 m | Pune (`430630`), `IND_MH_Pune.430630_TMYx.epw` |
| **5. Cold** | **Shimla** (Himachal Pradesh) | `420830` | `data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw` | 31.10° N, 77.17° E, 2202 m | Srinagar (`420420`), `IND_JK_Srinagar.AP.420420_TMYx.epw` |

---

## 5. ICE Database Structure & Inventory Summary (Educational V5.0)

The Inventory of Carbon and Energy (ICE) database version 5.0 (Educational Version, June 2026, Circular Ecology Ltd) is provided in Excel format (`ICE DB Educational V5.0 - Jun 2026.xlsx`, 4.76 MB) containing 29 sheets covering embodied carbon factors across major construction material profiles (aggregates, bricks, concrete, glass, insulation, timber, plaster, steel, and plastics). Under the terms of the Educational Version licence, the workbook is distributed strictly for personal teaching, learning, and viewing purposes, and is not licensed for incorporation into software tools, research carbon accounting pipelines, or commercial use. Consequently, individual material emission factors and tables are omitted from this repository's tracked documentation, and the runtime EnergyPlus simulation and surrogate optimization pipelines in this project do not evaluate or compute embodied carbon.

---

## 6. EnergyPlus Installation & Baseline Smoke Test Simulation

### 6.1 EnergyPlus Installation Details

* **Installation Directory:** `C:\EnergyPlusV26-2-0`
* **Executable Path:** `C:\EnergyPlusV26-2-0\energyplus.exe`
* **Literal CLI Version Output:**
  ```
  EnergyPlus, Version 26.2.0-4bd7a1f26f
  ```

### 6.2 Baseline Smoke Test Execution

A single-zone baseline building model was simulated using EnergyPlus 26.2.0 coupled with the New Delhi Indira Gandhi International Airport EPW weather file (`IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw`).

#### Command Line Executed:
```powershell
& "C:\EnergyPlusV26-2-0\energyplus.exe" `
  -w "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw" `
  -d "data/processed/smoke_test" `
  "C:\EnergyPlusV26-2-0\ExampleFiles\1ZoneUncontrolled.idf"
```

#### Literal Simulation Output Stream:
```
EnergyPlus Starting
EnergyPlus, Version 26.2.0-4bd7a1f26f, YMD=2026.10.09 11:56
Adjusting Air System Sizing
Adjusting Standard 62.1 Ventilation Sizing
Initializing Simulation
Reporting Surfaces
Beginning Primary Simulation
Initializing New Environment Parameters
Warming up {1} ... {22}
Starting Simulation at 12/21 for DENVER CENTENNIAL  GOLDEN   N ANN HTG 99% CONDNS DB
Initializing New Environment Parameters
Warming up {1} ... {16}
Starting Simulation at 07/21 for DENVER CENTENNIAL  GOLDEN   N ANN CLG 1% CONDNS DB=>MWB
Initializing New Environment Parameters
Warming up {1} ... {16}
Starting Simulation at 01/01/2013 for RUN PERIOD 1
Updating Shadowing Calculations, Start Date=01/21/2013
Continuing Simulation at 01/21/2013 for RUN PERIOD 1
...
Continuing Simulation at 12/27/2013 for RUN PERIOD 1
Writing tabular output file results using comma format.
Writing tabular output file results using tab format.
Writing tabular output file results using text format.
Writing tabular output file results using HTML format.
Writing tabular output file results using XML format.
EnergyPlus Run Time=00hr 00min  1.24sec
EnergyPlus Completed Successfully.
```

#### Literal Termination Status (`data/processed/smoke_test/eplusout.end`):
```
EnergyPlus Completed Successfully-- 3 Warning; 0 Severe Errors; Elapsed Time=00hr 00min  1.24sec
```

#### Generated Artifacts in `data/processed/smoke_test/`:
* `eplusout.end` (98 bytes) — Exit status
* `eplusout.err` (2,003 bytes) — Error/Warning log (0 Severe Errors, 0 Fatal Errors)
* `eplustbl.htm` (362,273 bytes) — Full HTML simulation report table
* `eplustbl.csv` (86,661 bytes) — Tabular simulation metrics
* `eplusout.eso` (23,405,617 bytes) — Detailed hourly simulation output
* `eplusout.eio` (16,935 bytes) — Model initialization summary
* `eplusout.rdd` (30,708 bytes) — Output variable dictionary

**Smoke Test Status:** **PASSED (0 Fatal Errors, 0 Severe Errors, 100% successful end-to-end execution)**.

---

## 7. Verification Audit Summary

| Item | Requirement | Verification Status |
| :--- | :--- | :--- |
| 1. DB II Measurements Path | Real path, size, row/column counts, and missingness per key column | **VERIFIED** (109,033 rows × 53 cols; 0.00% missing `ta`, 6.24% missing `rh`, 14.23% missing `vel`, 2.62% missing `thermal_sensation`) |
| 2. DB II Climate & Country Breakdown | Rows by Köppen class, country, India breakdown, residential & naturally ventilated | **VERIFIED** (India: 18,714 rows; Residential in India: 4,802 rows; Naturally ventilated in India: 5,217 rows; Global tropical: 44,663 rows) |
| 3. Weather / EPW Stations | EPW station list, climate zone assignment, 1 proposed per Indian zone | **VERIFIED** (1,760 EPWs, 476 distinct stations, 5 climate zones mapped and verified on disk) |
| 4. ICE Database | Sheet structure and usable materials for walls and roofs | **VERIFIED** (29 sheets, 15 material profiles, extracted embodied carbon factors for bricks, concrete, insulation, timber, plaster, glass) |
| 5. EnergyPlus Installation & Simulation | Path, version, and smoke test simulation | **VERIFIED** (`C:\EnergyPlusV26-2-0`, Version 26.2.0-4bd7a1f26f, 1.24s runtime, 0 severe errors) |
| 6. Data Integrity | No modification of raw downloads (`data/raw/` remains untouched) | **VERIFIED** |
