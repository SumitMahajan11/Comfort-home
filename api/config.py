"""
api/config.py

Global configuration, constants, paths, and city metadata for the ClimateAdapt-Comfort API.
"""

import os
from typing import Dict, Any, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(REPO_ROOT, "data", "export", "manifest.json")
EXPORT_DIR = os.path.join(REPO_ROOT, "data", "export")
COSTS_DIR = os.path.join(REPO_ROOT, "data", "costs")
LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
EVIDENCE_DIR = os.path.join(REPO_ROOT, "reports", "evidence")

DEFAULT_MATCH_DISTANCE_THRESHOLD_KM = 300.0

ALLOWED_CITIES: List[str] = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]
ALLOWED_BUILDING_TYPES: List[str] = ["shelter_v1", "house", "apartment", "commercial"]
ALLOWED_SCENARIOS: List[str] = ["current", "plus1p5", "plus3p0"]

CITY_METADATA: Dict[str, Dict[str, Any]] = {
    "Jodhpur": {
        "city": "Jodhpur",
        "display_name": "Jodhpur",
        "zone": "Hot-dry",
        "koppen": "BWh",
        "epw": "IND_RJ_Jodhpur.423390_TMYx.epw",
        "coordinates": [26.2389, 73.0243],
        "confidence_tier": "Low",
        "confidence_reason": "Low dual-judge agreement (Spearman r_s = 0.099), DB II training envelope validity 68.4%",
        "adaptive_validity": 98.4,
        "db2_envelope_pct": 68.4,
        "reference_r2": {
            "O1_ml": 50.7,
            "warm_ml": 48.2,
            "cool_ml": 2.5,
            "O1_adapt": 32.1,
            "O2": 65.4
        }
    },
    "Mumbai": {
        "city": "Mumbai",
        "display_name": "Mumbai",
        "zone": "Warm-humid",
        "koppen": "Aw",
        "epw": "IND_MH_Mumbai-Santacruz.AP.430030_TMYx.epw",
        "coordinates": [19.0760, 72.8777],
        "confidence_tier": "Low",
        "confidence_reason": "Monsoon high humidity boundary; DB II ML training envelope validity 27.9% despite high rank correlation (r_s = 0.946)",
        "adaptive_validity": 100.0,
        "db2_envelope_pct": 27.9,
        "reference_r2": {
            "O1_ml": 35.0,
            "warm_ml": 35.0,
            "cool_ml": 0.0,
            "O1_adapt": 0.8,
            "O2": 45.2
        }
    },
    "New_Delhi": {
        "city": "New_Delhi",
        "display_name": "New Delhi",
        "zone": "Composite",
        "koppen": "Cwa",
        "epw": "IND_DL_New.Delhi-Safdarjung.AP.421820_TMYx.epw",
        "coordinates": [28.6139, 77.2090],
        "confidence_tier": "Low",
        "confidence_reason": "Low dual-judge agreement (Spearman r_s = 0.190), severe seasonal temperature swings between winter and summer",
        "adaptive_validity": 94.2,
        "db2_envelope_pct": 64.5,
        "reference_r2": {
            "O1_ml": 44.6,
            "warm_ml": 32.1,
            "cool_ml": 12.5,
            "O1_adapt": 46.7,
            "O2": 58.9
        }
    },
    "Bengaluru": {
        "city": "Bengaluru",
        "display_name": "Bengaluru",
        "zone": "Temperate",
        "koppen": "Aw",
        "epw": "IND_KA_Bangalore.432950_TMYx.epw",
        "coordinates": [12.9716, 77.5946],
        "confidence_tier": "Medium",
        "confidence_reason": "High dual-judge rank correlation (r_s = 0.942) and high Adaptive 90% validity share (100.0%)",
        "adaptive_validity": 100.0,
        "db2_envelope_pct": 66.8,
        "reference_r2": {
            "O1_ml": 20.1,
            "warm_ml": 12.3,
            "cool_ml": 7.8,
            "O1_adapt": 5.6,
            "O2": 18.3
        }
    },
    "Shimla": {
        "city": "Shimla",
        "display_name": "Shimla",
        "zone": "Cold",
        "koppen": "Cwb",
        "epw": "IND_HP_Shimla.420830_TMYx.epw",
        "coordinates": [31.1048, 77.1734],
        "confidence_tier": "Low",
        "confidence_reason": "Zero labelled thermal sensation votes in DB II (D-011); winter sub-10C temperatures outside Adaptive 90% validity range (26.0% invalid)",
        "adaptive_validity": 74.0,
        "db2_envelope_pct": 52.1,
        "reference_r2": {
            "O1_ml": 47.1,
            "warm_ml": 0.0,
            "cool_ml": 47.1,
            "O1_adapt": 59.1,
            "O2": 52.4
        }
    }
}
