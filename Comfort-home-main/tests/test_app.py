"""
tests/test_app.py

Automated Streamlit application testing using streamlit.testing.v1.AppTest.
Verifies the new 'Get My Shelter Design' default user flow and all 5 research details sub-pages.
"""

import pytest
from streamlit.testing.v1 import AppTest


def test_get_my_shelter_design_default_page():
    """Tests the new default page: 'Get My Shelter Design'."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"App raised exception on default page: {at.exception}"
    assert "Get My Climate-Adapted Shelter Design" in at.title[0].value
    
    # Check that location input exists
    assert len(at.text_input) >= 1
    # Check that questionnaire inputs exist
    assert len(at.radio) >= 1
    # Check that metrics (points better, energy saving) are computed and displayed
    assert len(at.metric) >= 2


def test_get_my_shelter_design_form_submission():
    """Tests submitting the shelter questionnaire form with custom inputs."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Change location to Shimla
    at.text_input[0].input("Shimla, Himachal Pradesh").run()
    assert not at.exception, f"App raised exception on location change: {at.exception}"
    
    # Submit form via button
    if len(at.button) > 0:
        at.button[0].click().run()
        assert not at.exception, f"App raised exception on form submit: {at.exception}"
    assert len(at.metric) >= 2


def test_research_details_overview_subpage():
    """Tests navigating to Research Details -> 1. Overview."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    # Navigate to Research Details
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    assert not at.exception, f"App raised exception on Research Details navigation: {at.exception}"
    assert "ClimateAdapt-Comfort: Research Overview" in at.title[0].value


def test_research_details_city_selection():
    """Tests selecting a different climate station in Research Details."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    # Select Shimla in sidebar selectbox (station picker is index 1 in sidebar)
    at.sidebar.selectbox[1].select("Shimla").run()
    assert not at.exception, f"App raised exception on Shimla selection: {at.exception}"
    assert "Shimla" in at.metric[0].value or "Shimla" in at.sidebar.markdown[0].value


def test_research_details_evaluate_page():
    """Tests Research Details -> 2. Evaluate a Design."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    at.sidebar.selectbox[0].select("2. Evaluate a Design").run()
    assert not at.exception, f"App raised exception on Evaluate page: {at.exception}"
    assert "Evaluate a Custom Shelter Design" in at.title[0].value
    assert len(at.metric) >= 3  # O1_ml, O1_adapt, O2


def test_research_details_recommend_page():
    """Tests Research Details -> 3. Recommend."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    at.sidebar.selectbox[0].select("3. Recommend").run()
    assert not at.exception, f"App raised exception on Recommend page: {at.exception}"
    assert "Recommend: Multi-Objective Pareto Explorer" in at.title[0].value


def test_research_details_explain_page():
    """Tests Research Details -> 4. Explain."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    at.sidebar.selectbox[0].select("4. Explain").run()
    assert not at.exception, f"App raised exception on Explain page: {at.exception}"
    assert "Explain: SHAP Attribution & Model Drivers" in at.title[0].value


def test_research_details_about_page():
    """Tests Research Details -> 5. About."""
    at = AppTest.from_file("src/app/app.py", default_timeout=30)
    at.run()
    
    at.sidebar.radio[0].set_value("🔬 Research Details").run()
    at.sidebar.selectbox[0].select("5. About").run()
    assert not at.exception, f"App raised exception on About page: {at.exception}"
    assert "About ClimateAdapt-Comfort & Research Audit" in at.title[0].value

