import os
import sys
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import (
    calculate_daily_mean_series,
    compute_running_mean_outdoor_temperature_db2,
    evaluate_adaptive_90_comfort,
    ADAPTIVE_TRM_MIN,
    ADAPTIVE_TRM_MAX
)

def parse_epw_hourly_drybulb(epw_path):
    df = pd.read_csv(epw_path, skiprows=8, header=None)
    return df[6].values.astype(float)[:8760]

def compute_valid_adaptive_hours_from_tout(tout: np.ndarray) -> int:
    daily_tout = calculate_daily_mean_series(tout)
    t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    valid_mask = (t_rm_hourly >= ADAPTIVE_TRM_MIN) & (t_rm_hourly <= ADAPTIVE_TRM_MAX)
    return int(valid_mask.sum())

def compute_valid_adaptive_hours_from_epw(epw_path: str) -> int:
    tout = parse_epw_hourly_drybulb(epw_path)
    return compute_valid_adaptive_hours_from_tout(tout)

if __name__ == "__main__":
    manifest = pd.read_csv("reports/batch_epw_manifest.csv")
    old_climate = pd.read_csv("reports/batch_climate_table.csv")

    print(f"{'City':<18} {'Function (coupling)':<22} {'Old Climate Table':<20} {'Diff':<8}")
    print("-" * 70)
    for _, row in manifest.iterrows():
        city = row['city']
        epw_path = row['path']
        v_func = compute_valid_adaptive_hours_from_epw(epw_path)
        
        old_row = old_climate[old_climate['city'] == city]
        v_old = int(old_row['valid_adaptive_hours'].values[0]) if len(old_row) > 0 else -1
        diff = v_func - v_old
        print(f"{city:<18} {v_func:<22} {v_old:<20} {diff:<8}")
