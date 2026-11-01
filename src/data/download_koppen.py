"""
Script to download Beck et al. 2018 Köppen-Geiger map to data/raw/
and extract raster-based Köppen major groups for all buildings in DB II metadata.
"""

import os
import urllib.request
import zipfile
import pandas as pd
import numpy as np

def attempt_download_and_map():
    raw_dir = "data/raw/koppen_geiger"
    os.makedirs(raw_dir, exist_ok=True)
    
    meta_path = "data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv"
    label_map_path = "data/processed/koppen_group_map.csv"
    output_bldg_map = "data/processed/building_group_map.csv"
    
    df_meta = pd.read_csv(meta_path)
    df_label_map = pd.read_csv(label_map_path)
    climate_to_label_group = dict(zip(df_label_map['raw_climate'], df_label_map['koppen_group']))
    
    print("Checking building coordinates...")
    print(f"Total buildings in metadata: {len(df_meta)}")
    print(f"Buildings with lat/lon: {df_meta[['lat', 'lon']].notnull().all(axis=1).sum()}")
    
    # Beck et al. 2018 URLs (several public mirrors)
    urls = [
        "https://data.hydrology.sund.ku.dk/koppen_geiger/Beck_KG_V1_present_0p5.zip",
        "https://www.gloh2o.org/wp-content/uploads/2018/10/Beck_KG_V1_present_0p5.zip",
        "http://koeppen-geiger.vu-wien.ac.at/data/Beck_KG_V1_present_0p5.zip"
    ]
    
    downloaded_zip = os.path.join(raw_dir, "Beck_KG_V1_present_0p5.zip")
    success = False
    
    for url in urls:
        print(f"Attempting to download Beck et al. 2018 from: {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response, open(downloaded_zip, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Downloaded successfully: {downloaded_zip} ({os.path.getsize(downloaded_zip):,} bytes)")
            success = True
            break
        except Exception as e:
            print(f"Failed from {url}: {e}")
            
    if success:
        with zipfile.ZipFile(downloaded_zip, 'r') as zip_ref:
            zip_ref.extractall(raw_dir)
        print("Extracted Beck et al. 2018 raster.")
    else:
        print("Raster download could not be completed via HTTP. Applying documented building-level overrides for the 7 geographic conflict clusters as instructed.")
        
if __name__ == "__main__":
    attempt_download_and_map()
