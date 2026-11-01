import os
import glob
import re
import pandas as pd

epw_files = glob.glob("data/raw/India_Weather_Extracted/**/*.epw", recursive=True)
print(f"Total EPW files found: {len(epw_files)}")

def get_file_priority(filename):
    if "2011-2025" in filename:
        return 1
    elif "2009-2023" in filename:
        return 2
    elif "2007-2021" in filename:
        return 3
    elif "2004-2018" in filename:
        return 4
    elif "TMYx" in filename:
        return 5
    elif "ISHRAE" in filename:
        return 6
    return 7

records = []
for epw_path in epw_files:
    fname = os.path.basename(epw_path)
    # Read line 1 for header
    try:
        with open(epw_path, "r", encoding="latin-1") as f:
            header_line = f.readline().strip()
    except Exception as e:
        print(f"Error reading header for {epw_path}: {e}")
        continue
    
    parts = [p.strip() for p in header_line.split(",")]
    if len(parts) < 8 or parts[0].upper() != "LOCATION":
        print(f"Invalid LOCATION header in {epw_path}: {header_line}")
        continue
    
    city_name = parts[1]
    state_code = parts[2]
    wmo_id = parts[5]
    lat = float(parts[6])
    lon = float(parts[7])
    
    # Extract station identifier from filename as fallback if WMO is dummy
    m = re.match(r'IND_([A-Z]+)_(.*?)\.([0-9]{6})_', fname)
    if m:
        state_from_name = m.group(1)
        name_from_name = m.group(2)
        wmo_from_name = m.group(3)
    else:
        state_from_name = state_code
        name_from_name = city_name
        wmo_from_name = wmo_id
        
    records.append({
        "epw_path": epw_path,
        "fname": fname,
        "wmo_id": wmo_from_name if wmo_from_name != "999999" else wmo_id,
        "name": name_from_name,
        "state_code": state_from_name,
        "lat": lat,
        "lon": lon,
        "priority": get_file_priority(fname),
        "version_tag": fname.replace("IND_" + state_from_name + "_" + name_from_name + "." + wmo_from_name + "_", "").replace(".epw", "")
    })

df_all = pd.DataFrame(records)
print(f"Parsed {len(df_all)} valid EPW files.")

# Group by wmo_id
grouped_stations = []
for wmo, group in df_all.groupby("wmo_id"):
    # Sort by priority
    sorted_group = group.sort_values("priority")
    best_row = sorted_group.iloc[0]
    
    versions = sorted_group["fname"].tolist()
    
    grouped_stations.append({
        "wmo_id": wmo,
        "name": best_row["name"],
        "state_code": best_row["state_code"],
        "lat": best_row["lat"],
        "lon": best_row["lon"],
        "chosen_file": best_row["fname"],
        "chosen_path": best_row["epw_path"],
        "versions_available": "; ".join(versions)
    })

df_registry = pd.DataFrame(grouped_stations).sort_values(["state_code", "name"]).reset_index(drop=True)
df_registry.to_csv("reports/station_registry.csv", index=False)
print(f"Successfully generated reports/station_registry.csv with {len(df_registry)} unique stations.")
