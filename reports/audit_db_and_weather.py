import os
import glob
import pandas as pd
import numpy as np

# Set display options
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 500)
pd.set_option('display.width', 1000)

print("================================================================================")
print("PHASE 0: DATA AUDIT AUTOMATED EXTRACTION SCRIPT")
print("================================================================================")

# 1. DB II Files
meas_gz = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz'
meas_uncomp = 'data/raw/ashrae_db_ii/db_measurements_v2.1.0.csv/db_measurements_v2.1.0.csv'
meta_csv = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv'

print(f"Measurements GZ Path: {meas_gz}")
print(f"Measurements GZ Size: {os.path.getsize(meas_gz)} bytes ({os.path.getsize(meas_gz)/(1024*1024):.2f} MB)")
if os.path.exists(meas_uncomp):
    print(f"Measurements Uncompressed Path: {meas_uncomp}")
    print(f"Measurements Uncompressed Size: {os.path.getsize(meas_uncomp)} bytes ({os.path.getsize(meas_uncomp)/(1024*1024):.2f} MB)")
print(f"Metadata Path: {meta_csv}")
print(f"Metadata Size: {os.path.getsize(meta_csv)} bytes ({os.path.getsize(meta_csv)/1024:.2f} KB)")

df_meas = pd.read_csv(meas_gz, low_memory=False)
df_meta = pd.read_csv(meta_csv, low_memory=False)

print(f"\nMeasurements Shape: {df_meas.shape[0]} rows, {df_meas.shape[1]} columns")
print(f"Metadata Shape: {df_meta.shape[0]} rows, {df_meta.shape[1]} columns")

df_merged = df_meas.merge(df_meta, on='building_id', how='left')
print(f"Merged Dataset Shape: {df_merged.shape[0]} rows, {df_merged.shape[1]} columns")

print("\n--- MISSINGNESS PER KEY COLUMN ---")
key_cols = [
    'building_id', 'ta', 'ta_h', 'ta_m', 'ta_l', 'top', 'tr', 'tg', 'tg_h', 'tg_m', 'tg_l',
    'rh', 'vel', 'vel_h', 'vel_m', 'vel_l', 'met', 'clo',
    'thermal_sensation', 'thermal_acceptability', 'thermal_preference', 'thermal_comfort',
    't_out', 'rh_out', 't_out_monthly', 't_out_isd', 'rh_out_isd', 't_mot_isd',
    'climate', 'country', 'city', 'building_type', 'cooling_type'
]

missing_records = []
total_rows = len(df_merged)
for col in key_cols:
    if col in df_merged.columns:
        n_null = int(df_merged[col].isnull().sum())
        n_non_null = total_rows - n_null
        pct = (n_null / total_rows) * 100.0
        dtype_str = str(df_merged[col].dtype)
        missing_records.append({
            'Column': col,
            'Non-Null Count': n_non_null,
            'Null Count': n_null,
            'Missing %': f"{pct:.2f}%",
            'Dtype': dtype_str
        })

df_miss = pd.DataFrame(missing_records)
print(df_miss.to_string(index=False))

# 2. Rows by Köppen Class (Global)
print("\n--- GLOBAL ROWS BY KOPPEN CLASS ---")
koppen_counts = df_merged['climate'].value_counts(dropna=False)
df_koppen = pd.DataFrame({'Climate Class': koppen_counts.index, 'Count': koppen_counts.values, 'Percentage': (koppen_counts.values / total_rows * 100).round(2)})
print(df_koppen.to_string(index=False))

# Global Rows by Country
print("\n--- GLOBAL ROWS BY COUNTRY ---")
country_counts = df_merged['country'].value_counts(dropna=False)
df_country = pd.DataFrame({'Country': country_counts.index, 'Count': country_counts.values, 'Percentage': (country_counts.values / total_rows * 100).round(2)})
print(df_country.to_string(index=False))

# India Breakdown
df_india = df_merged[df_merged['country'].str.lower() == 'india']
india_total = len(df_india)
print(f"\n--- INDIA DATASET (Total: {india_total} rows, {india_total/total_rows*100:.2f}% of global) ---")

print("\nIndia Rows by Koppen Class:")
in_koppen = df_india['climate'].value_counts(dropna=False)
df_in_koppen = pd.DataFrame({'Climate Class': in_koppen.index, 'Count': in_koppen.values, 'Percentage': (in_koppen.values / india_total * 100).round(2)})
print(df_in_koppen.to_string(index=False))

print("\nIndia Rows by Building Type:")
in_bldg = df_india['building_type'].value_counts(dropna=False)
df_in_bldg = pd.DataFrame({'Building Type': in_bldg.index, 'Count': in_bldg.values, 'Percentage': (in_bldg.values / india_total * 100).round(2)})
print(df_in_bldg.to_string(index=False))

print("\nIndia Rows by Cooling / Ventilation Strategy:")
in_cool = df_india['cooling_type'].value_counts(dropna=False)
df_in_cool = pd.DataFrame({'Cooling Type': in_cool.index.astype(str), 'Count': in_cool.values, 'Percentage': (in_cool.values / india_total * 100).round(2)})
print(df_in_cool.to_string(index=False))

print("\nIndia Cross-Tabulation: Building Type x Cooling Type:")
ct_india = pd.crosstab(df_india['building_type'], df_india['cooling_type'].fillna('Unspecified (NaN)'), margins=True)
print(ct_india.to_string())

print("\nIndia Cities Detailed Breakdown:")
ct_in_city = df_india.groupby(['city', 'climate', 'building_type', df_india['cooling_type'].fillna('Unspecified')])['record_id'].count().reset_index()
ct_in_city.rename(columns={'record_id': 'Count', 'cooling_type': 'Cooling_Type'}, inplace=True)
print(ct_in_city.to_string(index=False))

# Tropical Climates Analysis
tropical_keywords = ['tropical', 'wet equatorial', 'savanna', 'monsoon', 'rainforest']
df_tropical = df_merged[df_merged['climate'].str.contains('|'.join(tropical_keywords), case=False, na=False)]
print(f"\n--- TROPICAL CLIMATES IN DB II (Total: {len(df_tropical)} rows, {len(df_tropical)/total_rows*100:.2f}%) ---")
print(df_tropical['climate'].value_counts().to_string())
print("\nTropical Rows by Country:")
print(df_tropical['country'].value_counts().to_string())

# Global Residential & Naturally Ventilated
print("\n--- GLOBAL BUILDING TYPE X COOLING STRATEGY ---")
ct_global = pd.crosstab(df_merged['building_type'], df_merged['cooling_type'].fillna('Unspecified (NaN)'), margins=True)
print(ct_global.to_string())

# 3. EPW Weather Files
print("\n================================================================================")
print("EPW WEATHER FILES AUDIT")
print("================================================================================")
epw_files = glob.glob('data/raw/India_Weather_Extracted/**/*.epw', recursive=True)
print(f"Total EPW Files: {len(epw_files)}")

station_dict = {}
for epw in epw_files:
    with open(epw, 'r', errors='ignore') as f:
        line = f.readline().strip()
        parts = line.split(',')
        if len(parts) >= 10:
            city, state, country, src, wmo, lat, lon, tz, elev = parts[1:10]
            key = (city, state, wmo)
            if key not in station_dict:
                station_dict[key] = {
                    'City': city,
                    'State': state,
                    'WMO': wmo,
                    'Source': src,
                    'Latitude': float(lat),
                    'Longitude': float(lon),
                    'Elevation_m': float(elev),
                    'Sample_Path': epw
                }

print(f"Total Distinct Indian Weather Stations: {len(station_dict)}")

# Representative proposals for the 5 Indian Climate Zones
zone_proposals = [
    {
        'Climate Zone': 'Hot and Dry',
        'Proposed City': 'Jodhpur (Rajasthan)',
        'WMO': '423390',
        'EPW File': 'data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_ISHRAE2014/IND_RJ_Jodhpur.423390_ISHRAE2014.epw',
        'Alternate City': 'Ahmedabad (Gujarat) [WMO 426470]',
        'Alternate EPW': 'data/raw/India_Weather_Extracted/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.epw'
    },
    {
        'Climate Zone': 'Warm and Humid',
        'Proposed City': 'Mumbai (Maharashtra)',
        'WMO': '430030',
        'EPW File': 'data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw',
        'Alternate City': 'Chennai (Tamil Nadu) [WMO 432790] / Kolkata (WB) [WMO 428090]',
        'Alternate EPW': 'data/raw/India_Weather_Extracted/IND_TN_Chennai.Intl.AP.432790_TMYx/IND_TN_Chennai.Intl.AP.432790_TMYx.epw'
    },
    {
        'Climate Zone': 'Composite',
        'Proposed City': 'New Delhi (Delhi)',
        'WMO': '421810',
        'EPW File': 'data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw',
        'Alternate City': 'New Delhi Safdarjung [WMO 421820]',
        'Alternate EPW': 'data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Safdarjung.AP.421820_TMYx/IND_DL_New.Delhi-Safdarjung.AP.421820_TMYx.epw'
    },
    {
        'Climate Zone': 'Temperate',
        'Proposed City': 'Bengaluru (Karnataka)',
        'WMO': '432960',
        'EPW File': 'data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw',
        'Alternate City': 'Pune (Maharashtra) [WMO 430630]',
        'Alternate EPW': 'data/raw/India_Weather_Extracted/IND_MH_Pune.430630_TMYx/IND_MH_Pune.430630_TMYx.epw'
    },
    {
        'Climate Zone': 'Cold',
        'Proposed City': 'Shimla (Himachal Pradesh)',
        'WMO': '420830',
        'EPW File': 'data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw',
        'Alternate City': 'Srinagar (Jammu & Kashmir) [WMO 420420]',
        'Alternate EPW': 'data/raw/India_Weather_Extracted/IND_JK_Srinagar.AP.420420_TMYx/IND_JK_Srinagar.AP.420420_TMYx.epw'
    }
]

df_proposals = pd.DataFrame(zone_proposals)
print("\nProposed Representative Cities per Indian Climate Zone:")
print(df_proposals.to_string(index=False))

# Verify existence of all proposed EPW files
for p in zone_proposals:
    exists_main = os.path.exists(p['EPW File'])
    exists_alt = os.path.exists(p['Alternate EPW'])
    print(f"Verification: {p['Climate Zone']} -> Main Exists: {exists_main}, Alt Exists: {exists_alt}")
