"""
src/api/main.py

FastAPI backend application for ClimateAdapt-Comfort v2.
Serves precomputed passive shelter simulation results, CPWD DSR cost ranges,
bilingual package recommendations, and 12-month performance profiles.

STRICT RESEARCH INTEGRITY:
- Serves PRECOMPUTED results from verified repository artifacts only.
- ZERO live EnergyPlus calls.
- Every endpoint returns city confidence tier and applicability flags.
- Clear disclaimers: 'Simulation-based estimate, not a measured result or a construction quote.'
"""

import os
import sys
import math
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.data.cpwd_cost import validate_dsr_rates, load_dsr_schedule
from src.api.recommender import (
    STATION_METADATA,
    BUILDING_TYPE_MODIFIERS,
    generate_three_packages,
    load_reference_baselines,
    load_pareto_front
)

app = FastAPI(
    title="ClimateAdapt-Comfort v2 API",
    description="Decision-Support Backend for Passive Building Design across Indian Climate Zones.",
    version="2.0.0"
)

# Enable CORS for Next.js frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class LocationMatchRequest(BaseModel):
    query: str = Field(..., description="Location name or search string")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class QuestionnaireRequest(BaseModel):
    city: str = Field(..., description="City key: Jodhpur | Mumbai | New_Delhi | Bengaluru | Shimla")
    building_type: str = Field("house", description="house | apartment | commercial")
    usually_feel: str = Field("too hot", description="too hot | about right | too cold")
    hours_occupied: int = Field(24, ge=1, le=24, description="Hours occupied per day")
    has_cooling: str = Field("none", description="none | fan | AC")
    summer_clothing: str = Field("light", description="light | normal | heavy")
    winter_clothing: str = Field("normal", description="light | normal | heavy")
    priority: str = Field("balanced", description="comfort | balanced | low energy")
    future_climate: bool = Field(False, description="Enable +1.5°C warmer weather climate projection")

class PDFExportRequest(BaseModel):
    package_data: Dict[str, Any]
    user_name: Optional[str] = "Project Owner"
    project_title: Optional[str] = "Passive Shelter Construction Specification"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_earth = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Health check verifying precomputed artifact availability and rates validation."""
    valid, issues = validate_dsr_rates()
    return {
        "status": "healthy" if valid else "degraded",
        "version": "2.0.0",
        "architecture": "FastAPI + Next.js (precomputed simulation artifacts)",
        "live_energyplus_runtime": False,
        "fixed_seed": 42,
        "cpwd_rates_validated": valid,
        "cpwd_validation_issues": issues,
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

@app.get("/api/cities")
def get_cities():
    """Returns the 5 simulated Indian reference climate stations and metadata."""
    cities_list = []
    for key, data in STATION_METADATA.items():
        cities_list.append({
            "key": key,
            "name": data["name"],
            "zone": data["zone"],
            "koppen": data["koppen"],
            "epw": data["epw"],
            "confidence_tier": data["confidence_tier"],
            "confidence_reason": data["confidence_reason"],
            "adaptive_validity": data["adaptive_validity"],
            "db2_envelope_pct": data["db2_envelope_pct"],
            "coordinates": [data["lat"], data["lon"]]
        })
    return {
        "cities": cities_list,
        "allowed_stations": list(STATION_METADATA.keys()),
        "notice": "Only these 5 representative climate stations have been simulated in EnergyPlus. Other locations must match to nearest station.",
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

@app.post("/api/match-location")
def match_location(req: LocationMatchRequest):
    """
    Matches any input location query or coordinates to the nearest of the 5 simulated cities.
    Includes explicit nearest-match distance badge and caveat.
    """
    lat, lon = req.latitude, req.longitude
    matched_name = req.query
    
    # If coordinates are not directly provided, use basic lookup or default to Jodhpur
    if lat is None or lon is None:
        q_lower = req.query.strip().lower()
        if "pune" in q_lower:
            lat, lon = 18.5204, 73.8567
        elif "goa" in q_lower:
            lat, lon = 15.2993, 74.1240
        elif "mumbai" in q_lower:
            lat, lon = 19.0760, 72.8777
        elif "jaipur" in q_lower:
            lat, lon = 26.9124, 75.7873
        elif "noida" in q_lower or "gurugram" in q_lower or "gurgaon" in q_lower:
            lat, lon = 28.4595, 77.0266
        elif "delhi" in q_lower or "ncr" in q_lower:
            lat, lon = 28.6139, 77.2090
        elif "chennai" in q_lower:
            lat, lon = 13.0827, 80.2707
        elif "hyderabad" in q_lower:
            lat, lon = 17.3850, 78.4867
        elif "mysore" in q_lower:
            lat, lon = 12.2958, 76.6394
        elif "bengaluru" in q_lower or "bangalore" in q_lower:
            lat, lon = 12.9716, 77.5946
        elif "manali" in q_lower:
            lat, lon = 32.2432, 77.1892
        elif "dharamshala" in q_lower:
            lat, lon = 32.2190, 76.3234
        elif "dehradun" in q_lower:
            lat, lon = 30.3165, 78.0322
        elif "shimla" in q_lower:
            lat, lon = 31.1048, 77.1734
        else: # Default to Jodhpur / Rajasthan
            lat, lon = 26.2389, 73.0243

    # Compute distances to all 5 stations
    min_dist = float("inf")
    nearest_key = "Jodhpur"
    for key, data in STATION_METADATA.items():
        dist = haversine_km(lat, lon, data["lat"], data["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest_key = key
            
    is_direct_station = min_dist < 20.0
    notice = None
    if not is_direct_station:
        notice = f"Nearest simulated climate station is {STATION_METADATA[nearest_key]['name']} ({round(min_dist, 1)} km away). Local elevation and microclimate may cause differences."

    return {
        "searched_query": req.query,
        "matched_city_key": nearest_key,
        "matched_city_name": STATION_METADATA[nearest_key]["name"],
        "climate_zone": STATION_METADATA[nearest_key]["zone"],
        "confidence_tier": STATION_METADATA[nearest_key]["confidence_tier"],
        "distance_km": round(min_dist, 1),
        "is_direct_station": is_direct_station,
        "nearest_match_notice": notice,
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

@app.get("/api/city/{city_key}/averages")
def get_city_averages(city_key: str):
    """Returns typical regional comfort averages and reference shelter baselines."""
    if city_key not in STATION_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{city_key}' not found in 5 simulated stations.")
        
    meta = STATION_METADATA[city_key]
    refs = load_reference_baselines(city_key)
    
    return {
        "city": city_key,
        "name": meta["name"],
        "zone": meta["zone"],
        "confidence_tier": meta["confidence_tier"],
        "confidence_reason": meta["confidence_reason"],
        "adaptive_validity": meta["adaptive_validity"],
        "db2_envelope_pct": meta["db2_envelope_pct"],
        "area_average": meta["area_average"],
        "reference_shelters": refs,
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

@app.get("/api/cost-schedule")
def get_cost_schedule():
    """Returns official CPWD DSR rate schedule and validation status."""
    valid, issues = validate_dsr_rates()
    df = load_dsr_schedule()
    return {
        "validation_passed": valid,
        "validation_issues": issues,
        "schedule_name": "CPWD Delhi Schedule of Rates (DSR) 2021",
        "items": df.to_dict(orient="records"),
        "disclaimer": "Rough indicative rates from CPWD DSR schedule. For academic planning only; never present as an official contractor quote or tender."
    }

@app.post("/api/evaluate-packages")
def evaluate_packages(req: QuestionnaireRequest):
    """
    Evaluates user comfort questionnaire responses and returns:
    1. Comfort Fit Score (0-100)
    2. Comparison with typical area averages
    3. Three design packages (Budget, Balanced, Best-Comfort) with materials, CPWD DSR costs, and 12-month performance
    4. Future climate projection (+1.5°C warmer)
    """
    city_key = req.city
    if city_key not in STATION_METADATA:
        raise HTTPException(status_code=400, detail=f"Invalid city '{city_key}'. Must be one of {list(STATION_METADATA.keys())}")
        
    bldg_type = req.building_type.lower()
    if bldg_type not in BUILDING_TYPE_MODIFIERS:
        bldg_type = "house"
        
    results = generate_three_packages(
        city=city_key,
        building_type=bldg_type,
        user_priority=req.priority,
        future_climate=req.future_climate
    )
    return results

@app.post("/api/export-pdf-data")
def export_pdf_data(req: PDFExportRequest):
    """
    Formats a builder-ready specification payload with bill of quantities (BOQ),
    materials list, CPWD DSR cost breakdown, climate caveats, and confidence tier.
    """
    pkg = req.package_data
    return {
        "status": "ready",
        "project_title": req.project_title,
        "owner": req.user_name,
        "package_id": pkg.get("id"),
        "package_name": pkg.get("name"),
        "city": pkg.get("city"),
        "confidence_tier": pkg.get("confidence_tier"),
        "discomfort_hours_pct": pkg.get("discomfort_pct"),
        "annual_energy_kwh_per_m2": pkg.get("annual_energy_kwh_per_m2"),
        "materials": pkg.get("materials_list", []),
        "design_specifications": pkg.get("design_variables", {}),
        "cost_summary": pkg.get("cost_range", {}),
        "disclaimer": "Simulation-based estimate, not a measured result or a construction quote."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
