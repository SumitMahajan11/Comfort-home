"""
tools/parse_5cities_ground_temps.py

Parses and prints the 12 monthly 0.5 m ground temperatures from each of the 5 EPW files:
- Jodhpur
- Mumbai
- New_Delhi
- Bengaluru
- Shimla

Flags any fallbacks.
"""

import os
import sys

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.render import (
    parse_epw_ground_temperatures,
    resolve_epw_path,
    get_ground_temperatures_from_epw,
    DEFAULT_GROUND_TEMP
)

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def main():
    print("=" * 110)
    print("12 MONTHLY 0.5 M GROUND TEMPERATURES PARSED FROM EPW WEATHER FILES")
    print("=" * 110)
    
    header = f"| {'City':<11} | {'Status':<10} | " + " | ".join([f"{m:<5}" for m in MONTHS]) + " |"
    print(header)
    print("|" + "-|"*14)
    
    for city in CITIES:
        epw_path = resolve_epw_path(city=city)
        if not epw_path or not os.path.exists(epw_path):
            status = "FALLBACK"
            temps = [DEFAULT_GROUND_TEMP] * 12
        else:
            depths = parse_epw_ground_temperatures(epw_path)
            if depths and 0.5 in depths:
                status = "EPW 0.5m"
                temps = depths[0.5]
            elif depths:
                shallowest = min(depths.keys())
                status = f"FALLBACK({shallowest}m)"
                temps = depths[shallowest]
            else:
                status = "FALLBACK(18C)"
                temps = [DEFAULT_GROUND_TEMP] * 12
                
        row_str = f"| {city:<11} | {status:<10} | " + " | ".join([f"{t:5.2f}" for t in temps]) + " |"
        print(row_str)
        
    print("=" * 110)

if __name__ == '__main__':
    main()
