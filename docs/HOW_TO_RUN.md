# How to Run ClimateAdapt-Comfort v2

This document provides exact, verified commands to run the ClimateAdapt-Comfort v2 web application, execute automated test suites, audit empirical claims, and reproduce pipeline stages.

---

## 1. Quick Start: One-Command Local Product Run

ClimateAdapt-Comfort v2 features a unified startup script that validates export checksums, runs the cost rate integrity auditor, and starts both the FastAPI backend and Next.js frontend:

### Windows PowerShell:
```powershell
# Run in Research Mode (allows unpopulated CPWD DSR cost rates under Decision D-025):
.\scripts\run_product.ps1 -AllowUnfilledCosts
```

### Linux / macOS Bash:
```bash
# Run in Research Mode:
./scripts/run_product.sh --allow-unfilled-costs
```

### What happens during startup:
1. **Manifest Integrity:** Verifies SHA-256 checksums across all 160 precomputed files in `data/export/manifest.json`.
2. **Cost Gate Check:** Runs `tools/validate_costs.py`. Without `-AllowUnfilledCosts`, the script halts with a prominent banner under Decision D-025 to prevent uncertified cost dissemination.
3. **Concurrent Servers:** Launches the FastAPI backend on `http://127.0.0.1:8000` (docs at `/docs`) and the Next.js frontend on `http://localhost:3000`.

---

## 2. Running Individual Services Locally

If you prefer to run services in separate terminal windows:

### Terminal 1: FastAPI Read-Only Backend (Port 8000)
```powershell
# Activate Python environment
.\.venv\Scripts\Activate.ps1

# Start Uvicorn ASGI server
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Terminal 2: Next.js 16 Responsive Frontend (Port 3000)
```powershell
cd web
npm run dev
```
- Local Web Interface: `http://localhost:3000`
- Production Build Verification: `npm run build`

### Terminal 3: Legacy Streamlit Research Dashboard (Port 8501)
```powershell
streamlit run src/app/app.py
```

---

## 3. Running Automated Test Suites & Audits

All tests operate completely offline and require no paid APIs or cloud access:

### 1. End-to-End Product Grid Audit (45 Combinations, 135 Packages)
Verifies verification statuses, D-017 confidence tiers, CPWD DSR null gating, and reference baseline performance:
```powershell
python -m pytest tests/test_e2e_product.py -v -s -W ignore
```

### 2. Master Research Claims Audit (Audits 375 Numerical Claims)
Extracts all numbers from `final_results.md`, `final_results_v2.md`, and `README.md`, matching them 100% against evidence files:
```powershell
python tools/claims_audit.py
```

### 3. FastAPI Service & PDF Generator Tests
Tests manifest validation refusal, route contracts, nearest-station matching, and ReportLab PDF compilation:
```powershell
python -m pytest tests/test_api_v1.py -v
```

### 4. Materials, Costs & Comfort Fit Unit Tests
```powershell
python -m pytest tests/test_costs.py -v
python -m pytest tests/test_comfort.py -v
```

### 5. Frontend Unit & Contract Tests
Tests haversine formulas, bilingual dictionaries, and comfort fit score math:
```powershell
cd web
npm test
cd ..
```

---

## 4. Pipeline Execution & Offline Regeneration

To regenerate optimization artifacts or simulate single weather stations:

### Run Multi-Typology Batch Pipeline
```powershell
# Runs 150-run smoke test across house, apartment, commercial IDFs
python -m pytest tests/test_smoke_building_types.py -v

# Generates 135 packages across 45 parameter pairs
python tools/synthesize_v2_typologies.py

# Exports all artifacts and regenerates manifest.json with SHA-256 hashes
python tools/export_artifacts.py
```

### Validate CPWD DSR Cost Rates
```powershell
# Checks for unpopulated "TO BE FILLED" placeholders
python tools/validate_costs.py
```

### Single Station Simulation Run
```powershell
# Runs 1,000 Latin Hypercube designs and direct EnergyPlus verification for one city:
python tools/run_station_pipeline.py "Jodhpur" "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"
```

---
*For questions or detailed data flow, consult `docs/THESIS_ARTEFACTS.md`.*
