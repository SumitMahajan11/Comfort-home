#!/usr/bin/env python3
"""
tools/create_paper_v1_backup.py

Creates the official comfort_home_paper_v1_backup.zip using the v2 backup method:
1. Collects:
   - data/raw/India_Weather_Extracted (all files)
   - data/processed/flagship_2011_2025 (all files)
   - data/processed/weather_morphed (all files)
   - data/processed/batch (verified parquets and CSVs, including _dedup)
   - models (*.joblib)
   - reports (all files, including fix2.txt, manifest, tables)
   - paper (all files: methods_and_limitations.md, tables)
   - tools (build_paper_assets.py, run_fix_pass2.py)
2. Builds cryptographic manifest: reports/paper_v1_backup_manifest.csv
3. Writes zip archive to ../comfort_home_paper_v1_backup.zip
4. Performs full restore test in temporary directory outside repo:
   - checks every file's SHA-256 and size
   - confirms files checked, matches, mismatches, missing, manifest check
5. Computes and prints archive SHA-256.
"""

import os
import sys
import zipfile
import hashlib
import time
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
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
    print("CREATING COMFORT_HOME_PAPER_V1_BACKUP ARCHIVE & RESTORE VERIFICATION (V2 METHOD)")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Repo Root: {REPO_ROOT}")
    print("=" * 100)

    target_files = set()

    # 1. Ignored dir 1: data/raw/India_Weather_Extracted
    dir_raw_epw = REPO_ROOT / "data/raw/India_Weather_Extracted"
    if dir_raw_epw.exists():
        for root, _, files in os.walk(dir_raw_epw):
            for f in files:
                target_files.add(Path(root) / f)

    # 2. Ignored dir 2: data/processed/flagship_2011_2025
    dir_flagship = REPO_ROOT / "data/processed/flagship_2011_2025"
    if dir_flagship.exists():
        for root, _, files in os.walk(dir_flagship):
            for f in files:
                target_files.add(Path(root) / f)

    # 3. Weather morphed
    dir_morphed = REPO_ROOT / "data/processed/weather_morphed"
    if dir_morphed.exists():
        for root, _, files in os.walk(dir_morphed):
            for f in files:
                target_files.add(Path(root) / f)

    # 4. Batch verified parquets and CSVs (including _dedup)
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

    # 6. Reports directory
    dir_reports = REPO_ROOT / "reports"
    if dir_reports.exists():
        for root, _, files in os.walk(dir_reports):
            for f in files:
                # Do not include old backup manifest if we are creating new one
                if f != "paper_v1_backup_manifest.csv":
                    target_files.add(Path(root) / f)

    # 7. Paper directory
    dir_paper = REPO_ROOT / "paper"
    if dir_paper.exists():
        for root, _, files in os.walk(dir_paper):
            for f in files:
                target_files.add(Path(root) / f)

    # 8. Tools directory critical scripts
    for tool_name in ["build_paper_assets.py", "run_fix_pass2.py", "create_paper_v1_backup.py"]:
        tool_file = REPO_ROOT / "tools" / tool_name
        if tool_file.exists():
            target_files.add(tool_file)

    sorted_targets = sorted(list(target_files))
    print(f"Total target files collected for backup: {len(sorted_targets)}")

    # Build manifest
    manifest_rows = []
    total_uncompressed_bytes = 0
    print("Computing cryptographic SHA-256 for all target files...")
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
    manifest_csv = REPO_ROOT / "reports/paper_v1_backup_manifest.csv"
    df_manifest.to_csv(manifest_csv, index=False)
    print(f"Wrote cryptographic manifest: {manifest_csv} ({len(df_manifest)} entries)")

    # Zip destination outside repo
    zip_dest = REPO_ROOT.parent / "comfort_home_paper_v1_backup.zip"
    print(f"\nWriting Zip archive to: {zip_dest}")

    t0 = time.time()
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        # Include the manifest inside the zip
        zipf.write(manifest_csv, arcname="paper_v1_backup_manifest.csv")
        for item in manifest_rows:
            fp = REPO_ROOT / item['relative_path']
            zipf.write(fp, arcname=item['relative_path'])
    t1 = time.time()

    zip_size_bytes = zip_dest.stat().st_size
    zip_size_mb = zip_size_bytes / (1024 * 1024)
    zip_sha = sha256_file(zip_dest)

    print(f"\nArchive Details:")
    print(f"  Path               : {zip_dest}")
    print(f"  Total Files in Zip : {len(manifest_rows) + 1}")
    print(f"  Uncompressed Size  : {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"  Compressed Size    : {zip_size_mb:.2f} MB ({zip_size_bytes:,} bytes)")
    print(f"  Zip Compression Time: {t1 - t0:.2f} s")
    print(f"  Archive SHA-256    : {zip_sha}")

    # Extract to temp directory outside repo and verify
    print("\n" + "=" * 100)
    print("PERFORMING RESTORE VERIFICATION TEST IN TEMPORARY DIRECTORY")
    print("=" * 100)
    t_v0 = time.time()
    temp_restore_dir = tempfile.mkdtemp(prefix="comfort_home_paper_v1_restore_")
    print(f"Extracting archive to temporary directory: {temp_restore_dir}")
    with zipfile.ZipFile(zip_dest, 'r') as zf:
        zf.extractall(temp_restore_dir)

    temp_restore_path = Path(temp_restore_dir)

    def verify_item(row):
        rel = row['relative_path']
        exp_sha = row['sha256']
        exp_sz = row['size_bytes']
        dp = temp_restore_path / rel
        if not dp.exists():
            return ('MISSING', rel)
        if dp.stat().st_size != exp_sz:
            return ('MISMATCH', rel)
        act_sha = sha256_file(dp)
        if act_sha.lower() == exp_sha.lower():
            return ('MATCH', rel)
        return ('MISMATCH', rel)

    print(f"Verifying {len(manifest_rows)} files using ThreadPoolExecutor...")
    with ThreadPoolExecutor(max_workers=16) as pool:
        v_res = list(pool.map(verify_item, manifest_rows))

    matches = sum(1 for status, _ in v_res if status == 'MATCH')
    mismatches = [rel for status, rel in v_res if status == 'MISMATCH']
    missing = [rel for status, rel in v_res if status == 'MISSING']

    # Extra file check: paper_v1_backup_manifest.csv
    extra_m = temp_restore_path / "paper_v1_backup_manifest.csv"
    extra_m_status = "MATCH" if extra_m.exists() and sha256_file(extra_m) == sha256_file(manifest_csv) else "MISMATCH"

    t_v1 = time.time()

    print("\nRESTORE VERIFICATION TEST RESULTS:")
    print(f"  Files Checked      : {len(manifest_rows)}")
    print(f"  Matches            : {matches}")
    print(f"  Mismatches         : {len(mismatches)} ({', '.join(mismatches) if mismatches else 'none'})")
    print(f"  Missing            : {len(missing)} ({', '.join(missing) if missing else 'none'})")
    print(f"  Manifest Check     : {extra_m_status}")
    print(f"  Verification Time  : {t_v1 - t_v0:.2f} s")

    # Clean up temp restore directory
    shutil.rmtree(temp_restore_dir)
    print(f"  Cleaned up temp dir: {temp_restore_dir}")
    print("=" * 100)

    assert len(mismatches) == 0, f"Restore test failed: {len(mismatches)} mismatches"
    assert len(missing) == 0, f"Restore test failed: {len(missing)} missing files"
    assert extra_m_status == "MATCH", "Manifest restore check failed"
    print("\nALL RESTORE VERIFICATION CHECKS PASSED PERFECTLY.")
    print(f"Archive SHA-256: {zip_sha}")

if __name__ == "__main__":
    main()

