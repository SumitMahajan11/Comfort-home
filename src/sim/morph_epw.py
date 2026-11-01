"""
src/sim/morph_epw.py

Constructs morphed EPW weather files for future-climate warming scenarios
(+1.5°C and +3.0°C) across the 5 reference Indian climate stations:
- Jodhpur (Hot-Dry)
- Mumbai (Warm-Humid)
- New Delhi (Composite)
- Bengaluru (Temperate)
- Shimla (Cold)

METHODOLOGY:
- Monthly/hourly mean dry-bulb temperature shift: T_db_new = T_db + delta_T
- Proportional psychrometric humidity handling: maintains relative humidity (RH_new = RH)
  and calculates the thermodynamically consistent new dew point (T_dp_new) using the
  Magnus-Tetens relation.
- Strictly documents: This is a synthetic uniform thermal shift method (Belcher et al., 2005),
  NOT a dynamically downscaled regional climate model (RCM) projection.
"""

import os
import math
from typing import Dict, List, Tuple

BASE_RAW_DIR = os.path.abspath("data/raw/India_Weather_Extracted")
PROCESSED_WEATHER_DIR = os.path.abspath("data/processed/weather_morphed")

CITIES_EPW_MAP = {
    "Jodhpur": os.path.join(BASE_RAW_DIR, "IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"),
    "Mumbai": os.path.join(BASE_RAW_DIR, "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw"),
    "New_Delhi": os.path.join(BASE_RAW_DIR, "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw"),
    "Bengaluru": os.path.join(BASE_RAW_DIR, "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw"),
    "Shimla": os.path.join(BASE_RAW_DIR, "IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw")
}

def magnus_dew_point(t_db: float, rh_pct: float) -> float:
    """
    Computes dew point temperature from dry-bulb (C) and RH (%) using Magnus formula.
    """
    rh_frac = max(0.01, min(1.0, rh_pct / 100.0))
    a = 17.67
    b = 243.5
    alpha = ((a * t_db) / (b + t_db)) + math.log(rh_frac)
    t_dp = (b * alpha) / (a - alpha)
    return min(t_db, t_dp)

def morph_single_epw(src_path: str, dst_path: str, delta_t: float) -> Dict[str, float]:
    """
    Applies +delta_t warming shift to dry-bulb and psychrometrically updates dew point.
    Returns summary statistics of the shift.
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source EPW not found: {src_path}")
        
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    
    with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    morphed_lines = []
    # Lines 0 to 7 are header lines
    for idx, line in enumerate(lines):
        if idx < 8:
            morphed_lines.append(line)
            continue
            
        parts = line.strip().split(",")
        if len(parts) < 10:
            morphed_lines.append(line)
            continue
            
        try:
            t_db = float(parts[6])
            rh = float(parts[8])
            
            # Apply temperature offset
            t_db_new = t_db + delta_t
            t_dp_new = magnus_dew_point(t_db_new, rh)
            
            parts[6] = f"{t_db_new:.2f}"
            parts[7] = f"{t_dp_new:.2f}"
            # parts[8] is RH, maintained proportionally
            
            morphed_lines.append(",".join(parts) + "\n")
        except ValueError:
            morphed_lines.append(line)
            
    with open(dst_path, "w", encoding="utf-8") as f:
        f.writelines(morphed_lines)
        
    return {
        "src": src_path,
        "dst": dst_path,
        "delta_t": delta_t,
        "total_hours": len(lines) - 8
    }

def generate_all_morphed_epws() -> List[Dict[str, any]]:
    """
    Generates +1.5C and +3.0C morphed EPWs for all 5 stations.
    """
    results = []
    for city, src_path in CITIES_EPW_MAP.items():
        if not os.path.exists(src_path):
            print(f"Warning: {src_path} not found. Skipping {city}.")
            continue
            
        for delta, tag in [(1.5, "plus1p5"), (3.0, "plus3p0")]:
            dst_filename = f"{city}_{tag}.epw"
            dst_path = os.path.join(PROCESSED_WEATHER_DIR, dst_filename)
            res = morph_single_epw(src_path, dst_path, delta)
            print(f"[{city}] Created {tag}: {dst_path}")
            results.append(res)
            
    return results

if __name__ == "__main__":
    generate_all_morphed_epws()
