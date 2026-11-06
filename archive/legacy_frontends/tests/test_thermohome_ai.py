"""
Automated Unit and Integration Tests for ThermoHome AI (app.py)
==============================================================
Tests verify:
1. Season auto-detection across Northern & Southern hemispheres.
2. Degree days calculation (HDD18 and CDD24).
3. ASHRAE climate classification rules ('ASHRAE-based approximation').
4. Physiological & clothing-based thermal comfort adjustments.
5. Building material recommendations coverage.
6. Orientation-specific wall layout strategies & hemisphere reversal.
7. Graceful Open-Meteo failure handling with sample data fallback.
8. Streamlit AppTest end-to-end execution.
"""

import datetime
import unittest.mock as mock
import pytest
from streamlit.testing.v1 import AppTest

import app


def test_detect_season():
    # Northern Hemisphere summer date (July 15)
    summer_date = datetime.date(2026, 7, 15)
    season, hemi = app.detect_season(18.52, reference_date=summer_date)
    assert season == "Summer"
    assert hemi == "Northern"

    # Northern Hemisphere winter date (January 15)
    winter_date = datetime.date(2026, 1, 15)
    season, hemi = app.detect_season(28.61, reference_date=winter_date)
    assert season == "Winter"
    assert hemi == "Northern"

    # Southern Hemisphere: July 15 must be Winter
    season, hemi = app.detect_season(-33.86, reference_date=summer_date)
    assert season == "Winter"
    assert hemi == "Southern"

    # Southern Hemisphere: January 15 must be Summer
    season, hemi = app.detect_season(-33.86, reference_date=winter_date)
    assert season == "Summer"
    assert hemi == "Southern"


def test_calculate_degree_days():
    # 5 days: [10, 15, 20, 25, 30]
    # HDD base 18:
    # 18-10 = 8
    # 18-15 = 3
    # 18-20 = 0
    # 18-25 = 0
    # 18-30 = 0 -> Total HDD = 11
    # CDD base 24:
    # 10-24 = 0
    # 15-24 = 0
    # 20-24 = 0
    # 25-24 = 1
    # 30-24 = 6 -> Total CDD = 7
    temps = [10.0, 15.0, 20.0, 25.0, 30.0]
    hdd, cdd, mean_t = app.calculate_degree_days(temps, hdd_base=18.0, cdd_base=24.0)
    assert hdd == 11.0
    assert cdd == 7.0
    assert mean_t == 20.0


def test_classify_ashrae_zone():
    # Cold zone
    zone, _ = app.classify_ashrae_zone(hdd=1600, cdd=0, humidity=50, mean_temp=12)
    assert zone == "Cold"

    # Mixed zone (both high HDD and CDD)
    zone, _ = app.classify_ashrae_zone(hdd=300, cdd=600, humidity=50, mean_temp=22)
    assert zone == "Mixed"

    # Hot-Humid zone
    zone, _ = app.classify_ashrae_zone(hdd=0, cdd=1400, humidity=75, mean_temp=28)
    assert zone == "Hot-Humid"

    # Hot-Dry zone
    zone, _ = app.classify_ashrae_zone(hdd=50, cdd=1600, humidity=30, mean_temp=29)
    assert zone == "Hot-Dry"

    # Warm zone (Pune archetype)
    zone, _ = app.classify_ashrae_zone(hdd=0, cdd=780, humidity=60, mean_temp=25)
    assert zone == "Warm"


def test_evaluate_comfort_need():
    # Baseline condition: 24C, standard body temp, medium clothing, light activity
    res = app.evaluate_comfort_need(current_temp=24.0, body_temp=36.8, clothing_level="Medium", activity_level="Light")
    assert res["need"] == "Balanced"
    assert res["adj_neutral"] == 24.0

    # Person wearing heavy clothing and actively moving at 26C ambient:
    # Heavy clothing (-2.5C) + Active (-2.0C) -> adjusted neutral drops to 19.5C
    # Current temp 26C is far above 19.5 + 1.8 -> Needs Cooling!
    res_cooling = app.evaluate_comfort_need(current_temp=26.0, body_temp=36.8, clothing_level="Heavy", activity_level="Active")
    assert res_cooling["need"] == "Needs Cooling"

    # Person wearing light clothing, resting, at 20C ambient:
    # Light (+2.0C) + Resting (+1.5C) -> adjusted neutral rises to 27.5C
    # Current temp 20C is far below 27.5 - 1.8 -> Needs Heating!
    res_heating = app.evaluate_comfort_need(current_temp=20.0, body_temp=36.8, clothing_level="Light", activity_level="Resting")
    assert res_heating["need"] == "Needs Heating"


def test_recommended_materials():
    for zone in ["Hot-Humid", "Hot-Dry", "Warm", "Mixed", "Cold"]:
        mats = app.get_recommended_materials(zone, "Balanced")
        assert "walls" in mats
        assert "insulation" in mats
        assert "roof" in mats
        assert "glazing" in mats
        assert "finishes" in mats
        assert len(mats["walls"][0]) > 0


def test_wall_orientation_strategy_hemisphere():
    # Northern hemisphere: South is primary solar collector
    strat_north = app.get_wall_orientation_strategy("Warm", latitude=18.52)
    assert "South" in strat_north
    assert "Solar" in strat_north["South"]["role"] or "Sun" in strat_north["South"]["role"]

    # Southern hemisphere: North is equator-facing solar collector
    strat_south = app.get_wall_orientation_strategy("Warm", latitude=-33.86)
    assert "North" in strat_south
    assert "Solar" in strat_south["North"]["role"] or "Sun" in strat_south["North"]["role"]


def test_api_failure_fallback():
    # When network error occurs, fallback returns cached sample data
    with mock.patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        # Clear cache for testing
        app.fetch_climate_data.clear()
        data = app.fetch_climate_data(18.52, 73.86)
        assert data["is_cached_sample"] is True
        assert data["error_message"] is not None
        assert len(data["daily_means"]) == 365
        assert data["current_temp"] == 26.5


def test_streamlit_app_execution():
    # End-to-end execution of app.py with 3 tabs: (Climate | Materials | Wall Layout)
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.tabs) == 3
    assert at.tabs[0].label == "Climate"
    assert at.tabs[1].label == "Materials"
    assert at.tabs[2].label == "Wall Layout"


def test_offline_demo_mode_execution():
    """Verifies that activating the Offline Demo Mode checkbox uses cached data without network calls."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    demo_cb = at.sidebar.checkbox[0]
    assert "Offline Demo Mode" in demo_cb.label
    assert demo_cb.value is False

    # Toggle checkbox to True
    demo_cb.check().run()
    assert not at.exception
    # Check that info banner indicates offline demo mode active
    assert any("Offline Demo Mode Active" in info.value for info in at.info)


def test_summary_generators():
    """Verifies that Markdown and PDF report generators produce valid advisory artifacts."""
    from rules import recommend
    sample_weather = app.get_cached_sample_data(18.52, 73.86)
    hdd18, cdd24, annual_mean = app.calculate_degree_days(sample_weather["daily_means"])
    zone, zone_desc = app.classify_ashrae_zone(hdd18, cdd24, sample_weather["current_humidity"], annual_mean)
    comfort_res = app.evaluate_comfort_need(sample_weather["current_temp"], 36.8, "Medium", "Light")
    rec_results = recommend(zone, "Summer", 18.52, comfort_res["need"])
    wall_strat = app.get_wall_orientation_strategy(zone, 18.52)

    # Markdown report
    md_report = app.generate_markdown_summary(
        lat=18.52,
        lon=73.86,
        season="Summer",
        hemisphere="Northern",
        weather=sample_weather,
        hdd18=hdd18,
        cdd24=cdd24,
        annual_mean=annual_mean,
        ashrae_zone=zone,
        zone_desc=zone_desc,
        comfort_res=comfort_res,
        rec_results=rec_results,
        wall_strategies=wall_strat,
        is_demo_mode=True
    )
    assert isinstance(md_report, str)
    assert "# ThermoHome AI" in md_report
    assert "Offline Demo Mode" in md_report
    assert "ASHRAE-based approximation" in md_report
    assert "North Wall" in md_report

    # PDF report
    pdf_bytes = app.generate_pdf_summary(
        lat=18.52,
        lon=73.86,
        season="Summer",
        hemisphere="Northern",
        weather=sample_weather,
        hdd18=hdd18,
        cdd24=cdd24,
        annual_mean=annual_mean,
        ashrae_zone=zone,
        zone_desc=zone_desc,
        comfort_res=comfort_res,
        rec_results=rec_results,
        wall_strategies=wall_strat,
        is_demo_mode=True
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_top_view_house_diagram_and_gauge():
    """Verifies that the top-view diagram and thermometer gauge render without exceptions."""
    from rules import recommend
    import matplotlib.pyplot as plt

    rec = recommend("Cold", "Winter", 31.10, "Needs Heating")
    fig_house = app.plot_top_view_house_diagram(rec, "Northern", "Cold")
    assert fig_house is not None
    plt.close(fig_house)

    # Test Southern hemisphere flip diagram
    rec_south = recommend("Hot-Dry", "Summer", -33.86, "Needs Cooling")
    fig_house_south = app.plot_top_view_house_diagram(rec_south, "Southern", "Hot-Dry")
    assert fig_house_south is not None
    plt.close(fig_house_south)

    # Test thermometer gauge
    comfort_res = app.evaluate_comfort_need(28.0, 36.8, "Medium", "Light")
    fig_gauge = app.plot_thermometer_gauge(comfort_res, 28.0)
    assert fig_gauge is not None
    plt.close(fig_gauge)

