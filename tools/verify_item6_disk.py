import os
import sys
import shutil
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.run_batch import purge_sims_for_city

chennai_dir = "data/processed/batch/Chennai"

# 1. Size of data/processed/batch/Chennai split by subfolder
sub_sizes = {}
total_chennai_bytes = 0

for root, dirs, files in os.walk(chennai_dir):
    rel = os.path.relpath(root, chennai_dir)
    s = sum(os.path.getsize(os.path.join(root, f)) for f in files)
    total_chennai_bytes += s
    top_folder = rel.split(os.sep)[0]
    sub_sizes[top_folder] = sub_sizes.get(top_folder, 0) + s

print("=" * 90)
print("DISK USAGE ANALYSIS: CHENNAI PIPELINE OUTPUTS")
print("=" * 90)
rows = []
for k, v in sorted(sub_sizes.items(), key=lambda x: x[1], reverse=True):
    name = "(top-level files)" if k == "." else k
    rows.append({
        "Subfolder": name,
        "Size (MB)": round(v / (1024**2), 3),
        "Size (GB)": round(v / (1024**3), 5),
        "Share (%)": round(v / total_chennai_bytes * 100.0, 2)
    })

df_sizes = pd.DataFrame(rows)
print(df_sizes.to_string(index=False))

total_gb = total_chennai_bytes / (1024**3)
total_mb = total_chennai_bytes / (1024**2)
print("-" * 90)
print(f"Total Chennai folder size: {total_mb:.3f} MB ({total_gb:.5f} GB)")

# 2. Project for 23 remaining cities
projected_23_gb = total_gb * 23
projected_23_mb = total_mb * 23
print(f"\nProjected footprint for remaining 23 cities: {projected_23_mb:.2f} MB ({projected_23_gb:.4f} GB)")

# 3. Free disk comparison
du = shutil.disk_usage(REPO_ROOT)
free_gb = du.free / (1024**3)
free_minus_guard_gb = free_gb - 5.0

print(f"\nCurrent Free Disk Space:            {free_gb:.2f} GB")
print(f"Free Space minus 5.0 GB Safety Guard: {free_minus_guard_gb:.2f} GB")
print(f"Projected 23 Cities Usage:          {projected_23_gb:.4f} GB")
print(f"Disk Safety Headroom Margin:         {free_minus_guard_gb - projected_23_gb:.2f} GB")

# 4. Dry run of --purge-sims on Chennai
print("\n" + "=" * 90)
print("DRY RUN: --purge-sims ON CHENNAI (No files moved or deleted)")
print("=" * 90)
purged_bytes, purged_items = purge_sims_for_city("Chennai", chennai_dir, dry_run=True)
purge_rows = []
for folder, size_b in purged_items:
    purge_rows.append({
        "Folder": folder,
        "Would Remove (MB)": round(size_b / (1024**2), 3),
        "Would Remove (GB)": round(size_b / (1024**3), 5)
    })
df_purge = pd.DataFrame(purge_rows)
print(df_purge.to_string(index=False))
print("-" * 90)
print(f"Total size that would be purged: {purged_bytes / (1024**2):.3f} MB ({purged_bytes / (1024**3):.5f} GB)")
print(f"Retained size (parquets, history, timing, markers): {(total_chennai_bytes - purged_bytes) / (1024**2):.3f} MB")
