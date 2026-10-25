# Phase 1 Exploratory Data Analysis (EDA) Report (Regenerated from Verified Literal Outputs)

**Generated Date:** 2026-10-09  
**Source Dataset:** `data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz` & `db_metadata.csv`  
**Execution Evidence:** `reports/evidence/phase1_eda_calc_output.txt`  
**Execution Environment:** Python 3.13.7, pandas 2.3.2, scikit-learn 1.7.1, NumPy 2.2.3  
**Data Integrity Policy:** Built strictly using `data/raw/` only; no raw files were modified or deleted.

---

## 1. Thermal Sensation Distribution in the 3-Class Target

### 1.1 Target Definition & 7-Point to 3-Class Mapping
In thermal comfort standards (ASHRAE Standard 55, ISO 7730) and project decision **D-003a**, the continuous/7-point Thermal Sensation Vote (TSV) is binned into a 3-class target:

$$\text{Class} = \begin{cases} \text{Cool (-1)}, & TSV < -0.5 \\ \text{Neutral (0)}, & -0.5 \le TSV \le 0.5 \\ \text{Warm (+1)}, & TSV > 0.5 \end{cases}$$

### 1.2 Overall Global Distribution (109,033 Raw Merged Rows)

*Literal output from verified script:*

| Class Label | TSV Range | Count | % of Total Records ($N=109,033$) | % of Valid Votes ($N=106,171$) |
| :--- | :--- | :--- | :--- | :--- |
| **Neutral (0)** | $[-0.5, +0.5]$ | **51,805** | **47.51%** | **48.80%** |
| **Cool (-1)** | $< -0.5$ | **27,816** | **25.51%** | **26.20%** |
| **Warm (+1)** | $> +0.5$ | **26,550** | **24.35%** | **25.01%** |
| *Missing (NaN)* | — | 2,862 | 2.62% | — |
| **Total** | — | **109,033** | **100.00%** | **100.00%** |

### 1.3 3-Class Target Distribution per Köppen Climate Class

*Literal counts and distributions across all 31 climate classes:*

| Climate Class (Köppen) | Cool (-1) | Neutral (0) | Warm (+1) | Missing (NaN) | Total Raw Rows |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **cold semi-arid** | 58 | 152 | 32 | 0 | 242 |
| **continental subarctic** | 277 | 461 | 131 | 0 | 869 |
| **cool-summer mediterranean** | 269 | 868 | 269 | 0 | 1,406 |
| **desert (hot arid)** | 563 | 751 | 526 | 171 | 2,011 |
| **hot arid** | 185 | 670 | 374 | 0 | 1,229 |
| **hot desert** | 741 | 988 | 354 | 0 | 2,083 |
| **hot semi-arid** | 2,042 | 4,213 | 2,045 | 342 | 8,642 |
| **hot-summer mediterranean** | 6,564 | 10,771 | 4,387 | 0 | 21,722 |
| **humid midlatitude** | 557 | 851 | 536 | 0 | 1,944 |
| **humid subtropical** | 3,923 | 6,942 | 3,980 | 412 | 15,257 |
| **mediterranean** | 1,518 | 2,298 | 745 | 23 | 4,584 |
| **monsoon-influenced hot-summer continental** | 903 | 1,939 | 897 | 0 | 3,739 |
| **monsoon-influenced humid subtropical** | 500 | 618 | 668 | 0 | 1,786 |
| **monsoon-influenced temperate oceanic** | 0 | 0 | 0 | 460 | 460 |
| **semi arid high altitude** | 192 | 763 | 117 | 0 | 1,072 |
| **semi arid midlatitude** | 234 | 639 | 193 | 0 | 1,066 |
| **subtropical highland** | 511 | 556 | 339 | 0 | 1,406 |
| **subtropical hot and dry** | 13 | 19 | 9 | 0 | 41 |
| **temperate** | 363 | 1,023 | 374 | 0 | 1,760 |
| **temperate oceanic** | 993 | 2,260 | 1,149 | 20 | 4,422 |
| **temperature marine** | 0 | 0 | 0 | 1,065 | 1,065 |
| **tropical** | 338 | 887 | 369 | 0 | 1,594 |
| **tropical dry savanna** | 11 | 94 | 8 | 39 | 152 |
| **tropical monsoon** | 487 | 1,173 | 424 | 17 | 2,101 |
| **tropical rainforest** | 240 | 711 | 399 | 0 | 1,350 |
| **tropical savanna** | 1,228 | 3,365 | 2,200 | 187 | 6,980 |
| **tropical wet savanna** | 1,732 | 3,844 | 2,740 | 67 | 8,383 |
| **warm-summer mediterranean** | 1,029 | 2,933 | 1,779 | 32 | 5,773 |
| **warm-summer humid continental** | 1,028 | 1,363 | 599 | 0 | 2,990 |
| **west coast marine** | 499 | 674 | 316 | 1 | 1,490 |
| **wet equatorial** | 291 | 660 | 463 | 0 | 1,414 |
| **Total** | **27,816** | **51,805** | **26,550** | **2,862** | **109,033** |

### 1.4 India-Specific Target Distribution (18,714 Total Rows)
* **Neutral (0):** **8,635 rows** (46.14% of total, 47.17% of valid TSV)
* **Warm (+1):** **4,896 rows** (26.16% of total, 26.75% of valid TSV)
* **Cool (-1):** **4,775 rows** (25.52% of total, 26.08% of valid TSV)
* **Missing TSV:** **408 rows** (2.18%)

---

## 2. Statistical Distributions & Physical Anomaly Audit

### 2.1 Distribution Metrics & Percentiles for Physical Variables

*Literal output calculated from raw data:*

| Variable | Non-Null | Null | Missing % | Min | P01 | P05 | Q1 (25%) | Median | Mean | Q3 (75%) | P95 | P99 | Max | Std | IQR | IQR Outliers Count (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ta` (°C)** | 109,033 | 0 | 0.00% | 9.800 | 18.000 | 20.000 | 22.300 | 24.000 | 24.161 | 25.900 | 29.300 | 32.500 | 40.200 | 2.871 | 3.600 | 2,752 (2.52%) |
| **`tr` (°C)** | 71,043 | 37,990 | 34.84% | 9.300 | 17.500 | 19.900 | 22.400 | 24.100 | 24.375 | 26.100 | 30.000 | 33.600 | 50.000 | 3.149 | 3.700 | 2,059 (2.90%) |
| **`rh` (%)** | 102,234 | 6,799 | 6.24% | 2.000 | 12.800 | 20.000 | 35.000 | 47.000 | 47.167 | 58.700 | 76.000 | 85.000 | 100.000 | 16.038 | 23.700 | 316 (0.31%) |
| **`vel` (m/s)** | 93,515 | 15,518 | 14.23% | 0.000 | 0.000 | 0.010 | 0.050 | 0.100 | 0.205 | 0.200 | 0.700 | 1.620 | 8.500 | 0.320 | 0.150 | 9,842 (10.52%) |
| **`clo` (clo)** | 102,085 | 6,948 | 6.37% | 0.030 | 0.230 | 0.350 | 0.500 | 0.620 | 0.669 | 0.790 | 1.130 | 1.480 | 3.290 | 0.252 | 0.290 | 3,363 (3.29%) |
| **`met` (met)** | 94,346 | 14,687 | 13.47% | 0.600 | 1.000 | 1.000 | 1.100 | 1.200 | 1.229 | 1.300 | 1.600 | 2.100 | 5.600 | 0.257 | 0.200 | 10,753 (11.40%) |

### 2.2 Boundary Audit
* `ta <= 0` or `ta >= 50`: **0 rows** (Min: 9.8°C, Max: 40.2°C).
* `tr <= 0` or `tr >= 60`: **0 rows** (Min: 9.3°C, Max: 50.0°C).
* `rh <= 0` or `rh > 100`: **0 rows** (Min: 2.0%, Max: 100.0%).
* `vel < 0` or `vel > 10`: **0 rows** (Min: 0.0 m/s, Max: 8.5 m/s).
* `clo <= 0` or `clo > 4`: **0 rows** (Min: 0.03 clo, Max: 3.29 clo).
* `met <= 0` or `met > 6`: **0 rows** (Min: 0.6 met, Max: 5.6 met).

---

## 3. Climate Classes & Sparse Building Audit (<3 Buildings)

### 3.1 Distinct Buildings and Records per Köppen Class

*Literal output grouped by raw `climate`:*

| Climate Class | Distinct Buildings | Total Rows | Min Rows / Bldg | Median Rows / Bldg | Max Rows / Bldg | % of DB II | Flag: < 3 Buildings |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **tropical wet savanna** | 162 | 8,383 | 1 | 34.0 | 735 | 7.69% | False |
| **hot semi-arid** | 101 | 8,642 | 1 | 7.0 | 1,830 | 7.93% | False |
| **humid subtropical** | 61 | 15,257 | 3 | 137.0 | 2,069 | 13.99% | False |
| **monsoon-influenced temperate oceanic** | 60 | 460 | 1 | 6.0 | 27 | 0.42% | False |
| **tropical savanna** | 55 | 6,980 | 12 | 61.0 | 608 | 6.40% | False |
| **hot-summer mediterranean** | 41 | 21,722 | 4 | 121.0 | 1,982 | 19.92% | False |
| **monsoon-influenced humid subtropical** | 39 | 1,786 | 2 | 12.0 | 525 | 1.64% | False |
| **hot arid** | 38 | 1,229 | 10 | 25.5 | 95 | 1.13% | False |
| **temperate oceanic** | 37 | 4,422 | 12 | 104.0 | 421 | 4.06% | False |
| **mediterranean** | 31 | 4,584 | 23 | 123.0 | 442 | 4.20% | False |
| **temperate** | 30 | 1,760 | 1 | 35.0 | 251 | 1.61% | False |
| **continental subarctic** | 23 | 869 | 6 | 40.0 | 44 | 0.80% | False |
| **west coast marine** | 20 | 1,490 | 6 | 31.0 | 496 | 1.37% | False |
| **hot desert** | 16 | 2,083 | 1 | 85.5 | 587 | 1.91% | False |
| **monsoon-influenced hot-summer continental**| 15 | 3,739 | 11 | 221.0 | 607 | 3.43% | False |
| **tropical rainforest** | 15 | 1,350 | 7 | 43.0 | 399 | 1.24% | False |
| **wet equatorial** | 9 | 1,414 | 41 | 97.0 | 583 | 1.30% | False |
| **warm-summer mediterranean** | 8 | 5,773 | 134 | 540.0 | 1,920 | 5.29% | False |
| **tropical** | 8 | 1,594 | 23 | 124.5 | 629 | 1.46% | False |
| **temperature marine** | 7 | 1,065 | 16 | 102.0 | 411 | 0.98% | False |
| **cold semi-arid** | 6 | 242 | 1 | 8.0 | 112 | 0.22% | False |
| **desert (hot arid)** | 5 | 2,011 | 190 | 436.0 | 491 | 1.84% | False |
| **humid midlatitude** | 5 | 1,944 | 44 | 390.0 | 988 | 1.78% | False |
| **subtropical highland** | 4 | 1,406 | 207 | 333.0 | 533 | 1.29% | False |
| **tropical monsoon** | 3 | 2,101 | 27 | 914.0 | 1,160 | 1.93% | False |
| **warm-summer humid continental** | **2** | 2,990 | 748 | 1,495.0 | 2,242 | 2.74% | **TRUE (Flagged)** |
| **cool-summer mediterranean** | **2** | 1,406 | 661 | 703.0 | 745 | 1.29% | **TRUE (Flagged)** |
| **semi arid high altitude** | **2** | 1,072 | 504 | 536.0 | 568 | 0.98% | **TRUE (Flagged)** |
| **semi arid midlatitude** | **2** | 1,066 | 511 | 533.0 | 555 | 0.98% | **TRUE (Flagged)** |
| **tropical dry savanna** | **1** | 152 | 152 | 152.0 | 152 | 0.14% | **TRUE (Flagged)** |
| **subtropical hot and dry** | **1** | 41 | 41 | 41.0 | 41 | 0.04% | **TRUE (Flagged)** |

*Result:* Exactly **6 climate classes** have $< 3$ distinct buildings (totaling 6,727 rows, 6.17% of database).

---

## 4. Complete-Case Analysis for Candidate Feature Sets

*Literal counts per candidate feature set:*

| Feature Set Name | Features Included | Global Rows | Global % | India Rows | India % | NV Rows | NV % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Set A: 6 Physics + TSV** | `ta, tr, rh, vel, clo, met, tsv` | **58,512** | **53.66%** | **2,170** | **11.60%** | **29,207** | **62.91%** |
| **Set B: 5 Features (no $T_r$) + TSV** | `ta, rh, vel, clo, met, tsv` | **82,789** | **75.93%** | **18,061** | **96.51%** | **35,791** | **77.09%** |
| **Set C: $T_{op}$ + 4 Features + TSV** | `top, rh, vel, clo, met, tsv` | **32,321** | **29.64%** | **2,170** | **11.60%** | **17,883** | **38.52%** |
| **Set D: 6 Physics + $T_{out}$ + TSV**| `ta, tr, rh, vel, clo, met, t_out, tsv` | **34,175** | **31.34%** | **2,170** | **11.60%** | **16,337** | **35.19%** |
| **Set E: 6 Physics + $T_{mot}$ + TSV**| `ta, tr, rh, vel, clo, met, t_mot_isd, tsv` | **27,254** | **25.00%** | **2,094** | **11.19%** | **11,857** | **25.54%** |
| **Set F: 6 Physics + TSV + PMV** | `ta, tr, rh, vel, clo, met, tsv, pmv` | **51,968** | **47.66%** | **1,227** | **6.56%** | **23,845** | **51.36%** |

*True Tropical Raw Breakdown (Group A):*
* **Total True Tropical Rows in DB II:** **21,974 rows (20.15% of DB II)** across 7 classes: `tropical wet savanna` (8,383), `tropical savanna` (6,980), `tropical monsoon` (2,101), `tropical` (1,594), `wet equatorial` (1,414), `tropical rainforest` (1,350), `tropical dry savanna` (152).
* Clean Complete Cases in Group A: **8,968 rows** (40.81% retention; 59.19% row loss due to missing $T_r$).

---

## 5. Reference Baseline Benchmarks (Raw Subsets)

*Reference metrics scored on available subsets (superseded in Phase 2 for identical-row evaluations per D-007):*

| Baseline Model | Subdomain Evaluated | Sample Size ($N$) | Accuracy | Macro-F1 |
| :--- | :--- | :--- | :--- | :--- |
| **PMV (Fanger)** | Full Available Data (where PMV & TSV exist) | 51,968 | 41.70% | **0.3999** |
| **Adaptive 90% Band** | Naturally Ventilated (where $T_{mot}$ & TSV exist) | 31,443 | 51.63% | **0.4834** |
| **Adaptive 90% Band** | Full Available Data | 77,892 | 48.33% | **0.4597** |
