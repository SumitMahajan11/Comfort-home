import os
import sys
import urllib.request
import zipfile
import io
import pypdf
import pandas as pd
import numpy as np

# Load station registry
df_registry = pd.read_csv("reports/station_registry.csv")

# Map of relative paths from content.md
content_path = r"C:\Users\SUMIT\.gemini\antigravity-ide\brain\b09c13ca-8bc8-4b7a-9872-b61c6c7989f9\.system_generated\steps\1094\content.md"
with open(content_path, "r", encoding="utf-8") as f:
    import re
    matches = re.findall(r'href="([^"]*?IND_[^"]*?\.zip)"', f.read())
zip_relpaths = {os.path.basename(m): m for m in matches}

BASE_URL = "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/"

print("="*100)
print("DECISION 2: PRAYAGRAJ (Allahabad-Bamrauli.AP - WMO 424750)")
print("="*100)
allah_rows = df_registry[df_registry['wmo_id'] == 424750]
if len(allah_rows) == 0:
    allah_rows = df_registry[df_registry['name'].str.contains("Allahabad", case=False)]
print("Raw registry row:")
print(allah_rows.to_string(index=False))

allah_file = "IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025.zip"
allah_rel = zip_relpaths.get(allah_file)
allah_url = BASE_URL + allah_rel if allah_rel else None
print(f"\nDownload URL: {allah_url}")

# HEAD check
req = urllib.request.Request(allah_url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"HEAD check status: {resp.status} {resp.reason}")
        print(f"Content-Length: {resp.headers.get('Content-Length')} bytes")
        head_ok = (resp.status == 200)
except Exception as e:
    print(f"HEAD check failed: {e}")
    head_ok = False

if not head_ok:
    print("STOP: HEAD check failed for Allahabad-Bamrauli.AP!")
    sys.exit(1)

print("\n" + "="*100)
print("DECISION 3: KULLU-MANALI STATIONS (Bhuntar, Kullu.Manali, Manali)")
print("="*100)
kullu_stations = [420810, 427051, 420650]
kullu_df = df_registry[df_registry['wmo_id'].isin(kullu_stations)]

# We also want elevation for these stations from EPW headers
stations_info = []
for _, r in kullu_df.iterrows():
    wmo = r['wmo_id']
    name = r['name']
    lat = r['lat']
    lon = r['lon']
    
    # Download zip in memory to inspect EPW header
    zip_name = r['chosen_file'].replace(".epw", ".zip")
    rel_p = zip_relpaths.get(zip_name)
    url = BASE_URL + rel_p
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        zdata = resp.read()
    with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
        epw_content = zf.read(r['chosen_file']).decode('latin-1')
        
    lines = epw_content.splitlines()
    loc_parts = lines[0].split(',')
    elevation = float(loc_parts[-1]) if len(loc_parts) >= 9 else None
    
    # Ground temperatures on line 4: GROUND TEMPERATURES,<n_depths>,...
    ground_line = None
    for l in lines[:10]:
        if l.startswith("GROUND TEMPERATURES"):
            ground_line = l
            break
            
    # Check hourly data for missing dry-bulb (col 6) or relative humidity (col 8)
    # EPW format: Year, Month, Day, Hour, Minute, Data Source and Uncertainty Flags, Dry Bulb {C}, Dew Point {C}, Rel Hum {%}, ...
    missing_count = 0
    t_db = []
    rh_vals = []
    for l in lines[8:]:
        if not l.strip():
            continue
        p = l.split(',')
        if len(p) > 8:
            try:
                tdb = float(p[6])
                rh = float(p[8])
                if tdb >= 99.0 or rh >= 999.0:
                    missing_count += 1
                t_db.append(tdb)
                rh_vals.append(rh)
            except Exception:
                missing_count += 1
                
    stations_info.append({
        "station": name,
        "wmo": wmo,
        "lat": lat,
        "lon": lon,
        "elevation_m": elevation,
        "ground_line": ground_line,
        "hourly_rows": len(t_db),
        "missing_count": missing_count,
        "mean_tdb": np.mean(t_db),
        "mean_rh": np.mean(rh_vals)
    })

df_kullu_info = pd.DataFrame(stations_info)
print(df_kullu_info[["station", "wmo", "lat", "lon", "elevation_m", "hourly_rows", "missing_count", "mean_tdb", "mean_rh"]].to_string(index=False))
for s in stations_info:
    print(f"\nStation: {s['station']} (WMO {s['wmo']})")
    print(f"  Ground line: {s['ground_line']}")

print("\n" + "="*100)
print("DECISION 4: MULTI-STATION CITIES (Varanasi, Visakhapatnam, Lucknow, Agra)")
print("="*100)
multi_cities = [
    ("Varanasi", ["Varanasi", "Varanasi-Shastri.Intl.AP"]),
    ("Visakhapatnam", ["Vishakhapatnam", "Vishakhapatnam.Intl.AP"]),
    ("Lucknow", ["Lucknow", "Lucknow-Amausi-Singh.Intl.AP"]),
    ("Agra", ["Agra", "Agra.AP"])
]

multi_records = []
for cname, st_names in multi_cities:
    sub = df_registry[df_registry['name'].isin(st_names)]
    for _, r in sub.iterrows():
        # Check versions
        vers = [v.strip() for v in str(r['versions_available']).split(';') if v.strip()]
        has_2011 = any("2011-2025" in v for v in vers) or ("2011-2025" in str(r['chosen_file']))
        multi_records.append({
            "city": cname,
            "station": r['name'],
            "wmo": r['wmo_id'],
            "state": r['state_code'],
            "lat": r['lat'],
            "lon": r['lon'],
            "chosen_file": r['chosen_file'],
            "has_2011_2025": has_2011
        })

df_multi = pd.DataFrame(multi_records)
print(df_multi.to_string(index=False))

print("\nPick reasons:")
print("1. Lucknow: Picked 'Lucknow-Amausi-Singh.Intl.AP' (WMO 423690, 26.761 N, 80.883 E). Reason: Station 'Lucknow' (WMO 423680) only has legacy unsuffixed TMYx.epw; only Amausi Airport has the mandatory TMYx.2011-2025.epw file.")
print("2. Agra: Picked 'Agra.AP' (WMO 422600, 27.157 N, 77.961 E). Reason: Station 'Agra' (WMO 422610) only has legacy unsuffixed TMYx.epw; only Agra Airport has the mandatory TMYx.2011-2025.epw file.")
print("3. Varanasi: Picked 'Varanasi' (WMO 424830, 25.317 N, 83.033 E). Reason: Both stations have 2011-2025 EPWs; 'Varanasi' represents the primary city meteorological observatory directly inside Varanasi urban area (25.317 N, 83.033 E), whereas 'Varanasi-Shastri.Intl.AP' (Babatpur, 25.45 N, 82.859 E) is located ~20 km outside the city.")
print("4. Visakhapatnam: Picked 'Vishakhapatnam' (WMO 431500, 17.700 N, 83.300 E). Reason: Both stations have 2011-2025 EPWs; 'Vishakhapatnam' (WMO 431500) represents the primary IMD city coastal station, exactly matching the city coordinates.")

print("\n" + "="*100)
print("DECISION 1: CLIMATE ZONE CROSS-CHECK AGAINST ECBC 2017 & ENS 2024")
print("="*100)
# Final 24 cities list
final_24_cities = [
    # Cold
    ("Srinagar", "Srinagar", 420270, "Cold", "Leh"),
    ("Manali", "Manali", 420650, "Cold", "Leh"),
    ("Gangtok", "Gangtok", 422990, "Cold", "Leh"),
    # Composite
    ("Jammu", "Jammu", 420560, "Composite", "New_Delhi"),
    ("Dehradun", "Dehradun", 421110, "Composite", "New_Delhi"),
    ("Lucknow", "Lucknow-Amausi-Singh.Intl.AP", 423690, "Composite", "New_Delhi"),
    ("Varanasi", "Varanasi", 424830, "Composite", "New_Delhi"),
    ("Prayagraj", "Allahabad-Bamrauli.AP", 424750, "Composite", "New_Delhi"),
    ("Agra", "Agra.AP", 422600, "Composite", "New_Delhi"),
    ("Gorakhpur", "Gorakhpur", 423790, "Composite", "New_Delhi"),
    ("Patna", "Patna-Jayaprakash.AP", 424920, "Composite", "New_Delhi"),
    ("Nagpur", "Nagpur-Ambedkar.Intl.AP", 428670, "Composite", "New_Delhi"),
    # Warm-humid
    ("Guwahati", "Guwahati-Bordoloi.Intl.AP", 424100, "Warm-humid", "Mumbai"),
    ("Dibrugarh", "Dibrugarh.AP", 423140, "Warm-humid", "Mumbai"),
    ("Imphal", "Imphal", 426230, "Warm-humid", "Mumbai"),
    ("Bhubaneswar", "Bhubaneshwar-Patnaik.Intl.AP", 429710, "Warm-humid", "Mumbai"),
    ("Kolkata", "Kolkata-Bose.Intl.AP", 428090, "Warm-humid", "Mumbai"),
    ("Visakhapatnam", "Vishakhapatnam", 431500, "Warm-humid", "Mumbai"),
    ("Chennai", "Chennai.Intl.AP", 432790, "Warm-humid", "Mumbai"),
    ("Surat", "Surat", 428400, "Warm-humid", "Mumbai"),
    ("Kochi", "Kochi.NAS", 433530, "Warm-humid", "Mumbai"),
    ("Port Blair", "Port.Blair", 433330, "Warm-humid", "Mumbai"),
    # Hot-dry
    ("Bhuj", "Bhuj", 426340, "Hot-dry", "Jodhpur"),
    ("Jaisalmer", "Jaisalmer", 423280, "Hot-dry", "Jodhpur"),
]

# Read ECBC 2017 Table 11-1
reader_ecbc = pypdf.PdfReader('data/docs/ECBC_2017.pdf')
# ECBC 2017 Table 11-1 is on page 201
ecbc_text = reader_ecbc.pages[200].extract_text()

# Read ENS 2024 Table 62 (page 131)
reader_ens = pypdf.PdfReader('data/docs/ENS_2024.pdf')
ens_text = reader_ens.pages[130].extract_text()

print(f"Citing standard documents in data/docs:")
print(f"1. ECBC 2017 (Commercial): Appendix B, Table 11-1 'Climate Zone for Major Indian Cities' (PDF Page 201, internal page 168)")
print(f"2. ENS 2024 (Residential): Table 62 'Climate Zone for major Indian Cities' (PDF Page 131, internal page 129)")
print(f"3. ECSBC 2024: Appendix 2, Table A2.1 'Climate Zone for Major Indian Cities' (PDF Page 177, internal page 163)")

# Check each city
crosscheck_rows = []
for city, st_name, wmo, unverified_zone, r3_ref in final_24_cities:
    # search name in table
    # Alias mapping for table search:
    search_names = [city]
    if city == "Prayagraj":
        search_names = ["Allahabad", "Prayagraj"]
    elif city == "Bhubaneswar":
        search_names = ["Bhubaneshwar", "Bhubaneswar"]
    elif city == "Visakhapatnam":
        search_names = ["Vishakhapatnam", "Visakhapatnam"]
        
    ecbc_zone = "NOT_IN_TABLE (Map lookup)"
    # parse from ecbc text
    for sn in search_names:
        m = re.search(r'\b' + re.escape(sn) + r'\b\s+([A-Za-z\s\&]+?)(?=\s+[A-Z][a-z]|\n|$)', ecbc_text)
        if m:
            raw_z = m.group(1).strip()
            # Clean up
            if "Composite" in raw_z:
                ecbc_zone = "Composite"
            elif "Warm" in raw_z and "Humid" in raw_z:
                ecbc_zone = "Warm-humid"
            elif "Hot" in raw_z and "Dry" in raw_z:
                ecbc_zone = "Hot-dry"
            elif "Cold" in raw_z:
                ecbc_zone = "Cold"
            elif "Temperate" in raw_z:
                ecbc_zone = "Temperate"
            break
            
    # Also check ENS text
    if ecbc_zone.startswith("NOT_IN_TABLE"):
        for sn in search_names:
            m = re.search(r'\b' + re.escape(sn) + r'\b\s+([A-Za-z\s\-\&]+?)(?=\s+[A-Z][a-z]|\n|$)', ens_text)
            if m:
                raw_z = m.group(1).strip()
                if "Composite" in raw_z:
                    ecbc_zone = "Composite"
                elif "Warm" in raw_z and "Humid" in raw_z:
                    ecbc_zone = "Warm-humid"
                elif "Hot" in raw_z and "Dry" in raw_z:
                    ecbc_zone = "Hot-dry"
                elif "Cold" in raw_z:
                    ecbc_zone = "Cold"
                elif "Temperate" in raw_z:
                    ecbc_zone = "Temperate"
                break
                
    disagrees = (ecbc_zone != unverified_zone and not ecbc_zone.startswith("NOT_IN_TABLE"))
    crosscheck_rows.append({
        "city": city,
        "station": st_name,
        "unverified_zone": unverified_zone,
        "ecbc_table_zone": ecbc_zone,
        "disagrees": disagrees,
        "pdf_source": "ECBC 2017 Table 11-1 (p. 201) / ENS 2024 Table 62 (p. 131)"
    })

df_crosscheck = pd.DataFrame(crosscheck_rows)
print("\n" + "="*100)
print("CLIMATE ZONE CROSS-CHECK TABLE")
print("="*100)
print(df_crosscheck.to_string(index=False))
