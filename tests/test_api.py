"""
tests/test_api.py

Automated test suite for FastAPI backend (ClimateAdapt-Comfort v2).
Verifies all REST endpoints, DSR rates validation, honesty rules,
and ensures zero live EnergyPlus dependencies.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["live_energyplus_runtime"] is False
    assert data["cpwd_rates_validated"] is True
    assert "Simulation-based estimate" in data["disclaimer"]

def test_api_cities():
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert len(data["cities"]) == 5
    city_keys = [c["key"] for c in data["cities"]]
    assert "Jodhpur" in city_keys
    assert "Shimla" in city_keys
    assert "Mumbai" in city_keys
    assert "Bengaluru" in city_keys
    assert "New_Delhi" in city_keys

def test_api_match_location_direct():
    response = client.post("/api/match-location", json={"query": "Mumbai, Maharashtra"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched_city_key"] == "Mumbai"
    assert data["distance_km"] < 25.0
    assert data["confidence_tier"] == "Medium"

def test_api_match_location_distance_notice():
    # Jaipur is ~280 km from Jodhpur
    response = client.post("/api/match-location", json={"query": "Jaipur, Rajasthan", "latitude": 26.9124, "longitude": 75.7873})
    assert response.status_code == 200
    data = response.json()
    assert data["is_direct_station"] is False
    assert data["nearest_match_notice"] is not None
    assert "km away" in data["nearest_match_notice"]

def test_api_city_averages():
    response = client.get("/api/city/Jodhpur/averages")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence_tier"] == "Low"
    assert "area_average" in data
    assert "usually_feel" in data["area_average"]

def test_api_cost_schedule():
    response = client.get("/api/cost-schedule")
    assert response.status_code == 200
    data = response.json()
    assert data["validation_passed"] is True
    assert len(data["items"]) >= 7
    # Verify no unapproved placeholders remain
    for item in data["items"]:
        assert item["validation_status"] == "VERIFIED"
        assert item["rate_inr"] > 0

def test_api_evaluate_packages():
    payload = {
        "city": "Bengaluru",
        "building_type": "apartment",
        "usually_feel": "about right",
        "hours_occupied": 16,
        "has_cooling": "fan",
        "summer_clothing": "light",
        "winter_clothing": "normal",
        "priority": "balanced",
        "future_climate": False
    }
    response = client.post("/api/evaluate-packages", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["city"] == "Bengaluru"
    assert data["confidence_tier"] == "Medium"
    assert "packages" in data
    pkgs = data["packages"]
    assert "budget" in pkgs
    assert "balanced" in pkgs
    assert "best_comfort" in pkgs
    
    # Check that comfort fit score is populated
    assert pkgs["balanced"]["comfort_fit_score"] >= 50
    # Check 12-month performance
    monthly = pkgs["balanced"]["monthly_performance"]
    assert len(monthly["months"]) == 12
    assert len(monthly["indoor_ta_baseline_r2"]) == 12
    assert len(monthly["indoor_ta_recommended"]) == 12
    
    # Check cost range
    cost = pkgs["balanced"]["cost_range"]
    assert cost["cost_inr_nominal"] > 0
    assert "CPWD" in cost["source"]

def test_api_future_climate_toggle():
    payload = {
        "city": "Jodhpur",
        "building_type": "house",
        "usually_feel": "too hot",
        "hours_occupied": 24,
        "has_cooling": "none",
        "summer_clothing": "light",
        "winter_clothing": "normal",
        "priority": "comfort",
        "future_climate": True
    }
    response = client.post("/api/evaluate-packages", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["future_climate_active"] is True
    assert "+1.5" in data["future_climate_note"]
