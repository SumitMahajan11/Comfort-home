"""
api/main.py

FastAPI application entrypoint for ClimateAdapt-Comfort Decision-Support Service.
Can be executed with: `uvicorn api.main:app`

Core Architectural Principles:
- Read-only service: Zero EnergyPlus runtime calls, zero model retraining.
- High integrity: Data loaded once at startup with cryptographic SHA256 checksum verification.
- Strictly refuses to start if any file fails manifest verification.
- Full bilingual English/Hindi localization support.
- CORS enabled for http://localhost:3000.
- OpenAPI docs available at /docs.
"""

import os
import sys
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.config import DOCS_DIR
from api.loader import get_store
from api.routes import cities, comfort, packages, pareto, model_lab, export_pdf

# Configure logging without recording personal data
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("climateadapt.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads and verifies all data from data/export/manifest.json once at startup.
    Refuses to start if any file is missing or checksum verification fails.
    """
    logger.info("Initializing ClimateAdapt-Comfort API...")
    store = get_store()
    try:
        store.verify_and_load()
        logger.info(f"Artifact verification successful. Manifest SHA256: {store.manifest_checksum}")
    except Exception as e:
        logger.critical(f"FATAL: Application refusing to start due to integrity check failure: {e}")
        raise e

    # Export OpenAPI schema to docs/openapi.json on startup
    try:
        openapi_schema = app.openapi()
        os.makedirs(DOCS_DIR, exist_ok=True)
        openapi_path = os.path.join(DOCS_DIR, "openapi.json")
        with open(openapi_path, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2)
        logger.info(f"OpenAPI schema exported to {openapi_path}")
    except Exception as e:
        logger.warning(f"Could not export openapi.json: {e}")

    yield
    logger.info("Shutting down ClimateAdapt-Comfort API.")

app = FastAPI(
    title="ClimateAdapt-Comfort Decision-Support API",
    description=(
        "Research decision-support API for passive building design across Indian climate zones. "
        "Serves verified simulation results, CPWD DSR cost ranges, Comfort Fit Scores, and SHAP explainability. "
        "Zero live EnergyPlus runs; all numbers trace to audited repository artifacts."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware that sanitizes/avoids logging user questionnaire bodies
@app.middleware("http")
async def sanitize_logging_middleware(request: Request, call_next):
    # Log endpoint and method only (no request bodies or personal data)
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response

# Versioned router under /api/v1
from fastapi import APIRouter
v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(cities.router)
v1_router.include_router(comfort.router)
v1_router.include_router(packages.router)
v1_router.include_router(pareto.router)
v1_router.include_router(model_lab.router)
v1_router.include_router(export_pdf.router)

app.include_router(v1_router)

# Also include un-prefixed routers so root endpoints (e.g. GET /cities) work directly
app.include_router(cities.router)
app.include_router(comfort.router)
app.include_router(packages.router)
app.include_router(pareto.router)
app.include_router(model_lab.router)
app.include_router(export_pdf.router)

@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
def health():
    """Health check endpoint providing manifest checksum and service status."""
    store = get_store()
    return {
        "status": "healthy" if store.is_loaded else "uninitialized",
        "version": "2.0.0",
        "manifest_checksum": store.manifest_checksum,
        "cached_artifacts_count": len(store.cache),
        "live_energyplus_runtime": False,
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
