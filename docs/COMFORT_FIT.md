# Comfort Fit Score & Area Norms Specification (docs/COMFORT_FIT.md)

Project: ClimateAdapt-Comfort v2  
Document Version: 1.0.0  
Last Updated: 2026-10-25  
Status: Verified & Exported to `data/export/city_comfort_norms.json`  

---

## 1. Executive Summary & Product Flow Context

In the 5-step ClimateAdapt-Comfort decision-support flow:
- **Step 1:** Location selection and nearest climate station matching.
- **Step 2:** Climate data loading and applicability/confidence tier display.
- **Step 3 (Area Norms):** Presenting typical outdoor climate and typical building performance for the region alongside DB II empirical occupant satisfaction.
- **Step 4 (User Profile & Fit Scoring):** Gathering the resident's specific comfort preferences and computing an individualized **Comfort Fit Score (0–100)** with deterministic bilingual explanations.
- **Step 5:** Presenting 3 curated passive design packages (Budget, Balanced, Best-Comfort) with full BOM, cost ranges, and 12-month temperature profiles.

---

## 2. City Comfort Norms Methodology (`src/comfort/city_norms.py`)

All city comfort norms are derived strictly from real, verifiable data sources and exported to [data/export/city_comfort_norms.json](file:///c:/Users/vardh/OneDrive/Comfort-home-main/data/export/city_comfort_norms.json):

1. **Monthly Outdoor Climate Summary (EPW):**
   - Extracted directly from official TMYx weather files (`data/raw/India_Weather_Extracted/`).
   - For all 12 months: Mean, minimum, and maximum dry-bulb temperatures ($T_{\text{db}}$), mean and extreme relative humidity ($\text{RH}$), and share of hours in ASHRAE 55 Adaptive 90% outcomes (comfortable, too warm, too cool).
2. **Typical Local Building Baseline Performance:**
   - Evaluated from the conventional reference building (`R2_Conventional`, medium-mass clay brick, uninsulated, free-running mode).
   - Tracks monthly $O_{1,\text{adapt}}$, $O_{1,\text{ml}}$, warm %, cool %, and annual $O_2$ heating/cooling energy intensity ($\text{kWh/m}^2/\text{yr}$).
3. **Applicability Domain & Confidence Tiers (Decision D-017):**
   - **Bengaluru, Mumbai:** **Medium Confidence** (Spearman $r_s \ge 0.8$ and Adaptive 90% validity $\ge 80\%$; Bengaluru $r_s = 0.942$, Adapt $100.0\%$; Mumbai $r_s = 0.946$, Adapt $100.0\%$).
   - **New Delhi, Jodhpur, Shimla:** **Low Confidence** (New Delhi $r_s = 0.190 < 0.8$; Jodhpur $r_s = 0.099 < 0.8$; Shimla $r_s = 0.867$, but Adapt validity $73.97\% < 80\%$ due to winter heating boundary violation per D-011).

---

## 3. Thin Data & Zero-Fabrication Disclosures

In accordance with project rules (*"Do not fabricate to fill gaps. Missing data stays missing"*), empirical occupant preferences from the ASHRAE Global Thermal Comfort Database II are reported with complete transparency:

| Reference Station | Climate Zone | DB II India Sample Scope | Building Count | Row Count | Labelled Votes | Empirical Vote Breakdown (Cool / Neutral / Warm) | Median Neutral $T_a$ | Thin Data / Integrity Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Jodhpur** | Hot-Dry (BWh/BSh) | Koppen Group B (Ahmedabad & Jaipur) | 88 bldgs | 4,498 | Yes | 30.3% / 38.0% / 31.7% | $27.0^\circ\text{C}$ | DB II lacks a station inside Jodhpur municipal limits; matched to regional Group B cohort. |
| **Mumbai** | Warm-Humid (Aw) | Mumbai city records | 15 bldgs | 2,246 | Yes | 28.5% / 45.2% / 26.3% | $26.5^\circ\text{C}$ | Coastal urban sample; fans prevalent in 100% of buildings. |
| **New Delhi** | Composite (Cwa) | Delhi NCR records | 31 bldgs | 3,115 | Yes | 27.2% / 46.1% / 26.7% | $26.0^\circ\text{C}$ | Strong seasonal dichotomy captured in votes. |
| **Bengaluru** | Temperate (Aw/Cfb) | Bengaluru records | 36 bldgs | 4,028 | Yes | 31.8% / 51.4% / 16.8% | $24.8^\circ\text{C}$ | Highest neutral satisfaction rate (51.4%) across Indian DB II cohorts. |
| **Shimla** | Cold (Cwb) | Shimla records | 64 bldgs | 460 | **No (0 votes)** | **None (Reported as null)** | **None (Reported as null)** | **Decision D-011:** Shimla has 64 buildings in DB II, but exactly 0 labelled votes (all 460 rows NaN). Preference statistics are reported as unavailable; **NEVER fabricated**. |

---

## 4. User Comfort Profile Schema (`src/comfort/profile.py`)

The bilingual (English / Hindi) questionnaire captures 6 dimensions:
1. **Seasonal Feel:** 7-point ASHRAE thermal sensation scale (-3 Cold to +3 Hot) for Summer, Winter, and Monsoon.
2. **Sensitivity:** Heat sensitive ($w_{\text{warm}} = 1.35, w_{\text{cool}} = 0.75$), Balanced ($1.0 / 1.0$), or Cold sensitive ($0.75 / 1.35$).
3. **Clothing & Activity:** Summer (0.45 to 0.85 clo), Winter (0.75 to 1.35 clo), metabolic rate (1.0 to 1.6 met), occupied hours (4 to 24 h/day).
4. **Cooling Equipment:** Available equipment (none, fan, cooler, AC) and willingness to run active cooling.
5. **Priorities:** Sliders summing to 100% for Comfort ($W_{\text{comfort}}$), Energy ($W_{\text{energy}}$), and Cost ($W_{\text{cost}}$).
6. **Special Needs:** Elderly ($+0.20$ cold penalty), Infants ($+0.15$ both), Work-from-home (extends daytime occupied hours to $\ge 22\text{ h/day}$).

> [!NOTE]
> **User Override Mode:**  
> User responses are mapped to Post-Hoc post-processing overrides (`user_clo`, `user_met`, `user_occupied_hours`). They **never silently alter the project's locked baseline simulation assumptions A-001..A-007**.

---

## 5. Comfort Fit Score Mathematical Formulation (`src/comfort/fit.py`)

For any candidate design and its reference building:

### 5.1 Dual-Judge Evaluation & Disagreement
- ML Champion discomfort: $O_{1,\text{ml}} = \text{warm\_ml} + \text{cool\_ml}$
- Physical Adaptive 90% discomfort: $O_{1,\text{adapt}}$
- Dual-judge consensus discomfort:
  $$O_{1,\text{dual}} = \frac{O_{1,\text{ml}} + O_{1,\text{adapt}}}{2.0}$$
- Dual-judge disagreement:
  $$\Delta_{\text{judge}} = |O_{1,\text{ml}} - O_{1,\text{adapt}}| \quad [\text{percentage points}]$$

### 5.2 User-Weighted Discomfort
Applying user sensitivity weights $w_{\text{warm}}$ and $w_{\text{cool}}$ (mean $\bar{w} = (w_{\text{warm}} + w_{\text{cool}}) / 2.0$):
$$D_{\text{ml}} = w_{\text{warm}} \times \text{warm\_ml} + w_{\text{cool}} \times \text{cool\_ml}$$
$$D_{\text{adapt}} = O_{1,\text{adapt}} \times \bar{w}$$
$$D_{\text{weighted}} = 0.5 \times D_{\text{ml}} + 0.5 \times D_{\text{adapt}}$$

### 5.3 Component Sub-Scores (0 to 100)
1. **Comfort Sub-Score:**
   $$S_{\text{comfort}} = \max\left(0.0, \min\left(100.0, 100.0 - D_{\text{weighted}}\right)\right)$$
2. **Energy Sub-Score:**
   $$\text{Relative Energy} = \frac{O_{2,\text{design}}}{O_{2,\text{ref}}}$$
   $$S_{\text{energy}} = \begin{cases} \min(100.0, 50.0 + 50.0 \times (1.0 - \text{Relative Energy})), & \text{if Relative Energy} \le 1.0 \\ \max(0.0, 50.0 - 50.0 \times (\text{Relative Energy} - 1.0)), & \text{if Relative Energy} > 1.0 \end{cases}$$
3. **Cost Sub-Score:**
   - Baseline reference building scores 70.0.
   - If cost estimate is loaded: Lower capital cost awards up to 95; high investment scales down toward 30.
   - If cost estimate is unavailable (rates null): Neutral 70.0.

### 5.4 Overall Comfort Fit Score (0 to 100)
$$\text{Fit Score} = \text{round}\left(W_{\text{comfort}} \times S_{\text{comfort}} + W_{\text{energy}} \times S_{\text{energy}} + W_{\text{cost}} \times S_{\text{cost}}, 1\right)$$
where $W_{\text{comfort}} + W_{\text{energy}} + W_{\text{cost}} = 1.0$.

### 5.5 Area Comparison & Comfort Gain
$$\text{Comfort Gain} = \text{Fit Score}_{\text{design}} - \text{Fit Score}_{\text{ref}} \quad [\text{points}]$$
$$\text{Discomfort Reduction} = O_{1,\text{dual, ref}} - O_{1,\text{dual, design}} \quad [\% \text{ of year}]$$

---

## 6. Deterministic Bilingual Explanation Templates

All text strings shown to users are generated through deterministic template substitution without external LLMs:

- **English Example (Jodhpur):**
  > *"This package achieves a strong Comfort Fit Score of 78.6/100, outperforming the local typical building by +32.9 points. Annual discomfort is reduced from 50.7% down to 19.8%. Given your sensitivity to overheating, envelope passive cooling features are strongly aligned with your priorities. Dual-Judge Note: The empirical ML comfort model and physical Adaptive 90% model differ by 18.6 percentage points in Jodhpur, reflecting climate humidity or boundary conditions."*
- **Hindi Example (Jodhpur):**
  > *"यह पैकेज 78.6/100 का मजबूत कम्फर्ट फिट स्कोर प्रदान करता है, जो स्थानीय सामान्य इमारत से +32.9 अंक बेहतर है। वार्षिक असुविधा समय 50.7% से घटकर 19.8% रह जाता है। आपकी अत्यधिक गर्मी के प्रति संवेदनशीलता को देखते हुए, पैसिव डिज़ाइन आपकी प्राथमिकताओं के अनुकूल है। दोहरा मॉडल मूल्यांकन नोट: Jodhpur में अनुभवजन्य एमएल मॉडल और भौतिक अनुकूली मॉडल के बीच 18.6% का अंतर है, जो जलवायु की उमस व सीमा स्थिति को दर्शाता है।"*

---

## 7. Assumptions Introduced

- **Assumption A-013:** Sensitivity weighting multipliers for user comfort profiles:
  - Heat sensitive: $w_{\text{warm}} = 1.35, w_{\text{cool}} = 0.75$.
  - Cold sensitive: $w_{\text{cool}} = 1.35, w_{\text{warm}} = 0.75$.
  - Balanced: $w_{\text{warm}} = 1.00, w_{\text{cool}} = 1.00$.
  - Elderly consideration: $+0.20$ cool discomfort penalty.
- **Assumption A-014:** Energy sub-score formulation benchmarked against the typology conventional reference building ($R_2 = 50.0\text{ points}$; zero-energy design $= 100.0\text{ points}$).
