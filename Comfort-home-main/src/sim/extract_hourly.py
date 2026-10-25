"""
Extract hourly float32 indoor conditions (ta, tr, rh, t_out) for all 5,000 free-running simulations.
Saves compressed parquet files per city to data/processed/hourly_fr_{city}.parquet.
Cleans up EnergyPlus run directories after extraction.
"""

import sys
import os
import time
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

def worker_sim_extract(task_dict):
    """
    Renders IDF, runs EnergyPlus free-running simulation, extracts hourly series, and cleans run folder.
    """
    idf_path = task_dict['idf_path']
    epw_path = task_dict['epw_path']
    output_dir = task_dict['output_dir']
    design_params = task_dict['params']
    city = task_dict['city']
    design_id = task_dict['design_id']
    
    os.makedirs(output_dir, exist_ok=True)
    render_shelter_idf(design_params, idf_path, mode='free_running')
    sim_res = run_single_simulation(idf_path, epw_path, output_dir)
    
    if sim_res['status'] != 'SUCCESS':
        # Clean up directory even on failure
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        return {
            "status": sim_res['status'],
            "city": city,
            "design_id": design_id,
            "error": sim_res.get('error_summary', ['Unknown failure'])
        }
        
    csv_path = os.path.join(output_dir, "eplusout.csv")
    try:
        hdf, sm = parse_simulation_csv(csv_path)
        
        # Extract float32 hourly arrays (8,760 hours)
        ta = hdf['ta'].values.astype(np.float32)
        tr = hdf['tr'].values.astype(np.float32)
        rh = hdf['rh'].values.astype(np.float32)
        tout = hdf['t_out'].values.astype(np.float32)
        
        # Clean up directory completely to save disk space
        shutil.rmtree(output_dir, ignore_errors=True)
        
        return {
            "status": "SUCCESS",
            "city": city,
            "design_id": design_id,
            "ta": ta,
            "tr": tr,
            "rh": rh,
            "t_out": tout
        }
    except Exception as e:
        shutil.rmtree(output_dir, ignore_errors=True)
        return {
            "status": "PARSE_ERROR",
            "city": city,
            "design_id": design_id,
            "error": str(e)
        }

def run_hourly_extraction(n_designs=1000, max_workers=10):
    print("="*80)
    print(f"STARTING HOURLY SIMULATION DATA EXTRACTION ({n_designs:,} DESIGNS x 5 CITIES = {n_designs*5:,} RUNS)")
    print("="*80)
    
    temp_sim_dir = "data/processed/temp_hourly_sims"
    os.makedirs(temp_sim_dir, exist_ok=True)
    
    df_samples = sample_designs(n_samples=n_designs, seed=42)
    print(f"Generated {len(df_samples):,} design vectors.")
    
    tasks = []
    for city_name, epw_path in CITIES_EPW.items():
        for _, row in df_samples.iterrows():
            d_id = row['design_id']
            p_dict = row.to_dict()
            run_dir = os.path.join(temp_sim_dir, f"{city_name}_{d_id}")
            tasks.append({
                "idf_path": os.path.join(run_dir, "shelter.idf"),
                "epw_path": epw_path,
                "output_dir": run_dir,
                "params": p_dict,
                "city": city_name,
                "design_id": d_id
            })
            
    total_tasks = len(tasks)
    print(f"Total tasks prepared: {total_tasks:,}. Launching execution across {max_workers} processes...")
    
    t0 = time.time()
    city_results = {c: {} for c in CITIES_EPW.keys()}
    failed_runs = []
    completed = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_sim_extract, t): t for t in tasks}
        for future in as_completed(futures):
            res = future.result()
            completed += 1
            if res.get('status') == 'SUCCESS':
                city_results[res['city']][res['design_id']] = {
                    'ta': res['ta'],
                    'tr': res['tr'],
                    'rh': res['rh'],
                    't_out': res['t_out']
                }
            else:
                failed_runs.append(res)
                
            if completed % 250 == 0 or completed == total_tasks:
                elapsed = time.time() - t0
                rate = completed / elapsed
                rem = (total_tasks - completed) / rate if rate > 0 else 0
                print(f"Progress: {completed:,}/{total_tasks:,} ({completed/total_tasks*100:.1f}%) | "
                      f"Success: {completed - len(failed_runs):,} | Failed: {len(failed_runs):,} | "
                      f"Speed: {rate:.1f} runs/s | ETA: {rem/60:.1f} min")
                      
    total_time = time.time() - t0
    print(f"\nCompleted all simulations in {total_time:.1f}s ({total_time/60:.2f} min).")
    print(f"Failed runs count: {len(failed_runs)}")
    
    # Save per-city parquet files
    for city_name, designs_dict in city_results.items():
        print(f"Saving hourly data for {city_name} ({len(designs_dict)} designs)...")
        rows = []
        d_ids = sorted(list(designs_dict.keys()))
        for d_id in d_ids:
            d_data = designs_dict[d_id]
            df_d = pd.DataFrame({
                'design_id': d_id,
                'hour': np.arange(8760, dtype=np.int16),
                'ta': d_data['ta'],
                'tr': d_data['tr'],
                'rh': d_data['rh'],
                't_out': d_data['t_out']
            })
            rows.append(df_d)
            
        df_city = pd.concat(rows, ignore_index=True)
        df_city['design_id'] = df_city['design_id'].astype('category')
        
        parquet_path = f"data/processed/hourly_fr_{city_name}.parquet"
        df_city.to_parquet(parquet_path, compression='snappy', index=False)
        print(f"  -> Saved {parquet_path} ({len(df_city):,} rows, {os.path.getsize(parquet_path)/(1024*1024):.2f} MB)")
        
    # Clean up temp sim directory
    if os.path.exists(temp_sim_dir):
        shutil.rmtree(temp_sim_dir, ignore_errors=True)
        
    # Also clean up the bulky data/processed/sim_runs folder if it exists
    old_sim_runs = "data/processed/sim_runs"
    if os.path.exists(old_sim_runs):
        print(f"Cleaning up bulky directory {old_sim_runs}...")
        shutil.rmtree(old_sim_runs, ignore_errors=True)
        
    print("\nHourly extraction complete!")
    return city_results, failed_runs

if __name__ == "__main__":
    run_hourly_extraction(n_designs=1000, max_workers=10)
