"""
tools/download_epws.py

Downloads and extracts the 5 reference Indian climate station EPW files
from climate.onebuilding.org into data/raw/India_Weather_Extracted/.
"""

import os
import sys
import zipfile
import urllib.request

BASE_DIR = os.path.abspath("data/raw/India_Weather_Extracted")

EPW_DOWNLOADS = [
    {
        "city": "Jodhpur",
        "url": "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/RJ_Rajasthan/IND_RJ_Jodhpur.423390_TMYx.zip",
        "dest_dir": os.path.join(BASE_DIR, "IND_RJ_Jodhpur.423390_TMYx"),
        "expected_epw": "IND_RJ_Jodhpur.423390_TMYx.epw"
    },
    {
        "city": "Mumbai",
        "url": "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/MH_Maharashtra/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.zip",
        "dest_dir": os.path.join(BASE_DIR, "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx"),
        "expected_epw": "IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw"
    },
    {
        "city": "New_Delhi",
        "url": "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/DL_Delhi/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.zip",
        "dest_dir": os.path.join(BASE_DIR, "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx"),
        "expected_epw": "IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw"
    },
    {
        "city": "Bengaluru",
        "url": "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/KA_Karnataka/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.zip",
        "dest_dir": os.path.join(BASE_DIR, "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx"),
        "expected_epw": "IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw"
    },
    {
        "city": "Shimla",
        "url": "https://climate.onebuilding.org/WMO_Region_2_Asia/IND_India/HP_Himachal_Pradesh/IND_HP_Shimla.420830_TMYx.zip",
        "dest_dir": os.path.join(BASE_DIR, "IND_HP_Shimla.420830_TMYx"),
        "expected_epw": "IND_HP_Shimla.420830_TMYx.epw"
    }
]

def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    for item in EPW_DOWNLOADS:
        city = item["city"]
        dest_dir = item["dest_dir"]
        expected_path = os.path.join(dest_dir, item["expected_epw"])
        
        if os.path.exists(expected_path) and os.path.getsize(expected_path) > 100000:
            print(f"[{city}] EPW already exists at {expected_path}")
            continue
            
        os.makedirs(dest_dir, exist_ok=True)
        zip_path = os.path.join(dest_dir, "temp.zip")
        print(f"[{city}] Downloading {item['url']} ...")
        
        req = urllib.request.Request(item["url"], headers={"User-Agent": "python-urllib"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as f_out:
            f_out.write(resp.read())
            
        print(f"[{city}] Extracting ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if member.endswith(".epw"):
                    epw_data = zf.read(member)
                    # Write to both member filename and expected filename
                    with open(os.path.join(dest_dir, os.path.basename(member)), "wb") as f_epw:
                        f_epw.write(epw_data)
                    with open(expected_path, "wb") as f_epw:
                        f_epw.write(epw_data)
                        
        if os.path.exists(zip_path):
            os.remove(zip_path)
            
        if os.path.exists(expected_path):
            print(f"[{city}] Verified: {expected_path} ({os.path.getsize(expected_path):,} bytes)")
        else:
            print(f"[{city}] Warning: expected {expected_path} not found.")

if __name__ == "__main__":
    main()
