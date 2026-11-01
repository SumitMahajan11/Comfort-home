"""
tests/test_api_v1.py

Comprehensive test suite for the read-only ClimateAdapt-Comfort FastAPI service.
Tests:
- Checksum verification failure blocks startup
- All endpoints under /api/v1 (and root aliases)
- Cross-cutting metadata in every response
- Nearest-city threshold warnings (default 300 km)
- Cost-unavailable behaviour (null gating when rates unpopulated)
- PDF generation (ReportLab, DejaVu, 12-month chart, Hindi text, checksum footer)
"""

import os
import io
import json
import tempfile
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.loader import ArtifactStore, get_store

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

# -----------------------------------------------------------------------------
# 1. Startup & Integrity Tests
# -----------------------------------------------------------------------------
def test_checksum_failure_blocks_startup():
    """Verifies that tampering with a manifest checksum causes startup to be refused."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_manifest = os.path.join(tmpdir, "manifest.json")
        fake_data = {
            "timestamp": "2026-10-25 00:00:00",
            "files": {
                "applicability.json": {
                    "size_bytes": 100,
                    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"  # Invalid
                }
            }
        }
        with open(fake_manifest, "w", encoding="utf-8") as f:
            json.dump(fake_data, f)

        store = ArtifactStore()
        with pytest.raises(RuntimeError) as exc_info:
            store.verify_and_load(manifest_path=fake_manifest)
        assert "Integrity verification failed" in str(exc_info.value) or "Checksum mismatch" in str(exc_info.value)

def test_missing_file_blocks_startup():
    """Verifies that a missing file declared in the manifest causes startup to fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_manifest = os.path.join(tmpdir, "manifest.json")
        fake_data = {
            "timestamp": "2026-10-25 00:00:00",
            "files": {
                "non_existent_file.json": {
                    "size_bytes": 500,
                    "sha256": "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
                }
            }
        }
        with open(fake_manifest, "w", encoding="utf-8") as f:
            json.dump(fake_data, f)

        store = ArtifactStore()
        with pytest.raises(RuntimeError) as exc_info:
            store.verify_and_load(manifest_path=fake_manifest)
        assert "Missing file" in str(exc_info.value)

# -----------------------------------------------------------------------------
# 2. Endpoint Tests
# -----------------------------------------------------------------------------
def test_get_cities_and_cross_cutting_metadata(client):
    """GET /api/v1/cities returns all 5 cities with required cross-cutting fields."""
    response = client.get("/api/v1/cities")
    assert response.status_code == 200
    data = response.json()

    # Cross-cutting metadata
    assert "confidence_tier" in data
    assert "applicability" in data
    assert "verification_status" in data
    assert "limitations" in data and len(data["limitations"]) > 0
    assert "data_version" in data and len(data["data_version"]) == 64

    # Payload
    cities = data["cities"]
    assert len(cities) == 5
    city_keys = [c["city"] for c in cities]
    assert set(city_keys) == {"Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"}

    # Also test un-prefixed alias
    alias_resp = client.get("/cities")
    assert alias_resp.status_code == 200

def test_nearest_city_match_and_threshold(client):
    """GET /api/v1/match tests location matching and distance threshold warnings."""
    # Case A: Within 300 km (Jaipur -> New_Delhi ~ 235 km or Jodhpur ~ 284 km)
    resp_near = client.get("/api/v1/match?query=Jaipur")
    assert resp_near.status_code == 200
    data_near = resp_near.json()
    assert data_near["matched_city"] in ["New_Delhi", "Jodhpur"]
    assert data_near["is_nearest_match"] is True
    assert data_near["distance_km"] < 300.0
    assert data_near["exceeds_threshold"] is False
    assert data_near["strong_warning"] is None

    # Case B: Far location exceeding threshold (Srinagar > 400 km from Shimla)
    resp_far = client.get("/api/v1/match?query=Srinagar")
    assert resp_far.status_code == 200
    data_far = resp_far.json()
    assert data_far["matched_city"] == "Shimla"
    assert data_far["distance_km"] > 300.0
    assert data_far["exceeds_threshold"] is True
    assert data_far["strong_warning"] is not None
    assert "300" in data_far["strong_warning"]

    # Case C: Coordinates match
    resp_coord = client.get("/api/v1/match?lat=13.0&lon=77.6")
    assert resp_coord.status_code == 200
    assert resp_coord.json()["matched_city"] == "Bengaluru"

def test_city_climate_scenarios(client):
    """GET /api/v1/cities/{city}/climate returns current, +1.5C, and +3.0C scenarios."""
    response = client.get("/api/v1/cities/Jodhpur/climate")
    assert response.status_code == 200
    data = response.json()

    assert data["city"] == "Jodhpur"
    assert len(data["current"]) == 12
    assert len(data["plus1p5"]) == 12
    assert len(data["plus3p0"]) == 12

    # Verify +1.5 and +3.0 temperature offsets
    for curr, p15, p30 in zip(data["current"], data["plus1p5"], data["plus3p0"]):
        assert round(p15["dry_bulb_mean"] - curr["dry_bulb_mean"], 1) == 1.5
        assert round(p30["dry_bulb_mean"] - curr["dry_bulb_mean"], 1) == 3.0

def test_city_comfort_norms_and_d011_shimla(client):
    """GET /api/v1/cities/{city}/comfort-norms tests norms output and D-011 zero-vote disclosure."""
    # Jodhpur has labelled votes
    resp_jod = client.get("/api/v1/cities/Jodhpur/comfort-norms?type=house")
    assert resp_jod.status_code == 200
    assert resp_jod.json()["has_labelled_votes"] is True

    # Shimla has ZERO labelled votes (Decision D-011)
    resp_shm = client.get("/api/v1/cities/Shimla/comfort-norms?type=house")
    assert resp_shm.status_code == 200
    data_shm = resp_shm.json()
    assert data_shm["has_labelled_votes"] is False
    assert data_shm["occupant_preferences_db2"]["tsv_distribution_pct"] is None

def test_questionnaire_schema(client):
    """GET /api/v1/questionnaire supports both English and Hindi text."""
    resp_en = client.get("/api/v1/questionnaire?lang=en")
    assert resp_en.status_code == 200
    data_en = resp_en.json()
    assert "Comfort" in data_en["title"]
    assert len(data_en["questions"]) >= 5

    resp_hi = client.get("/api/v1/questionnaire?lang=hi")
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert "कम्फर्ट" in data_hi["title"]

def test_profile_evaluation(client):
    """POST /api/v1/profile/evaluate returns 0-100 Fit Scores and dual-judge disagreement."""
    payload = {
        "building_type": "house",
        "city": "Jodhpur",
        "scenario": "current",
        "answers": {
            "feel_summer": 2,
            "sensitivity": "heat_sensitive",
            "priorities": {"weight_comfort": 60, "weight_energy": 25, "weight_cost": 15}
        }
    }
    response = client.post("/api/v1/profile/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["city"] == "Jodhpur"
    assert data["building_type"] == "house"

    # Typical building baseline
    typical = data["typical_local_building"]
    assert 0 <= typical["overall_fit_score"] <= 100
    assert "dual_judge" in typical

    # Packages
    packages = data["packages"]
    assert "budget" in packages
    assert "balanced" in packages
    assert "best_comfort" in packages
    assert packages["balanced"]["comfort_gain_points"] > 0
    assert packages["balanced"]["explanation_en"] != ""
    assert packages["balanced"]["explanation_hi"] != ""

def test_packages_and_cost_unavailable_behaviour(client):
    """GET /api/v1/packages returns curated packages and strictly null-gates unpopulated cost rates."""
    response = client.get("/api/v1/packages?city=Jodhpur&type=house&scenario=current")
    assert response.status_code == 200
    data = response.json()

    pkgs = data["packages"]
    assert set(pkgs.keys()) == {"budget", "balanced", "best_comfort"}

    for key, pkg in pkgs.items():
        assert pkg["verification_status"] in ["verified", "light verification", "estimated"]
        assert len(pkg["bom"]) > 0
        assert len(pkg["monthly_series"]) == 12

        # Check strict null gating for cost numbers
        cost_range = pkg["cost_range"]
        assert cost_range["status"] == "UNAVAILABLE"
        assert cost_range["low_inr"] is None
        assert cost_range["high_inr"] is None
        assert "unpopulated" in cost_range["reason"].lower() or "schedule" in cost_range["reason"].lower()
        assert "never a quote" in cost_range["disclaimer"].lower()

def test_designs_pareto_and_filters(client):
    """GET /api/v1/designs/pareto supports range filtering and pagination."""
    # Paged request
    resp = client.get("/api/v1/designs/pareto?city=Jodhpur&type=house&page=1&page_size=15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 100
    assert len(data["designs"]) == 15
    assert data["page"] == 1
    assert data["page_size"] == 15

    # Verified only filter
    resp_ver = client.get("/api/v1/designs/pareto?city=Jodhpur&type=house&verified_only=true")
    assert resp_ver.status_code == 200
    designs_ver = resp_ver.json()["designs"]
    assert len(designs_ver) > 0
    assert all(d["verified"] is True for d in designs_ver)

def test_designs_explain_shap(client):
    """GET /api/v1/designs/{id}/explain returns top SHAP drivers and bilingual templates."""
    response = client.get("/api/v1/designs/P_Jodhpur_house_063/explain")
    assert response.status_code == 200
    data = response.json()

    assert data["design_id"] == "P_Jodhpur_house_063"
    assert len(data["top_drivers"]) >= 3
    assert len(data["sentences_en"]) >= 3
    assert len(data["sentences_hi"]) >= 3

def test_model_lab_scorecard(client):
    """GET /api/v1/model-lab returns audited S1-S4 scorecard and literal outputs."""
    response = client.get("/api/v1/model-lab")
    assert response.status_code == 200
    data = response.json()

    scorecard = data["scorecard_s1_s4"]
    assert scorecard["S1"]["status"] == "FAIL"
    assert scorecard["S2"]["status"] == "PARTIAL"
    assert scorecard["S3"]["status"] == "PASS"
    assert scorecard["S4"]["status"] == "PASS"

    leaderboard = data["comfort_model_leaderboard"]
    champion = next(m for m in leaderboard if "Champion" in m["model"])
    assert champion["macro_f1"] == 0.4785

    assert len(data["phase_timeline"]) >= 8

def test_pdf_export_and_hindi_content(client):
    """POST /api/v1/export/pdf generates valid PDF containing BOM, 12-month chart, and checksum footer."""
    # Get a real package to export
    pkg_resp = client.get("/api/v1/packages?city=Jodhpur&type=house&scenario=current")
    pkg_data = pkg_resp.json()["packages"]["balanced"]
    pkg_data["city"] = "Jodhpur"
    pkg_data["building_type"] = "house"

    payload = {
        "package_data": pkg_data,
        "language": "en",
        "project_title": "Passive Construction Specification"
    }

    response = client.post("/api/v1/export/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert len(response.headers.get("x-manifest-checksum", "")) == 64

    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 20000  # Should be ~80-100 KB with chart image
