import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import compute_valid_adaptive_hours_from_epw
from tools.run_city_pipeline import CITY_CLIMATE_ZONES

# Read manifest to ensure canonical 24 cities and EPW paths
manifest_path = "reports/batch_epw_manifest.csv"
if not os.path.exists(manifest_path):
    raise FileNotFoundError(f"{manifest_path} not found.")

df_manifest = pd.read_csv(manifest_path)

rows = []
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

for _, c in df_manifest.iterrows():
    city = c["city"]
    epw_path = c["path"]
    with open(epw_path, "r", encoding="latin-1") as f:
        content = f.read()
        
    lines = content.splitlines()
    header_line = lines[0].split(",")
    station_name = header_line[1] if len(header_line) > 1 else city
    wmo_code = header_line[5] if len(header_line) > 5 else ""

    ground_line = None
    for l in lines[:10]:
        if l.startswith("GROUND TEMPERATURES"):
            ground_line = l
            break
            
    p = ground_line.split(",")
    g_0p5 = [float(p[6 + m]) for m in range(12)]
            
    valid_hours = compute_valid_adaptive_hours_from_epw(epw_path)
    climate_zone = CITY_CLIMATE_ZONES[city]
    
    row = {
        "city": city,
        "station": station_name,
        "wmo": wmo_code,
        "climate_zone": climate_zone,
        "valid_adaptive_hours": valid_hours
    }
    for m_idx, m_name in enumerate(months):
        row[m_name] = round(g_0p5[m_idx], 2)
        
    rows.append(row)

df_climate = pd.DataFrame(rows)
cols_order = ["city", "climate_zone", "valid_adaptive_hours"] + months
df_display = df_climate[cols_order]

print("="*120)
print("STEP 3: CLIMATE TABLE - 12 MONTHLY 0.5M GROUND TEMPS & ADAPTIVE HOURS (24 CITIES)")
print("="*120)
print(df_display.to_string(index=False))

# Save to reports/batch_climate_table.csv
os.makedirs("reports", exist_ok=True)
df_climate.to_csv("reports/batch_climate_table.csv", index=False)
print(f"\nSaved climate table to reports/batch_climate_table.csv ({len(df_climate)} rows)")
