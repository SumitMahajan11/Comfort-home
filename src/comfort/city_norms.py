"""
src/comfort/city_norms.py

Computes empirical City Comfort Norms from real data only:
1. EPW outdoor climate summary (monthly mean/min/max dry-bulb, RH, Adaptive 90% outcomes).
2. Typical reference building indoor comfort (monthly O1_adapt, O1_ml, warm%, cool%).
3. Occupant comfort preferences from DB II India records in matching Koppen groups.
   (With strict null-handling and flagging when votes are missing, e.g. Shimla D-011).
4. Applicability flags and confidence tier.

Output exported to: data/export/city_comfort_norms.json
"""

import os
import sys
import json
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import (
    calculate_daily_mean_series,
    compute_running_mean_outdoor_temperature_db2,
    evaluate_adaptive_90_comfort,
    evaluate_ml_champion_comfort,
    compute_clo_schedule_a004,
    load_champion_model
)

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
HOURS_PER_MONTH = [d * 24 for d in DAYS_PER_MONTH]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Real empirical DB II India statistics by Koppen group & city
# Compiled directly from DB II India records audit (reports/evidence/phase1_eda_calc_output.txt)
DB2_INDIA_NORMS = {
    "Jodhpur": {
        "koppen_group": "B",
        "climate_description": "Hot semi-arid / desert (Rajasthan)",
        "sample_scope": "DB II India records in Koppen Group B (Ahmedabad & Jaipur)",
        "has_labelled_votes": True,
        "n_rows": 4498,
        "n_buildings": 88,
        "flag_small_sample": False,
        "flag_missing_votes": False,
        "tsv_distribution_pct": {
            "cool": 30.3,
            "neutral": 38.0,
            "warm": 31.7
        },
        "median_neutral_temp_c": 27.0,
        "notes": "Matches Koppen Group B arid thermal regime; high summer neutral temperature tolerance."
    },
    "Mumbai": {
        "koppen_group": "A",
        "climate_description": "Tropical wet savanna / warm-humid coastal (Maharashtra)",
        "sample_scope": "DB II India Mumbai city records (15 buildings)",
        "has_labelled_votes": True,
        "n_rows": 2246,
        "n_buildings": 15,
        "flag_small_sample": False,
        "flag_missing_votes": False,
        "tsv_distribution_pct": {
            "cool": 28.5,
            "neutral": 45.2,
            "warm": 26.3
        },
        "median_neutral_temp_c": 26.5,
        "notes": "High humidity year-round; fans heavily utilized."
    },
    "New_Delhi": {
        "koppen_group": "C",
        "climate_description": "Monsoon-influenced humid subtropical / composite (Delhi NCR)",
        "sample_scope": "DB II India Delhi NCR records (31 buildings)",
        "has_labelled_votes": True,
        "n_rows": 3115,
        "n_buildings": 31,
        "flag_small_sample": False,
        "flag_missing_votes": False,
        "tsv_distribution_pct": {
            "cool": 27.2,
            "neutral": 46.1,
            "warm": 26.7
        },
        "median_neutral_temp_c": 26.0,
        "notes": "Strong seasonal dichotomy; cool winters and scorching summers."
    },
    "Bengaluru": {
        "koppen_group": "A",
        "climate_description": "Tropical wet savanna / temperate plateau (Karnataka)",
        "sample_scope": "DB II India Bengaluru records (36 buildings)",
        "has_labelled_votes": True,
        "n_rows": 4028,
        "n_buildings": 36,
        "flag_small_sample": False,
        "flag_missing_votes": False,
        "tsv_distribution_pct": {
            "cool": 31.8,
            "neutral": 51.4,
            "warm": 16.8
        },
        "median_neutral_temp_c": 24.8,
        "notes": "Highest neutral satisfaction rate (51.4%) across Indian DB II cohorts."
    },
    "Shimla": {
        "koppen_group": "C",
        "climate_description": "Subtropical highland / temperate montane (Himachal Pradesh)",
        "sample_scope": "DB II India Shimla records (64 buildings)",
        "has_labelled_votes": False,
        "n_rows": 460,
        "n_buildings": 64,
        "flag_small_sample": False,
        "flag_missing_votes": True,
        "tsv_distribution_pct": None,
        "median_neutral_temp_c": None,
        "notes": "Decision D-011: Shimla contains 64 buildings in DB II, but 0 labelled thermal sensation votes (all 460 rows NaN). Occupant preference statistics are reported as unavailable; NEVER fabricated."
    }
}

CITY_APPLICABILITY_TIERS = {
    "Jodhpur": {
        "confidence_tier": "Low",
        "ml_confidence": "Low",
        "adaptive_confidence": "Standard",
        "notes": "Dry desert summer heat exceeds DB II training bounds."
    },
    "Mumbai": {
        "confidence_tier": "Low",
        "ml_confidence": "Low",
        "adaptive_confidence": "Standard",
        "notes": "Monsoon relative humidity exceeds 82.6% upper training bound."
    },
    "New_Delhi": {
        "confidence_tier": "Low",
        "ml_confidence": "Low",
        "adaptive_confidence": "Standard",
        "notes": "Extreme summer heat and monsoon humidity violate DB II envelope."
    },
    "Bengaluru": {
        "confidence_tier": "Medium",
        "ml_confidence": "Standard",
        "adaptive_confidence": "Standard",
        "notes": "High validity share and strong dual-judge rank correlation (r_s = 0.942)."
    },
    "Shimla": {
        "confidence_tier": "Low",
        "ml_confidence": "Low",
        "adaptive_confidence": "Flagged",
        "notes": "Winter T_rm < 10 C violates Adaptive-90 validity bound; zero DB II votes."
    }
}

def parse_epw_hourly(epw_path: str):
    """Parses dry-bulb temperature and relative humidity from EPW file."""
    dry_bulbs = []
    rhs = []
    with open(epw_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 35:
                try:
                    year = int(parts[0])
                    # EPW data lines start with year (4 digits)
                    if 1900 <= year <= 2100:
                        db = float(parts[6]) # dry bulb temperature (deg C)
                        rh = float(parts[8]) # relative humidity (%)
                        dry_bulbs.append(db)
                        rhs.append(rh)
                except ValueError:
                    continue
    return np.array(dry_bulbs[:8760], dtype=np.float32), np.array(rhs[:8760], dtype=np.float32)

def compute_city_norms():
    """Computes comprehensive empirical city comfort norms and exports to JSON."""
    champ_model = load_champion_model()
    results = {}

    for city, epw_path in CITIES_EPW.items():
        if not os.path.exists(epw_path):
            raise FileNotFoundError(f"EPW file not found: {epw_path}")

        dry_bulbs, rhs = parse_epw_hourly(epw_path)
        daily_tout = calculate_daily_mean_series(dry_bulbs)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)

        # Monthly Outdoor Summaries
        monthly_outdoor = []
        start_h = 0
        for m_idx, n_h in enumerate(HOURS_PER_MONTH):
            end_h = start_h + n_h
            m_db = dry_bulbs[start_h:end_h]
            m_rh = rhs[start_h:end_h]
            m_trm = t_rm_hourly[start_h:end_h]

            # Adaptive 90% benchmark for outdoor conditions
            t_cmf = 17.8 + 0.31 * m_trm
            valid_mask = (m_trm >= 10.0) & (m_trm <= 33.5)
            
            # Using outdoor dry-bulb as operative proxy to characterize climate severity
            comfort_mask = valid_mask & (np.abs(m_db - t_cmf) <= 2.5)
            warm_mask = valid_mask & (m_db > (t_cmf + 2.5))
            cool_mask = valid_mask & (m_db < (t_cmf - 2.5))

            n_v = float(np.sum(valid_mask)) or 1.0
            monthly_outdoor.append({
                "month_index": m_idx + 1,
                "month_name": MONTH_NAMES[m_idx],
                "hours_in_month": n_h,
                "dry_bulb_mean": round(float(np.mean(m_db)), 1),
                "dry_bulb_min": round(float(np.min(m_db)), 1),
                "dry_bulb_max": round(float(np.max(m_db)), 1),
                "relative_humidity_mean": round(float(np.mean(m_rh)), 1),
                "relative_humidity_min": round(float(np.min(m_rh)), 1),
                "relative_humidity_max": round(float(np.max(m_rh)), 1),
                "adaptive_90_valid_pct": round(float(np.mean(valid_mask) * 100.0), 1),
                "outdoor_comfortable_pct": round(float(np.sum(comfort_mask) / n_v * 100.0), 1),
                "outdoor_too_warm_pct": round(float(np.sum(warm_mask) / n_v * 100.0), 1),
                "outdoor_too_cool_pct": round(float(np.sum(cool_mask) / n_v * 100.0), 1)
            })
            start_h = end_h

        # Reference building conventional baseline (R2) monthly performance
        ref_file = f"data/export/reference_{city}_shelter_v1.json"
        ref_data = {}
        if os.path.exists(ref_file):
            with open(ref_file, "r", encoding="utf-8") as f:
                ref_data = json.load(f).get("R2", {})

        # Monthly indoor reference profile
        monthly_indoor_file = f"data/export/monthly_indoor_{city}_shelter_v1_R2_{city}_shelter_v1_free_running_curr.json"
        indoor_profiles = []
        if os.path.exists(monthly_indoor_file):
            with open(monthly_indoor_file, "r", encoding="utf-8") as f:
                prof_data = json.load(f)
                indoor_profiles = prof_data.get("current", [])

        # Annual reference comfort metrics
        ref_annual = {
            "reference_name": "R2_Conventional",
            "annual_O1_adapt_pct": round(float(ref_data.get("O1_adapt", 0.0)), 1),
            "annual_O1_ml_pct": round(float(ref_data.get("O1_ml", 0.0)), 1),
            "annual_warm_ml_pct": round(float(ref_data.get("warm_ml", 0.0)), 1),
            "annual_cool_ml_pct": round(float(ref_data.get("cool_ml", 0.0)), 1),
            "annual_O2_kwh_per_m2": round(float(ref_data.get("O2", 0.0)), 1),
            "monthly_indoor_profiles": indoor_profiles
        }

        # Combine into complete city norms structure
        results[city] = {
            "city": city,
            "applicability": CITY_APPLICABILITY_TIERS[city],
            "monthly_climate_summary": monthly_outdoor,
            "reference_building_performance": ref_annual,
            "occupant_preferences_db2": DB2_INDIA_NORMS[city]
        }

    # Save to data/export/city_comfort_norms.json
    export_path = "data/export/city_comfort_norms.json"
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Successfully exported city comfort norms for 5 cities to {export_path}")
    return results

if __name__ == "__main__":
    compute_city_norms()
