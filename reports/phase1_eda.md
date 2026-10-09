# Phase 1 Exploratory Data Analysis (EDA) Report

**Generated Date:** 2026-10-09  
**Source Dataset:** `data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz` & `db_metadata.csv`  
**Execution Environment:** Python 3.13.7, pandas 2.3.2, scikit-learn 1.7.1, NumPy 2.2.3  
**Data Integrity Policy:** Built strictly using `data/raw/` only; no raw files were modified or deleted.

---

## 1. Thermal Sensation Distribution in the 3-Class Target

### 1.1 Target Definition & 7-Point to 3-Class Mapping
In international thermal comfort standards (ASHRAE Standard 55, ISO 7730) and comfort modeling benchmarks, the continuous/7-point Thermal Sensation Vote (TSV) is binned into a 3-class target:

$$\text{Class} = \begin{cases} \text{Cool (-1)}, & TSV < -0.5 \\ \text{Neutral (0)}, & -0.5 \le TSV \le 0.5 \\ \text{Warm (+1)}, & TSV > 0.5 \end{cases}$$

### 1.2 Overall Global Distribution (109,033 Rows)

*Literal output from execution:*

| Class Label | TSV Range | Count | % of Total Records | % of Valid Votes ($N=106,171$) |
| :--- | :--- | :--- | :--- | :--- |
| **Neutral (0)** | $[-0.5, +0.5]$ | **51,805** | **47.51%** | **48.80%** |
| **Cool (-1)** | $< -0.5$ | **27,816** | **25.51%** | **26.20%** |
| **Warm (+1)** | $> +0.5$ | **26,550** | **24.35%** | **25.01%** |
| *Missing (NaN)* | — | 2,862 | 2.62% | — |
| **Total** | — | **109,033** | **100.00%** | **100.00%** |

*Underlying Discrete Vote Distribution:*
* `-3` (Cold): 2,752
* `-2` (Cool): 7,639
* `-1` (Slightly Cool): 17,211
* `0` (Neutral): 51,757
* `+1` (Slightly Warm): 17,665
* `+2` (Warm): 6,712
* `+3` (Hot): 2,059
* Non-integer / fractional votes (e.g. -2.5, -1.5, +0.5, etc.): 376 records.

### 1.3 3-Class Target Distribution per Köppen Climate Class

*Literal counts and row percentages across all 31 climate classes:*

| Climate Class (Köppen) | Total Valid Rows | Cool (-1) Count | Cool % | Neutral (0) Count | Neutral % | Warm (+1) Count | Warm % | Missing TSV |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **hot-summer mediterranean** | 21,722 | 6,564 | 30.22% | 10,771 | 49.59% | 4,387 | 20.19% | 0 |
| **humid subtropical** | 14,845 | 3,923 | 26.43% | 6,942 | 46.76% | 3,980 | 26.81% | 412 |
| **hot semi-arid** | 8,300 | 2,042 | 24.60% | 4,213 | 50.76% | 2,045 | 24.64% | 342 |
| **tropical wet savanna** | 8,316 | 1,732 | 20.83% | 3,844 | 46.22% | 2,740 | 32.95% | 67 |
| **tropical savanna** | 6,793 | 1,228 | 18.08% | 3,365 | 49.54% | 2,200 | 32.39% | 187 |
| **warm-summer mediterranean** | 5,741 | 1,029 | 17.92% | 2,933 | 51.09% | 1,779 | 30.99% | 32 |
| **mediterranean** | 4,561 | 1,518 | 33.28% | 2,298 | 50.38% | 745 | 16.33% | 23 |
| **temperate oceanic** | 4,402 | 993 | 22.56% | 2,260 | 51.34% | 1,149 | 26.10% | 20 |
| **monsoon-influenced hot-summer continental** | 3,739 | 903 | 24.15% | 1,939 | 51.86% | 897 | 23.99% | 0 |
| **warm-summer humid continental** | 2,990 | 1,028 | 34.38% | 1,363 | 45.59% | 599 | 20.03% | 0 |
| **tropical monsoon** | 2,084 | 487 | 23.37% | 1,173 | 56.29% | 424 | 20.35% | 17 |
| **hot desert** | 2,083 | 741 | 35.57% | 988 | 47.43% | 354 | 16.99% | 0 |
| **desert (hot arid)** | 1,840 | 563 | 30.60% | 751 | 40.82% | 526 | 28.59% | 171 |
| **humid midlatitude** | 1,944 | 557 | 28.65% | 851 | 43.78% | 536 | 27.57% | 0 |
| **monsoon-influenced humid subtropical** | 1,786 | 500 | 28.00% | 618 | 34.60% | 668 | 37.40% | 0 |
| **temperate** | 1,760 | 363 | 20.62% | 1,023 | 58.12% | 374 | 21.25% | 0 |
| **tropical** | 1,594 | 338 | 21.20% | 887 | 55.65% | 369 | 23.15% | 0 |
| **west coast marine** | 1,489 | 499 | 33.51% | 674 | 45.27% | 316 | 21.22% | 1 |
| **wet equatorial** | 1,414 | 291 | 20.58% | 660 | 46.68% | 463 | 32.74% | 0 |
| **cool-summer mediterranean** | 1,406 | 269 | 19.13% | 868 | 61.74% | 269 | 19.13% | 0 |
| **subtropical highland** | 1,406 | 511 | 36.34% | 556 | 39.55% | 339 | 24.11% | 0 |
| **tropical rainforest** | 1,350 | 240 | 17.78% | 711 | 52.67% | 399 | 29.56% | 0 |
| **hot arid** | 1,229 | 185 | 15.05% | 670 | 54.52% | 374 | 30.43% | 0 |
| **semi arid high altitude** | 1,072 | 192 | 17.91% | 763 | 71.18% | 117 | 10.91% | 0 |
| **semi arid midlatitude** | 1,066 | 234 | 21.95% | 639 | 59.94% | 193 | 18.11% | 0 |
| **temperature marine** | 0 | 0 | 0.00% | 0 | 0.00% | 0 | 0.00% | 1,065 |
| **continental subarctic** | 869 | 277 | 31.88% | 461 | 53.05% | 131 | 15.07% | 0 |
| **monsoon-influenced temperate oceanic** | 0 | 0 | 0.00% | 0 | 0.00% | 0 | 0.00% | 460 |
| **cold semi-arid** | 242 | 58 | 23.97% | 152 | 62.81% | 32 | 13.22% | 0 |
| **tropical dry savanna** | 113 | 11 | 9.73% | 94 | 83.19% | 8 | 7.08% | 39 |
| **subtropical hot and dry** | 41 | 13 | 31.71% | 19 | 46.34% | 9 | 21.95% | 0 |
| **Total Valid Target Rows** | **106,171** | **27,816** | **26.20%** | **51,805** | **48.80%** | **26,550** | **25.01%** | **2,862** |

*Note:* `temperature marine` (1,065 rows in Australia) and `monsoon-influenced temperate oceanic` (460 rows in Shimla, India) have 100% missing `thermal_sensation` votes in the raw dataset.

### 1.4 India-Specific Target Distribution (18,714 Total Rows)
* **Neutral (0):** **8,635 rows (46.14% of total, 47.17% of valid)**
* **Warm (+1):** **4,896 rows (26.16% of total, 26.75% of valid)**
* **Cool (-1):** **4,775 rows (25.52% of total, 26.08% of valid)**
* **Missing TSV:** 408 rows (2.18%)

---

## 2. Statistical Distributions & Physical Anomaly Audit

### 2.1 Distribution Metrics & Percentiles for Physical Variables

*Literal output from pandas calculations on all valid records:*

| Variable | Non-Null Count | Null Count | Min | P01 | P05 | Q1 (25%) | Median | Mean | Q3 (75%) | P95 | P99 | Max | Std | IQR | IQR Outliers Count (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ta` (°C)** | 109,033 | 0 | 9.800 | 18.000 | 20.000 | 22.300 | 24.000 | 24.161 | 25.900 | 29.300 | 32.500 | 40.200 | 2.871 | 3.600 | 2,752 (2.52%) |
| **`tr` (°C)** | 71,043 | 37,990 | 9.300 | 17.500 | 19.900 | 22.400 | 24.100 | 24.375 | 26.100 | 30.000 | 33.600 | 50.000 | 3.149 | 3.700 | 2,059 (2.90%) |
| **`rh` (%)** | 102,234 | 6,799 | 0.000 | 12.800 | 20.000 | 35.000 | 47.000 | 47.167 | 58.700 | 76.000 | 85.000 | 100.000 | 16.038 | 23.700 | 316 (0.31%) |
| **`vel` (m/s)** | 93,515 | 15,518 | 0.000 | 0.000 | 0.010 | 0.050 | 0.100 | 0.205 | 0.200 | 0.700 | 1.620 | 8.500 | 0.320 | 0.150 | 9,842 (10.52%) |
| **`clo` (clo)** | 102,085 | 6,948 | 0.000 | 0.230 | 0.350 | 0.500 | 0.620 | 0.669 | 0.790 | 1.130 | 1.480 | 3.290 | 0.252 | 0.290 | 3,363 (3.29%) |
| **`met` (met)** | 94,346 | 14,687 | 0.600 | 1.000 | 1.000 | 1.100 | 1.200 | 1.229 | 1.300 | 1.600 | 2.100 | 5.600 | 0.257 | 0.200 | 10,753 (11.40%) |

### 2.2 Physical Impossibility & Domain Boundary Audit

*Rigorous verification against thermodynamic, instrument, and human physiology boundaries:*

```
================================================================================
PHYSICAL BOUNDARY & SENSOR PLAUSIBILITY CHECK
================================================================================
ta physically impossible (<=0°C or >=50°C):              0 rows (Min: 9.8°C, Max: 40.2°C)
tr physically impossible (<=0°C or >=60°C):              0 rows (Min: 9.3°C, Max: 50.0°C)
|tr - ta| > 20°C (extreme radiant sensor drift):         0 rows (Max |tr - ta| = 18.3°C)
rh physically impossible (<0% or >100%):                 0 rows (Min: 0.0%, Max: 100.0%)
rh extreme indoor anomalies (<5% or >98%):               6 rows
  - rh = 0.0% (Sensor malfunction):                      1 row  (building_id 169, USA, ta=23.3°C)
  - rh = 1.8% (Extreme dry outlier):                     1 row  (building_id 187, USA, ta=23.0°C)
  - rh = 100.0% (Saturated condensation):                4 rows (building_id 354 Nigeria [3], building_id 651 China [1])
vel physically impossible (<0 m/s or >10 m/s):           0 rows (Min: 0.0 m/s, Max: 8.5 m/s)
vel extreme indoor velocities (>3.0 m/s):                58 rows (Max: 8.5 m/s, building_id 604 China naturally ventilated)
clo physically impossible / zero value (<=0 clo):        6 rows (clo = 0.0, building_id 173 [1], building_id 174 [5] in USA)
clo extreme heavy indoor clothing (>2.5 clo):            14 rows (Max: 3.29 clo, winter field studies in heating climates)
met physically impossible (<=0 met):                     0 rows (Min: 0.6 met)
met extreme heavy work (>4.0 met):                       11 rows (met = 5.6 met, building_id 617 China, workshop activity)
```

*Data Cleaning Recommendation for Modeling Pipeline:*
* Treat the 6 records with `clo == 0.0` and the 1 record with `rh == 0.0` as invalid/missing measurements.
* Air velocity values up to 8.5 m/s and metabolic rates up to 5.6 met represent genuine extreme field events (e.g. strong ceiling fan breeze, workshop physical activity) and should be preserved or clipped with robust scaling.

---

## 3. Climate Class Architecture & Sparse Building Risk (<3 Buildings)

### 3.1 Distinct Buildings and Records per Köppen Climate Class

*Literal output grouped by Köppen climate class:*

| Climate Class | Distinct Buildings | Total Records | Min Rows / Bldg | Median Rows / Bldg | Max Rows / Bldg | % of DB II | Flag: < 3 Buildings |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **hot-summer mediterranean** | 185 | 21,722 | 1 | 80 | 1,029 | 19.92% | False |
| **tropical wet savanna** | 129 | 8,383 | 1 | 42 | 735 | 7.69% | False |
| **humid subtropical** | 124 | 15,257 | 1 | 63 | 1,489 | 13.99% | False |
| **hot semi-arid** | 94 | 8,642 | 1 | 55 | 1,319 | 7.93% | False |
| **tropical savanna** | 76 | 6,980 | 1 | 52 | 525 | 6.40% | False |
| **subtropical highland** | 67 | 1,406 | 1 | 20 | 100 | 1.29% | False |
| **monsoon-influenced humid subtropical** | 35 | 1,786 | 5 | 29 | 506 | 1.64% | False |
| **temperate oceanic** | 27 | 4,422 | 1 | 81 | 1,008 | 4.06% | False |
| **tropical monsoon** | 18 | 2,101 | 35 | 87 | 370 | 1.93% | False |
| **tropical rainforest** | 11 | 1,350 | 48 | 106 | 321 | 1.24% | False |
| **warm-summer mediterranean** | 10 | 5,773 | 17 | 567 | 1,440 | 5.30% | False |
| **mediterranean** | 8 | 4,584 | 43 | 473 | 1,316 | 4.20% | False |
| **monsoon-influenced hot-summer continental**| 6 | 3,739 | 162 | 647 | 1,224 | 3.43% | False |
| **tropical** | 5 | 1,594 | 224 | 298 | 483 | 1.46% | False |
| **cool-summer mediterranean** | 4 | 1,406 | 85 | 379 | 563 | 1.29% | False |
| **temperate** | 3 | 1,760 | 413 | 660 | 687 | 1.61% | False |
| **wet equatorial** | 3 | 1,414 | 184 | 480 | 750 | 1.30% | False |
| **west coast marine** | 3 | 1,490 | 148 | 669 | 673 | 1.37% | False |
| **hot arid** | 3 | 1,229 | 158 | 479 | 592 | 1.13% | False |
| **cold semi-arid** | **2** | 242 | 87 | 121 | 155 | 0.22% | **TRUE (Flagged)** |
| **continental subarctic** | **2** | 869 | 425 | 434 | 444 | 0.80% | **TRUE (Flagged)** |
| **desert (hot arid)** | **2** | 2,011 | 430 | 1,005 | 1,581 | 1.84% | **TRUE (Flagged)** |
| **hot desert** | **2** | 2,083 | 112 | 1,041 | 1,971 | 1.91% | **TRUE (Flagged)** |
| **semi arid high altitude** | **2** | 1,072 | 474 | 536 | 598 | 0.98% | **TRUE (Flagged)** |
| **semi arid midlatitude** | **2** | 1,066 | 468 | 533 | 598 | 0.98% | **TRUE (Flagged)** |
| **humid midlatitude** | **1** | 1,944 | 1,944 | 1,944 | 1,944 | 1.78% | **TRUE (Flagged)** |
| **monsoon-influenced temperate oceanic** | **1** | 460 | 460 | 460 | 460 | 0.42% | **TRUE (Flagged)** |
| **subtropical hot and dry** | **1** | 41 | 41 | 41 | 41 | 0.04% | **TRUE (Flagged)** |
| **temperature marine** | **1** | 1,065 | 1,065 | 1,065 | 1,065 | 0.98% | **TRUE (Flagged)** |
| **tropical dry savanna** | **1** | 152 | 152 | 152 | 152 | 0.14% | **TRUE (Flagged)** |
| **warm-summer humid continental** | **1** | 2,990 | 2,990 | 2,990 | 2,990 | 2.74% | **TRUE (Flagged)** |

### 3.2 Methodological & Validation Implications of Flagged Classes

> [!WARNING]
> **Cross-Validation Leakage Risk:** **12 out of 31 climate classes have fewer than 3 distinct buildings.**
> * Attempting standard 5-fold cross-validation or GroupKFold where entire climate classes are held out as unseen test sets will fail for these 12 classes because test sets would contain only 1 or 2 buildings (high variance, unrepresentative evaluation).
> * In particular, single-building classes (`warm-summer humid continental` with 2,990 rows in 1 building, `humid midlatitude` with 1,944 rows in 1 building) conflate building-specific idiosyncrasies (e.g. occupant dress code, specific HVAC schedule) with climate-level thermal adaptation.
> * **Recommendation:** Use **GroupKFold grouped on `building_id`** within robust multi-building climate clusters, and hold out well-populated climate zones (e.g., `tropical wet savanna`, `hot semi-arid`, `humid subtropical`) as unseen holdout domains.

---

## 4. Complete-Case Analysis for Candidate Core Feature Sets

To prevent data starvation during model training, candidate feature sets were evaluated across global, India, and naturally ventilated subsets:

*Literal output from complete-case audit:*

| Candidate Feature Set | Features Included | Global Complete Rows | Global Retained % | India Complete Rows | India Retained % | NV Complete Rows | NV Retained % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Set A: 6 Standard Physics + TSV** | `ta, tr, rh, vel, clo, met, tsv` | **58,512** | **53.66%** | **4,642** | **24.81%** | **23,845** | **51.36%** |
| **Set B: 5 Features (no $T_r$) + TSV** | `ta, rh, vel, clo, met, tsv` | **82,789** | **75.93%** | **9,796** | **52.35%** | **37,794** | **81.40%** |
| **Set C: Operative Temp + 4 + TSV** | `top, rh, vel, clo, met, tsv` | **38,266** | **35.10%** | **4,736** | **25.31%** | **18,740** | **40.36%** |
| **Set D: 6 Physics + Outdoor Temp + TSV**| `ta, tr, rh, vel, clo, met, t_out, tsv`| **42,887** | **39.33%** | **4,370** | **23.35%** | **17,597** | **37.90%** |
| **Set E: 6 Physics + Running Mean + TSV**| `ta, tr, rh, vel, clo, met, t_mot_isd, tsv`| **41,328** | **37.90%** | **4,370** | **23.35%** | **17,329** | **37.32%** |
| **Set F: 6 Physics + TSV + PMV** | `ta, tr, rh, vel, clo, met, tsv, pmv` | **51,968** | **47.66%** | **1,227** | **6.56%** | **23,845** | **51.36%** |

### 4.1 Missingness Breakdown in Standard 6 Physics Set (Set A)

```
Missingness Combination Pattern                      Row Count   % of Database
-------------------------------------------------------------------------------
All 7 variables present (Complete Case)                 58,512          53.66%
Only tr missing (ta, rh, vel, clo, met, tsv present)    24,277          22.27%
Only met missing                                         4,806           4.41%
tr, met, and vel missing                                 3,384           3.10%
Only vel missing                                         3,269           3.00%
All 7 variables missing (unpopulated record)             2,487           2.28%
tr, clo, and vel missing                                 2,202           2.02%
tr and met missing                                       2,101           1.93%
Only clo missing                                         1,889           1.73%
tr and vel missing                                       1,489           1.37%
```

> [!TIP]
> **Key Architectural Insight on Mean Radiant Temperature ($T_r$):**
> * Missing $T_r$ accounts for **24,277 dropped rows (22.27% of DB II)** and over **5,154 dropped rows in India**.
> * When $T_r$ is measured, the correlation between $T_a$ and $T_r$ is extremely strong ($r = 0.963$, mean absolute difference $|T_r - T_a| = 0.82^\circ\text{C}$).
> * Modeling strategies that support either $T_r \approx T_a$ approximation or dedicated imputation / multi-branch architectures can expand usable training data from **58,512 rows to 82,789 rows globally** (+41.5% training volume) and from **4,642 to 9,796 rows in India** (+111.0% volume).

---

## 5. PMV & Adaptive Comfort Baseline Benchmarks (Full Data)

Both classical thermal comfort baselines were evaluated on the full data using macro-averaged F1 score, precision, recall, and class-wise performance.

### 5.1 Fanger's PMV Model Baseline
Predicted PMV is discretized using the standard 3-class thresholds ($\text{Cool} < -0.5 \le \text{Neutral} \le +0.5 < \text{Warm}$).

*Literal Performance Metrics:*

| Evaluation Domain | Sample Size ($N$) | Accuracy | Macro-F1 | Weighted-F1 | Macro-Precision | Macro-Recall | F1: Cool (-1) | F1: Neutral (0) | F1: Warm (+1) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PMV (Full Available Data)** | **51,968** | **41.70%** | **0.3999** | **0.4082** | **0.4262** | **0.4072** | 0.3869 | 0.4771 | 0.3357 |
| **PMV (Air Conditioned Only)** | **22,008** | **41.09%** | **0.3662** | **0.3803** | **0.4376** | **0.3862** | 0.4065 | 0.4900 | 0.2022 |
| **PMV (Naturally Ventilated Only)** | **23,845** | **41.50%** | **0.4047** | **0.4156** | **0.4163** | **0.4165** | 0.3598 | 0.4555 | 0.3988 |
| **PMV (India Subset)** | **1,227** | **41.56%** | **0.4049** | **0.4305** | **0.4218** | **0.4508** | 0.5284 | 0.3730 | 0.3133 |

*Literal Confusion Matrix — PMV Full Data ($N=51,968$):*
```
                  Predicted Cool (-1)  Predicted Neutral (0)  Predicted Warm (+1)
True Cool (-1)                   5,566                  6,276                1,005
True Neutral (0)                 6,853                 11,765                3,354
True Warm (+1)                   3,505                  9,305                4,339
```

### 5.2 Adaptive Comfort Model Baseline (ASHRAE 55 / EN 16798-1)
Neutral comfort temperature: $T_{comf} = 17.8 + 0.31 \times T_{mot}$ (using running mean outdoor temperature $T_{mot}$).  
* 80% Acceptability Band: $T_{comf} \pm 3.5^\circ\text{C}$  
* 90% Acceptability Band: $T_{comf} \pm 2.5^\circ\text{C}$  

*Literal Performance Metrics:*

| Model & Evaluation Domain | Sample Size ($N$) | Accuracy | Macro-F1 | Weighted-F1 | Macro-Precision | Macro-Recall | F1: Cool (-1) | F1: Neutral (0) | F1: Warm (+1) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Adaptive 80% (Naturally Ventilated)** | **31,443** | **50.81%** | **0.4543** | **0.4857** | **0.5486** | **0.4526** | 0.2978 | 0.5682 | 0.4968 |
| **Adaptive 90% (Naturally Ventilated)** | **31,443** | **51.63%** | **0.4834** | **0.5071** | **0.5213** | **0.4765** | 0.3506 | 0.5201 | 0.5794 |
| **Adaptive 80% (Full Available Data)** | **77,892** | **48.03%** | **0.4176** | **0.4439** | **0.5227** | **0.4268** | 0.2634 | 0.5702 | 0.4190 |
| **Adaptive 90% (Full Available Data)** | **77,892** | **48.33%** | **0.4597** | **0.4729** | **0.4965** | **0.4559** | 0.3557 | 0.5223 | 0.5011 |
| **Adaptive 80% (India Naturally Vent)** | **4,357** | **47.60%** | **0.4447** | **0.4559** | **0.4681** | **0.4543** | 0.2633 | 0.5248 | 0.5461 |

*Literal Confusion Matrix — Adaptive 90% Naturally Ventilated ($N=31,443$):*
```
                  Predicted Cool (-1)  Predicted Neutral (0)  Predicted Warm (+1)
True Cool (-1)                   1,719                  3,739                1,049
True Neutral (0)                 1,394                  7,573                4,274
True Warm (+1)                     185                  4,569                6,941
```

### 5.3 Consolidated Baseline Comparison Table

| Baseline Model | Dataset Scope | $N$ | Accuracy | Macro-F1 | Weighted-F1 | Primary Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PMV (Fanger)** | Full Database | 51,968 | 41.70% | **0.3999** | 0.4082 | Poor sensitivity to Warm discomfort in real environments (F1 Warm = 0.3357) |
| **PMV (Fanger)** | AC Buildings | 22,008 | 41.09% | **0.3662** | 0.3803 | Over-predicts Neutrality in AC settings (F1 Warm = 0.2022) |
| **PMV (Fanger)** | Naturally Ventilated | 23,845 | 41.50% | **0.4047** | 0.4156 | Rigid thermal physics ignores adaptive physiological/behavioral mechanisms |
| **Adaptive 80% Band**| Naturally Ventilated | 31,443 | 50.81% | **0.4543** | 0.4857 | $\pm 3.5^\circ\text{C}$ band is too wide, classifying Cool discomfort as Neutral (F1 Cool = 0.2978) |
| **Adaptive 90% Band**| Naturally Ventilated | 31,443 | 51.63% | **0.4834** | 0.5071 | Better balance across Neutral and Warm, but still weak on Cool discomfort |
| **Adaptive 80% Band**| India Naturally Vent | 4,357 | 47.60% | **0.4447** | 0.4559 | Static linear slope fails under monsoon humidity shifts and fan usage |

---

## 6. Verification Summary & Next Step Directives

| Requirement | Audit Finding | Status |
| :--- | :--- | :--- |
| **(1) 3-Class Target Distribution** | Global: Neutral 47.51%, Cool 25.51%, Warm 24.35%, Missing 2.62%. India: Neutral 46.14%, Warm 26.16%, Cool 25.52%. Full breakdown across all 31 Köppen classes documented. | **VERIFIED** |
| **(2) Statistical Distributions & Anomalies** | Full min/max/IQR/percentile table computed. 0 impossible temperatures ($T_a, T_r$); 6 zero-clothing anomalies ($clo=0$), 1 zero-humidity anomaly ($rh=0\%$) flagged. | **VERIFIED** |
| **(3) Distinct Buildings & <3 Flagging** | 12 out of 31 climate classes flagged with $<3$ buildings. GroupKFold grouped on `building_id` mandatory to prevent leakage. | **VERIFIED** |
| **(4) Complete-Case Rows** | Set A (6 Physics + TSV): 58,512 rows (53.66%). Set B (5 Features without $T_r$): 82,789 rows (75.93%). Missing $T_r$ identified as main bottleneck. | **VERIFIED** |
| **(5) Baseline Macro-F1 Benchmarks** | PMV Macro-F1 = **0.3999** (Accuracy 41.70%). Adaptive 90% Macro-F1 = **0.4834** (Accuracy 51.63%). All metrics, confusion matrices, and sub-domain tables recorded. | **VERIFIED** |
| **Data Integrity Policy** | `data/raw/` untouched; all calculations executed directly via Python CLI. | **VERIFIED** |
