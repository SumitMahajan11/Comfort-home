"""
tools/run_3_stations.py

Runs the complete 5-stage pipeline for Ahmedabad, Chennai, and Leh.
Profiles per-stage wall-clock timings, disk usage per station (including run folders),
and surrogate model R2 per target.
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("."))

from tools.run_station_pipeline import run_pipeline_for_station

STATIONS = [
    {
        "name": "Ahmedabad",
        "epw": "data/raw/India_Weather_Extracted/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2011-2025/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2011-2025.epw"
    },
    {
        "name": "Chennai",
        "epw": "data/raw/India_Weather_Extracted/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"
    },
    {
        "name": "Leh",
        "epw": "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
    }
]

def get_dir_size_bytes(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except Exception:
                pass
    return total

def main():
    print("="*80)
    print("RUNNING 3-STATION PIPELINE: Ahmedabad, Chennai, Leh")
    print("="*80)
    
    out_dir = "data/processed/scaling"
    models_dir = "models/scaling"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    all_timings = {}
    all_metrics = []
    disk_records = []
    
    t_global_start = time.time()
    
    for st_info in STATIONS:
        st_name = st_info["name"]
        epw_path = st_info["epw"]
        
        print(f"\n>>> Starting {st_name} ...")
        res = run_pipeline_for_station(st_name, epw_path, output_dir=out_dir, models_dir=models_dir, max_sim_workers=8)
        
        all_timings[st_name] = res["timings"]
        for _, m_row in res["surrogate_metrics_df"].iterrows():
            all_metrics.append(m_row.to_dict())
            
        # Measure disk
        sim_dir = os.path.join(out_dir, f"sim_{st_name}")
        ver_dir = os.path.join(out_dir, f"ver_{st_name}")
        hourly_pq = os.path.join(out_dir, f"hourly_fr_{st_name}.parquet")
        obj_pq = os.path.join(out_dir, f"objectives_{st_name}.parquet")
        par_pq = os.path.join(out_dir, f"pareto_{st_name}.parquet")
        ver_csv = os.path.join(out_dir, f"verification_{st_name}.csv")
        
        sim_sz = get_dir_size_bytes(sim_dir)
        ver_sz = get_dir_size_bytes(ver_dir)
        h_sz = os.path.getsize(hourly_pq) if os.path.exists(hourly_pq) else 0
        o_sz = os.path.getsize(obj_pq) if os.path.exists(obj_pq) else 0
        p_sz = os.path.getsize(par_pq) if os.path.exists(par_pq) else 0
        v_sz = os.path.getsize(ver_csv) if os.path.exists(ver_csv) else 0
        
        models_sz = 0
        for tgt in ['O1_ml', 'warm_ml', 'cool_ml', 'O1_adapt', 'O2']:
            mf = os.path.join(models_dir, f"surrogate_{st_name}_{tgt}.joblib")
            if os.path.exists(mf):
                models_sz += os.path.getsize(mf)
                
        total_st_bytes = sim_sz + ver_sz + h_sz + o_sz + p_sz + v_sz + models_sz
        disk_records.append({
            'station': st_name,
            'sim_folders_kb': round(sim_sz / 1024, 1),
            'ver_folders_kb': round(ver_sz / 1024, 1),
            'hourly_parquet_kb': round(h_sz / 1024, 1),
            'objectives_parquet_kb': round(o_sz / 1024, 1),
            'pareto_parquet_kb': round(p_sz / 1024, 1),
            'models_kb': round(models_sz / 1024, 1),
            'total_mb': round(total_st_bytes / (1024 * 1024), 2)
        })
        
    t_global_elapsed = time.time() - t_global_start
    print("\n" + "="*80)
    print(f"3-STATION PIPELINE COMPLETED IN {t_global_elapsed:.2f} s ({t_global_elapsed/60:.2f} min)")
    print("="*80)
    
    # Print Timing Summary Table
    df_time = pd.DataFrame(all_timings).T
    print("\n=== LITERAL PER-STAGE TIMINGS (SECONDS) ===")
    print(df_time.to_string())
    
    # Print Disk Usage Table
    df_disk = pd.DataFrame(disk_records)
    print("\n=== LITERAL DISK USAGE PER STATION (INCLUDING RUN FOLDERS) ===")
    print(df_disk.to_string(index=False))
    
    # Print Surrogate Metrics Table
    df_met = pd.DataFrame(all_metrics)
    print("\n=== LITERAL SURROGATE MODEL METRICS (R2 PER TARGET) ===")
    print(df_met.to_string(index=False))
    
    # Save results to scaling log
    with open("data/processed/scaling/three_stations_summary.json", "w") as f:
        json.dump({
            "timings": all_timings,
            "disk": disk_records,
            "metrics": all_metrics
        }, f, indent=2)

if __name__ == "__main__":
    main()
