"""
tools/report_adaptive_applicability.py

Computes and prints the fraction of hours where the running-mean outdoor temperature
is inside the ASHRAE 55 Adaptive 90% model's valid range (10.0 °C to 33.5 °C)
for Shimla and Leh baseline EPWs, and documents how out-of-range hours are treated in O1_adapt.
"""

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
    compute_valid_adaptive_hours,
    ADAPTIVE_TRM_MIN,
    ADAPTIVE_TRM_MAX
)

EPW_PATHS = {
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw",
    "Leh": "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
}

def parse_epw_hourly_drybulb(epw_path):
    # EPW: 8 header lines, col 6 (0-indexed) is drybulb
    df = pd.read_csv(epw_path, skiprows=8, header=None)
    return df[6].values.astype(float)[:8760]

def main():
    print("=" * 95)
    print("ADAPTIVE COMFORT MODEL APPLICABILITY ANALYSIS (SHIMLA vs LEH)")
    print(f"Adaptive Model Valid Range: [{ADAPTIVE_TRM_MIN:.1f} °C, {ADAPTIVE_TRM_MAX:.1f} °C] running-mean outdoor temperature")
    print("=" * 95)

    print(f"{'Station':<10} {'Total Hrs':<12} {'Valid Hrs':<12} {'Valid (%)':<12} {'Invalid Hrs':<14} {'Invalid (%)':<14} {'T_rm Min':<10} {'T_rm Max':<10}")
    print("-" * 95)

    for city, path in EPW_PATHS.items():
        if not os.path.exists(path):
            print(f"{city:<10} File not found at {path}")
            continue

        tout = parse_epw_hourly_drybulb(path)
        daily = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)

        n_valid = compute_valid_adaptive_hours(t_rm_hourly)
        n_total = len(t_rm_hourly)
        valid_frac = n_valid / n_total * 100.0
        invalid_frac = 100.0 - valid_frac

        print(f"{city:<10} {n_total:<12} {n_valid:<12} {valid_frac:<12.2f} {n_total - n_valid:<14} {invalid_frac:<14.2f} {t_rm_hourly.min():<10.2f} {t_rm_hourly.max():<10.2f}")

    print("=" * 95)
    print("\nTREATMENT OF OUT-OF-RANGE HOURS IN O1_adapt (from src/optimize/coupling.py):")
    print("-" * 95)
    print("1. Calculation Domain: Out-of-range hours (T_rm < 10.0 °C or T_rm > 33.5 °C) are EXCLUDED")
    print("   from the calculation of O1_adapt. In coupling.py:evaluate_adaptive_90_comfort():")
    print("     valid_mask = (t_rm_hourly >= ADAPTIVE_TRM_MIN) & (t_rm_hourly <= ADAPTIVE_TRM_MAX)")
    print("     top_valid = top[valid_mask]")
    print("     discomfort_mask = (top_valid > t_cmf + 2.5) | (top_valid < t_cmf - 2.5)")
    print("     O1_adapt = float(discomfort_mask.mean() * 100.0)")
    print("2. Normalization / Denominator: The percentage of discomfort O1_adapt is normalized ONLY over")
    print("   the valid hours (n_valid), NOT over the 8,760 annual hours.")
    print("3. Separate Auditing: The fraction of invalid hours is tracked independently as 'invalid_share_adapt':")
    print("     invalid_share_adapt = float((n_total - n_valid) / n_total * 100.0)")
    print("4. Fallback: If no hours fall in the valid range (n_valid == 0), O1_adapt returns np.nan.")
    print("5. Key Consequence for Cold Climates:")
    print("   - For Shimla, O1_adapt reflects comfort across 73.97% of the year (spring/summer/autumn).")
    print("   - For Leh, because 86.03% of the year has T_rm < 10 °C, O1_adapt evaluates ONLY the 13.97% (1,224 h)")
    print("     warmest summer window. Extreme winter freeze is invisible to O1_adapt, making the ML judge (O1_ml)")
    print("     and operative temperature safety bounds (< 5 °C) essential safety constraints.")
    print("-" * 95)

if __name__ == '__main__':
    main()
