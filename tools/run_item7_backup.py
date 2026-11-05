#!/usr/bin/env python3
"""
tools/run_item7_backup.py

Item 7: Pre-Phase 6 Core Assets Backup & Manifest Generation
1. Checks and prints git remote status.
2. Runs and prints git count-objects -vH.
3. Computes and prints directory sizes for:
   - data/processed/batch
   - models/batch
   - reports
4. Generates a comprehensive cryptographic manifest (path, size_bytes, sha256) for:
   - all final_verified* parquets and CSVs
   - all round_*_verified parquets
   - all surrogate model .joblib files
   - all results CSVs in reports/
5. Archives all identified assets into a zip file outside the repository:
   D:\\Projects\\Comfort-home-main\\comfort_home_pre_phase6_backup.zip
6. Prints literal manifest preview and destination archive path and size.
"""

import os
import sys
import glob
import zipfile
import hashlib
import subprocess
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_dir_size_bytes(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except:
                pass
    return total

def main():
    print("=" * 125)
    print("ITEM 7: PRE-PHASE 6 REPOSITORY STATUS & CORE ASSET BACKUP")
    print("=" * 125)

    # 1. Git Remote Check
    print("\n[1. GIT REMOTE STATUS]")
    res_remote = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
    remotes = res_remote.stdout.strip()
    if remotes:
        print(f"Git remotes found:\n{remotes}")
    else:
        print("Git remote check: NO REMOTE CONFIGURED (Local standalone repository)")

    # 2. Git Count Objects
    print("\n[2. GIT COUNT OBJECTS]")
    res_count = subprocess.run(["git", "count-objects", "-vH"], capture_output=True, text=True)
    print(res_count.stdout.strip())

    # 3. Directory Sizes
    print("\n[3. CORE DIRECTORY SIZES ON DISK]")
    dirs_to_check = [
        "data/processed/batch",
        "models/batch",
        "reports"
    ]
    for d in dirs_to_check:
        b = get_dir_size_bytes(d)
        mb = b / (1024 * 1024)
        gb = b / (1024 * 1024 * 1024)
        print(f"  - {d:25s}: {mb:8.2f} MB ({gb:.3f} GB)")

    # 4. Gather Target Files for Backup Manifest
    print("\n[4. GATHERING CRITICAL TARGET ASSETS FOR MANIFEST & ZIP]")
    collected_files = set()

    # final_verified*
    for root, _, files in os.walk("data/processed"):
        for f in files:
            if f.startswith("final_verified"):
                collected_files.add(os.path.normpath(os.path.join(root, f)))

    # round_*_verified
    for root, _, files in os.walk("data/processed"):
        for f in files:
            if "_verified" in f and f.startswith("round_"):
                collected_files.add(os.path.normpath(os.path.join(root, f)))

    # surrogate models (*.joblib)
    for root, _, files in os.walk("models"):
        for f in files:
            if f.endswith(".joblib"):
                collected_files.add(os.path.normpath(os.path.join(root, f)))

    # results CSVs
    for f in os.listdir("reports"):
        if f.endswith(".csv"):
            collected_files.add(os.path.normpath(os.path.join("reports", f)))

    collected_list = sorted(list(collected_files))
    print(f"Total critical assets collected: {len(collected_list)} files.")

    manifest_rows = []
    for fp in collected_list:
        sz = os.path.getsize(fp)
        sha = compute_sha256(fp)
        rel_p = os.path.relpath(fp, REPO_ROOT).replace("\\", "/")
        manifest_rows.append({
            'relative_path': rel_p,
            'size_bytes': sz,
            'sha256': sha
        })

    df_manifest = pd.DataFrame(manifest_rows)
    manifest_out_path = "reports/pre_phase6_backup_manifest.csv"
    df_manifest.to_csv(manifest_out_path, index=False)
    print(f"Cryptographic manifest written to: {manifest_out_path}")

    # 5. Zip Archive Creation Outside Repo
    # Repo is at D:\Projects\Comfort-home-main\Comfort-home-main
    # Outside repo is at D:\Projects\Comfort-home-main\
    zip_dest = os.path.abspath(os.path.join(REPO_ROOT, "..", "comfort_home_pre_phase6_backup.zip"))
    print(f"\n[5. CREATING ZIP ARCHIVE OUTSIDE REPO]")
    print(f"Archive Destination: {zip_dest}")

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add manifest itself
        zipf.write(manifest_out_path, arcname="pre_phase6_backup_manifest.csv")
        # Add all critical files
        for item in manifest_rows:
            fp = os.path.join(REPO_ROOT, item['relative_path'])
            zipf.write(fp, arcname=item['relative_path'])

    zip_size_mb = os.path.getsize(zip_dest) / (1024 * 1024)
    zip_sha256 = compute_sha256(zip_dest)
    print(f"SUCCESS: Zip archive created with {len(manifest_rows) + 1} files.")
    print(f"Archive Path:   {zip_dest}")
    print(f"Archive Size:   {zip_size_mb:.2f} MB")
    print(f"Archive SHA256: {zip_sha256}")
    print("=" * 125)

if __name__ == "__main__":
    main()

