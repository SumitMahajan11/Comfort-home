"""
tests/test_app.py

Automated Streamlit application testing using streamlit.testing.v1.AppTest.
Verifies that all 5 pages and city transitions render without exceptions.
"""

import pytest
from streamlit.testing.v1 import AppTest

def test_app_overview_page():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"App raised exception on Overview page: {at.exception}"
    assert "ClimateAdapt-Comfort" in at.title[0].value

def test_app_city_selection():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Test changing city to Shimla
    city_select = at.sidebar.selectbox[0]
    city_select.select("Shimla").run()
    assert not at.exception, f"App raised exception on Shimla selection: {at.exception}"
    assert "Shimla" in at.sidebar.markdown[0].value or "Shimla" in at.metric[0].value

def test_app_evaluate_page():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Navigate to Evaluate a Design
    nav_radio = at.sidebar.radio[0]
    nav_radio.set_value("2. Evaluate a Design").run()
    assert not at.exception, f"App raised exception on Evaluate page: {at.exception}"
    assert "Evaluate a Custom Shelter Design" in at.title[0].value
    assert len(at.metric) >= 3 # O1_ml, O1_adapt, O2

def test_app_recommend_page():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Navigate to Recommend
    nav_radio = at.sidebar.radio[0]
    nav_radio.set_value("3. Recommend").run()
    assert not at.exception, f"App raised exception on Recommend page: {at.exception}"
    assert "Recommend: Multi-Objective Pareto Explorer" in at.title[0].value

def test_app_explain_page():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Navigate to Explain
    nav_radio = at.sidebar.radio[0]
    nav_radio.set_value("4. Explain").run()
    assert not at.exception, f"App raised exception on Explain page: {at.exception}"
    assert "Explain: SHAP Attribution & Model Drivers" in at.title[0].value

def test_app_about_page():
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Navigate to About
    nav_radio = at.sidebar.radio[0]
    nav_radio.set_value("5. About").run()
    assert not at.exception, f"App raised exception on About page: {at.exception}"
    assert "About ClimateAdapt-Comfort & Research Audit" in at.title[0].value
