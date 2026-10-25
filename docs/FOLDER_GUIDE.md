# Repository Folder Guide: ClimateAdapt-Comfort v2

This guide describes the organization and contents of every directory in the `ClimateAdapt-Comfort` repository to support independent navigation, reproducibility, and contribution.

---

## High-Level Layout

| Directory / File | Category | Purpose / Description | Git Tracking Status |
| :--- | :--- | :--- | :--- |
| `api/` | **Backend Service** | Read-only FastAPI service (v1 routes, schemas, PDF generator) | Tracked |
| `web/` | **Frontend Application** | Next.js 16 (React 19, TypeScript, Tailwind CSS) web product | Tracked (except node_modules/.next) |
| `scripts/` | **Launchers** | One-command local runners (`run_product.ps1`, `run_product.sh`) | Tracked |
| `src/` | **Core Physics & ML** | Core computational physics, simulation engine, and optimization | Tracked |
| `data/costs/` | **Cost Engine** | Materials database, CPWD DSR rate schedules, retail tariffs | Tracked |
| `data/export/` | **Precomputed Exports**| 160 precomputed runtime artifacts with `manifest.json` SHA-256 | Tracked |
| `data/processed/` | **Derived Research** | Cleaned datasets, split matrices, simulation parquet files | Core artifacts tracked |
| `data/raw/` | **Raw Inputs** | Raw weather files (TMYx), ASHRAE DB II, and ICE DB | Gitignored / External |
| `models/` | **Trained Models** | ML champion model (`champion_comfort_model.joblib`) and surrogates | Champion model tracked |
| `tools/` | **Utilities & Audits** | Claims auditor, cost validator, screenshot and export tools | Tracked |
| `tests/` | **Test Suites** | Pytest suites for E2E grid, API, costs, comfort, and Streamlit | Tracked |
| `docs/` | **Documentation** | Specs, phase gates, thesis artefacts, and user guides | Tracked |
| `reports/` | **Evidence & Reports** | Final synthesis reports, literal command evidence logs, figures | Tracked |

---

## Detailed Directory Breakdown

### 1. `api/` (FastAPI Precomputed Backend)
Production read-only REST API package serving precomputed research artifacts with zero live EnergyPlus calls.
- `api/main.py`: Application entrypoint with Starlette lifespan, CORS middleware, and root aliases.
- `api/routes.py`: Versioned API endpoints under `/api/v1` (`/cities`, `/match`, `/climate`, `/comfort-norms`, `/questionnaire`, `/fit-score`, `/packages`, `/export/pdf`).
- `api/models.py`: Strongly typed Pydantic v2 request/response schemas with rich field documentation.
- `api/store.py`: `ArtifactStore` verifying `data/export/manifest.json` SHA-256 checksums at startup and caching artifacts in memory.
- `api/config.py`: City metadata, reference shelter baselines, and D-017 confidence tiers.

### 2. `web/` (Next.js 16 Modern Frontend)
Full-featured, responsive architectural decision-support web application.
- `web/src/app/`: Next.js 16 App Router pages:
  - `page.tsx`: Landing page with hero, S1-S4 scorecard, and climate zone overview.
  - `wizard/`: 5-step guided decision flow (`where`, `what`, `climate`, `comfort`, `plan`).
  - `expert/`: Professional architectural studio (`design-studio`, `pareto-explorer`, `model-lab`).
  - `about/`: Project methodology, assumptions A-001..A-014, and decision log D-001..D-028.
- `web/src/components/`: Reusable components including honest-labelling badges (`<ConfidenceBadge/>`, `<VerificationBadge/>`, `<ApplicabilityGauge/>`, `<LimitationsDrawer/>`), language switchers, and comparison modals.
- `web/src/lib/`: API client (`api.ts`), bilingual English/Hindi dictionary (`i18n.ts`), and helper utilities.
- `web/tests/`: Automated Vitest/Jest unit tests covering math, distances, and confidence tiers.

### 3. `scripts/` (Local Launchers)
- `scripts/run_product.ps1` (PowerShell): Single-command local startup script. Validates export manifest checksums, runs `tools/validate_costs.py`, enforces Decision D-025 null-gating, and launches FastAPI and Next.js concurrently.
- `scripts/run_product.sh` (Bash): Linux/macOS equivalent launcher.

### 4. `src/` (Core Computational Physics & ML)
- `src/sim/`: Parametric EnergyPlus IDF templates (`shelter`, `house`, `apartment`, `commercial`), renderers (`render.py`), and climate morphing (`morph_weather.py`).
- `src/models/`: ML comfort classifier training (`train_champion.py`), baseline evaluations (`eval_baselines.py`), and SHAP explainability (`explain.py`).
- `src/optimize/`: Dual comfort judge coupling (`coupling.py`), XGBoost surrogate training (`train_surrogates.py`), and NSGA-II optimization (`run_nsga2.py`).
- `src/costs/`: Bill of materials generator (`bom.py`), cost range estimator (`estimate.py`), and embodied carbon calculator (`carbon.py`).
- `src/comfort/`: City norms calculator (`city_norms.py`), questionnaire profile mapper (`profile.py`), and Comfort Fit Score engine (`fit.py`).
- `src/app/`: Original standalone Streamlit decision-support application (`app.py`).

### 5. `data/` (Data Layers)
- `data/costs/`:
  - `materials.json`: 10 architectural assemblies with thermal conductivity, density, and ICE embodied carbon factors.
  - `dsr_rates.json`: CPWD DSR rate schedules with "TO BE FILLED" placeholder registry and strict null gating.
  - `tariffs.json`: Electricity utility tariffs for annual operational cost estimations.
- `data/export/`: Precomputed runtime vault containing 160 verified JSON files and `manifest.json`.
- `data/processed/`: Ground-truth datasets (`comfort_clean.parquet`, `splits.json`, `surrogate_metrics.csv`, `s3_evaluation_results.csv`).
- `data/raw/`: Immutable external data (ASHRAE DB II, EPW weather files).

### 6. `tools/` (Operational Scripts & Audit Tools)
- `tools/claims_audit.py`: Automated claims audit verifying numerical claims in reports against literal evidence files.
- `tools/validate_costs.py`: Integrity validator checking that CPWD DSR rates are verified or correctly null-gated.
- `tools/export_artifacts.py`: Serializes optimization and surrogate results into `data/export/` with SHA-256 hashes.
- `tools/capture_wizard_screenshots.py`: Headless Playwright script capturing UI evidence screenshots.
- `tools/test_pdf_export.py`: Verifies vector PDF generation via ReportLab.

### 7. `reports/` (Evidence & Technical Reports)
- `reports/evidence/`: Immutable command execution outputs:
  - `e2e_tests_output.txt`: Literal output of 45-combination grid audit (135 packages).
  - `claims_audit_v2_output.txt`: Output of master 375-claim verification script.
  - `*.png`: 10 high-resolution evidence screenshots of wizard steps and expert tools.
  - `pdf_export_verification.txt`: Byte-size and header verification of ReportLab PDF.
- `reports/final_results_v2.md`: Master v2 synthesis report reviewing S1-S4 across typologies and limitations.
- `reports/final_results.md`: Baseline v1 synthesis report.

### 8. `docs/` (Specifications & Thesis Compendium)
- `docs/PROJECT_SPEC.md`: Master project specification with locked decisions D-001 through D-028.
- `docs/PHASES.md`: Deliverables and acceptance criteria for all Phases 0 through 11.
- `docs/TRACKER.md`: Project ledger, evidence trail (E-001..E-036), and risk register (R-001..R-014).
- `docs/THESIS_ARTEFACTS.md`: Compendium featuring Mermaid architecture, data-flow, user-flow diagrams, master evidence table, and 2-page reproduction guide.
- `docs/HOW_TO_RUN.md`: Execution instructions for pipeline, test suites, and product runners.
