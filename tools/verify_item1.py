import os
import sys
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import compute_valid_adaptive_hours_from_epw
from tools.run_city_pipeline import CITY_CLIMATE_ZONES, ZONE_TO_FLAGSHIP_R3

# Old values recorded from the original reports/batch_climate_table.csv prior to regeneration
OLD_VALID_HOURS = {
    "Srinagar": 4800,
    "Bhuntar": 4848,
    "Gangtok": 6384,
    "Jammu": 8544,
    "Dehradun": 8616,
    "Lucknow": 8280,
    "Varanasi": 8208,
    "Prayagraj": 7800,
    "Agra": 8040,
    "Gorakhpur": 8688,
    "Patna": 8760,
    "Nagpur": 7824,
    "Guwahati": 8760,
    "Dibrugarh": 8760,
    "Imphal": 8760,
    "Bhubaneswar": 8760,
    "Kolkata": 8760,
    "Visakhapatnam": 8760,
    "Chennai": 8760,
    "Surat": 8760,
    "Kochi": 8760,
    "Port Blair": 8760,
    "Bhuj": 8760,
    "Jaisalmer": 6984
}

manifest = pd.read_csv("reports/batch_epw_manifest.csv")
new_climate = pd.read_csv("reports/batch_climate_table.csv")

print("=" * 80)
print("1. VALID ADAPTIVE HOURS: FUNCTION vs OLD TABLE (ALL 24 CITIES)")
print("=" * 80)
rows = []
for _, r in manifest.iterrows():
    c = r['city']
    epw = r['path']
    val_func = compute_valid_adaptive_hours_from_epw(epw)
    val_old = OLD_VALID_HOURS.get(c, -1)
    val_new_csv = int(new_climate.loc[new_climate['city'] == c, 'valid_adaptive_hours'].values[0])
    rows.append({
        "City": c,
        "Function (Canonical)": val_func,
        "Old Table Value": val_old,
        "New Table Value": val_new_csv,
        "Diff (Func - Old)": val_func - val_old
    })

df_comp = pd.DataFrame(rows)
print(df_comp.to_string(index=False))

print("\n" + "=" * 80)
print("ZONE DICT IN run_city_pipeline.py (City, Zone, R3 Flagship)")
print("=" * 80)
zone_rows = []
for _, r in manifest.iterrows():
    c = r['city']
    z = CITY_CLIMATE_ZONES[c]
    r3 = ZONE_TO_FLAGSHIP_R3[z]
    zone_rows.append({
        "City": c,
        "Climate Zone": z,
        "R3 Flagship": r3
    })
df_zone = pd.DataFrame(zone_rows)
print(df_zone.to_string(index=False))

# Surat verification
surat_row = df_zone[df_zone['City'] == 'Surat'].iloc[0]
print("\nSurat Verification:")
print(f"  City: {surat_row['City']}, Zone: {surat_row['Climate Zone']}, R3 Flagship: {surat_row['R3 Flagship']}")
assert surat_row['Climate Zone'] == 'Hot-dry', f"Surat zone is {surat_row['Climate Zone']}, expected Hot-dry"
assert surat_row['R3 Flagship'] == 'Jodhpur', f"Surat R3 flagship is {surat_row['R3 Flagship']}, expected Jodhpur"
print("  Surat check PASSED: Surat is Hot-dry (Jodhpur R3).")

# Check if any city disagrees between regenerated table and CITY_CLIMATE_ZONES
for _, r in new_climate.iterrows():
    c = r['city']
    z_tab = r['climate_zone']
    z_dict = CITY_CLIMATE_ZONES[c]
    if z_tab != z_dict:
        print(f"DISAGREEMENT: City {c} has table zone '{z_tab}' != dict zone '{z_dict}'")
        sys.exit(1)
print("All 24 cities agree between regenerated reports/batch_climate_table.csv and CITY_CLIMATE_ZONES.")
