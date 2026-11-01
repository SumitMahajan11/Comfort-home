"""
Phase 3 Full Simulation Batch Execution Pipeline.
Executes 10,000 simulations (1,000 Latin Hypercube designs x 5 cities x 2 modes).
Storage Rule:
- Parses hourly data and computes annual summaries, O2 energy, and comfort metrics.
- Saves consolidated dataset to data/processed/sim_runs.parquet.
- Cleans transient raw simulation CSVs to maintain efficient disk usage while retaining .err files.
"""

import sys
import os
import time
import json
import shutil
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath("."))

from src.sim.sampler import sample_designs
from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

def compute_adaptive_metrics(hdf, alpha=0.7):
    """
    Computes percentage of hours outside ASHRAE 55 Adaptive 90% and 80% comfort bands.
    """
    tout = hdf['t_out'].values
    daily_tout = tout.reshape(365, 24).mean(axis=1)
    
    t_rm_daily = np.zeros(365)
    t_rm_daily[0] = daily_tout[0]
    for d in range(1, 365):
        t_rm_daily[d] = (1.0 - alpha) * daily_tout[d-1] + alpha * t_rm_daily[d-1]
        
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    t_comf = 17.8 + 0.31 * t_rm_hourly
    top = (hdf['ta'].values + hdf['tr'].values) / 2.0
    
    # 90% band (+/- 2.5 C)
    cold_90 = top < (t_comf - 2.5)
    hot_90 = top > (t_comf + 2.5)
    
    # 80% band (+/- 3.5 C)
    cold_80 = top < (t_comf - 3.5)
    hot_80 = top > (t_comf + 3.5)
    
    return {
        "adapt90_discomfort_pct": float(np.mean(cold_90 | hot_90) * 100.0),
        "adapt90_cold_pct": float(np.mean(cold_90) * 100.0),
        "adapt90_hot_pct": float(np.mean(hot_90) * 100.0),
        "adapt80_discomfort_pct": float(np.mean(cold_80 | hot_80) * 100.0),
        "adapt80_cold_pct": float(np.mean(cold_80) * 100.0),
        "adapt80_hot_pct": float(np.mean(hot_80) * 100.0),
    }

def worker_sim_task(task_dict):
    """
    Worker function executed in parallel process:
    1. Renders IDF
    2. Runs EnergyPlus simulation
    3. Parses output CSV for summary metrics
    4. Cleans large CSV to save disk space
    """
    idf_path = task_dict['idf_path']
    epw_path = task_dict['epw_path']
    output_dir = task_dict['output_dir']
    design_params = task_dict['params']
    mode = task_dict['mode']
    city = task_dict['city']
    design_id = task_dict['design_id']
    
    # Render IDF
    render_shelter_idf(design_params, idf_path, mode=mode)
    
    # Run Simulation
    sim_res = run_single_simulation(idf_path, epw_path, output_dir)
    
    if sim_res['status'] != 'SUCCESS':
        return {
            "status": sim_res['status'],
            "city": city,
            "design_id": design_id,
            "mode": mode,
            "severe_errors": sim_res['severe_errors'],
            "fatal_errors": sim_res['fatal_errors'],
            "error_summary": sim_res.get('error_summary', [])
        }
        
    # Parse CSV
    csv_path = os.path.join(output_dir, "eplusout.csv")
    try:
        hdf, sm = parse_simulation_csv(csv_path)
        adapt_metrics = compute_adaptive_metrics(hdf)
        
        # Combine all attributes
        record = {
            "status": "SUCCESS",
            "city": city,
            "design_id": design_id,
            "mode": mode,
            **design_params,
            "mean_ta": float(sm['mean_ta']),
            "max_ta": float(sm['max_ta']),
            "min_ta": float(sm['min_ta']),
            "mean_tr": float(sm['mean_tr']),
            "mean_rh": float(sm['mean_rh']),
            "mean_tout": float(sm['mean_tout']),
            "total_heating_kwh": float(sm['total_heating_kwh']),
            "total_cooling_kwh": float(sm['total_cooling_kwh']),
            "o2_energy_kwh_per_m2": float(sm['o2_energy_kwh_per_m2']),
            **adapt_metrics,
            "runtime_sec": sim_res['runtime_sec']
        }
        
        # Disk cleanup rule: remove bulky CSV after successful parsing, keep .err for verification
        if os.path.exists(csv_path):
            os.remove(csv_path)
        eso_path = os.path.join(output_dir, "eplusout.eso")
        if os.path.exists(eso_path):
            os.remove(eso_path)
            
        return record
    except Exception as e:
        return {
            "status": "PARSE_ERROR",
            "city": city,
            "design_id": design_id,
            "mode": mode,
            "error": str(e)
        }

def run_full_batch(n_designs=1000, max_workers=6, output_parquet="data/processed/sim_runs.parquet"):
    print("="*80)
    print(f"STARTING PHASE 3 FULL SIMULATION BATCH ({n_designs:,} DESIGNS x 5 CITIES x 2 MODES = {n_designs*10:,} RUNS)")
    print("="*80)
    
    sim_base_dir = "data/processed/sim_runs"
    os.makedirs(sim_base_dir, exist_ok=True)
    
    # 1. Generate Latin Hypercube samples
    df_samples = sample_designs(n_samples=n_designs, seed=42)
    print(f"Generated {len(df_samples):,} Latin Hypercube design vectors (seed 42).")
    
    # 2. Build task list
    tasks = []
    for city_name, epw_path in CITIES_EPW.items():
        if not os.path.exists(epw_path):
            raise FileNotFoundError(f"Missing EPW for {city_name}: {epw_path}")
            
        for _, row in df_samples.iterrows():
            d_id = row['design_id']
            p_dict = row.to_dict()
            
            # Mode 1: Free Running
            dir_fr = os.path.join(sim_base_dir, city_name, d_id, "free_running")
            tasks.append({
                "idf_path": os.path.join(dir_fr, "shelter.idf"),
                "epw_path": epw_path,
                "output_dir": dir_fr,
                "params": p_dict,
                "mode": "free_running",
                "city": city_name,
                "design_id": d_id
            })
            
            # Mode 2: Ideal Loads
            dir_il = os.path.join(sim_base_dir, city_name, d_id, "ideal_loads")
            tasks.append({
                "idf_path": os.path.join(dir_il, "shelter.idf"),
                "epw_path": epw_path,
                "output_dir": dir_il,
                "params": p_dict,
                "mode": "ideal_loads",
                "city": city_name,
                "design_id": d_id
            })
            
    total_tasks = len(tasks)
    print(f"Prepared {total_tasks:,} simulation tasks. Launching parallel execution across {max_workers} processes...")
    
    t0 = time.time()
    records = []
    failed_runs = []
    completed = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_sim_task, t): t for t in tasks}
        
        for future in as_completed(futures):
            res = future.result()
            completed += 1
            if res.get('status') == 'SUCCESS':
                records.append(res)
            else:
                failed_runs.append(res)
                
            if completed % 500 == 0 or completed == total_tasks:
                elapsed = time.time() - t0
                rate = completed / elapsed
                rem = (total_tasks - completed) / rate if rate > 0 else 0
                print(f"Progress: {completed:,}/{total_tasks:,} ({completed/total_tasks*100:.1f}%) | "
                      f"Success: {len(records):,} | Failed: {len(failed_runs):,} | "
                      f"Speed: {rate:.1f} runs/s | ETA: {rem/60:.1f} min")
                
    total_wall_time = time.time() - t0
    success_rate = len(records) / total_tasks * 100.0
    
    print("\n" + "="*80)
    print("SIMULATION BATCH EXECUTION COMPLETE")
    print("="*80)
    print(f"Total Simulations:  {total_tasks:,}")
    print(f"Successful Runs:    {len(records):,} ({success_rate:.2f}%)")
    print(f"Failed Runs:        {len(failed_runs):,}")
    print(f"Total Elapsed Time: {total_wall_time:.1f} s ({total_wall_time/60:.2f} min)")
    print(f"Average Throughput: {total_tasks/total_wall_time:.2f} runs/sec")
    
    # Save to Parquet
    df_results = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_results.to_parquet(output_parquet, index=False)
    print(f"\nSaved consolidated simulation results ({len(df_results):,} rows x {len(df_results.columns)} cols) to {output_parquet}")
    
    # Save batch summary log
    summary_txt = "reports/evidence/phase3_batch_execution_log.txt"
    os.makedirs(os.path.dirname(summary_txt), exist_ok=True)
    with open(summary_txt, 'w', encoding='utf-8') as f:
        f.write(f"Phase 3 Full Simulation Batch Report\n")
        f.write(f"Total Runs: {total_tasks}\n")
        f.write(f"Successful Runs: {len(records)} ({success_rate:.2f}%)\n")
        f.write(f"Failed Runs: {len(failed_runs)}\n")
        f.write(f"Total Wall Time: {total_wall_time:.2f} s\n")
        f.write(f"Average Speed: {total_tasks/total_wall_time:.2f} runs/s\n")
        if failed_runs:
            f.write(f"\nFailed Runs Details:\n{json.dumps(failed_runs[:20], indent=2)}\n")
            
    return df_results, failed_runs

if __name__ == "__main__":
    n_designs = 1000
    if len(sys.argv) > 1:
        n_designs = int(sys.argv[1])
    run_full_batch(n_designs=n_designs, max_workers=6)
