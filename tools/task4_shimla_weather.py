"""
tools/task4_shimla_weather.py
Executes TASK 4: SHIMLA WEATHER FILE AUDIT & SHA256 HASH VERIFICATION
"""

import os
import hashlib

def get_file_sha256(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def extract_epw_path_from_script(script_path, city_key="Shimla"):
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            if "EPW_PATH" in line and "=" in line and ".epw" in line:
                return line.split("=")[1].strip().strip('"').strip("'")
            if f'"{city_key}"' in line and ":" in line and ".epw" in line:
                val = line.split(":", 1)[1].strip().strip(",").strip().strip('"').strip("'")
                return val
    return None

def main():
    print("=" * 105)
    print("TASK 4 - SHIMLA EPW WEATHER FILE AUDIT & SHA256 VERIFICATION")
    print("=" * 105)
    
    # 1. Path from tools/run_shimla_pilot.py and tools/run_active_learning_shimla.py
    script_pilot = "tools/run_shimla_pilot.py"
    script_al = "tools/run_active_learning_shimla.py"
    path_pilot = extract_epw_path_from_script(script_pilot)
    path_al = extract_epw_path_from_script(script_al)
    
    sha_pilot = get_file_sha256(path_pilot)
    sha_al = get_file_sha256(path_al)
    
    print(f"1. tools/run_shimla_pilot.py EPW Path:")
    print(f"   Path   : {path_pilot}")
    print(f"   SHA256 : {sha_pilot}")
    
    print(f"\n2. tools/run_active_learning_shimla.py EPW Path:")
    print(f"   Path   : {path_al}")
    print(f"   SHA256 : {sha_al}")
    
    # 2. Path from tools/report_adaptive_applicability.py
    script_adapt = "tools/report_adaptive_applicability.py"
    path_adapt = extract_epw_path_from_script(script_adapt, city_key="Shimla")
    sha_adapt = get_file_sha256(path_adapt)
    
    print(f"\n3. tools/report_adaptive_applicability.py EPW Path for Shimla:")
    print(f"   Path   : {path_adapt}")
    print(f"   SHA256 : {sha_adapt}")
    
    # 3. Say if they are the same file
    same_file = (path_pilot == path_al == path_adapt) and (sha_pilot == sha_al == sha_adapt)
    print("\n4. Are they the exact same file?")
    if same_file:
        print("   YES: Both scripts and the applicability report reference the exact same file path")
        print(f"   ({path_pilot}) with identical SHA256 checksum ({sha_pilot}).")
    else:
        print("   NO: Discrepancy detected.")
        
    # 4. Say if data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx.2011-2025 exists
    target_dir = "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx.2011-2025"
    exists = os.path.exists(target_dir)
    print(f"\n5. Does '{target_dir}' exist?")
    if exists:
        is_dir = os.path.isdir(target_dir)
        print(f"   YES: '{target_dir}' EXISTS on the filesystem (Type: {'Directory' if is_dir else 'File'}).")
    else:
        print(f"   NO: '{target_dir}' DOES NOT exist.")

if __name__ == '__main__':
    main()
