"""
tools/download_eplus.py

Downloads EnergyPlus 26.2.0 for Windows x86_64 from GitHub releases
and extracts energyplus.exe into C:\EnergyPlusV26-2-0.
"""

import os
import sys
import zipfile
import urllib.request

EPLUS_URL = "https://github.com/NatLabRockies/EnergyPlus/releases/download/v26.2.0/EnergyPlus-26.2.0-4bd7a1f26f-Windows-x86_64.zip"
TARGET_DIR = r"C:\EnergyPlusV26-2-0"
ZIP_PATH = os.path.join(TARGET_DIR, "eplus.zip")

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    eplus_exe = os.path.join(TARGET_DIR, "energyplus.exe")
    if os.path.exists(eplus_exe):
        print(f"EnergyPlus already installed at {eplus_exe}")
        return 0

    print(f"Downloading EnergyPlus 26.2.0 from {EPLUS_URL} ...")
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = (downloaded / total_size) * 100
            if block_num % 1000 == 0:
                print(f"  {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)")

    urllib.request.urlretrieve(EPLUS_URL, ZIP_PATH, reporthook=report_progress)
    print("Download complete. Extracting zip archive ...")

    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        # Find root folder in zip
        for member in zf.namelist():
            # Strip top-level directory if present (e.g., EnergyPlus-26-2-0/)
            parts = member.split('/')
            if len(parts) > 1:
                rel_path = os.path.join(*parts[1:])
            else:
                rel_path = parts[0]
            if not rel_path:
                continue
            target_path = os.path.join(TARGET_DIR, rel_path)
            if member.endswith('/'):
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(member) as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())

    print("Extraction complete. Cleaning up zip archive ...")
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    if os.path.exists(eplus_exe):
        print(f"[SUCCESS] energyplus.exe ready at {eplus_exe}")
        return 0
    else:
        print(f"[ERROR] energyplus.exe not found in {TARGET_DIR}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
