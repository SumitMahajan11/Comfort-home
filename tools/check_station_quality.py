import os
import pandas as pd
import numpy as np

registry_path = "reports/station_registry.csv"
df_registry = pd.read_csv(registry_path)

quality_results = []

for idx, row in df_registry.iterrows():
    wmo_id = str(row["wmo_id"])
    name = row["name"]
    state = row["state_code"]
    fname = row["chosen_file"]
    fpath = row["chosen_path"]
    
    if not os.path.exists(fpath):
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "FAIL",
            "reason": f"File does not exist at {fpath}"
        })
        continue
        
    try:
        with open(fpath, "r", encoding="latin-1") as f:
            lines = f.readlines()
    except Exception as e:
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "FAIL",
            "reason": f"Read error: {str(e)}"
        })
        continue
        
    # EPW has 8 header lines, data begins at line 9
    if len(lines) < 8:
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "FAIL",
            "reason": f"Incomplete header: only {len(lines)} lines"
        })
        continue
        
    data_lines = lines[8:]
    if len(data_lines) != 8760:
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "FAIL",
            "reason": f"Wrong row count: {len(data_lines)} (expected 8760)"
        })
        continue
        
    # Parse data lines
    failed_reason = None
    for line_num, l in enumerate(data_lines, 1):
        fields = l.strip().split(",")
        if len(fields) < 30:
            failed_reason = f"Corrupt data line {line_num}: only {len(fields)} fields"
            break
            
        try:
            # Col 6: Drybulb temp (C)
            drybulb = float(fields[6])
            # Col 7: Dewpoint temp (C)
            dewpoint = float(fields[7])
            # Col 8: Relative humidity (%)
            rel_hum = float(fields[8])
            # Col 9: Atmospheric pressure (Pa)
            pressure = float(fields[9])
            # Col 13: Global horizontal radiation (Wh/m2)
            ghi = float(fields[13])
            # Col 21: Wind speed (m/s)
            wind_spd = float(fields[21])
        except ValueError as ve:
            failed_reason = f"Non-numeric value on line {line_num}: {str(ve)}"
            break
            
        # Check physically impossible values
        if not (-50.0 <= drybulb <= 65.0):
            failed_reason = f"Impossible drybulb temp on line {line_num}: {drybulb} C"
            break
        if not (-60.0 <= dewpoint <= 45.0):
            failed_reason = f"Impossible dewpoint temp on line {line_num}: {dewpoint} C"
            break
        if not (0.0 <= rel_hum <= 105.0):
            failed_reason = f"Impossible relative humidity on line {line_num}: {rel_hum} %"
            break
        if not (25000.0 <= pressure <= 115000.0):
            failed_reason = f"Impossible atmospheric pressure on line {line_num}: {pressure} Pa"
            break
        if not (0.0 <= ghi <= 2000.0):
            failed_reason = f"Impossible global horizontal solar radiation on line {line_num}: {ghi} Wh/m2"
            break
        if not (0.0 <= wind_spd <= 75.0):
            failed_reason = f"Impossible wind speed on line {line_num}: {wind_spd} m/s"
            break

    if failed_reason:
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "FAIL",
            "reason": failed_reason
        })
    else:
        quality_results.append({
            "wmo_id": wmo_id,
            "name": name,
            "state_code": state,
            "chosen_file": fname,
            "status": "PASS",
            "reason": "8760 hourly rows, all physical variables in valid range"
        })

df_quality = pd.DataFrame(quality_results)
df_quality.to_csv("reports/station_quality.csv", index=False)

pass_count = (df_quality["status"] == "PASS").sum()
fail_count = (df_quality["status"] == "FAIL").sum()
print(f"Data Quality Gate Results: {pass_count} PASSED, {fail_count} FAILED out of {len(df_quality)} total stations.")
