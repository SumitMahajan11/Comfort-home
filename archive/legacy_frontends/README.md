# Archived Legacy Frontends

This directory preserves early prototype frontends that were decommissioned in favor of the production **ClimateAdapt-Comfort Web App** (`web/`, Next.js 16 / React 19 / TypeScript / Tailwind CSS v4).

### Archived Components:
1. `app.py`: Early Streamlit-based ThermoHome AI prototype.
2. `src_app/`: Early Streamlit-based ClimateAdapt research dashboard.
3. `tests/`: Streamlit `AppTest` suites for the above prototypes (`test_app.py`, `test_thermohome_ai.py`).

### Active Production Frontend:
The canonical and only active frontend for ClimateAdapt-Comfort is located at `web/` (`http://localhost:3000`).
Run with:
```bash
cd web
npm run dev
```
