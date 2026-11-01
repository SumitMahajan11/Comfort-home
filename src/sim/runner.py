"""
EnergyPlus Simulation Runner for ClimateAdapt-Comfort.
Executes batch simulations using local EnergyPlus 26.2.0 installation.
Features:
- Parallel execution using concurrent.futures
- Resumable (skips existing valid runs)
- Error checking and error parsing (eplusout.err)
- Output verification
"""

import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

DEFAULT_EPLUS_EXE = r"C:\EnergyPlusV26-2-0\energyplus.exe"

def run_single_simulation(
    idf_path,
    epw_path,
    output_dir,
    eplus_exe=DEFAULT_EPLUS_EXE,
    timeout_sec=120
):
    """
    Runs EnergyPlus for a single IDF and EPW.
    Returns dict with status, returncode, runtime_sec, severe_errors, fatal_errors, error_summary.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if already completed successfully
    csv_out = os.path.join(output_dir, "eplusout.csv")
    err_out = os.path.join(output_dir, "eplusout.err")
    end_out = os.path.join(output_dir, "eplusout.end")
    
    if os.path.exists(end_out) and os.path.exists(csv_out) and os.path.getsize(csv_out) > 1000:
        # Check if completed with 0 fatal errors
        with open(end_out, 'r') as f:
            end_text = f.read()
        if "EnergyPlus Completed Successfully" in end_text:
            return {
                "status": "SKIPPED_ALREADY_DONE",
                "returncode": 0,
                "runtime_sec": 0.0,
                "severe_errors": 0,
                "fatal_errors": 0,
                "output_dir": output_dir,
                "csv_path": csv_out
            }

    max_attempts = 3
    for attempt in range(max_attempts):
        cmd = [
            eplus_exe,
            "-w", os.path.abspath(epw_path),
            "-d", os.path.abspath(output_dir),
            "-r", # create eplusout.csv table
            os.path.abspath(idf_path)
        ]
        
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=os.path.abspath(output_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            runtime = time.time() - t0
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "returncode": -1,
                "runtime_sec": timeout_sec,
                "severe_errors": 0,
                "fatal_errors": 1,
                "output_dir": output_dir,
                "csv_path": None,
                "error_msg": "Simulation timed out"
            }
        except Exception as e:
            return {
                "status": "FAILED_LAUNCH",
                "returncode": -1,
                "runtime_sec": time.time() - t0,
                "severe_errors": 0,
                "fatal_errors": 1,
                "output_dir": output_dir,
                "csv_path": None,
                "error_msg": str(e)
            }

        # Parse eplusout.err for severe and fatal errors
        severe_count = 0
        fatal_count = 0
        err_lines = []
        if os.path.exists(err_out):
            with open(err_out, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "** Severe  **" in line:
                        severe_count += 1
                        err_lines.append(line.strip())
                    elif "**  Fatal  **" in line:
                        fatal_count += 1
                        err_lines.append(line.strip())

        # Check if the only severe error is transient readvars.audit lock and retry if needed
        is_transient_lock = (severe_count > 0 and any("readvars.audit" in l for l in err_lines))
        if is_transient_lock and attempt < max_attempts - 1:
            time.sleep(0.15 * (attempt + 1))
            continue
            
        success = (returncode == 0 and fatal_count == 0 and severe_count == 0)
        
        return {
            "status": "SUCCESS" if success else "FAILED",
            "returncode": returncode,
            "runtime_sec": runtime,
            "severe_errors": severe_count,
            "fatal_errors": fatal_count,
            "output_dir": output_dir,
            "csv_path": csv_out if os.path.exists(csv_out) else None,
            "error_summary": err_lines[:5]
        }

def run_batch_simulations(sim_tasks, max_workers=4):
    """
    Executes a list of simulation tasks in parallel.
    Each task in sim_tasks is a dict: {'idf_path', 'epw_path', 'output_dir', 'task_id'}
    """
    print(f"Launching batch of {len(sim_tasks)} simulations across {max_workers} worker processes...")
    results = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(
                run_single_simulation,
                t['idf_path'],
                t['epw_path'],
                t['output_dir']
            ): t for t in sim_tasks
        }
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                res = future.result()
                res['task_id'] = task.get('task_id', '')
                results.append(res)
            except Exception as exc:
                results.append({
                    "task_id": task.get('task_id', ''),
                    "status": "EXCEPTION",
                    "returncode": -1,
                    "runtime_sec": 0.0,
                    "severe_errors": 0,
                    "fatal_errors": 1,
                    "error_msg": str(exc)
                })
                
    n_success = sum(1 for r in results if r['status'] in ['SUCCESS', 'SKIPPED_ALREADY_DONE'])
    print(f"Batch completed: {n_success}/{len(sim_tasks)} successful runs.")
    return results
