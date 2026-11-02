import os
import sys
import pandas as pd

# Load station registry
df_registry = pd.read_csv("reports/station_registry.csv")

# Load onebuilding file list
with open("reports/climate_onebuilding_india_file_list.txt", "r") as f:
    onebuilding_files = [line.strip() for line in f if line.strip()]

# 24 cities grouped by hazard / geographic category
cities_spec = [
    # Himalaya
    ("Srinagar", ["srinagar"]),
    ("Jammu", ["jammu"]),
    ("Bhuntar (Kullu-Manali)", ["bhuntar", "kullu", "manali"]),
    ("Dehradun", ["dehradun"]),
    ("Gangtok", ["gangtok"]),
    ("Bagdogra", ["bagdogra"]),
    # Gangetic plain
    ("Lucknow", ["lucknow"]),
    ("Varanasi", ["varanasi"]),
    ("Prayagraj", ["prayagraj"]),
    ("Agra", ["agra"]),
    ("Gorakhpur", ["gorakhpur"]),
    ("Patna", ["patna"]),
    # Northeast
    ("Guwahati", ["guwahati"]),
    ("Dibrugarh", ["dibrugarh"]),
    ("Imphal", ["imphal"]),
    # East coast
    ("Bhubaneswar", ["bhubaneswar", "bhubaneshwar"]),
    ("Kolkata", ["kolkata"]),
    ("Visakhapatnam", ["visakhapatnam", "vishakhapatnam"]),
    ("Chennai", ["chennai"]),
    # West
    ("Bhuj", ["bhuj"]),
    ("Surat", ["surat"]),
    # South/islands
    ("Kochi", ["kochi"]),
    ("Port Blair", ["port.blair", "port blair"]),
    ("Car Nicobar", ["car.nicobar", "car nicobar"]),
    # Heat
    ("Nagpur", ["nagpur"]),
    ("Jaisalmer", ["jaisalmer"]),
]

print("="*100)
print("STEP 1: REGISTRY MATCHES FOR EVERY CITY")
print("="*100)

table_rows = []

for city_name, patterns in cities_spec:
    print(f"\n--- City Query: {city_name} ---")
    
    matches = pd.DataFrame()
    for p in patterns:
        if p == "patna":
            m = df_registry[df_registry['name'].str.contains(r'(?:^|[\.\-_])Patna(?:[\.\-_]|$)', case=False, regex=True)]
        else:
            m = df_registry[df_registry['name'].str.lower().str.contains(p, na=False)]
        matches = pd.concat([matches, m]).drop_duplicates(subset=['wmo_id', 'name'])
    
    if len(matches) == 0:
        print(f"  NO MATCH found in reports/station_registry.csv for query '{city_name}'.")
        ob_m = [f for f in onebuilding_files if any(p in f.lower() for p in patterns)]
        print(f"  Available files in reports/climate_onebuilding_india_file_list.txt: {ob_m if ob_m else 'None'}")
        table_rows.append({
            "city": city_name,
            "station": "NONE_IN_REGISTRY",
            "wmo": "N/A",
            "state": "N/A",
            "epw_filename": "NONE",
            "status": "NEEDS_DECISION"
        })
        continue

    # Print every match
    candidates_2011 = []
    candidates_other = []
    for _, r in matches.iterrows():
        versions = [v.strip() for v in str(r['versions_available']).split(';') if v.strip()]
        has_2011 = any("2011-2025" in v for v in versions) or ("2011-2025" in str(r['chosen_file']))
        v_2011 = [v for v in versions if "2011-2025" in v]
        if not v_2011 and "2011-2025" in str(r['chosen_file']):
            v_2011 = [str(r['chosen_file'])]
            
        print(f"  Match: station='{r['name']}', WMO={r['wmo_id']}, state={r['state_code']}")
        print(f"         chosen_file: {r['chosen_file']}")
        print(f"         versions_available: {versions}")
        print(f"         has_2011_2025: {has_2011}")
        
        if v_2011:
            candidates_2011.append((r, v_2011[0]))
        else:
            candidates_other.append((r, r['chosen_file'], versions))

    if candidates_2011:
        # Pick best match (exact name match priority)
        selected_r, selected_epw = candidates_2011[0]
        for c_r, c_epw in candidates_2011:
            if c_r['name'].lower() == city_name.lower():
                selected_r, selected_epw = c_r, c_epw
                break
        table_rows.append({
            "city": city_name,
            "station": selected_r['name'],
            "wmo": selected_r['wmo_id'],
            "state": selected_r['state_code'],
            "epw_filename": selected_epw,
            "status": "MATCHED_2011_2025"
        })
    else:
        r0, epw0, vers0 = candidates_other[0]
        print(f"  NEEDS_DECISION: No 2011-2025 EPW for station '{r0['name']}'. Files available: {vers0}")
        table_rows.append({
            "city": city_name,
            "station": r0['name'],
            "wmo": r0['wmo_id'],
            "state": r0['state_code'],
            "epw_filename": epw0,
            "status": "NEEDS_DECISION"
        })

df_cities = pd.DataFrame(table_rows)

print("\n" + "="*100)
print("TABLE: CITY, STATION, WMO, STATE, EPW FILENAME, STATUS")
print("="*100)
print(df_cities.to_string(index=False))

print("\n" + "="*100)
print("FLAGSHIP EPW VERIFICATION")
print("="*100)
flagships = ['Jodhpur', 'Mumbai', 'New_Delhi', 'Bengaluru', 'Shimla']
flagship_rows = []
base_dir = "data/raw/India_Weather_Extracted"

for f in flagships:
    f_clean = f.replace('_', '.')
    extracted_dirs = [d for d in os.listdir(base_dir) if f_clean.lower() in d.lower() and os.path.isdir(os.path.join(base_dir, d))]
    
    folder_2011_exists = any("2011-2025" in d for d in extracted_dirs)
    epw_file_inside = False
    epw_filename = "NONE"
    
    for d in extracted_dirs:
        if "2011-2025" in d:
            epws = [x for x in os.listdir(os.path.join(base_dir, d)) if x.endswith(".epw")]
            if epws:
                epw_file_inside = True
                epw_filename = epws[0]

    flagship_rows.append({
        "city": f,
        "folder_2011_2025_exists": folder_2011_exists,
        "epw_file_inside": epw_file_inside,
        "epw_filename": epw_filename
    })

df_flagships = pd.DataFrame(flagship_rows)
print(df_flagships.to_string(index=False))
