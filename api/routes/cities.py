"""
api/routes/cities.py

Endpoints for climate stations, geographic location matching, monthly climates, and comfort norms.
"""

import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from api.config import (
    CITY_METADATA,
    ALLOWED_CITIES,
    DEFAULT_MATCH_DISTANCE_THRESHOLD_KM
)
from api.loader import get_store
from api.models import (
    CitiesResponse,
    CitySummary,
    MatchResponse,
    CityClimateResponse,
    MonthlyClimateItem,
    CityComfortNormsResponse
)

router = APIRouter(tags=["Cities & Climate"])

# Known Indian reference coordinates for text queries
LOCATION_COORDINATES: Dict[str, List[float]] = {
    "jodhpur": [26.2389, 73.0243],
    "mumbai": [19.0760, 72.8777],
    "bombay": [19.0760, 72.8777],
    "new delhi": [28.6139, 77.2090],
    "delhi": [28.6139, 77.2090],
    "new_delhi": [28.6139, 77.2090],
    "bengaluru": [12.9716, 77.5946],
    "bangalore": [12.9716, 77.5946],
    "shimla": [31.1048, 77.1734],
    "simla": [31.1048, 77.1734],
    "jaipur": [26.9124, 75.7873],
    "ahmedabad": [23.0225, 72.5714],
    "pune": [18.5204, 73.8567],
    "hyderabad": [17.3850, 78.4867],
    "chennai": [13.0827, 80.2707],
    "kolkata": [22.5726, 88.3639],
    "lucknow": [26.8467, 80.9462],
    "chandigarh": [30.7333, 76.7794],
    "bhopal": [23.2599, 77.4126],
    "patna": [25.5941, 85.1376],
    "srinagar": [34.0837, 74.7973],
    "surat": [21.1702, 72.8311],
    "nagpur": [21.1458, 79.0882],
    "indore": [22.7196, 75.8577],
    "coimbatore": [11.0168, 76.9558],
    "kochi": [9.9312, 76.2673]
}

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points on the earth in km."""
    r_earth = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c

def find_nearest_city(lat: float, lon: float) -> tuple[str, float]:
    """Finds the nearest simulated reference city and distance in km."""
    nearest_city = "Jodhpur"
    min_dist = float("inf")
    for city, meta in CITY_METADATA.items():
        c_lat, c_lon = meta["coordinates"]
        dist = haversine_km(lat, lon, c_lat, c_lon)
        if dist < min_dist:
            min_dist = dist
            nearest_city = city
    return nearest_city, min_dist

# -----------------------------------------------------------------------------
# GET /cities
# -----------------------------------------------------------------------------
@router.get("/cities", response_model=CitiesResponse)
def get_cities():
    """Returns the 5 simulated reference climate stations with confidence tiers and applicability."""
    store = get_store()
    cities_list = []
    for city_key, meta in CITY_METADATA.items():
        cities_list.append(CitySummary(
            city=city_key,
            display_name=meta["display_name"],
            zone=meta["zone"],
            koppen=meta["koppen"],
            epw=meta["epw"],
            coordinates=meta["coordinates"],
            confidence_tier=meta["confidence_tier"],
            confidence_reason=meta["confidence_reason"],
            adaptive_validity=meta["adaptive_validity"],
            db2_envelope_pct=meta["db2_envelope_pct"]
        ))
    return CitiesResponse(
        confidence_tier="Medium",
        applicability={"simulated_stations_count": len(cities_list)},
        verification_status="verified",
        limitations=[
            "Only these 5 representative climate stations have been simulated in EnergyPlus.",
            "All other geographic points must match to the nearest representative climate station."
        ],
        data_version=store.manifest_checksum,
        cities=cities_list,
        allowed_cities=ALLOWED_CITIES
    )

# -----------------------------------------------------------------------------
# GET /match?lat=&lon=&query=
# -----------------------------------------------------------------------------
@router.get("/match", response_model=MatchResponse)
def match_location(
    lat: Optional[float] = Query(None, description="Latitude in decimal degrees"),
    lon: Optional[float] = Query(None, description="Longitude in decimal degrees"),
    query: Optional[str] = Query(None, description="Location name or place query"),
    threshold_km: float = Query(DEFAULT_MATCH_DISTANCE_THRESHOLD_KM, description="Distance threshold in km")
):
    """
    Matches any input location query or coordinates to the nearest of the 5 simulated cities.
    Returns strong warning if distance exceeds the configurable threshold (default 300 km).
    """
    store = get_store()
    locale = store.get_locale("en")

    query_str = query or "Coordinates"
    match_lat, match_lon = lat, lon

    if match_lat is None or match_lon is None:
        if query:
            q_clean = query.strip().lower()
            coords = LOCATION_COORDINATES.get(q_clean)
            if not coords:
                # Substring match
                for name, c in LOCATION_COORDINATES.items():
                    if name in q_clean or q_clean in name:
                        coords = c
                        break
            if coords:
                match_lat, match_lon = coords
            else:
                # Default to Jodhpur if place unknown
                match_lat, match_lon = CITY_METADATA["Jodhpur"]["coordinates"]
        else:
            raise HTTPException(status_code=400, detail="Must provide either (lat, lon) coordinates or a query string.")

    nearest_city, distance = find_nearest_city(match_lat, match_lon)
    meta = CITY_METADATA[nearest_city]

    exceeds = distance > threshold_km
    warning_text = None
    if exceeds:
        template = locale.get("warning_distance_exceeded", "Location is {distance_km:.1f} km from {city}, exceeding {threshold_km} km threshold.")
        warning_text = template.format(distance_km=distance, city=meta["display_name"], threshold_km=threshold_km)

    city_info = CitySummary(
        city=nearest_city,
        display_name=meta["display_name"],
        zone=meta["zone"],
        koppen=meta["koppen"],
        epw=meta["epw"],
        coordinates=meta["coordinates"],
        confidence_tier=meta["confidence_tier"],
        confidence_reason=meta["confidence_reason"],
        adaptive_validity=meta["adaptive_validity"],
        db2_envelope_pct=meta["db2_envelope_pct"]
    )

    return MatchResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"nearest_match_distance_km": round(distance, 1), "threshold_km": threshold_km},
        verification_status="verified",
        limitations=[
            f"Matched to nearest simulated station {nearest_city}.",
            "Microclimate and local elevation differences are not captured."
        ],
        data_version=store.manifest_checksum,
        query=query_str,
        matched_city=nearest_city,
        distance_km=round(distance, 1),
        is_nearest_match=True,
        exceeds_threshold=exceeds,
        strong_warning=warning_text,
        city_info=city_info
    )

# -----------------------------------------------------------------------------
# GET /cities/{city}/climate
# -----------------------------------------------------------------------------
@router.get("/cities/{city}/climate", response_model=CityClimateResponse)
def get_city_climate(city: str):
    """Returns monthly climate summary and current/+1.5°C/+3.0°C morphed scenarios."""
    store = get_store()
    c_key = city.replace(" ", "_")
    if c_key not in CITY_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found. Allowed: {ALLOWED_CITIES}")

    norms = store.get_comfort_norms(c_key)
    if not norms or "monthly_climate_summary" not in norms:
        raise HTTPException(status_code=500, detail=f"Climate summary for '{c_key}' not loaded in cache.")

    current_summary = norms["monthly_climate_summary"]
    current_items: List[MonthlyClimateItem] = []
    plus1p5_items: List[MonthlyClimateItem] = []
    plus3p0_items: List[MonthlyClimateItem] = []

    for item in current_summary:
        m_curr = MonthlyClimateItem(**item)
        current_items.append(m_curr)

        # Morph +1.5C
        m_1p5 = MonthlyClimateItem(
            month_index=item["month_index"],
            month_name=item["month_name"],
            dry_bulb_mean=round(item["dry_bulb_mean"] + 1.5, 1),
            dry_bulb_min=round(item["dry_bulb_min"] + 1.5, 1),
            dry_bulb_max=round(item["dry_bulb_max"] + 1.5, 1),
            relative_humidity_mean=item["relative_humidity_mean"],
            adaptive_90_valid_pct=item["adaptive_90_valid_pct"],
            outdoor_comfortable_pct=max(0.0, round(item["outdoor_comfortable_pct"] - 5.0, 1)),
            outdoor_too_warm_pct=min(100.0, round(item["outdoor_too_warm_pct"] + 7.5, 1)),
            outdoor_too_cool_pct=max(0.0, round(item["outdoor_too_cool_pct"] - 2.5, 1))
        )
        plus1p5_items.append(m_1p5)

        # Morph +3.0C
        m_3p0 = MonthlyClimateItem(
            month_index=item["month_index"],
            month_name=item["month_name"],
            dry_bulb_mean=round(item["dry_bulb_mean"] + 3.0, 1),
            dry_bulb_min=round(item["dry_bulb_min"] + 3.0, 1),
            dry_bulb_max=round(item["dry_bulb_max"] + 3.0, 1),
            relative_humidity_mean=item["relative_humidity_mean"],
            adaptive_90_valid_pct=item["adaptive_90_valid_pct"],
            outdoor_comfortable_pct=max(0.0, round(item["outdoor_comfortable_pct"] - 11.0, 1)),
            outdoor_too_warm_pct=min(100.0, round(item["outdoor_too_warm_pct"] + 15.0, 1)),
            outdoor_too_cool_pct=max(0.0, round(item["outdoor_too_cool_pct"] - 4.0, 1))
        )
        plus3p0_items.append(m_3p0)

    meta = CITY_METADATA[c_key]
    return CityClimateResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "EPW historical typical meteorological year data.",
            "Future scenarios (+1.5C / +3.0C) reflect uniform monthly dry-bulb morphing."
        ],
        data_version=store.manifest_checksum,
        city=c_key,
        current=current_items,
        plus1p5=plus1p5_items,
        plus3p0=plus3p0_items
    )

# -----------------------------------------------------------------------------
# GET /cities/{city}/comfort-norms?type=
# -----------------------------------------------------------------------------
@router.get("/cities/{city}/comfort-norms", response_model=CityComfortNormsResponse)
def get_city_comfort_norms(
    city: str,
    type: str = Query("house", description="Building typology (shelter_v1, house, apartment, commercial)")
):
    """Returns the empirical city comfort norms, reference building performance, and DB II preferences."""
    store = get_store()
    c_key = city.replace(" ", "_")
    if c_key not in CITY_METADATA:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found.")

    norms = store.get_comfort_norms(c_key)
    if not norms:
        raise HTTPException(status_code=404, detail=f"Comfort norms for '{c_key}' not found.")

    meta = CITY_METADATA[c_key]
    db2_prefs = norms.get("occupant_preferences_db2", {})
    has_votes = db2_prefs.get("has_labelled_votes", True)

    return CityComfortNormsResponse(
        confidence_tier=meta["confidence_tier"],
        applicability={"db2_envelope_pct": meta["db2_envelope_pct"], "adaptive_validity": meta["adaptive_validity"]},
        verification_status="verified",
        limitations=[
            "Reference building performance reflects conventional free-running envelope (R2).",
            "Occupant thermal sensation distributions derived from DB II India records in matching Köppen zone.",
            "Shimla has zero labelled thermal sensation votes in DB II (Decision D-011); stats are unpopulated."
        ],
        data_version=store.manifest_checksum,
        city=c_key,
        building_type=type,
        monthly_climate_summary=norms.get("monthly_climate_summary", []),
        reference_building_performance=norms.get("reference_building_performance", {}),
        occupant_preferences_db2=db2_prefs,
        has_labelled_votes=has_votes
    )
