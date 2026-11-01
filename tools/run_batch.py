"""
tools/run_batch.py

Batch Execution Engine for ClimateAdapt-Comfort Scaling to All India Stations.

Features:
- Station Selection: Ingests reports/station_registry.csv, filters out the 5 original cities
  and 3 benchmark cities (Ahmedabad, Chennai, Leh), yielding 435 unique stations.
- Unique Station Keying: Keys all outputs by {station_name}_{wmo_id} to prevent name collision.
- Sequential & Resumable: Runs stations sequentially and skips stations already completed.
- Circuit Breaker: Automatically halts execution after 2 consecutive station failures.
- Robust Error Handling: try/except per station; logs failures and full tracebacks to reports/batch_errors.log.
- Memory Start Guard: Requires at least 5.0 GB available RAM before starting each station; waits 60s up to 5 times.
- Disk Guard: Aborts immediately if free disk space on D: drops below threshold (default: 5.0 GB).
- Time Guard: Gracefully stops after the currently running station if --max-hours (default: 10.0) is reached.
- Limit Guard: Stops after processing --limit N stations (if specified).
- Comprehensive Telemetry: Logs process-tree RSS, system available RAM, peak RAM, CPU %, CPU freq, disk free.
- Lean Module Import: Defers pipeline and ML imports inside station runner to prevent worker spawn overhead.
"""

import os
import sys
import time
import shutil
import argparse
import datetime
import traceback
import psutil
import pandas as pd

# Add repository root to path
REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXCLUDED_WMO_IDS = {
    423390,  # Jodhpur (Original)
    430030,  # Mumbai (Original)
    421810,  # New Delhi (Original)
    432960,  # Bengaluru (Original)
    420830,  # Shimla (Original)
    426470,  # Ahmedabad (Benchmark)
    432790,  # Chennai (Benchmark)
    427053   # Leh (Benchmark)
}

def get_system_telemetry(drive="D:\\"):
    """
    Returns current system and process-tree performance metrics.
    """
    vm = psutil.virtual_memory()
    ram_used_gb = round(vm.used / (1024**3), 2)
    ram_avail_gb = round(vm.available / (1024**3), 2)
    
    # Calculate process tree RSS (current process + all children)
    try:
        parent = psutil.Process(os.getpid())
        procs = [parent] + parent.children(recursive=True)
        tree_rss_bytes = sum(p.memory_info().rss for p in procs if p.is_running())
        process_tree_rss_gb = round(tree_rss_bytes / (1024**3), 2)
    except Exception:
        process_tree_rss_gb = 0.0
    
    cpu_pct = psutil.cpu_percent(interval=0.5)
    
    cpu_freq_obj = psutil.cpu_freq()
    cpu_mhz = cpu_freq_obj.current if cpu_freq_obj else 0.0
    
    try:
        du = shutil.disk_usage(drive)
        disk_free_gb = round(du.free / (1024**3), 2)
    except Exception:
        disk_free_gb = 0.0
        
    return {
        'ram_gb': ram_used_gb,
        'available_ram_gb': ram_avail_gb,
        'process_tree_rss_gb': process_tree_rss_gb,
        'cpu_percent': round(cpu_pct, 1),
        'cpu_freq_mhz': round(cpu_mhz, 1),
        'disk_free_gb': disk_free_gb
    }

def log_batch_entry(log_file, entry_dict):
    """
    Appends a row to reports/batch_log.csv.
    """
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    df_row = pd.DataFrame([entry_dict])
    if not os.path.exists(log_file):
        df_row.to_csv(log_file, index=False)
    else:
        df_row.to_csv(log_file, mode='a', header=False, index=False)

def log_error_traceback(error_log_path, station_name, wmo_id, tb_str):
    """
    Appends full error traceback to reports/batch_errors.log.
    """
    os.makedirs(os.path.dirname(os.path.abspath(error_log_path)), exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    with open(error_log_path, "a", encoding="utf-8") as ef:
        ef.write(f"\n{'='*80}\n")
        ef.write(f"[{timestamp}] STATION FAILURE: {station_name} (WMO: {wmo_id})\n")
        ef.write(f"{'='*80}\n")
        ef.write(tb_str.strip() + "\n")

def check_and_wait_for_ram(min_avail_gb=5.0, max_retries=5, wait_sec=60):
    """
    Checks if system available RAM is at least min_avail_gb.
    If not, waits wait_sec up to max_retries times.
    Returns True if sufficient RAM is available, False if timed out.
    """
    for attempt in range(1, max_retries + 1):
        vm = psutil.virtual_memory()
        avail_gb = vm.available / (1024**3)
        if avail_gb >= min_avail_gb:
            return True
        print(f"[MEMORY GUARD WARNING] Available RAM is {avail_gb:.2f} GB (< {min_avail_gb:.1f} GB required). Attempt {attempt}/{max_retries}: waiting {wait_sec}s...")
        time.sleep(wait_sec)
        
    vm = psutil.virtual_memory()
    avail_gb = vm.available / (1024**3)
    return avail_gb >= min_avail_gb

def execute_station(station_key, epw_path, output_dir, models_dir, max_sim_workers):
    """
    Executes a single station pipeline with lazy import of run_pipeline_for_station
    to keep worker spawning lightweight and free of heavy top-level imports.
    """
    from tools.run_station_pipeline import run_pipeline_for_station
    return run_pipeline_for_station(
        station_name=station_key,
        epw_path=epw_path,
        output_dir=output_dir,
        models_dir=models_dir,
        max_sim_workers=max_sim_workers,
        force_rerun=False
    )

def main():
    parser = argparse.ArgumentParser(description="Batch Runner for ClimateAdapt-Comfort Scaling")
    parser.add_argument("--registry-csv", default="reports/station_registry.csv", help="Path to station registry CSV")
    parser.add_argument("--output-dir", default="data/processed/scaling", help="Output directory for processed artifacts")
    parser.add_argument("--models-dir", default="models/scaling", help="Output directory for surrogate models")
    parser.add_argument("--max-hours", type=float, default=10.0, help="Maximum execution hours before stopping")
    parser.add_argument("--max-sim-workers", type=int, default=8, help="Max parallel EnergyPlus simulation workers")
    parser.add_argument("--min-free-disk-gb", type=float, default=5.0, help="Minimum free disk space on D: in GB")
    parser.add_argument("--min-avail-ram-gb", type=float, default=5.0, help="Minimum available RAM in GB before starting station")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of stations to process in this run")
    parser.add_argument("--log-csv", default="reports/batch_log.csv", help="CSV log destination")
    parser.add_argument("--error-log", default="reports/batch_errors.log", help="Error log destination for full tracebacks")
    parser.add_argument("--dry-run", action="store_true", help="Print station list and exit without running")
    args = parser.parse_args()

    print("=" * 80)
    print("CLIMATEADAPT-COMFORT: BATCH RUNNER INITIALIZATION")
    print(f"Start Local Time: {datetime.datetime.now().isoformat()}")
    print(f"Max Runtime     : {args.max_hours:.2f} hours ({args.max_hours * 3600:.0f} s)")
    print(f"Station Limit   : {args.limit if args.limit is not None else 'ALL (unlimited)'}")
    print(f"Worker Count    : {args.max_sim_workers}")
    print(f"Disk Safety Gate: >= {args.min_free_disk_gb:.1f} GB free on D:")
    print(f"RAM Start Gate  : >= {args.min_avail_ram_gb:.1f} GB available")
    print(f"Circuit Breaker : Stop after 2 consecutive failures")
    print("=" * 80)

    if not os.path.exists(args.registry_csv):
        raise FileNotFoundError(f"Station registry not found at {args.registry_csv}")

    df_reg = pd.read_csv(args.registry_csv)
    
    # Filter out 8 excluded original and benchmark stations
    batch_df = df_reg[~df_reg['wmo_id'].isin(EXCLUDED_WMO_IDS)].drop_duplicates(subset=['wmo_id']).reset_index(drop=True)
    
    print(f"\nTotal Stations in Registry: {len(df_reg)}")
    print(f"Excluded Stations (Original 5 + Benchmark 3): {len(EXCLUDED_WMO_IDS)}")
    print(f"Final Batch Stations Count: {len(batch_df)}\n")

    print("Station List (first 10 and last 10):")
    for idx, r in batch_df.head(10).iterrows():
        print(f"  [{idx+1:03d}/{len(batch_df):03d}] WMO: {r['wmo_id']} | Key: {r['name'].strip().replace(' ', '_')}_{r['wmo_id']} | File: {r['chosen_file']}")
    print("  ...")
    for idx, r in batch_df.tail(10).iterrows():
        print(f"  [{idx+1:03d}/{len(batch_df):03d}] WMO: {r['wmo_id']} | Key: {r['name'].strip().replace(' ', '_')}_{r['wmo_id']} | File: {r['chosen_file']}")

    if args.dry_run:
        print("\nDry run requested. Exiting.")
        return

    start_time = time.time()
    max_duration_sec = args.max_hours * 3600.0

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.models_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("STARTING BATCH EXECUTION")
    print("=" * 80)

    completed_count = 0
    skipped_count = 0
    failed_count = 0
    consecutive_failures = 0
    processed_in_session = 0

    for idx, row in batch_df.iterrows():
        if args.limit is not None and processed_in_session >= args.limit:
            print(f"\n[LIMIT REACHED] Processed {processed_in_session} stations (--limit {args.limit}). Stopping batch.")
            break

        station_name = str(row['name']).strip().replace(" ", "_")
        wmo_id = row['wmo_id']
        station_key = f"{station_name}_{wmo_id}"
        epw_path = str(row['chosen_path']).strip()
        
        elapsed_total = time.time() - start_time
        if elapsed_total >= max_duration_sec:
            print(f"\n[TIME GUARD] Max duration of {args.max_hours} hours reached ({elapsed_total/3600:.2f} h elapsed). Stopping batch.")
            break

        # Check memory headroom before starting station
        ram_ok = check_and_wait_for_ram(min_avail_gb=args.min_avail_ram_gb, max_retries=5, wait_sec=60)
        if not ram_ok:
            telemetry_now = get_system_telemetry(drive="D:\\")
            print(f"\n[MEMORY GUARD CRITICAL] Available RAM is {telemetry_now['available_ram_gb']:.2f} GB (< {args.min_avail_ram_gb:.1f} GB required after 5 retries). Halting batch!")
            log_batch_entry(args.log_csv, {
                'timestamp': datetime.datetime.now().isoformat(),
                'station_index': idx + 1,
                'station_name': station_key,
                'wmo_id': wmo_id,
                'status': 'ABORTED_LOW_RAM',
                'wall_clock_sec': 0.0,
                'peak_ram_gb': telemetry_now['ram_gb'],
                'available_ram_gb': telemetry_now['available_ram_gb'],
                'process_tree_rss_gb': telemetry_now['process_tree_rss_gb'],
                'cpu_freq_mhz': telemetry_now['cpu_freq_mhz'],
                'cpu_percent': telemetry_now['cpu_percent'],
                'disk_free_gb': telemetry_now['disk_free_gb'],
                'error_message': f"Available RAM below {args.min_avail_ram_gb} GB after 5 retries"
            })
            break

        # Check disk space before starting station
        telemetry_pre = get_system_telemetry(drive="D:\\")
        if telemetry_pre['disk_free_gb'] < args.min_free_disk_gb:
            print(f"\n[DISK GUARD CRITICAL] Free disk space on D: is {telemetry_pre['disk_free_gb']:.2f} GB (< {args.min_free_disk_gb:.1f} GB limit). Aborting batch!")
            log_batch_entry(args.log_csv, {
                'timestamp': datetime.datetime.now().isoformat(),
                'station_index': idx + 1,
                'station_name': station_key,
                'wmo_id': wmo_id,
                'status': 'ABORTED_LOW_DISK',
                'wall_clock_sec': 0.0,
                'peak_ram_gb': telemetry_pre['ram_gb'],
                'available_ram_gb': telemetry_pre['available_ram_gb'],
                'process_tree_rss_gb': telemetry_pre['process_tree_rss_gb'],
                'cpu_freq_mhz': telemetry_pre['cpu_freq_mhz'],
                'cpu_percent': telemetry_pre['cpu_percent'],
                'disk_free_gb': telemetry_pre['disk_free_gb'],
                'error_message': f"Disk space below {args.min_free_disk_gb} GB"
            })
            break

        print(f"\n[{idx+1:03d}/{len(batch_df):03d}] Processing Station: {station_key} (WMO: {wmo_id})")
        t_st_start = time.time()
        
        try:
            res = execute_station(
                station_key=station_key,
                epw_path=epw_path,
                output_dir=args.output_dir,
                models_dir=args.models_dir,
                max_sim_workers=args.max_sim_workers
            )
            
            t_st_elapsed = time.time() - t_st_start
            status = res.get('status', 'SUCCESS')
            if status == 'SKIPPED_ALREADY_DONE':
                skipped_count += 1
            else:
                completed_count += 1
                
            consecutive_failures = 0
            processed_in_session += 1
            telemetry_post = get_system_telemetry(drive="D:\\")
            
            log_batch_entry(args.log_csv, {
                'timestamp': datetime.datetime.now().isoformat(),
                'station_index': idx + 1,
                'station_name': station_key,
                'wmo_id': wmo_id,
                'status': status,
                'wall_clock_sec': round(t_st_elapsed, 2),
                'peak_ram_gb': telemetry_post['ram_gb'],
                'available_ram_gb': telemetry_post['available_ram_gb'],
                'process_tree_rss_gb': telemetry_post['process_tree_rss_gb'],
                'cpu_freq_mhz': telemetry_post['cpu_freq_mhz'],
                'cpu_percent': telemetry_post['cpu_percent'],
                'disk_free_gb': telemetry_post['disk_free_gb'],
                'error_message': None
            })
            
            print(f"Station {station_key} finished in {t_st_elapsed:.2f} s | Status: {status} | Tree RSS: {telemetry_post['process_tree_rss_gb']} GB | Avail RAM: {telemetry_post['available_ram_gb']} GB | Free Disk: {telemetry_post['disk_free_gb']:.2f} GB")

        except Exception as e:
            failed_count += 1
            consecutive_failures += 1
            processed_in_session += 1
            t_st_elapsed = time.time() - t_st_start
            telemetry_post = get_system_telemetry(drive="D:\\")
            err_msg = str(e).replace("\n", " ")[:200]
            tb_str = traceback.format_exc()
            
            log_error_traceback(args.error_log, station_key, wmo_id, tb_str)
            
            print(f"Station {station_key} FAILED after {t_st_elapsed:.2f} s: {err_msg}")
            print(f"  [ERROR LOG] Full traceback written to {args.error_log}")
            
            log_batch_entry(args.log_csv, {
                'timestamp': datetime.datetime.now().isoformat(),
                'station_index': idx + 1,
                'station_name': station_key,
                'wmo_id': wmo_id,
                'status': 'FAILED',
                'wall_clock_sec': round(t_st_elapsed, 2),
                'peak_ram_gb': telemetry_post['ram_gb'],
                'available_ram_gb': telemetry_post['available_ram_gb'],
                'process_tree_rss_gb': telemetry_post['process_tree_rss_gb'],
                'cpu_freq_mhz': telemetry_post['cpu_freq_mhz'],
                'cpu_percent': telemetry_post['cpu_percent'],
                'disk_free_gb': telemetry_post['disk_free_gb'],
                'error_message': err_msg
            })
            
            if consecutive_failures >= 2:
                print(f"\n[CIRCUIT BREAKER TRIGGERED] {consecutive_failures} consecutive stations failed. Stopping batch to prevent cascading errors.")
                break

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("BATCH SESSION SUMMARY")
    print(f"Total Wall-Clock Time: {total_time:.2f} s ({total_time/3600:.2f} h)")
    print(f"Completed Stations   : {completed_count}")
    print(f"Skipped (Pre-done)   : {skipped_count}")
    print(f"Failed Stations      : {failed_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()
