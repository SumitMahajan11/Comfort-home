import os
import sys
import pandas as pd
import numpy as np

# Final 24 cities configuration
cities_24 = [
    # Cold
    {"city": "Srinagar", "station": "Srinagar", "wmo": 420270, "zone": "Cold", "epw": "data/raw/India_Weather_Extracted/IND_JK_Srinagar.420270_TMYx.2011-2025/IND_JK_Srinagar.420270_TMYx.2011-2025.epw"},
    {"city": "Manali", "station": "Manali", "wmo": 420650, "zone": "Cold", "epw": "data/raw/India_Weather_Extracted/IND_HP_Manali.420650_TMYx.2011-2025/IND_HP_Manali.420650_TMYx.2011-2025.epw"},
    {"city": "Gangtok", "station": "Gangtok", "wmo": 422990, "zone": "Cold", "epw": "data/raw/India_Weather_Extracted/IND_SK_Gangtok.422990_TMYx.2011-2025/IND_SK_Gangtok.422990_TMYx.2011-2025.epw"},
    # Composite
    {"city": "Jammu", "station": "Jammu", "wmo": 420560, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_JK_Jammu.420560_TMYx.2011-2025/IND_JK_Jammu.420560_TMYx.2011-2025.epw"},
    {"city": "Dehradun", "station": "Dehradun", "wmo": 421110, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UT_Dehradun.421110_TMYx.2011-2025/IND_UT_Dehradun.421110_TMYx.2011-2025.epw"},
    {"city": "Lucknow", "station": "Lucknow-Amausi-Singh.Intl.AP", "wmo": 423690, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UP_Lucknow-Amausi-Singh.Intl.AP.423690_TMYx.2011-2025/IND_UP_Lucknow-Amausi-Singh.Intl.AP.423690_TMYx.2011-2025.epw"},
    {"city": "Varanasi", "station": "Varanasi", "wmo": 424830, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UP_Varanasi.424830_TMYx.2011-2025/IND_UP_Varanasi.424830_TMYx.2011-2025.epw"},
    {"city": "Prayagraj", "station": "Allahabad-Bamrauli.AP", "wmo": 424750, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025/IND_UP_Allahabad-Bamrauli.AP.424750_TMYx.2011-2025.epw"},
    {"city": "Agra", "station": "Agra.AP", "wmo": 422600, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UP_Agra.AP.422600_TMYx.2011-2025/IND_UP_Agra.AP.422600_TMYx.2011-2025.epw"},
    {"city": "Gorakhpur", "station": "Gorakhpur", "wmo": 423790, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_UP_Gorakhpur.423790_TMYx.2011-2025/IND_UP_Gorakhpur.423790_TMYx.2011-2025.epw"},
    {"city": "Patna", "station": "Patna-Jayaprakash.AP", "wmo": 424920, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025/IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025.epw"},
    {"city": "Nagpur", "station": "Nagpur-Ambedkar.Intl.AP", "wmo": 428670, "zone": "Composite", "epw": "data/raw/India_Weather_Extracted/IND_MH_Nagpur-Ambedkar.Intl.AP.428670_TMYx.2011-2025/IND_MH_Nagpur-Ambedkar.Intl.AP.428670_TMYx.2011-2025.epw"},
    # Warm-humid
    {"city": "Guwahati", "station": "Guwahati-Bordoloi.Intl.AP", "wmo": 424100, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025/IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025.epw"},
    {"city": "Dibrugarh", "station": "Dibrugarh.AP", "wmo": 423140, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025/IND_AS_Dibrugarh.AP.423140_TMYx.2011-2025.epw"},
    {"city": "Imphal", "station": "Imphal", "wmo": 426230, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_MN_Imphal.426230_TMYx.2011-2025/IND_MN_Imphal.426230_TMYx.2011-2025.epw"},
    {"city": "Bhubaneswar", "station": "Bhubaneshwar-Patnaik.Intl.AP", "wmo": 429710, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_OR_Bhubaneshwar-Patnaik.Intl.AP.429710_TMYx.2011-2025/IND_OR_Bhubaneshwar-Patnaik.Intl.AP.429710_TMYx.2011-2025.epw"},
    {"city": "Kolkata", "station": "Kolkata-Bose.Intl.AP", "wmo": 428090, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025/IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025.epw"},
    {"city": "Visakhapatnam", "station": "Vishakhapatnam", "wmo": 431500, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_AP_Vishakhapatnam.431500_TMYx.2011-2025/IND_AP_Vishakhapatnam.431500_TMYx.2011-2025.epw"},
    {"city": "Chennai", "station": "Chennai.Intl.AP", "wmo": 432790, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"},
    {"city": "Surat", "station": "Surat", "wmo": 428400, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_GJ_Surat.428400_TMYx.2011-2025/IND_GJ_Surat.428400_TMYx.2011-2025.epw"},
    {"city": "Kochi", "station": "Kochi.NAS", "wmo": 433530, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_KL_Kochi.NAS.433530_TMYx.2011-2025/IND_KL_Kochi.NAS.433530_TMYx.2011-2025.epw"},
    {"city": "Port Blair", "station": "Port.Blair", "wmo": 433330, "zone": "Warm-humid", "epw": "data/raw/India_Weather_Extracted/IND_AN_Port.Blair.433330_TMYx.2011-2025/IND_AN_Port.Blair.433330_TMYx.2011-2025.epw"},
    # Hot-dry
    {"city": "Bhuj", "station": "Bhuj", "wmo": 426340, "zone": "Hot-dry", "epw": "data/raw/India_Weather_Extracted/IND_GJ_Bhuj.426340_TMYx.2011-2025/IND_GJ_Bhuj.426340_TMYx.2011-2025.epw"},
    {"city": "Jaisalmer", "station": "Jaisalmer", "wmo": 423280, "zone": "Hot-dry", "epw": "data/raw/India_Weather_Extracted/IND_RJ_Jaisalmer.423280_TMYx.2011-2025/IND_RJ_Jaisalmer.423280_TMYx.2011-2025.epw"}
]

rows = []
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

for c in cities_24:
    epw_path = c["epw"]
    with open(epw_path, "r", encoding="latin-1") as f:
        content = f.read()
        
    lines = content.splitlines()
    ground_line = None
    for l in lines[:10]:
        if l.startswith("GROUND TEMPERATURES"):
            ground_line = l
            break
            
    p = ground_line.split(",")
    # In standard EPW:
    # Index 0: 'GROUND TEMPERATURES'
    # Index 1: '3' (number of depths)
    # Index 2: '.5' (depth in meters)
    # Indices 3, 4, 5: Soil Conductivity, Density, Specific Heat
    # Indices 6 to 17: 12 monthly ground temperatures for depth 0.5m
    g_0p5 = [float(p[6 + m]) for m in range(12)]
            
    # Hourly data for dry bulb
    t_db = []
    for l in lines[8:]:
        if not l.strip():
            continue
        parts = l.split(",")
        if len(parts) > 8:
            try:
                t_db.append(float(parts[6]))
            except Exception:
                pass
                
    t_db = np.array(t_db)
    daily_tout = t_db.reshape(-1, 24).mean(axis=1)
    alpha = 0.8
    t_rm_daily = np.zeros_like(daily_tout)
    t_rm_daily[0] = daily_tout[0]
    for d in range(1, len(daily_tout)):
        t_rm_daily[d] = (1 - alpha) * daily_tout[d-1] + alpha * t_rm_daily[d-1]
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    
    valid_hours = int(np.sum((t_rm_hourly >= 10.0) & (t_rm_hourly <= 33.5)))
    
    row = {
        "city": c["city"],
        "station": c["station"],
        "wmo": c["wmo"],
        "climate_zone": c["zone"],
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
