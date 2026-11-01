"""
Unit tests for Phase 4A coupling engine (src/optimize/coupling.py).
Tests:
- Adaptive 90% band center at T_rm = 25 C equals 25.55 C (+/- 2.5 C).
- Running mean outdoor temperature against pythermalcomfort / ASHRAE DB II formula.
- ML champion predictions on known synthetic inputs.
- Invalid running mean temperature handling.
"""

import pytest
import numpy as np
import pandas as pd
from pythermalcomfort.utilities import running_mean_outdoor_temperature

from src.optimize.coupling import (
    ADAPTIVE_SLOPE,
    ADAPTIVE_INTERCEPT,
    ADAPTIVE_BAND_90,
    ADAPTIVE_TRM_MIN,
    ADAPTIVE_TRM_MAX,
    calculate_daily_mean_series,
    compute_running_mean_outdoor_temperature_db2,
    compute_clo_schedule_a004,
    evaluate_adaptive_90_comfort,
    evaluate_ml_champion_comfort,
    load_champion_model
)

def test_adaptive_band_at_25c():
    """Acceptance Check: adaptive band at running mean 25 C equals 25.55 C center, +/-2.5 C."""
    t_rm = 25.0
    t_cmf = ADAPTIVE_SLOPE * t_rm + ADAPTIVE_INTERCEPT
    assert np.isclose(t_cmf, 25.55, atol=1e-5), f"Expected 25.55 C, got {t_cmf}"
    
    lower_bound = t_cmf - ADAPTIVE_BAND_90
    upper_bound = t_cmf + ADAPTIVE_BAND_90
    assert np.isclose(lower_bound, 23.05, atol=1e-5), f"Expected 23.05 C, got {lower_bound}"
    assert np.isclose(upper_bound, 28.05, atol=1e-5), f"Expected 28.05 C, got {upper_bound}"

def test_running_mean_formula_synthetic_series():
    """Unit test on a synthetic 7-day temperature series against pythermalcomfort utility."""
    # Synthetic series of 7 daily temperatures
    synthetic_7days = [32.0, 30.0, 28.0, 26.0, 24.0, 22.0, 20.0]
    expected_trm = running_mean_outdoor_temperature(synthetic_7days, alpha=0.8)
    
    # Check manual computation
    coeff = [0.8**i for i in range(7)]
    manual_trm = round(sum(c * t for c, t in zip(coeff, synthetic_7days)) / sum(coeff), 1)
    assert np.isclose(expected_trm, manual_trm, atol=1e-5)
    
    # Test 365-day series in compute_running_mean_outdoor_temperature_db2
    constant_365 = np.full(365, 25.0)
    res_365 = compute_running_mean_outdoor_temperature_db2(constant_365, alpha=0.8)
    assert len(res_365) == 365
    assert np.allclose(res_365, 25.0, atol=1e-3)

def test_clo_schedule_a004():
    """Test clo rule A-004 logic."""
    daily_t = np.array([28.0, 25.0, 20.0, 15.0, 10.0, 0.0])
    # Repeat for 365 days
    full_daily = np.tile(daily_t, 365 // len(daily_t) + 1)[:365]
    clo_hourly = compute_clo_schedule_a004(full_daily)
    assert len(clo_hourly) == 8760
    assert np.isclose(clo_hourly[0], 0.5)  # 28.0 C >= 25 -> 0.5
    assert np.isclose(clo_hourly[24], 0.5) # 25.0 C >= 25 -> 0.5
    assert np.isclose(clo_hourly[48], 0.7) # 20.0 C in [15, 25) -> 0.7
    assert np.isclose(clo_hourly[72], 0.7) # 15.0 C in [15, 25) -> 0.7
    assert np.isclose(clo_hourly[96], 1.0) # 10.0 C < 15 -> 1.0

def test_adaptive_comfort_evaluation():
    """Test adaptive comfort on known indoor temperatures."""
    t_rm_hourly = np.full(100, 25.0) # T_cmf = 25.55, band = [23.05, 28.05]
    # Test 1: all within band
    ta = np.full(100, 25.55)
    tr = np.full(100, 25.55)
    res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
    assert res['O1_adapt'] == 0.0
    assert res['hot_adapt'] == 0.0
    assert res['cold_adapt'] == 0.0
    assert res['invalid_share_adapt'] == 0.0
    
    # Test 2: all hot (30 C)
    ta_hot = np.full(100, 30.0)
    tr_hot = np.full(100, 30.0)
    res_hot = evaluate_adaptive_90_comfort(ta_hot, tr_hot, t_rm_hourly)
    assert res_hot['O1_adapt'] == 100.0
    assert res_hot['hot_adapt'] == 100.0
    assert res_hot['cold_adapt'] == 0.0
    
    # Test 3: out-of-range T_rm (5 C < 10 C)
    t_rm_cold = np.full(100, 5.0)
    res_invalid = evaluate_adaptive_90_comfort(ta, tr, t_rm_cold)
    assert res_invalid['invalid_share_adapt'] == 100.0
    assert np.isnan(res_invalid['O1_adapt'])

def test_ml_champion_model_known_inputs():
    """Test ML champion predictions on extreme and neutral indoor conditions."""
    model = load_champion_model()
    
    # Neutral conditions (ta=24, tr=24, rh=50, clo=0.7, met=1.1, vel=0.15, tout=20)
    res_neutral = evaluate_ml_champion_comfort(
        model=model,
        ta=np.full(10, 24.0, dtype=np.float32),
        tr=np.full(10, 24.0, dtype=np.float32),
        rh=np.full(10, 50.0, dtype=np.float32),
        t_outdoor_hourly=np.full(10, 20.0, dtype=np.float32),
        clo_hourly=np.full(10, 0.7, dtype=np.float32),
        met=1.1,
        vel=0.15
    )
    # Neutral class should predict O1_ml == 0 (all neutral)
    assert res_neutral['O1_ml'] == 0.0
    
    # Extreme Hot conditions (ta=38, tr=38, rh=70, clo=0.5, met=1.1, vel=0.15, tout=35)
    res_hot = evaluate_ml_champion_comfort(
        model=model,
        ta=np.full(10, 38.0, dtype=np.float32),
        tr=np.full(10, 38.0, dtype=np.float32),
        rh=np.full(10, 70.0, dtype=np.float32),
        t_outdoor_hourly=np.full(10, 35.0, dtype=np.float32),
        clo_hourly=np.full(10, 0.5, dtype=np.float32),
        met=1.1,
        vel=0.15
    )
    assert res_hot['warm_ml'] == 100.0
    assert res_hot['O1_ml'] == 100.0
    
    # Extreme Cold conditions (ta=12, tr=12, rh=40, clo=1.0, met=1.1, vel=0.15, tout=10)
    res_cold = evaluate_ml_champion_comfort(
        model=model,
        ta=np.full(10, 12.0, dtype=np.float32),
        tr=np.full(10, 12.0, dtype=np.float32),
        rh=np.full(10, 40.0, dtype=np.float32),
        t_outdoor_hourly=np.full(10, 10.0, dtype=np.float32),
        clo_hourly=np.full(10, 1.0, dtype=np.float32),
        met=1.1,
        vel=0.15
    )
    assert res_cold['cool_ml'] == 100.0
    assert res_cold['O1_ml'] == 100.0

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_coupling.py"])
