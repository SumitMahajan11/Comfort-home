"""
tests/test_ground_temperature.py

Unit tests for EPW ground temperature parsing, Site:GroundTemperature:BuildingSurface
generation, logging fallbacks, and template verification under Decision D-035.
"""

import os
import re
import pytest
import logging
from src.sim.render import (
    parse_epw_ground_temperatures,
    resolve_epw_path,
    get_ground_temperatures_from_epw,
    render_building_idf,
    render_shelter_idf,
    DEFAULT_GROUND_TEMP
)

JODHPUR_EPW = "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"

def test_parse_epw_ground_temperatures():
    """Verify ground temperature parser extracts 0.5 m, 2.0 m, 4.0 m depths correctly."""
    assert os.path.exists(JODHPUR_EPW), f"EPW file {JODHPUR_EPW} must exist"
    depths = parse_epw_ground_temperatures(JODHPUR_EPW)
    assert depths is not None
    assert 0.5 in depths
    assert 2.0 in depths
    assert 4.0 in depths
    assert len(depths[0.5]) == 12

    # Check Jodhpur expected values for 0.5m depth
    expected_jan = 18.91
    expected_jul = 34.79
    assert abs(depths[0.5][0] - expected_jan) < 0.01
    assert abs(depths[0.5][6] - expected_jul) < 0.01

def test_get_ground_temperatures_by_city_and_path():
    """Verify get_ground_temperatures_from_epw works with both explicit epw_path and city name."""
    temps_by_path = get_ground_temperatures_from_epw(epw_path=JODHPUR_EPW)
    temps_by_city = get_ground_temperatures_from_epw(city="Jodhpur")
    assert len(temps_by_path) == 12
    assert len(temps_by_city) == 12
    assert temps_by_path == temps_by_city

def test_ground_temperatures_fallback_and_logging(tmp_path, caplog):
    """Verify fallback to 18.0 C and warning logging when EPW is missing or missing header."""
    from src.sim.render import _GROUND_TEMPS_CACHE
    _GROUND_TEMPS_CACHE.clear()
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        # 1. Missing EPW file / unknown city
        fallback_temps = get_ground_temperatures_from_epw(city="NonExistentCity_XYZ")
        assert fallback_temps == [DEFAULT_GROUND_TEMP] * 12
        assert any("Falling back to constant 18.0" in rec.message for rec in caplog.records)

    _GROUND_TEMPS_CACHE.clear()
    caplog.clear()
    # 2. EPW file without GROUND TEMPERATURES block
    dummy_epw = str(tmp_path / "dummy.epw")
    with open(dummy_epw, "w") as f:
        f.write("LOCATION,Dummy,XX,ZZ\nDESIGN CONDITIONS,1\nDATA PERIODS,1\n")

    with caplog.at_level(logging.WARNING):
        fallback_dummy = get_ground_temperatures_from_epw(epw_path=dummy_epw)
        assert fallback_dummy == [DEFAULT_GROUND_TEMP] * 12
        assert any("GROUND TEMPERATURES header block missing" in rec.message for rec in caplog.records)

def test_render_includes_ground_temperature_object(tmp_path):
    """Verify render_building_idf outputs Site:GroundTemperature:BuildingSurface for all modes."""
    sample_params = {
        'roof_insulation_thickness': 0.05,
        'wall_insulation_thickness': 0.05,
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.7,
        'wwr': 0.20,
        'orientation': 0.0,
        'shading_depth': 0.5,
        'ventilation_ach': 5.0,
        'city': 'Jodhpur'
    }

    # Test shelter_v1 in both free_running and ideal_loads
    for mode in ['free_running', 'ideal_loads']:
        out_idf = str(tmp_path / f"shelter_{mode}.idf")
        render_shelter_idf(sample_params, output_idf_path=out_idf, mode=mode, epw_path=JODHPUR_EPW)
        with open(out_idf, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "Site:GroundTemperature:BuildingSurface" in content
        assert "18.91," in content  # Jan temp for Jodhpur
        assert "34.79," in content  # Jul temp for Jodhpur

    # Test multi-zone building type (commercial)
    out_comm = str(tmp_path / "commercial.idf")
    render_building_idf(
        sample_params,
        output_idf_path=out_comm,
        building_type='commercial',
        mode='ideal_loads',
        epw_path=JODHPUR_EPW
    )
    with open(out_comm, 'r', encoding='utf-8') as f:
        content_comm = f.read()
    assert "Site:GroundTemperature:BuildingSurface" in content_comm
    assert "18.91," in content_comm

def test_template_idf_contains_ground_temperature():
    """Verify static template.idf includes Site:GroundTemperature:BuildingSurface."""
    template_path = os.path.join("src", "sim", "template.idf")
    assert os.path.exists(template_path)
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r"Site:GroundTemperature:BuildingSurface,\s*\n(.*?);", content, re.DOTALL)
    assert match is not None, "Site:GroundTemperature:BuildingSurface missing in template.idf"
    lines = [line.strip().split(",")[0].strip() for line in match.group(1).split("\n") if line.strip()]
    assert len(lines) == 12, "Must contain exactly 12 monthly ground temperature entries"
