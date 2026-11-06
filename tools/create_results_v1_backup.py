#!/usr/bin/env python3
"""
tools/create_results_v1_backup.py

Creates the official results-v1 backup zip containing:
- Both git-ignored critical directories:
  1. data/raw/India_Weather_Extracted/ (all raw EPWs and station files)
  2. data/processed/flagship_2011_2025/ (all verified Pareto fronts, simulations, parquets)
- All processed weather files: data/processed/weather_morphed/
- All verified Pareto CSVs and Parquets across all 30 cities in data/processed/
- All champion and surrogate models in models/
- All reports, manifests, logs, and closure files in reports/
- Cryptographic manifest with SHA-256 for every single file.
"""

import os
import sys
import zipfile
import hashlib
import time
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 100)
    print("CREATING RESULTS-V1 OFFICIAL BACKUP ARCHIVE & CRYPTOGRAPHIC MANIFEST")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    target_files = set()

    # 1. Ignored directory 1: data/raw/India_Weather_Extracted
    dir_raw_epw = REPO_ROOT / "data/raw/India_Weather_Extracted"
    if dir_raw_epw.exists():
        for root, _, files in os.walk(dir_raw_epw):
            for f in files:
                target_files.add(Path(root) / f)

    # 2. Ignored directory 2: data/processed/flagship_2011_2025
    dir_flagship = REPO_ROOT / "data/processed/flagship_2011_2025"
    if dir_flagship.exists():
        for root, _, files in os.walk(dir_flagship):
            for f in files:
                target_files.add(Path(root) / f)

    # 3. Weather morphed files
    dir_morphed = REPO_ROOT / "data/processed/weather_morphed"
    if dir_morphed.exists():
        for root, _, files in os.walk(dir_morphed):
            for f in files:
                target_files.add(Path(root) / f)

    # 4. All verified parquets and CSVs across batch
    dir_batch = REPO_ROOT / "data/processed/batch"
    if dir_batch.exists():
        for root, _, files in os.walk(dir_batch):
            for f in files:
                if f.startswith("final_verified") or ("_verified" in f and f.startswith("round_")):
                    target_files.add(Path(root) / f)

    # 5. Models (*.joblib)
    dir_models = REPO_ROOT / "models"
    if dir_models.exists():
        for root, _, files in os.walk(dir_models):
            for f in files:
                if f.endswith(".joblib"):
                    target_files.add(Path(root) / f)

    # 6. Reports directory (all reports, markdown, CSVs, txt)
    dir_reports = REPO_ROOT / "reports"
    if dir_reports.exists():
        for root, _, files in os.walk(dir_reports):
            for f in files:
                target_files.add(Path(root) / f)

    sorted_targets = sorted(list(target_files))
    print(f"Total target files collected for backup: {len(sorted_targets)}")

    # Build manifest
    manifest_rows = []
    total_uncompressed_bytes = 0
    for p in sorted_targets:
        sz = p.stat().st_size
        total_uncompressed_bytes += sz
        sha = sha256_file(p)
        rel_p = str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        manifest_rows.append({
            'relative_path': rel_p,
            'size_bytes': sz,
            'sha256': sha
        })

    df_manifest = pd.DataFrame(manifest_rows)
    manifest_csv = REPO_ROOT / "reports/results_v1_backup_manifest.csv"
    df_manifest.to_csv(manifest_csv, index=False)
    print(f"Wrote cryptographic manifest: {manifest_csv} ({len(df_manifest)} entries)")

    # Zip destination outside repo
    zip_dest = REPO_ROOT.parent / "comfort_home_results_v1_backup.zip"
    print(f"\nWriting Zip archive to: {zip_dest}")

    t0 = time.time()
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        # Include the manifest in the zip
        zipf.write(manifest_csv, arcname="results_v1_backup_manifest.csv")
        for item in manifest_rows:
            fp = REPO_ROOT / item['relative_path']
            zipf.write(fp, arcname=item['relative_path'])
    t1 = time.time()

    zip_size_bytes = zip_dest.stat().st_size
    zip_size_mb = zip_size_bytes / (1024 * 1024)
    zip_sha = sha256_file(zip_dest)

    print(f"\nBACKUP COMPLETE in {t1 - t0:.2f} seconds.")
    print(f"  Archive Path       : {zip_dest}")
    print(f"  Total Files in Zip : {len(manifest_rows) + 1}")
    print(f"  Uncompressed Size  : {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"  Compressed Size    : {zip_size_mb:.2f} MB")
    print(f"  Archive SHA-256    : {zip_sha}")
    print("=" * 100)

if __name__ == "__main__":
    main()
