# Materials and Cost-Range Engine Specification (docs/COSTS.md)

Project: ClimateAdapt-Comfort v2  
Document Version: 1.0.0  
Last Updated: 2026-10-24  
Status: Gated / Awaiting Manual DSR & Tariff Entry  

---

## 1. Executive Summary & Purpose

The Materials and Cost-Range Engine translates envelope design decisions from the multi-objective optimizer into a physical **Bill of Materials (BOM)** and an indicative **Cost Range**, using Central Public Works Department (CPWD) Delhi Schedule of Rates (DSR) items and state-specific City Cost Indices (CCI).

> [!IMPORTANT]
> **Decision-Support Estimate, Never a Construction Quote:**  
> The output of this engine is strictly an indicative cost range intended for early-stage pre-feasibility, parametric trade-off comparison, and relative ranking against conventional reference buildings. It is not an engineering tender, contractor bid, or structural bill of quantities.

### Strict Honesty & Null-Gating Rule
Per project rule, **rates and retail tariffs are never fabricated or guessed**. All CPWD DSR rate numbers and SERC retail tariffs remain explicitly `null` with status `"TO BE FILLED"` until manually populated from official published schedules. The web application and backend API refuse to show arbitrary monetary figures while rates are null, presenting:
```
Cost range unavailable: rates not yet loaded
```

---

## 2. Typology Geometries & Geometric Derivations

All material quantities in `src/costs/bom.py` are derived geometrically from the same building dimensions defined in the EnergyPlus IDF simulation templates (`src/sim/templates/*.idf`):

| Building Typology | Floor Area ($A_{\text{floor}}$) | Ceiling Height ($H$) | Envelope Perimeter ($P$) | Gross Exterior Wall Area ($A_{\text{wall, gross}}$) | Roof Area ($A_{\text{roof}}$) | Window Height ($H_{\text{win}}$) | Roof Exposure |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`shelter_v1`** | $20.00\text{ m}^2$ ($5.0\text{m} \times 4.0\text{m}$) | $3.0\text{ m}$ | $18.0\text{ m}$ | $54.00\text{ m}^2$ | $20.00\text{ m}^2$ | $1.2\text{ m}$ | Always exposed |
| **`house`** | $59.00\text{ m}^2$ (3 zones) | $3.0\text{ m}$ | $31.5\text{ m}$ | $94.50\text{ m}^2$ | $59.00\text{ m}^2$ | $1.2\text{ m}$ | Always exposed |
| **`apartment`** | $55.00\text{ m}^2$ (2 zones) | $2.8\text{ m}$ | $15.0\text{ m}$ (2 exposed walls) | $42.00\text{ m}^2$ | $0.0\text{ m}^2$ (mid/ground), $55.0\text{ m}^2$ (top) | $1.2\text{ m}$ | Exposed only if `floor_position == "top"` |
| **`commercial`** | $80.00\text{ m}^2$ ($10\text{m} \times 8\text{m}$) | $3.5\text{ m}$ | $36.0\text{ m}$ | $126.00\text{ m}^2$ | $80.00\text{ m}^2$ | $1.5\text{ m}$ | Always exposed |

*Note on Area Scaling:* If a user inputs a custom floor area $A_{\text{user}}$, linear dimensions scale proportionally by $\lambda = \sqrt{A_{\text{user}} / A_{\text{base}}}$, scaling gross wall area as $A_{\text{wall, gross}} \times \lambda$ and roof area as $A_{\text{roof}} \times \lambda^2$.

---

## 3. Mathematical Equations for BOM Quantities

For any design defined by the 8 optimizer variables:
- Roof insulation thickness: $t_{\text{roof, ins}}$ (m)
- Wall insulation thickness: $t_{\text{wall, ins}}$ (m)
- Wall thermal mass class: $M_{\text{wall}} \in \{\text{light}, \text{medium}, \text{heavy}\}$
- Roof solar absorptance: $\alpha_{\text{roof}} \in [0.30, 0.90]$
- Window-to-wall ratio: $\text{WWR} \in [0.05, 0.40]$
- Orientation: $\theta \in [0^\circ, 359^\circ]$
- Shading overhang depth: $d_{\text{shade}} \in [0.0, 1.0]\text{ m}$
- Ventilation ACH: $\text{ACH} \in [1.0, 15.0]$

The physical BOM quantities are computed as follows:

### 3.1 Window Glazing Area ($A_{\text{win}}$)
$$A_{\text{win}} = A_{\text{wall, gross}} \times \text{WWR} \quad [\text{m}^2]$$

### 3.2 Net Exterior Wall Masonry Area ($A_{\text{wall, net}}$)
$$A_{\text{wall, net}} = A_{\text{wall, gross}} - A_{\text{win}} \quad [\text{m}^2]$$
- If $M_{\text{wall}} = \text{medium}$: Assigned to `wall_medium_brick` (200 mm clay brick).
- If $M_{\text{wall}} = \text{heavy}$: Assigned to `wall_heavy_rcc` (200 mm reinforced concrete).
- If $M_{\text{wall}} = \text{light}$: Assigned to `wall_light_drywall` (lightweight fiber cement panel system).

### 3.3 Wall Insulation Volume ($V_{\text{wall, ins}}$)
$$V_{\text{wall, ins}} = A_{\text{wall, net}} \times t_{\text{wall, ins}} \quad [\text{m}^3]$$
*(Included in BOM if $t_{\text{wall, ins}} > 0.0001\text{ m}$)*

### 3.4 Roof Slab Area ($A_{\text{roof, slab}}$)
$$A_{\text{roof, slab}} = A_{\text{roof}} \quad [\text{m}^2]$$
*(Zero for apartment middle and ground floors)*

### 3.5 Roof Insulation Volume ($V_{\text{roof, ins}}$)
$$V_{\text{roof, ins}} = A_{\text{roof}} \times t_{\text{roof, ins}} \quad [\text{m}^3]$$
*(Included in BOM if $t_{\text{roof, ins}} > 0.0001\text{ m}$ and roof is exposed)*

### 3.6 Roof Finish / Reflective Coating Area ($A_{\text{roof, finish}}$)
- If $\alpha_{\text{roof}} \le 0.45$: Assigned to `roof_cool_coating` (High-SRI elastomeric cool roof coating, $A_{\text{roof}}\text{ m}^2$).
- If $\alpha_{\text{roof}} > 0.45$: Assigned to `roof_standard_finish` (Standard cementitious waterproofing and wearing finish, $A_{\text{roof}}\text{ m}^2$).

### 3.7 Shading Overhang Area ($A_{\text{shade}}$)
Total window width is derived from total window area and window opening height:
$$W_{\text{win, total}} = \frac{A_{\text{win}}}{H_{\text{win}}} \quad [\text{m}]$$
$$A_{\text{shade}} = W_{\text{win, total}} \times d_{\text{shade}} \quad [\text{m}^2]$$
*(Included in BOM if $d_{\text{shade}} > 0.001\text{ m}$)*

### 3.8 Ventilation Louvers & Hardware ($A_{\text{vent}}$)
Operable fraction scales with required design air change rate:
$$f_{\text{operable}} = \min\left(0.60, \max\left(0.10, \frac{\text{ACH}}{15.0} \times 0.50\right)\right)$$
$$A_{\text{vent}} = A_{\text{win}} \times f_{\text{operable}} \quad [\text{m}^2]$$

---

## 4. Cost Range Calculation & Contingency Band

### 4.1 Base Subtotals
For each BOM item $i$ with physical quantity $Q_i$, low unit rate $R_{i, \text{low}}$, high unit rate $R_{i, \text{high}}$, and City Cost Index $\text{CCI}_{\text{city}}$:
$$\text{Cost}_{i, \text{low}} = Q_i \times R_{i, \text{low}} \times \text{CCI}_{\text{city}}$$
$$\text{Cost}_{i, \text{high}} = Q_i \times R_{i, \text{high}} \times \text{CCI}_{\text{city}}$$
$$\text{Cost}_{i, \text{mid}} = \frac{\text{Cost}_{i, \text{low}} + \text{Cost}_{i, \text{high}}}{2.0}$$

$$\text{Subtotal}_{\text{low}} = \sum_i \text{Cost}_{i, \text{low}}, \quad \text{Subtotal}_{\text{high}} = \sum_i \text{Cost}_{i, \text{high}}$$

### 4.2 Contingency Band (Assumption A-012)
To account for site variability, material wastage, local contractor margins, and ancillary fixing hardware, a configurable **$\pm 15\%$ contingency band** is applied:
$$\text{Cost}_{\text{final, low}} = \text{Subtotal}_{\text{low}} \times (1 - 0.15)$$
$$\text{Cost}_{\text{final, high}} = \text{Subtotal}_{\text{high}} \times (1 + 0.15)$$
$$\text{Cost}_{\text{final, mid}} = \frac{\text{Cost}_{\text{final, low}} + \text{Cost}_{\text{final, high}}}{2.0}$$

---

## 5. Incremental Cost vs Reference & Simple Payback

Each candidate design is benchmarked directly against the corresponding typology's conventional baseline reference building (e.g. `R2_Conventional`):

### 5.1 Incremental Envelope Cost
$$\Delta \text{Cost}_{\text{mid}} = \text{Cost}_{\text{design, mid}} - \text{Cost}_{\text{reference, mid}} \quad [\text{INR}]$$

### 5.2 Annual Electricity Bill Savings
Using the verified ideal-loads annual cooling/heating energy intensity $O_2$ ($\text{kWh/m}^2/\text{yr}$):
$$\Delta \text{kWh}_{\text{annual}} = \max\left(0.0, (O_{2, \text{reference}} - O_{2, \text{design}}) \times A_{\text{floor}}\right) \quad [\text{kWh/yr}]$$
$$\text{Annual Bill Savings} = \Delta \text{kWh}_{\text{annual}} \times \text{Tariff}_{\text{city}} \quad [\text{INR/yr}]$$

### 5.3 Simple Payback Period
$$\text{Payback} = \frac{\Delta \text{Cost}_{\text{mid}}}{\text{Annual Bill Savings}} \quad [\text{years}]$$
*(If $\Delta \text{Cost}_{\text{mid}} \le 0$, payback is $0.0\text{ years}$ indicating immediate capital savings; if $\Delta \text{kWh}_{\text{annual}} = 0$ or tariff is null, payback is reported as null)*

---

## 6. Embodied Carbon Protocol (Bath ICE Database)

Embodied carbon is evaluated from the University of Bath Inventory of Carbon and Energy (ICE) factors:
$$E_{\text{total}} = \sum_i (M_i \times f_{\text{carbon}, i}) \quad [\text{kgCO}_2\text{e}]$$
$$E_{\text{intensity}} = \frac{E_{\text{total}}}{A_{\text{floor}}} \quad [\text{kgCO}_2\text{e/m}^2]$$

### Missing Factor Rule
Per project rules:
> If any material used in the BOM lacks a verified factor in `data/processed/ice_materials_extracted.csv`, embodied carbon is strictly reported as `"not available"` with an explicit list of missing items. It is **never guessed, interpolated, or backfilled with unverified defaults**.

---

## 7. Curated Package Selection Protocol

From the verified Pareto frontier for each city and typology, three packages are curated:

1. **Budget Package:**
   - Evaluates designs that outperform the conventional reference (`R2`) on both thermal comfort ($O_1 \le O_{1, \text{ref}}$) and energy ($O_2 \le O_{2, \text{ref}}$).
   - If cost rates are loaded: Picks the design with lowest central cost estimate $\text{Cost}_{\text{mid}}$.
   - If cost rates are null: Picks the design with the lowest envelope intervention index (lowest insulation thickness, window area, and shading depth).
2. **Balanced Package (Knee Point):**
   - Identifies the compromise solution minimizing normalized Euclidean distance to the utopia point:
     $$d_{\text{knee}} = \sqrt{\left(\frac{O_{1} - O_{1, \min}}{O_{1, \max} - O_{1, \min}}\right)^2 + \left(\frac{O_2 - O_{2, \min}}{O_{2, \max} - O_{2, \min}}\right)^2}$$
3. **Best-Comfort Package:**
   - Picks the design with the lowest dual-judge average discomfort hours:
     $$O_{1, \text{dual}} = \frac{O_{1, \text{ml}} + O_{1, \text{adapt}}}{2.0}$$

### Mandatory Verification Gating
Packages **never select an unverified design when verified designs exist** in the candidate set.

---

## 8. Inputs Awaiting Manual Entry ("TO BE FILLED")

The following tables document every input parameter currently gated with `null` / `"TO BE FILLED"` status.

### 8.1 CPWD DSR Rate Items (`data/costs/dsr_rates.json`)

| Item ID | Component Description | Unit | DSR Code | Low Rate (INR) | High Rate (INR) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `wall_medium_brick` | Common burnt clay brick masonry 1:6 in cement mortar | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `wall_heavy_rcc` | Reinforced cement concrete M25 work in walls | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `wall_light_drywall` | Lightweight fiber cement panel drywall partition system | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `wall_insulation_eps` | EPS / mineral wool board exterior wall insulation | $\text{m}^3$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `roof_slab_rcc` | RCC 150mm roof slab including shuttering & steel | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `roof_insulation_eps` | EPS board roof insulation laid in bitumen | $\text{m}^3$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `roof_cool_coating` | High-SRI reflective elastomeric cool roof coating | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `roof_standard_finish`| Standard cementitious waterproofing terrace finish | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `window_glazing_standard`| Aluminium window frame with 6mm clear float glass | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `shading_overhang_cantilever`| Cantilever horizontal window sunshade overhang | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |
| `ventilation_louvers`| Operable glazed louvers / fly-proof wire mesh | $\text{m}^2$ | TO BE FILLED | `null` | `null` | TO BE FILLED |

### 8.2 City Cost Indices (`city_cost_index`)

| City | Reference Station | Index Multiplier | Status |
| :--- | :--- | :--- | :--- |
| **Jodhpur** | Rajasthan (Hot-Dry) | `null` | TO BE FILLED |
| **Mumbai** | Maharashtra (Warm-Humid) | `null` | TO BE FILLED |
| **New Delhi** | Delhi (Composite) | `null` | TO BE FILLED |
| **Bengaluru** | Karnataka (Temperate) | `null` | TO BE FILLED |
| **Shimla** | Himachal Pradesh (Cold) | `null` | TO BE FILLED |

### 8.3 State Retail Electricity Tariffs (`data/costs/tariffs.json`)

| City | State Regulator / Discom | Retail Tariff (INR/kWh) | Tariff Order Edition | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Jodhpur** | JVVNL / RERC | `null` | TO BE FILLED | TO BE FILLED |
| **Mumbai** | BEST / MSEDCL / MERC | `null` | TO BE FILLED | TO BE FILLED |
| **New Delhi** | BSES / TPDDL / DERC | `null` | TO BE FILLED | TO BE FILLED |
| **Bengaluru** | BESCOM / KERC | `null` | TO BE FILLED | TO BE FILLED |
| **Shimla** | HPSEBL / HPERC | `null` | TO BE FILLED | TO BE FILLED |

---

## 9. Workflow to Populate Rates

To activate cost range estimates:
1. Open [data/costs/dsr_rates_template.csv](file:///c:/Users/vardh/OneDrive/Comfort-home-main/data/costs/dsr_rates_template.csv) in Excel or text editor.
2. Enter the official low/high rates, DSR item codes, and City Cost Indices.
3. Open [data/costs/tariffs.json](file:///c:/Users/vardh/OneDrive/Comfort-home-main/data/costs/tariffs.json) and enter the state retail tariffs.
4. Run the conversion script:
   ```powershell
   python tools/csv_to_dsr_json.py
   ```
5. Run the validation auditor:
   ```powershell
   python tools/validate_costs.py
   ```
6. When validation passes with exit code 0, the web API will automatically switch from `"Cost range unavailable: rates not yet loaded"` to displaying the calculated cost range and payback metrics.
