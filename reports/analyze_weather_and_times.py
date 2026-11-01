import os
import re
import glob

# 1. Weather file analysis
content_path = r"C:\Users\SUMIT\.gemini\antigravity-ide\brain\b09c13ca-8bc8-4b7a-9872-b61c6c7989f9\.system_generated\steps\1094\content.md"
with open(content_path, "r", encoding="utf-8") as f:
    text = f.read()

matches = re.findall(r'href="[^"]*?(IND_[^"]*?\.zip)"', text)
unique_files = sorted(list(set(matches)))

with open("reports/climate_onebuilding_india_file_list.txt", "w", encoding="utf-8") as out:
    for item in unique_files:
        out.write(item + "\n")

print(f"Total EPW package ZIP files found: {len(unique_files)}")
ishrae = [f for f in unique_files if "ISHRAE" in f]
tmyx = [f for f in unique_files if "TMYx" in f]
other = [f for f in unique_files if "ISHRAE" not in f and "TMYx" not in f]

print(f"ISHRAE files count: {len(ishrae)}")
print(f"TMYx files count: {len(tmyx)}")
print(f"Other files count: {len(other)}")

# Extract unique location names / WMO station IDs
wmo_stations = set()
for f in unique_files:
    m = re.search(r'IND_[A-Z0-9]+_([A-Za-z0-9\.\-]+)\.([0-9]{6})_', f)
    if m:
        wmo_stations.add(f"{m.group(1)} ({m.group(2)})")
    else:
        m2 = re.search(r'IND_[A-Z0-9]+_([A-Za-z0-9\.\-]+)_', f)
        if m2:
            wmo_stations.add(m2.group(1))

print(f"Unique location stations count: {len(wmo_stations)}")

# 2. Check evidence files for wall-clock times
print("\n" + "="*80)
print("EVIDENCE FILES WALL CLOCK TIMES:")
print("="*80)

def read_file_text(path):
    for enc in ["utf-8", "utf-16", "latin-1"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            pass
    return ""

for ev_file in sorted(glob.glob("reports/evidence/*.txt")):
    text = read_file_text(ev_file)
    print(f"\n--- {ev_file} ---")
    for line in text.splitlines():
        if any(k in line.lower() for k in ["second", "minute", "time", "completed in", "duration", "elapsed", "runtime"]):
            print("  ", line.strip())

# 3. Disk space per city
print("\n" + "="*80)
print("DISK SPACE CALCULATION:")
print("="*80)

def get_dir_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            total += os.path.getsize(fp)
    return total

print("data/ directory size:", get_dir_size("data") / (1024*1024), "MB")
print("models/ directory size:", get_dir_size("models") / (1024*1024), "MB")

for city in ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]:
    c_files = glob.glob(f"data/**/*{city}*", recursive=True) + glob.glob(f"models/**/*{city}*", recursive=True)
    c_size = sum(os.path.getsize(f) for f in c_files if os.path.isfile(f))
    print(f"Disk space for {city}: {c_size / (1024*1024):.2f} MB ({len(c_files)} files)")
