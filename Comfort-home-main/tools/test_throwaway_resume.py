import os
import sys
import time
import subprocess
import shutil

epw = 'data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw'
test_dir = 'data/processed/scaling_test_throwaway'
os.makedirs(test_dir, exist_ok=True)

print("Starting Throwaway station run in subprocess...")
cmd = [
    sys.executable,
    'tools/run_station_pipeline.py',
    'Throwaway',
    epw,
    test_dir
]

p1 = subprocess.Popen(cmd)
time.sleep(8) # Let a few simulations run
print("Killing subprocess during Stage 1...")
p1.terminate()
try:
    p1.wait(timeout=3)
except Exception:
    p1.kill()

sim_d = os.path.join(test_dir, 'sim_Throwaway')
folders_before = os.listdir(sim_d) if os.path.exists(sim_d) else []
print(f"Run folders present after kill: {len(folders_before)}")

# Check if individual runs have eplusout.err/shelter.idf
sample_statuses = []
for f in folders_before[:5]:
    fp = os.path.join(sim_d, f)
    files = os.listdir(fp)
    sample_statuses.append((f, files))
print(f"Sample folder contents: {sample_statuses}")

print("\nRerunning Throwaway station...")
p2 = subprocess.Popen(cmd)
time.sleep(8)
print("Killing second run...")
p2.terminate()
try:
    p2.wait(timeout=3)
except Exception:
    p2.kill()

folders_after = os.listdir(sim_d) if os.path.exists(sim_d) else []
print(f"Run folders present after rerun attempt: {len(folders_after)}")

# Cleanup
shutil.rmtree(test_dir, ignore_errors=True)
print("Throwaway test directory cleaned.")
