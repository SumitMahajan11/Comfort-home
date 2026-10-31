"""
tests/test_rules.py: Unit tests for rules.py recommendation engine
==================================================================
Tests recommend(zone, season, lat, comfort_need) across 4 sample cities:
1. Shimla (Cold, Northern Hemisphere, lat 31.10)
2. Jodhpur (Hot-Dry, Northern Hemisphere, lat 26.28)
3. Mumbai (Hot-Humid, Northern Hemisphere, lat 19.07)
4. Pune (Warm/Mixed, Northern Hemisphere, lat 18.52)
Plus Southern Hemisphere Cold (e.g. Queenstown, lat -45.03) to verify hemisphere flip.

Verifies:
- Every material has: name, reason, approximate U-value or R-value, and relative cost (Low/Med/High).
- Cold rules: insulated walls, highest insulation on windward/north (or south if southern hemisphere),
  large double-glazed windows on sun-facing side, interior thermal mass.
- Hot-Dry rules: thick AAC / rammed earth on west/east, light reflective finish, small shaded windows
  west/east, cross-ventilation openings north/south, cool roof.
- Hot-Humid rules: lightweight ventilated walls, large shaded openings on windward, reflective roof,
  avoid heavy thermal mass.
- Warm/Mixed rules: balanced insulation, overhangs on sun side.
"""

import pytest
from rules import recommend


def _assert_material_fields(mat: dict):
    """Asserts each material has name, reason, U/R-value, and valid cost tier."""
    assert "name" in mat and len(mat["name"]) > 0, "Missing or empty material name"
    assert "reason" in mat and len(mat["reason"]) > 0, "Missing or empty material reason"
    assert ("u_value" in mat and len(mat["u_value"]) > 0) or ("r_value" in mat and len(mat["r_value"]) > 0), "Missing U/R-value"
    assert mat["cost"] in ("Low", "Med", "High"), f"Invalid cost: {mat.get('cost')}"


def test_city_1_shimla_cold():
    """
    City 1: Shimla (Zone: Cold, Lat: 31.10 N)
    Rules:
    - Insulated walls (rock wool/EPS + brick)
    - Highest insulation on the windward/north wall
    - Large double-glazed windows on the sun-facing side (South) for solar gain
    - Thermal mass (concrete/stone) inside
    """
    res = recommend(zone="Cold", season="Winter", lat=31.10, comfort_need="Needs Heating")

    # Structure check
    for wall_name in ["North", "South", "East", "West"]:
        assert wall_name in res["walls"]
        wall_data = res["walls"][wall_name]
        for m in wall_data["materials"]:
            _assert_material_fields(m)

    # 1. Highest insulation on North wall (Northern hemisphere)
    north_wall = res["walls"]["North"]["wall"]
    assert "Super-Insulated" in north_wall["name"] or "Rock Wool" in north_wall["name"]
    assert "0.24" in north_wall["u_value"] or "4.17" in north_wall["r_value"]

    # 2. Large double-glazed windows on sun-facing side (South)
    south_glazing = res["walls"]["South"]["glazing"]
    assert "Large" in south_glazing["name"] or "Double-Glazed" in south_glazing["name"]
    assert "solar gain" in south_glazing["reason"].lower() or "passive solar" in south_glazing["reason"].lower()

    # 3. Thermal mass inside
    assert "Interior" in res
    _assert_material_fields(res["interior"])
    assert "Concrete" in res["interior"]["name"] or "Stone" in res["interior"]["name"]


def test_city_2_jodhpur_hot_dry():
    """
    City 2: Jodhpur (Zone: Hot-Dry, Lat: 26.28 N)
    Rules:
    - Thick AAC blocks or rammed earth on west and east walls
    - Light-colored reflective finish
    - Small shaded windows west/east
    - Cross-ventilation openings north/south
    - Cool roof
    """
    res = recommend(zone="Hot-Dry", season="Summer", lat=26.28, comfort_need="Needs Cooling")

    # 1. Thick AAC blocks or rammed earth on West and East walls
    for flank in ["East", "West"]:
        wall = res["walls"][flank]["wall"]
        _assert_material_fields(wall)
        assert "AAC" in wall["name"] or "Rammed Earth" in wall["name"]

        # 2. Light-colored reflective finish
        finish = res["walls"][flank]["finish"]
        _assert_material_fields(finish)
        assert "Reflective" in finish["name"] or "SRI" in finish["name"]

        # 3. Small shaded windows west/east
        glazing = res["walls"][flank]["glazing"]
        _assert_material_fields(glazing)
        assert "Small" in glazing["name"] or "Recessed" in glazing["name"]

    # 4. Cross-ventilation openings north/south
    for ns in ["North", "South"]:
        glazing = res["walls"][ns]["glazing"]
        _assert_material_fields(glazing)
        assert "Cross-Ventilation" in glazing["name"] or "Ventilation" in glazing["name"]

    # 5. Cool roof
    assert "roof" in res
    _assert_material_fields(res["roof"])
    assert "Cool Roof" in res["roof"]["name"] or "SRI" in res["roof"]["name"]


def test_city_3_mumbai_hot_humid():
    """
    City 3: Mumbai (Zone: Hot-Humid, Lat: 19.07 N)
    Rules:
    - Lightweight, ventilated walls
    - Large shaded openings on windward sides
    - Reflective roof
    - Avoid heavy thermal mass
    """
    res = recommend(zone="Hot-Humid", season="Summer", lat=19.07, comfort_need="Needs Cooling")

    # 1. Lightweight ventilated walls
    for wall_name in ["North", "South", "East", "West"]:
        wall = res["walls"][wall_name]["wall"]
        _assert_material_fields(wall)
        assert "Lightweight" in wall["name"] or "Ventilated" in wall["name"]

    # 2. Large shaded openings on windward sides (South/West)
    south_glazing = res["walls"]["South"]["glazing"]
    _assert_material_fields(south_glazing)
    assert "Large" in south_glazing["name"] or "Louvered" in south_glazing["name"]
    assert "cross-ventilation" in south_glazing["reason"].lower() or "breeze" in south_glazing["reason"].lower()

    # 3. Reflective roof
    assert "roof" in res
    _assert_material_fields(res["roof"])
    assert "Reflective" in res["roof"]["name"] or "Cool Roof" in res["roof"]["name"]

    # 4. Avoid heavy thermal mass
    assert "interior" in res
    _assert_material_fields(res["interior"])
    assert "Avoid Heavy Thermal Mass" in res["interior"]["name"] or "Low-Mass" in res["interior"]["name"]


def test_city_4_pune_warm_mixed():
    """
    City 4: Pune (Zone: Warm/Mixed, Lat: 18.52 N)
    Rules:
    - Balanced insulation
    - Overhangs on sun side (South in Northern Hemisphere)
    """
    res = recommend(zone="Warm", season="Autumn", lat=18.52, comfort_need="Balanced")

    # 1. Balanced insulation across walls
    for wall_name in ["North", "South", "East", "West"]:
        wall = res["walls"][wall_name]["wall"]
        _assert_material_fields(wall)
        assert "Balanced" in wall["name"] or "Cavity Wall" in wall["name"]

    # 2. Overhangs on sun side (South)
    south_glazing = res["walls"]["South"]["glazing"]
    _assert_material_fields(south_glazing)
    assert "Overhang" in south_glazing["name"] or "Chajja" in south_glazing["name"]


def test_southern_hemisphere_cold_flip():
    """
    Test Southern Hemisphere Cold (e.g. Queenstown, New Zealand, Lat: -45.03)
    Rules:
    - Highest insulation on the windward/south wall (flipped from north)
    - Large double-glazed windows on the sun-facing side (North)
    """
    res = recommend(zone="Cold", season="Winter", lat=-45.03, comfort_need="Needs Heating")

    assert res["hemisphere"] == "Southern"
    assert res["sun_facing_wall"] == "North"
    assert res["polar_windward_wall"] == "South"

    # Flipped: South is windward/polar, so South gets the highest insulation
    south_wall = res["walls"]["South"]["wall"]
    _assert_material_fields(south_wall)
    assert "Super-Insulated" in south_wall["name"] or "Rock Wool" in south_wall["name"]

    # Flipped: North is sun-facing, so North gets the large double-glazed windows
    north_glazing = res["walls"]["North"]["glazing"]
    _assert_material_fields(north_glazing)
    assert "Large" in north_glazing["name"] or "Double-Glazed" in north_glazing["name"]
    assert "equator-facing" in north_glazing["reason"].lower() or "passive solar" in north_glazing["reason"].lower()
