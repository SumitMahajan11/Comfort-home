"""
ClimateAdapt-Comfort: Dual Comfort Judge Coupling Engine.
Phase 4A: Computes objectives O1 and O2 for every simulated shelter design
under two comfort judges:
1. ML Champion (calibrated Ablation_A3_OutdoorTemp XGBoost classifier)
2. Physical Adaptive 90% model (ASHRAE 55 / pythermalcomfort)

Includes:
- Running mean outdoor temperature (t_mot_isd) matching ASHRAE DB II
- Scenario assumptions A-001 (24h), A-002 (met=1.1), A-003 (vel=0.15 m/s), A-004 (daily clo rule)
- Applicability domain & validity checks
- Objective generation and sensitivity comparison (running mean vs raw tout)
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional

# Constants from Spec & pythermalcomfort
ADAPTIVE_SLOPE = 0.31
ADAPTIVE_INTERCEPT = 17.8
ADAPTIVE_BAND_90 = 2.5
ADAPTIVE_TRM_MIN = 10.0
ADAPTIVE_TRM_MAX = 33.5

def calculate_daily_mean_series(hourly_series: np.ndarray) -> np.ndarray:
    """Computes 365 daily means from 8,760 hourly values."""
    if len(hourly_series) != 8760:
        raise ValueError(f"Expected 8760 hourly values, got {len(hourly_series)}")
    return hourly_series.reshape(365, 24).mean(axis=1)

def compute_running_mean_outdoor_temperature_db2(
    daily_tout: np.ndarray,
    alpha: float = 0.8
) -> np.ndarray:
    """
    Computes 7-day running mean outdoor temperature matching ASHRAE DB II (t_mot_isd).
    
    Source in ASHRAE DB II:
    data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/main.py, lines 130-160
    using pythermalcomfort.utilities.running_mean_outdoor_temperature:
      coeff = [alpha**i for i in range(7)]  (ordered newest to oldest: d-1, d-2, ..., d-7)
      t_rm = sum(coeff * temp_array) / sum(coeff)
      rounded to 1 decimal place.
      
    For annual simulation with cyclic annual weather, boundary wrap is applied for the first 7 days.
    """
    if len(daily_tout) != 365:
        raise ValueError(f"Expected 365 daily values, got {len(daily_tout)}")
        
    coeff = np.array([alpha**i for i in range(7)], dtype=np.float64)
    coeff_sum = coeff.sum()
    
    # Extended series with cyclic wrap for previous 7 days (days 358..364 wrapped before day 0)
    extended_tout = np.concatenate([daily_tout[-7:], daily_tout])
    
    t_rm_daily = np.zeros(365, dtype=np.float64)
    for d in range(365):
        # Window of 7 previous days: indices d+6 down to d in extended_tout (newest to oldest)
        prev_7_days = extended_tout[d:d+7][::-1]
        t_rm_daily[d] = np.sum(coeff * prev_7_days) / coeff_sum
        
    return np.round(t_rm_daily, 1)

def compute_clo_schedule_a004(daily_tout: np.ndarray) -> np.ndarray:
    """
    Computes hourly clothing insulation according to Assumption A-004:
    - clo = 0.5 if daily mean tout >= 25.0 C
    - clo = 0.7 if 15.0 C <= daily mean tout < 25.0 C
    - clo = 1.0 if daily mean tout < 15.0 C
    Repeats 365 daily clo values across 24 hours (8,760 hourly values).
    """
    daily_clo = np.empty(365, dtype=np.float32)
    daily_clo[daily_tout >= 25.0] = 0.5
    daily_clo[(daily_tout >= 15.0) & (daily_tout < 25.0)] = 0.7
    daily_clo[daily_tout < 15.0] = 1.0
    return np.repeat(daily_clo, 24)

def evaluate_adaptive_90_comfort(
    ta: np.ndarray,
    tr: np.ndarray,
    t_rm_hourly: np.ndarray
) -> Dict[str, float]:
    """
    Evaluates comfort under ASHRAE 55 Adaptive 90% model.
    T_cmf = 0.31 * T_rm + 17.8
    Acceptability band: +/- 2.5 C
    Valid only for T_rm between 10.0 and 33.5 C.
    Hours outside this range are counted as invalid (not clipped).
    """
    top = (ta + tr) / 2.0
    valid_mask = (t_rm_hourly >= ADAPTIVE_TRM_MIN) & (t_rm_hourly <= ADAPTIVE_TRM_MAX)
    n_total = len(ta)
    n_valid = int(valid_mask.sum())
    
    if n_valid == 0:
        return {
            "O1_adapt": np.nan,
            "hot_adapt": np.nan,
            "cold_adapt": np.nan,
            "invalid_share_adapt": 100.0,
            "valid_hours_adapt": 0
        }
        
    t_cmf = ADAPTIVE_SLOPE * t_rm_hourly[valid_mask] + ADAPTIVE_INTERCEPT
    top_valid = top[valid_mask]
    
    hot_mask = top_valid > (t_cmf + ADAPTIVE_BAND_90)
    cold_mask = top_valid < (t_cmf - ADAPTIVE_BAND_90)
    discomfort_mask = hot_mask | cold_mask
    
    return {
        "O1_adapt": float(discomfort_mask.mean() * 100.0),
        "hot_adapt": float(hot_mask.mean() * 100.0),
        "cold_adapt": float(cold_mask.mean() * 100.0),
        "invalid_share_adapt": float((n_total - n_valid) / n_total * 100.0),
        "valid_hours_adapt": n_valid
    }

def evaluate_ml_champion_comfort(
    model,
    ta: np.ndarray,
    tr: np.ndarray,
    rh: np.ndarray,
    t_outdoor_hourly: np.ndarray,
    clo_hourly: np.ndarray,
    met: float = 1.1,
    vel: float = 0.15
) -> Dict[str, float]:
    """
    Evaluates comfort under calibrated ML Champion (Ablation_A3_OutdoorTemp).
    Features: ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_outdoor']
    Target mapping: 0=cool, 1=neutral, 2=warm
    """
    n_hours = len(ta)
    df_feat = pd.DataFrame({
        'ta': ta,
        'tr': tr,
        'rh': rh,
        'vel': np.full(n_hours, vel, dtype=np.float32),
        'clo': clo_hourly,
        'met': np.full(n_hours, met, dtype=np.float32),
        't_outdoor': t_outdoor_hourly
    })
    
    # Predict classes
    preds = model.predict(df_feat)
    
    cool_mask = (preds == 0)
    neutral_mask = (preds == 1)
    warm_mask = (preds == 2)
    discomfort_mask = ~neutral_mask
    
    return {
        "O1_ml": float(discomfort_mask.mean() * 100.0),
        "cool_ml": float(cool_mask.mean() * 100.0),
        "warm_ml": float(warm_mask.mean() * 100.0)
    }

def load_champion_model(model_path: str = "models/champion_comfort_model.joblib"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}")
    artifact = joblib.load(model_path)
    return artifact['model']
