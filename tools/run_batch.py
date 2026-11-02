"""
tools/run_batch.py

Sequential Batch Runner for ClimateAdapt-Comfort City Pipelines.

Specifications:
- Runs ONE city at a time in the prescribed order (Chennai is already done):
  Srinagar, Jammu, Bhuntar, Dehradun, Gangtok, Lucknow, Varanasi, Prayagraj, Agra,
  Gorakhpur, Patna, Guwahati, Dibrugarh, Imphal, Bhubaneswar, Kolkata,
  Visakhapatnam, Bhuj, Surat, Kochi, Port Blair, Nagpur, Jaisalmer.
- Option --max-hours N: do not START a new city after N hours.
- Uses tools/run_city_pipeline.py DONE markers, so a re-run resumes.
- If a city fails: log the error text, mark FAILED, go to the next city.
- Disk guard 5 GB: Stop cleanly if free disk is below 5.0 GB.
- Runs each city in a dedicated subprocess.
- After each city, append one row to reports/batch_log.csv (or reports/batch_log_smoke.csv for --smoke):
  city, status, start, end, minutes, front_size, unique_candidates per round,
  O2 mean error % per round, best O1_ml, best O1_adapt, best O2, R3 O1_ml, R3 O2,
  beats_R3_O1, beats_R3_O2, zone_source, hours Top<5 and Top>35 for best-O2 design,
  valid adaptive hours, list of AT BOUND variables.
  Flags: front_size < 5, O2 mean error rising over rounds, any city with all 3 rounds < 90 unique.
- --smoke writes to reports/batch_log_smoke.csv and reports/batch_errors_smoke.log only.
- --purge-sims removes only pilot_sims/round_*_sims folders of completed cities.
"""

import os
import sys
import time
import shutil
import argparse
import subprocess
import datetime
import traceback
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.run_city_pipeline import CITY_ZONE_SOURCE

DEFAULT_CITY_ORDER = [
    "Srinagar", "Jammu", "Bhuntar", "Dehradun", "Gangtok", "Lucknow",
    "Varanasi", "Prayagraj", "Agra", "Gorakhpur", "Patna", "Guwahati",
    "Dibrugarh", "Imphal", "Bhubaneswar", "Kolkata", "Visakhapatnam",
    "Bhuj", "Surat", "Kochi", "Port Blair", "Nagpur", "Jaisalmer"
]

DISK_GUARD_GB = 5.0
BATCH_LOG_CSV = "reports/batch_log.csv"
BATCH_ERRORS_LOG = "reports/batch_errors.log"
BATCH_LOG_SMOKE_CSV = "reports/batch_log_smoke.csv"
BATCH_ERRORS_SMOKE_LOG = "reports/batch_errors_smoke.log"

LOG_COLUMNS = [
    'city', 'status', 'start', 'end', 'minutes', 'front_size',
    'unique_candidates_per_round', 'O2_mean_error_pct_per_round',
    'best_O1_ml', 'best_O1_adapt', 'best_O2', 'R3_O1_ml', 'R3_O2',
    'beats_R3_O1', 'beats_R3_O2', 'zone_source',
    'top_lt_5_best_o2', 'top_gt_35_best_o2', 'valid_adaptive_hours',
    'at_bound_variables', 'flag_front_size_lt_5',
    'flag_o2_error_rising', 'flag_all_rounds_lt_90_unique'
]

def check_disk_space(threshold_gb=DISK_GUARD_GB):
    """Returns True if free disk space is at or above threshold, else False."""
    try:
        du = shutil.disk_usage(REPO_ROOT)
        free_gb = du.free / (1024 ** 3)
        return free_gb >= threshold_gb, free_gb
    except Exception as e:
        print(f"Warning: disk space check failed: {e}")
        return True, 999.0

def purge_sims_for_city(city, batch_dir, dry_run=False):
    """
    Removes only pilot_sims/round_*_sims folders of a city whose summary files exist.
    """
    pareto_p = os.path.join(batch_dir, f"final_verified_pareto_{city}.parquet")
    if not os.path.exists(pareto_p):
        return 0, []

    folders_to_purge = ["pilot_sims"] + [f"round_{r}_sims" for r in range(1, 10)]
    purged_items = []
    total_bytes = 0

    for f in folders_to_purge:
        fpath = os.path.join(batch_dir, f)
        if os.path.exists(fpath) and os.path.isdir(fpath):
            folder_size = sum(os.path.getsize(os.path.join(r, fn)) for r, _, fl in os.walk(fpath) for fn in fl)
            total_bytes += folder_size
            purged_items.append((f, folder_size))
            if not dry_run:
                shutil.rmtree(fpath, ignore_errors=True)

    return total_bytes, purged_items

def extract_city_metrics(city, batch_dir):
    """
    Extracts summary metrics and flags for a completed city pipeline.
    """
    pareto_p = os.path.join(batch_dir, f"final_verified_pareto_{city}.parquet")
    hist_p = os.path.join(batch_dir, "active_learning_history.csv")
    base_p = os.path.join(batch_dir, "baseline_results.csv")

    df_p = pd.read_parquet(pareto_p)
    df_hist = pd.read_csv(hist_p) if os.path.exists(hist_p) else pd.DataFrame()
    df_base = pd.read_csv(base_p) if os.path.exists(base_p) else pd.DataFrame()

    front_size = len(df_p)

    # Unique candidates per round
    uniques = []
    round_idx = 1
    while True:
        cand_p = os.path.join(batch_dir, f"round_{round_idx}_candidates.parquet")
        if not os.path.exists(cand_p):
            break
        df_c = pd.read_parquet(cand_p)
        cols = [
            'roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class',
            'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
        ]
        uniques.append(len(df_c.drop_duplicates(subset=cols)))
        round_idx += 1

    # O2 mean error % per round
    o2_errs = []
    if not df_hist.empty and 'mean_err_O2_pct' in df_hist.columns:
        o2_errs = [f"{x:.2f}%" for x in df_hist['mean_err_O2_pct']]

    # Best front metrics (lower is better for O1 and O2)
    best_o1_ml = round(float(df_p['O1_ml'].min()), 2)
    best_o1_ad = round(float(df_p['O1_adapt'].min()), 2)
    best_o2 = round(float(df_p['O2'].min()), 2)

    # R3 baselines
    r3_o1_ml = None
    r3_o2 = None
    if not df_base.empty:
        r3_rows = df_base[df_base['design_id'] == 'R3_Code_Compliant']
        if not r3_rows.empty:
            r3_o1_ml = round(float(r3_rows.iloc[0]['O1_ml']), 2)
            r3_o2 = round(float(r3_rows.iloc[0]['O2']), 2)

    # Beats R3 columns
    beats_r3_o1 = bool(best_o1_ml < r3_o1_ml) if (r3_o1_ml is not None) else False
    beats_r3_o2 = bool(best_o2 < r3_o2) if (r3_o2 is not None) else False

    # Zone source
    zone_source = CITY_ZONE_SOURCE.get(city, "ASSUMED")

    # Best O2 design safety metrics
    best_o2_row = df_p.loc[df_p['O2'].idxmin()]
    top_lt_5 = int(best_o2_row.get('top_lt_5', 0))
    top_gt_35 = int(best_o2_row.get('top_gt_35', 0))

    # Valid adaptive hours
    inv_share = float(df_p['invalid_share_adapt'].iloc[0]) if 'invalid_share_adapt' in df_p.columns else 0.0
    valid_hrs = int(round(8760 * (1.0 - inv_share / 100.0)))

    # Variables AT BOUND: (#low + #up) / front_size >= 2/3
    spans = {
        'roof_insulation_thickness': (0.0, 0.15),
        'wall_insulation_thickness': (0.0, 0.15),
        'roof_solar_absorptance': (0.30, 0.90),
        'wwr': (0.05, 0.40),
        'orientation': (0.0, 359.0),
        'shading_depth': (0.30, 1.00),
        'ventilation_ach': (1.0, 15.0)
    }
    at_bound_vars = []
    for var, (lb, ub) in spans.items():
        span = ub - lb
        tol = 0.05 * span
        n_b = np.sum((df_p[var] <= lb + tol + 1e-6) | (df_p[var] >= ub - tol - 1e-6))
        if n_b / front_size >= (2.0 / 3.0):
            at_bound_vars.append(var)

    counts = df_p['wall_mass_class'].value_counts()
    n_b_mass = counts.get('light', 0) + counts.get('heavy', 0)
    if n_b_mass / front_size >= (2.0 / 3.0):
        at_bound_vars.append('wall_mass_class')

    # Flags
    flag_front_size_lt_5 = front_size < 5
    flag_o2_error_rising = False
    if not df_hist.empty and 'mean_err_O2_pct' in df_hist.columns:
        raw_errs = df_hist['mean_err_O2_pct'].values
        if len(raw_errs) > 1 and all(raw_errs[i] < raw_errs[i+1] for i in range(len(raw_errs)-1)):
            flag_o2_error_rising = True

    flag_all_rounds_lt_90 = len(uniques) >= 3 and all(u < 90 for u in uniques)

    return {
        'front_size': front_size,
        'unique_candidates_per_round': "; ".join(str(u) for u in uniques) if uniques else "",
        'O2_mean_error_pct_per_round': "; ".join(o2_errs) if o2_errs else "",
        'best_O1_ml': best_o1_ml,
        'best_O1_adapt': best_o1_ad,
        'best_O2': best_o2,
        'R3_O1_ml': r3_o1_ml if r3_o1_ml is not None else "",
        'R3_O2': r3_o2 if r3_o2 is not None else "",
        'beats_R3_O1': beats_r3_o1,
        'beats_R3_O2': beats_r3_o2,
        'zone_source': zone_source,
        'top_lt_5_best_o2': top_lt_5,
        'top_gt_35_best_o2': top_gt_35,
        'valid_adaptive_hours': valid_hrs,
        'at_bound_variables': "; ".join(at_bound_vars) if at_bound_vars else "None",
        'flag_front_size_lt_5': flag_front_size_lt_5,
        'flag_o2_error_rising': flag_o2_error_rising,
        'flag_all_rounds_lt_90_unique': flag_all_rounds_lt_90
    }

def append_batch_log(row_dict, log_path=BATCH_LOG_CSV):
    """Appends a single dictionary row to the batch log CSV and prints to terminal."""
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    header = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
    df_row = pd.DataFrame([row_dict])[LOG_COLUMNS]
    df_row.to_csv(log_path, mode='a', index=False, header=header)

    print("\n" + "=" * 140)
    print("BATCH LOG ENTRY RECORDED:")
    print("=" * 140)
    for k in LOG_COLUMNS:
        print(f"  {k:<32}: {row_dict.get(k, '')}")
    print("=" * 140 + "\n")

def run_batch():
    parser = argparse.ArgumentParser(description="Sequential Batch Runner for ClimateAdapt-Comfort")
    parser.add_argument("--cities", type=str, default="", help="Comma-separated city list (overrides default order)")
    parser.add_argument("--max-hours", type=float, default=None, help="Do not start a new city after N hours")
    parser.add_argument("--smoke", action="store_true", help="Run in fast smoke mode")
    parser.add_argument("--smoke-rounds", type=int, default=None, help="Number of AL rounds in smoke mode")
    parser.add_argument("--purge-sims", action="store_true", help="Remove bulky simulation directories for completed cities")
    parser.add_argument("--log-path", type=str, default=None, help="Destination log file (overrides default)")
    args = parser.parse_args()

    # Configure log files: --smoke writes to reports/batch_log_smoke.csv and reports/batch_errors_smoke.log only
    if args.smoke:
        log_csv = args.log_path if args.log_path is not None else BATCH_LOG_SMOKE_CSV
        errors_log = BATCH_ERRORS_SMOKE_LOG
    else:
        log_csv = args.log_path if args.log_path is not None else BATCH_LOG_CSV
        errors_log = BATCH_ERRORS_LOG

    cities = [c.strip() for c in args.cities.split(",")] if args.cities else DEFAULT_CITY_ORDER
    base_batch_dir = "data/processed/batch_smoke" if args.smoke else "data/processed/batch"

    print("=" * 90)
    print("STARTING CLIMATEADAPT-COMFORT BATCH RUNNER")
    print("=" * 90)
    print(f"City Count:      {len(cities)}")
    print(f"City Order:      {cities}")
    print(f"Execution Mode:  {'SMOKE TEST' if args.smoke else 'FULL PRODUCTION'}")
    print(f"Smoke Rounds:    {args.smoke_rounds if args.smoke_rounds is not None else 'Default'}")
    print(f"Max Hours Guard: {args.max_hours if args.max_hours is not None else 'None (unlimited)'}")
    print(f"Disk Threshold:  >= {DISK_GUARD_GB} GB free required")
    print(f"Purge Sims:      {args.purge_sims}")
    print(f"Output Base Dir: {base_batch_dir}")
    print(f"Log CSV File:    {log_csv}")
    print(f"Errors Log File: {errors_log}")
    print("=" * 90 + "\n")

    t_batch_start = time.time()

    for idx, city in enumerate(cities, start=1):
        # 1. Time Guard Check
        elapsed_hours = (time.time() - t_batch_start) / 3600.0
        if args.max_hours is not None and elapsed_hours >= args.max_hours:
            print(f"TIME GUARD: Elapsed time {elapsed_hours:.2f} h >= --max-hours {args.max_hours:.2f} h. Halting batch cleanly.")
            break

        # 2. Disk Guard Check
        disk_ok, free_gb = check_disk_space()
        if not disk_ok:
            print(f"CRITICAL DISK GUARD: Free disk space {free_gb:.2f} GB < {DISK_GUARD_GB} GB threshold! Stopping batch cleanly.")
            break

        print(f"\n{'#'*80}\n[{idx}/{len(cities)}] PROCESSING CITY: {city.upper()}\n{'#'*80}")
        t_city_start = time.time()
        start_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        city_batch_dir = os.path.join(base_batch_dir, city)
        markers_dir = os.path.join(city_batch_dir, "stage_markers")
        done_marker = os.path.join(markers_dir, "stage_7_baselines_and_summary.done")

        # 3. Check Resumption / DONE Marker
        if os.path.exists(done_marker):
            print(f"City '{city}' is already completed (found {done_marker}). Resuming: marking SKIPPED.")
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)
            
            try:
                metrics = extract_city_metrics(city, city_batch_dir)
            except Exception as e:
                metrics = {
                    'front_size': 0, 'unique_candidates_per_round': '', 'O2_mean_error_pct_per_round': '',
                    'best_O1_ml': '', 'best_O1_adapt': '', 'best_O2': '', 'R3_O1_ml': '', 'R3_O2': '',
                    'beats_R3_O1': False, 'beats_R3_O2': False, 'zone_source': CITY_ZONE_SOURCE.get(city, 'ASSUMED'),
                    'top_lt_5_best_o2': 0, 'top_gt_35_best_o2': 0, 'valid_adaptive_hours': 0,
                    'at_bound_variables': '', 'flag_front_size_lt_5': False,
                    'flag_o2_error_rising': False, 'flag_all_rounds_lt_90_unique': False
                }

            row = {
                'city': city,
                'status': 'SKIPPED',
                'start': start_str,
                'end': end_str,
                'minutes': minutes,
                **metrics
            }
            append_batch_log(row, log_path=log_csv)

            if args.purge_sims:
                purged_bytes, purged_items = purge_sims_for_city(city, city_batch_dir, dry_run=False)
                print(f"Purged simulation files for {city}: {purged_bytes / (1024**2):.2f} MB freed across {len(purged_items)} directories.")

            continue

        # 4. Run City Pipeline in dedicated Subprocess
        cmd = [sys.executable, "tools/run_city_pipeline.py", "--city", city]
        if args.smoke:
            cmd.append("--smoke")
        if args.smoke_rounds is not None:
            cmd.extend(["--smoke-rounds", str(args.smoke_rounds)])

        print(f"Executing subprocess: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)

            if proc.returncode != 0:
                print(f"ERROR: City pipeline failed for '{city}' with returncode {proc.returncode}!")
                err_text = proc.stderr if proc.stderr else proc.stdout
                print(f"Error snippet: {err_text[-500:] if err_text else 'No output'}")

                # Log traceback
                os.makedirs(os.path.dirname(os.path.abspath(errors_log)), exist_ok=True)
                with open(errors_log, "a", encoding="utf-8") as ef:
                    ef.write(f"\n{'='*60}\nFAILED: {city} at {end_str}\nCMD: {' '.join(cmd)}\n{err_text}\n")

                failed_row = {
                    'city': city,
                    'status': 'FAILED',
                    'start': start_str,
                    'end': end_str,
                    'minutes': minutes,
                    'front_size': 0,
                    'unique_candidates_per_round': "",
                    'O2_mean_error_pct_per_round': "",
                    'best_O1_ml': "",
                    'best_O1_adapt': "",
                    'best_O2': "",
                    'R3_O1_ml': "",
                    'R3_O2': "",
                    'beats_R3_O1': False,
                    'beats_R3_O2': False,
                    'zone_source': CITY_ZONE_SOURCE.get(city, "ASSUMED"),
                    'top_lt_5_best_o2': 0,
                    'top_gt_35_best_o2': 0,
                    'valid_adaptive_hours': 0,
                    'at_bound_variables': "None",
                    'flag_front_size_lt_5': False,
                    'flag_o2_error_rising': False,
                    'flag_all_rounds_lt_90_unique': False
                }
                append_batch_log(failed_row, log_path=log_csv)
                continue

            # Subprocess Succeeded: extract metrics
            print(f"SUCCESS: City pipeline finished for '{city}' in {minutes} minutes.")
            metrics = extract_city_metrics(city, city_batch_dir)
            success_row = {
                'city': city,
                'status': 'SUCCESS',
                'start': start_str,
                'end': end_str,
                'minutes': minutes,
                **metrics
            }
            append_batch_log(success_row, log_path=log_csv)

            if args.purge_sims:
                purged_bytes, purged_items = purge_sims_for_city(city, city_batch_dir, dry_run=False)
                print(f"Purged simulation files for {city}: {purged_bytes / (1024**2):.2f} MB freed across {len(purged_items)} directories.")

        except Exception as e:
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)
            print(f"EXCEPTION encountered while launching city '{city}': {e}")
            tb_str = traceback.format_exc()
            os.makedirs(os.path.dirname(os.path.abspath(errors_log)), exist_ok=True)
            with open(errors_log, "a", encoding="utf-8") as ef:
                ef.write(f"\n{'='*60}\nEXCEPTION: {city} at {end_str}\n{tb_str}\n")

            failed_row = {
                'city': city,
                'status': 'FAILED',
                'start': start_str,
                'end': end_str,
                'minutes': minutes,
                'front_size': 0,
                'unique_candidates_per_round': "",
                'O2_mean_error_pct_per_round': "",
                'best_O1_ml': "",
                'best_O1_adapt': "",
                'best_O2': "",
                'R3_O1_ml': "",
                'R3_O2': "",
                'beats_R3_O1': False,
                'beats_R3_O2': False,
                'zone_source': CITY_ZONE_SOURCE.get(city, "ASSUMED"),
                'top_lt_5_best_o2': 0,
                'top_gt_35_best_o2': 0,
                'valid_adaptive_hours': 0,
                'at_bound_variables': "None",
                'flag_front_size_lt_5': False,
                'flag_o2_error_rising': False,
                'flag_all_rounds_lt_90_unique': False
            }
            append_batch_log(failed_row, log_path=log_csv)

    total_batch_min = round((time.time() - t_batch_start) / 60.0, 2)
    print(f"\nBATCH EXECUTION FINISHED in {total_batch_min} minutes.")

if __name__ == '__main__':
    run_batch()
