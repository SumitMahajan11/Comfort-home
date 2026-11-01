# ClimateAdapt-Comfort v2 Web Frontend

A modern, evidence-gated decision-support web application for passive building design across Indian climate zones. Built as part of a final-year thesis project on multi-objective passive building optimization.

---

## Architectural Principles

1. **Evidence Gating & Zero Fabrication**: Every metric shown to users traces directly to an audited repository artifact under `reports/evidence/` or precomputed EnergyPlus simulation outputs. If CPWD DSR cost rates are unpopulated in official schedules, fields are strictly displayed as null (`"Rates unpopulated in official DSR schedule"`) rather than fabricated numbers.
2. **Honest Limitations**: Negative and partial findings (Phase S1 FAIL, Phase S2 PARTIAL) are prominently disclosed. Sensation gaps (e.g. Shimla lacking physical sensation votes, Decision D-011) and dual-judge divergences are explicitly flagged.
3. **Read-Only Separation**: Zero live EnergyPlus simulation calls in the web layer. The frontend communicates with a read-only FastAPI service (`api/`) serving SHA256-verified precomputed packages.

---

## Tech Stack

- **Framework**: Next.js 16 (App Router) with React 19 and TypeScript 5
- **Styling**: Tailwind CSS with custom glassmorphism design system
- **Color Palette**:
  - Deep Navy (`#0B1F3A`) & Charcoal Slate backgrounds
  - Primary Teal (`#2A7F8E`) and Cyan accents
  - Warm Amber for heat / summer thermal discomfort
  - Cool Sky Blue for cold / winter thermal discomfort
  - Green / Amber / Rose strictly reserved for pass/partial/fail and confidence tiers
- **Visualization**: Recharts, SVG India Geographic Map, Canvas 2D Isometric Building Visualizer
- **Localization**: Bilingual dictionary (English & Hindi) covering all wizard questions and reports
- **Testing**: Built-in `tsx --test` test suite for client calculation utilities, D-017 bounds, and cost models

---

## Modes

### 1. Simple Mode (Guided 5-Step Wizard)
Accessible at `/recommender`:
1. **Where**: Interactive India climate map with 5 reference station pins + search box. Matches any Indian city to the nearest station via Haversine distance with an explicit distance warning if > 300 km.
2. **What**: Building typology selector (Detached House, Apartment Unit with Floor Position selector {ground, middle, top}, Small Commercial) + optional envelope budget slider.
3. **Your Climate**: Monthly dry-bulb and RH temperature bands, comfortable vs overheated hours, confidence tier badge (`<ConfidenceBadge />` with D-017 tooltip), applicability gauge (`<ApplicabilityGauge />`), and accessible data table toggle.
4. **Your Comfort**: Bilingual 7-question occupant comfort survey. Beside every answer, the verified typical regional area average is displayed ("In your area, most people..."). Live "You vs Area" comparison matrix and plain-language Comfort Gap summary sentences.
5. **Your Plan**: Three curated passive envelope packages side by side (Budget, Balanced, Best-Comfort) with 0–100 Comfort Fit Score ring gauge, CPWD DSR cost status, top BOM items, 12-month indoor temperature chart with scenario toggle (Today / +1.5°C / +3.0°C), "Download Builder PDF", "Compare 3 Packages" modal, and "Share Link".

### 2. Expert Mode
Accessible via the header toggle or direct navigation:
- **Design Studio** (`/evaluate`): 8 envelope variable sliders, live surrogate predictions ($O_{1,\text{ml}}$, $O_{1,\text{adapt}}$, warm%, cool%, $O_2$), $R^2$/MAE badges, delta vs R1/R2 baselines, and interactive 3D shelter canvas.
- **Pareto Explorer** (`/pareto`): Multi-objective Pareto frontier scatter plots, verified designs, knee-point highlights, and design variable tables.
- **Explain** (`/explain`): SHAP TreeExplainer feature importance rankings and local force waterfalls.
- **Model Lab** (`/models`): Empirical S1–S4 criteria scorecard (S1 FAIL and S2 PARTIAL prominently disclosed), LOGO cross-validated comfort model leaderboard with 95% bootstrap CIs, 25-surrogate accuracy matrix, and phase evidence ledger.
- **Methods & Limitations** (`/about`): Full pipeline architecture, simulation boundary assumptions A-001..A-007, and locked decision log D-001..D-027.

---

## Getting Started

### Prerequisites
- Node.js 18+ (Node 20+ recommended)
- Python 3.11+ (running the FastAPI service under `../api`)

### Installation & Run

1. **Install Frontend Dependencies**:
   ```bash
   cd web
   npm install
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env.local
   ```
   Default `NEXT_PUBLIC_API_URL`: `http://localhost:8000/api/v1`

3. **Start the FastAPI Backend Service** (from repo root):
   ```bash
   uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

4. **Start the Next.js Frontend Dev Server** (from `web/`):
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

5. **Run Frontend Tests**:
   ```bash
   npm test
   ```

---

## Mandatory Disclaimers

> **Scientific Disclosure**: Simulation-based estimate, not a measured result or a construction quote.
> All comfort predictions, discomfort hours, and energy savings are derived from EnergyPlus 24.2 thermodynamic simulations and empirical ASHRAE DB II models. Cost ranges are preliminary early-stage estimates based on CPWD Delhi Schedule of Rates (DSR 2021) and must never be used as construction contractor bids.
