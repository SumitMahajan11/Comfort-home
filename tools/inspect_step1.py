import os
import sys
import pandas as pd

df = pd.read_csv("reports/station_registry.csv")

with open("reports/climate_onebuilding_india_file_list.txt") as f:
    onebuilding_files = [line.strip() for line in f if line.strip()]

cities = [
    # Himalaya
    ("Srinagar", ["srinagar"]),
    ("Jammu", ["jammu"]),
    ("Bhuntar (Kullu-Manali)", ["bhuntar", "kullu", "manali"]),
    ("Dehradun", ["dehradun"]),
    ("Gangtok (if none: Bagdogra; print both)", ["gangtok", "bagdogra"]),
    # Gangetic plain
    ("Lucknow", ["lucknow"]),
    ("Varanasi", ["varanasi"]),
    ("Prayagraj", ["prayag", "allahabad"]),
    ("Agra", ["agra"]),
    ("Gorakhpur", ["gorakhpur"]),
    ("Patna", ["patna"]),
    # Northeast
    ("Guwahati", ["guwahati"]),
    ("Dibrugarh", ["dibrugarh"]),
    ("Imphal", ["imphal"]),
    # East coast
    ("Bhubaneswar", ["bhuban"]),
    ("Kolkata", ["kolkata"]),
    ("Visakhapatnam", ["visak", "vishak"]),
    ("Chennai", ["chennai"]),
    # West
    ("Bhuj", ["bhuj"]),
    ("Surat", ["surat"]),
    # South/islands
    ("Kochi", ["kochi"]),
    ("Port Blair (if none: Car Nicobar; print both)", ["port.blair", "port blair", "car.nicobar", "car nicobar"]),
    # Heat
    ("Nagpur", ["nagpur"]),
    ("Jaisalmer", ["jaisalmer"]),
]

print("="*80)
print("REGISTRY SEARCH FOR 24 CITIES")
print("="*80)

for city_label, patterns in cities:
    print(f"\nTarget City: {city_label}")
    # find matches in df
    matches = pd.DataFrame()
    for p in patterns:
        sub = df[df['name'].str.lower().str.contains(p)]
        matches = pd.concat([matches, sub]).drop_duplicates(subset=['wmo_id', 'name'])
    
    if len(matches) == 0:
        print("  NO MATCHES IN REGISTRY!")
        # check onebuilding file list directly
        ob_matches = []
        for p in patterns:
            ob_matches.extend([f for f in onebuilding_files if p in f.lower()])
        print(f"  Onebuilding file list matches: {ob_matches}")
    else:
        for _, row in matches.iterrows():
            versions = str(row['versions_available']).split('; ')
            has_2011 = any("2011-2025" in v for v in versions) or ("2011-2025" in str(row['chosen_file']))
            chosen_2011 = [v for v in versions if "2011-2025" in v]
            print(f"  Registry Match: name='{row['name']}', wmo={row['wmo_id']}, state={row['state_code']}")
            print(f"    chosen_file: {row['chosen_file']}")
            print(f"    2011-2025 available: {has_2011} -> {chosen_2011 if has_2011 else versions}")

print("\n" + "="*80)
print("FLAGSHIPS CHECK")
print("="*80)
flagships = ['Jodhpur', 'Mumbai', 'New_Delhi', 'Bengaluru', 'Shimla']
for f in flagships:
    f_clean = f.replace('_', '.')
    sub = df[df['name'].str.lower().str.contains(f_clean.lower())]
    print(f"\nFlagship: {f}")
    for _, row in sub.iterrows():
        print(f"  Registry Match: name='{row['name']}', wmo={row['wmo_id']}, state={row['state_code']}, chosen={row['chosen_file']}")
    # check disk
    extracted_dirs = [d for d in os.listdir("data/raw/India_Weather_Extracted") if f_clean.lower() in d.lower()]
    for ed in extracted_dirs:
        full_ed = os.path.join("data/raw/India_Weather_Extracted", ed)
        if os.path.isdir(full_ed):
            epws = [x for x in os.listdir(full_ed) if x.endswith(".epw")]
            has_2011_dir = "2011-2025" in ed
            print(f"  Disk folder: {ed} (is 2011-2025: {has_2011_dir}) -> EPWs: {epws}")
