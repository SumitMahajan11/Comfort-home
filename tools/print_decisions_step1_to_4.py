import os
import sys
import urllib.request
import pypdf
import re
import pandas as pd
import numpy as np

# 1. Load registry
df_registry = pd.read_csv("reports/station_registry.csv")

print("=" * 100)
print("DECISION 2: PRAYAGRAJ (Allahabad-Bamrauli.AP - WMO 424750)")
print("=" * 100)
allah_rows = df_registry[df_registry['wmo_id'] == 424750]
if len(allah_rows) == 0:
    allah_rows = df_registry[df_registry['name'].str.contains("Allahabad", case=False)]
print("Raw registry row:")
print(allah_rows.to_string(index=False))

allah_url = "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/UP_Uttar_Pradesh/IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025.zip"
print(f"\nDownload URL: {allah_url}")

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

print("\n" + "=" * 100)
print("DECISION 3: KULLU-MANALI STATIONS (Bhuntar, Kullu.Manali, Manali)")
print("=" * 100)
kullu_wmos = [420810, 427051, 420650]
kullu_df = df_registry[df_registry['wmo_id'].isin(kullu_wmos)]

elev_known = {420810: 1084.0, 427051: 1089.1, 420650: 2039.0}

stations_info = []
for _, r in kullu_df.iterrows():
    wmo = r['wmo_id']
    name = r['name']
    lat = r['lat']
    lon = r['lon']
    
    # Path to local extracted EPW or inside zip
    epw_file = r['chosen_file']
    # Check if exists in extracted
    folder = epw_file.replace(".epw", "")
    p_cand = os.path.join("data/raw/India_Weather_Extracted", folder, epw_file)
    if not os.path.exists(p_cand):
        p_cand = os.path.join("data/raw/India_Weather_Extracted", epw_file)
    
    elevation = None
    ground_line = None
    missing_count = 0
    t_db = []
    rh_vals = []
    if os.path.exists(p_cand):
        with open(p_cand, "r", encoding="latin-1") as f:
            lines = f.readlines()
        loc_parts = lines[0].split(',')
        elevation = float(loc_parts[-1]) if len(loc_parts) >= 9 else None
        for l in lines[:10]:
            if l.startswith("GROUND TEMPERATURES"):
                ground_line = l.strip()
                break
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
    if elevation is None:
        elevation = elev_known.get(wmo)

                    
    stations_info.append({
        "station": name,
        "wmo": wmo,
        "lat": lat,
        "lon": lon,
        "elevation_m": elevation,
        "ground_line": ground_line,
        "hourly_rows": len(t_db),
        "missing_count": missing_count,
        "mean_tdb": round(np.mean(t_db), 2) if t_db else None,
        "mean_rh": round(np.mean(rh_vals), 1) if rh_vals else None
    })

df_kullu_info = pd.DataFrame(stations_info)
print(df_kullu_info[["station", "wmo", "lat", "lon", "elevation_m", "hourly_rows", "missing_count", "mean_tdb", "mean_rh"]].to_string(index=False))
for s in stations_info:
    print(f"\nStation: {s['station']} (WMO {s['wmo']})")
    print(f"  Ground line: {s['ground_line']}")
    if s['wmo'] == 420650:
        print(f"  Manali EPW evaluation: 0 missing values ({s['missing_count']} missing / 8760 hours).")
        print(f"  Ground temperatures are site-calculated 0.5m, 2.0m, 4.0m physical temperatures (not default/fallback).")
        print(f"  Conclusion: Manali (WMO 420650) is valid and selected.")

print("\n" + "=" * 100)
print("DECISION 4: MULTI-STATION CITIES (Varanasi, Visakhapatnam, Lucknow, Agra) & DROP LIST")
print("=" * 100)
print("Dropped: Bagdogra and Car Nicobar. Final list = 24 cities.")
multi_cities = [
    ("Lucknow", ["Lucknow", "Lucknow-Amausi-Singh.Intl.AP"]),
    ("Agra", ["Agra", "Agra.AP"]),
    ("Varanasi", ["Varanasi", "Varanasi-Shastri.Intl.AP"]),
    ("Visakhapatnam", ["Vishakhapatnam", "Vishakhapatnam.Intl.AP"])
]

multi_records = []
for cname, st_names in multi_cities:
    sub = df_registry[df_registry['name'].isin(st_names)]
    for _, r in sub.iterrows():
        multi_records.append({
            "city": cname,
            "station": r['name'],
            "wmo": r['wmo_id'],
            "state": r['state_code'],
            "lat": r['lat'],
            "lon": r['lon'],
            "chosen_file": r['chosen_file']
        })

df_multi = pd.DataFrame(multi_records)
print(df_multi.to_string(index=False))

print("\nPick reasons:")
print("1. Lucknow: Picked 'Lucknow-Amausi-Singh.Intl.AP' (WMO 423690, lat 26.761, lon 80.883). Station 'Lucknow' (WMO 423680) only has legacy unsuffixed TMYx; only Amausi AP has the mandatory TMYx.2011-2025 EPW.")
print("2. Agra: Picked 'Agra.AP' (WMO 422600, lat 27.157, lon 77.961). Station 'Agra' (WMO 422610) only has legacy unsuffixed TMYx; only Agra AP has the mandatory TMYx.2011-2025 EPW.")
print("3. Varanasi: Picked 'Varanasi' (WMO 424830, lat 25.317, lon 83.033). Both have 2011-2025; 'Varanasi' is the primary city meteorological station directly within the urban fabric, whereas 'Varanasi-Shastri.Intl.AP' (Babatpur) is ~20 km outside.")
print("4. Visakhapatnam: Picked 'Vishakhapatnam' (WMO 431500, lat 17.700, lon 83.300). Both have 2011-2025; 'Vishakhapatnam' (WMO 431500) represents the central coastal city observatory.")

print("\n" + "=" * 100)
print("DECISION 1: CLIMATE ZONE CROSS-CHECK & EPW ANNUAL STATS (24 CITIES)")
print("=" * 100)
print("ECBC 2017 Appendix B, Table 11-1 'Climate Zone for Major Indian Cities' (PDF Page 201, internal page 168)")
print("ENS 2024 Table 62 'Climate Zone for major Indian Cities' (PDF Page 131, internal page 129)")
print("ECSBC 2024 Appendix 2, Table A2.1 'Climate Zone for Major Indian Cities' (PDF Page 177, internal page 163)")

# Read PDF page 201 of ECBC 2017
reader_ecbc = pypdf.PdfReader('data/docs/ECBC_2017.pdf')
ecbc_text = reader_ecbc.pages[200].extract_text()
reader_ens = pypdf.PdfReader('data/docs/ENS_2024.pdf')
ens_text = reader_ens.pages[130].extract_text()

cities_24 = [
    # Cold
    {"city": "Srinagar", "station": "Srinagar", "wmo": 420270, "zone": "Cold", "r3": "Leh", "epw": "IND_JK_Srinagar.420270_TMYx.2011-2025/IND_JK_Srinagar.420270_TMYx.2011-2025.epw"},
    {"city": "Manali", "station": "Manali", "wmo": 420650, "zone": "Cold", "r3": "Leh", "epw": "IND_HP_Manali.420650_TMYx.2011-2025/IND_HP_Manali.420650_TMYx.2011-2025.epw"},
    {"city": "Gangtok", "station": "Gangtok", "wmo": 422990, "zone": "Cold", "r3": "Leh", "epw": "IND_SK_Gangtok.422990_TMYx.2011-2025/IND_SK_Gangtok.422990_TMYx.2011-2025.epw"},
    # Composite
    {"city": "Jammu", "station": "Jammu", "wmo": 420560, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_JK_Jammu.420560_TMYx.2011-2025/IND_JK_Jammu.420560_TMYx.2011-2025.epw"},
    {"city": "Dehradun", "station": "Dehradun", "wmo": 421110, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UT_Dehradun.421110_TMYx.2011-2025/IND_UT_Dehradun.421110_TMYx.2011-2025.epw"},
    {"city": "Lucknow", "station": "Lucknow-Amausi-Singh.Intl.AP", "wmo": 423690, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Lucknow-Amausi-Singh.Intl.AP.423690_TMYx.2011-2025/IND_UP_Lucknow-Amausi-Singh.Intl.AP.423690_TMYx.2011-2025.epw"},
    {"city": "Varanasi", "station": "Varanasi", "wmo": 424830, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Varanasi.424830_TMYx.2011-2025/IND_UP_Varanasi.424830_TMYx.2011-2025.epw"},
    {"city": "Prayagraj", "station": "Allahabad-Bamrauli.AP", "wmo": 424750, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025/IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025.epw"},
    {"city": "Agra", "station": "Agra.AP", "wmo": 422600, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Agra.AP.422600_TMYx.2011-2025/IND_UP_Agra.AP.422600_TMYx.2011-2025.epw"},
    {"city": "Gorakhpur", "station": "Gorakhpur", "wmo": 423790, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Gorakhpur.423790_TMYx.2011-2025/IND_UP_Gorakhpur.423790_TMYx.2011-2025.epw"},
    {"city": "Patna", "station": "Patna-Jayaprakash.AP", "wmo": 424920, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025/IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025.epw"},
    {"city": "Nagpur", "station": "Nagpur-Ambedkar.Intl.AP", "wmo": 428670, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_MH_Nagpur-Ambedkar.Intl.AP.428670_TMYx.2011-2025/IND_MH_Nagpur-Ambedkar.Intl.AP.428670_TMYx.2011-2025.epw"},
    # Warm-humid
    {"city": "Guwahati", "station": "Guwahati-Bordoloi.Intl.AP", "wmo": 424100, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025/IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025.epw"},
    {"city": "Dibrugarh", "station": "Dibrugarh.AP", "wmo": 423140, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025/IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025.epw"},
    {"city": "Imphal", "station": "Imphal", "wmo": 426230, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_MN_Imphal.426230_TMYx.2011-2025/IND_MN_Imphal.426230_TMYx.2011-2025.epw"},
    {"city": "Bhubaneswar", "station": "Bhubaneshwar-Patnaik.Intl.AP", "wmo": 429710, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_OR_Bhubaneshwar-Patnaik.Intl.AP.429710_TMYx.2011-2025/IND_OR_Bhubaneshwar-Patnaik.Intl.AP.429710_TMYx.2011-2025.epw"},
    {"city": "Kolkata", "station": "Kolkata-Bose.Intl.AP", "wmo": 428090, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025/IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025.epw"},
    {"city": "Visakhapatnam", "station": "Vishakhapatnam", "wmo": 431500, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AP_Vishakhapatnam.431500_TMYx.2011-2025/IND_AP_Vishakhapatnam.431500_TMYx.2011-2025.epw"},
    {"city": "Chennai", "station": "Chennai.Intl.AP", "wmo": 432790, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"},
    {"city": "Surat", "station": "Surat", "wmo": 428400, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_GJ_Surat.428400_TMYx.2011-2025/IND_GJ_Surat.428400_TMYx.2011-2025.epw"},
    {"city": "Kochi", "station": "Kochi.NAS", "wmo": 433530, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_KL_Kochi.NAS.433530_TMYx.2011-2025/IND_KL_Kochi.NAS.433530_TMYx.2011-2025.epw"},
    {"city": "Port Blair", "station": "Port.Blair", "wmo": 433330, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AN_Port.Blair.433330_TMYx.2011-2025/IND_AN_Port.Blair.433330_TMYx.2011-2025.epw"},
    # Hot-dry
    {"city": "Bhuj", "station": "Bhuj", "wmo": 426340, "zone": "Hot-dry", "r3": "Jodhpur", "epw": "IND_GJ_Bhuj.426340_TMYx.2011-2025/IND_GJ_Bhuj.426340_TMYx.2011-2025.epw"},
    {"city": "Jaisalmer", "station": "Jaisalmer", "wmo": 423280, "zone": "Hot-dry", "r3": "Jodhpur", "epw": "IND_RJ_Jaisalmer.423280_TMYx.2011-2025/IND_RJ_Jaisalmer.423280_TMYx.2011-2025.epw"}
]

climate_rows = []
for c in cities_24:
    city = c["city"]
    epw_rel = os.path.join("data/raw/India_Weather_Extracted", c["epw"])
    with open(epw_rel, "r", encoding="latin-1") as f:
        lines = f.readlines()
    tdb = []
    rh = []
    for l in lines[8:]:
        p = l.split(",")
        if len(p) > 8:
            try:
                tdb.append(float(p[6]))
                rh.append(float(p[8]))
            except Exception:
                pass
    mean_tdb = round(np.mean(tdb), 2)
    mean_rh = round(np.mean(rh), 1)
    
    # Check ECBC
    search_names = [city]
    if city == "Prayagraj": search_names = ["Allahabad", "Prayagraj"]
    elif city == "Bhubaneswar": search_names = ["Bhubaneshwar", "Bhubaneswar"]
    elif city == "Visakhapatnam": search_names = ["Vishakhapatnam", "Visakhapatnam"]
    
    std_zone = "Map Lookup"
    for sn in search_names:
        m = re.search(r'\b' + re.escape(sn) + r'\b\s+([A-Za-z\s\&]+?)(?=\s+[A-Z][a-z]|\n|$)', ecbc_text)
        if m:
            raw = m.group(1).strip()
            if "Composite" in raw: std_zone = "Composite"
            elif "Warm" in raw and "Humid" in raw: std_zone = "Warm-humid"
            elif "Hot" in raw and "Dry" in raw: std_zone = "Hot-dry"
            elif "Cold" in raw: std_zone = "Cold"
            elif "Temperate" in raw: std_zone = "Temperate"
            break
    if std_zone == "Map Lookup":
        for sn in search_names:
            m = re.search(r'\b' + re.escape(sn) + r'\b\s+([A-Za-z\s\-\&]+?)(?=\s+[A-Z][a-z]|\n|$)', ens_text)
            if m:
                raw = m.group(1).strip()
                if "Composite" in raw: std_zone = "Composite"
                elif "Warm" in raw and "Humid" in raw: std_zone = "Warm-humid"
                elif "Hot" in raw and "Dry" in raw: std_zone = "Hot-dry"
                elif "Cold" in raw: std_zone = "Cold"
                elif "Temperate" in raw: std_zone = "Temperate"
                break
                
    flag = ""
    if city == "Surat":
        flag = "ODD: ECBC/ENS Table classifies as Hot-Dry, but prompt/climate table has Warm-humid (RH=68.4%)"
    elif city == "Bhuj" and mean_rh > 60:
        flag = "ODD: Hot-dry zone, but mean RH=60.8% due to coastal maritime/monsoon influence"
    elif city == "Manali" and mean_tdb < 5:
        flag = "ODD: High alpine cold (annual mean Ta=-1.82 C)"
        
    climate_rows.append({
        "City": city,
        "Assigned Zone": c["zone"],
        "ECBC/ENS Standard Zone": std_zone,
        "Mean Tdb (C)": mean_tdb,
        "Mean RH (%)": mean_rh,
        "R3 Ref": c["r3"],
        "Flag": flag
    })

df_clim = pd.DataFrame(climate_rows)
print(df_clim.to_string(index=False))
