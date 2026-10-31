"""
src/geometry.py

Canonical Single Source of Truth for building geometry in ClimateAdapt-Comfort v2.
Defines the exact geometric parameters actually simulated in EnergyPlus.
"""

from typing import Dict, Any

SHELTER_V1_GEOMETRY: Dict[str, Any] = {
    "building_type": "shelter_v1",
    "name": "Single-Zone Passive Shelter",
    "floor_width_m": 5.0,
    "floor_length_m": 4.0,
    "floor_area_m2": 20.0,
    "carpet_area_m2": 20.0,
    "height_m": 3.0,
    "perimeter_m": 18.0,
    "gross_wall_area_m2": 54.0,
    "roof_area_m2": 20.0,
    "volume_m3": 60.0,
    "exposed_roof_default": True,
    "window_height_m": 1.2,
    "display_text": "about 20 m² floor area (5 m x 4 m), 3 m high"
}

TYPOLOGY_GEOMETRY: Dict[str, Dict[str, Any]] = {
    "shelter_v1": SHELTER_V1_GEOMETRY,
    "house": {
        "building_type": "house",
        "name": "Detached House (Preliminary / Not Verified)",
        "floor_area_m2": 59.0,
        "carpet_area_m2": 59.0,
        "height_m": 3.0,
        "perimeter_m": 31.5,
        "gross_wall_area_m2": 94.5,
        "roof_area_m2": 59.0,
        "volume_m3": 177.0,
        "exposed_roof_default": True,
        "window_height_m": 1.2,
        "display_text": "about 59 m² floor area (preliminary / not verified)"
    },
    "apartment": {
        "building_type": "apartment",
        "name": "Apartment (Preliminary / Not Verified)",
        "floor_area_m2": 55.0,
        "carpet_area_m2": 55.0,
        "height_m": 2.8,
        "perimeter_m": 15.0,
        "gross_wall_area_m2": 42.0,
        "roof_area_m2": 0.0,
        "volume_m3": 154.0,
        "exposed_roof_default": False,
        "window_height_m": 1.2,
        "display_text": "about 55 m² floor area (preliminary / not verified)"
    },
    "commercial": {
        "building_type": "commercial",
        "name": "Commercial Office (Preliminary / Not Verified)",
        "floor_area_m2": 80.0,
        "carpet_area_m2": 80.0,
        "height_m": 3.5,
        "perimeter_m": 36.0,
        "gross_wall_area_m2": 126.0,
        "roof_area_m2": 80.0,
        "volume_m3": 280.0,
        "exposed_roof_default": True,
        "window_height_m": 1.5,
        "display_text": "about 80 m² floor area (preliminary / not verified)"
    }
}

def export_geometry_json():
    import json
    from pathlib import Path
    
    data = {
        "shelter_v1": SHELTER_V1_GEOMETRY,
        "typologies": TYPOLOGY_GEOMETRY
    }
    
    paths = [
        Path("data/export/geometry.json"),
        Path("web/src/data/geometry.json"),
        Path("web/public/data/geometry.json")
    ]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    print(f"Exported geometry to {len(paths)} locations.")

if __name__ == "__main__":
    export_geometry_json()
