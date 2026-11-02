import os
import sys
import hashlib
import urllib.request
import zipfile
import io
import pandas as pd
import numpy as np

BASE_URL = "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/"
TARGET_DIR = os.path.abspath("data/raw/India_Weather_Extracted")
os.makedirs(TARGET_DIR, exist_ok=True)

# Load relative paths from content.md
content_path = r"C:\Users\SUMIT\.gemini\antigravity-ide\brain\b09c13ca-8bc8-4b7a-9872-b61c6c7989f9\.system_generated\steps\1094\content.md"
with open(content_path, "r", encoding="utf-8") as f:
    import re
    matches = re.findall(r'href="([^"]*?IND_[^"]*?\.zip)"', f.read())
zip_relpaths = {os.path.basename(m): m for m in matches}

# 24 cities with picked stations and unverified zones
cities_24 = [
    # Cold
    {"city": "Srinagar", "station": "Srinagar", "wmo": 420270, "zone": "Cold", "r3": "Leh", "epw": "IND_JK_Srinagar.420270_TMYx.2011-2025.epw"},
    {"city": "Manali", "station": "Manali", "wmo": 420650, "zone": "Cold", "r3": "Leh", "epw": "IND_HP_Manali.420650_TMYx.2011-2025.epw"},
    {"city": "Gangtok", "station": "Gangtok", "wmo": 422990, "zone": "Cold", "r3": "Leh", "epw": "IND_SK_Gangtok.422990_TMYx.2011-2025.epw"},
    # Composite
    {"city": "Jammu", "station": "Jammu", "wmo": 420560, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_JK_Jammu.420560_TMYx.2011-2025.epw"},
    {"city": "Dehradun", "station": "Dehradun", "wmo": 421110, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UT_Dehradun.421110_TMYx.2011-2025.epw"},
    {"city": "Lucknow", "station": "Lucknow-Amausi-Singh.Intl.AP", "wmo": 423690, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Lucknow-Amausi-Singh.Intl.AP.423690_TMYx.2011-2025.epw"},
    {"city": "Varanasi", "station": "Varanasi", "wmo": 424830, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Varanasi.424830_TMYx.2011-2025.epw"},
    {"city": "Prayagraj", "station": "Allahabad-Bamrauli.AP", "wmo": 424750, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025.epw"},
    {"city": "Agra", "station": "Agra.AP", "wmo": 422600, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Agra.AP.422600_TMYx.2011-2025.epw"},
    {"city": "Gorakhpur", "station": "Gorakhpur", "wmo": 423790, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_UP_Gorakhpur.423790_TMYx.2011-2025.epw"},
    {"city": "Patna", "station": "Patna-Jayaprakash.AP", "wmo": 424920, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025.epw"},
    {"city": "Nagpur", "station": "Nagpur-Ambedkar.Intl.AP", "wmo": 428670, "zone": "Composite", "r3": "New_Delhi", "epw": "IND_MH_Nagpur-Ambedkar.Intl.AP.428670_TMYx.2011-2025.epw"},
    # Warm-humid
    {"city": "Guwahati", "station": "Guwahati-Bordoloi.Intl.AP", "wmo": 424100, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025.epw"},
    {"city": "Dibrugarh", "station": "Dibrugarh.AP", "wmo": 423140, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025.epw"},
    {"city": "Imphal", "station": "Imphal", "wmo": 426230, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_MN_Imphal.426230_TMYx.2011-2025.epw"},
    {"city": "Bhubaneswar", "station": "Bhubaneshwar-Patnaik.Intl.AP", "wmo": 429710, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_OR_Bhubaneshwar-Patnaik.Intl.AP.429710_TMYx.2011-2025.epw"},
    {"city": "Kolkata", "station": "Kolkata-Bose.Intl.AP", "wmo": 428090, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025.epw"},
    {"city": "Visakhapatnam", "station": "Vishakhapatnam", "wmo": 431500, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AP_Vishakhapatnam.431500_TMYx.2011-2025.epw"},
    {"city": "Chennai", "station": "Chennai.Intl.AP", "wmo": 432790, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"},
    {"city": "Surat", "station": "Surat", "wmo": 428400, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_GJ_Surat.428400_TMYx.2011-2025.epw"},
    {"city": "Kochi", "station": "Kochi.NAS", "wmo": 433530, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_KL_Kochi.NAS.433530_TMYx.2011-2025.epw"},
    {"city": "Port Blair", "station": "Port.Blair", "wmo": 433330, "zone": "Warm-humid", "r3": "Mumbai", "epw": "IND_AN_Port.Blair.433330_TMYx.2011-2025.epw"},
    # Hot-dry
    {"city": "Bhuj", "station": "Bhuj", "wmo": 426340, "zone": "Hot-dry", "r3": "Jodhpur", "epw": "IND_GJ_Bhuj.426340_TMYx.2011-2025.epw"},
    {"city": "Jaisalmer", "station": "Jaisalmer", "wmo": 423280, "zone": "Hot-dry", "r3": "Jodhpur", "epw": "IND_RJ_Jaisalmer.423280_TMYx.2011-2025.epw"}
]

manifest_rows = []
climate_stats_rows = []

print("="*100)
print("DOWNLOADING & ANALYZING EPW FILES FOR 24 CITIES")
print("="*100)

for cinfo in cities_24:
    city = cinfo["city"]
    epw_file = cinfo["epw"]
    folder_name = epw_file.replace(".epw", "")
    dest_dir = os.path.join(TARGET_DIR, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    
    local_epw_path = os.path.join(dest_dir, epw_file)
    # Also root copy if needed
    root_epw_path = os.path.join(TARGET_DIR, epw_file)
    
    zip_name = epw_file.replace(".epw", ".zip")
    rel_p = zip_relpaths.get(zip_name)
    if not rel_p:
        raise RuntimeError(f"Could not find relative path for {zip_name}")
    url = BASE_URL + rel_p
    
    if not os.path.exists(local_epw_path) or os.path.getsize(local_epw_path) < 100000:
        print(f"Downloading {city} from {url} ...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            zip_bytes = resp.read()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            epw_bytes = zf.read(epw_file)
            with open(local_epw_path, "wb") as f_out:
                f_out.write(epw_bytes)
            with open(root_epw_path, "wb") as f_out:
                f_out.write(epw_bytes)
    else:
        print(f"EPW for {city} already present: {local_epw_path}")

    # File size & SHA256
    with open(local_epw_path, "rb") as f_in:
        content = f_in.read()
    file_size = len(content)
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    manifest_rows.append({
        "city": city,
        "path": os.path.relpath(local_epw_path, ".").replace("\\", "/"),
        "size": file_size,
        "sha256": sha256_hash
    })
    
    # Parse EPW content for dry bulb, rh, and ground temperatures
    lines = content.decode("latin-1").splitlines()
    ground_line = ""
    for l in lines[:10]:
        if l.startswith("GROUND TEMPERATURES"):
            ground_line = l
            break
            
    # Monthly ground temps at 0.5m:
    # Format: GROUND TEMPERATURES, <n_depths>, <depth_1>, ..., 12 monthly temps, <depth_2>, ...
    ground_parts = ground_line.split(",")
    # Find depth .5 or 0.5
    g_0p5 = []
    idx = 1
    while idx < len(ground_parts):
        try:
            d_val = float(ground_parts[idx])
            if abs(d_val - 0.5) < 0.01:
                # next 4 are soil prop, then 12 temps
                # Actually standard EPW line:
                # GROUND TEMPERATURES, Num Depths, Depth 1, Soil Conductivity, Soil Density, Soil Specific Heat, Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Depth 2, ...
                g_0p5 = [float(ground_parts[idx + 4 + m]) for m in range(12)]
                break
            else:
                idx += 16
        except Exception:
            idx += 1
            
    # Hourly data:
    t_db = []
    rh_vals = []
    for l in lines[8:]:
        if not l.strip():
            continue
        p = l.split(",")
        if len(p) > 8:
            try:
                t_db.append(float(p[6]))
                rh_vals.append(float(p[8]))
            except Exception:
                pass
                
    t_db = np.array(t_db)
    rh_vals = np.array(rh_vals)
    mean_tdb = np.mean(t_db)
    mean_rh = np.mean(rh_vals)
    
    # Adaptive running-mean outdoor temperature calculation via canonical function
    from src.optimize.coupling import compute_valid_adaptive_hours_from_tout
    valid_hours = compute_valid_adaptive_hours_from_tout(t_db)
    
    # Flag oddity
    flag = ""
    # Surat: Warm-humid vs Hot-dry ECBC
    if city == "Surat":
        flag = "ECBC Table 11-1 lists Hot-Dry, but high RH (68.4%) & coastal location"
    elif city == "Bhuj" and mean_rh > 60:
        flag = "Hot-dry zone, moderate RH due to monsoon"
    elif city == "Manali" and mean_tdb < 5:
        flag = "Severe alpine cold (mean Ta=1.05 C, winter ground T<0 C)"
        
    climate_stats_rows.append({
        "city": city,
        "station": cinfo["station"],
        "zone": cinfo["zone"],
        "mean_tdb_C": round(mean_tdb, 2),
        "mean_rh_pct": round(mean_rh, 1),
        "valid_adaptive_hours": valid_hours,
        "g_0p5_monthly": g_0p5,
        "oddity_flag": flag
    })

# Save manifest
df_manifest = pd.DataFrame(manifest_rows)
df_manifest.to_csv("reports/batch_epw_manifest.csv", index=False)
print(f"\nSaved reports/batch_epw_manifest.csv ({len(df_manifest)} files)")

# Print summary table
df_summary = pd.DataFrame(climate_stats_rows)
print("\n" + "="*100)
print("EPW ANNUAL STATS AND CLIMATE ZONE REVIEW (24 CITIES)")
print("="*100)
cols_show = ["city", "zone", "mean_tdb_C", "mean_rh_pct", "valid_adaptive_hours", "oddity_flag"]
print(df_summary[cols_show].to_string(index=False))
