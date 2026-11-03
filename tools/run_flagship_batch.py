"""
tools/run_flagship_batch.py

Batch Runner for the 5 Flagship Cities on 2011-2025 TMYx EPW files.
Cities order: Shimla, Jodhpur, New_Delhi, Mumbai, Bengaluru.
Outputs written to data/processed/flagship_2011_2025/<city>.
Calls tools/run_city_pipeline.py unchanged via dedicated subprocesses.
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

FLAGSHIP_CITIES = ["Shimla", "Jodhpur", "New_Delhi", "Mumbai", "Bengaluru"]
DEFAULT_BASE_DIR = "data/processed/flagship_2011_2025"
FLAGSHIP_LOG_CSV = "reports/flagship_2011_2025_log.csv"
FLAGSHIP_ERRORS_LOG = "reports/flagship_2011_2025_errors.log"
DISK_GUARD_GB = 5.0

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
    try:
        du = shutil.disk_usage(REPO_ROOT)
        free_gb = du.free / (1024 ** 3)
        return free_gb >= threshold_gb, free_gb
    except Exception as e:
        print(f"Warning: disk space check failed: {e}")
        return True, 999.0

def extract_city_metrics(city, batch_dir):
    pareto_p = os.path.join(batch_dir, f"final_verified_pareto_{city}.parquet")
    hist_p = os.path.join(batch_dir, "active_learning_history.csv")
    base_p = os.path.join(batch_dir, "baseline_results.csv")

    df_p = pd.read_parquet(pareto_p)
    df_hist = pd.read_csv(hist_p) if os.path.exists(hist_p) else pd.DataFrame()
    df_base = pd.read_csv(base_p) if os.path.exists(base_p) else pd.DataFrame()

    front_size = len(df_p)

    uniques = []
    round_idx = 1
    cols = [
        'roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class',
        'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
    ]
    while True:
        cand_p = os.path.join(batch_dir, f"round_{round_idx}_candidates.parquet")
        if not os.path.exists(cand_p):
            break
        df_c = pd.read_parquet(cand_p)

        n_sim = None
        if not df_hist.empty and 'round' in df_hist.columns and 'pool_size_after' in df_hist.columns:
            r_rows = df_hist[df_hist['round'] == round_idx]
            if not r_rows.empty:
                n_sim = int(r_rows.iloc[0]['pool_size_after'] - r_rows.iloc[0]['pool_size_before'])

        if n_sim is None:
            sim_dir = os.path.join(batch_dir, f"round_{round_idx}_sims")
            if os.path.exists(sim_dir):
                dids = set(d.rsplit('_', 1)[0] for d in os.listdir(sim_dir) if os.path.isdir(os.path.join(sim_dir, d)))
                if dids:
                    n_sim = len(dids)

        df_simulated = df_c.iloc[:n_sim] if n_sim is not None else df_c
        uniques.append(len(df_simulated.drop_duplicates(subset=cols)))
        round_idx += 1

    o2_errs = []
    if not df_hist.empty and 'mean_err_O2_pct' in df_hist.columns:
        o2_errs = [f"{x:.2f}%" for x in df_hist['mean_err_O2_pct']]

    best_o1_ml = round(float(df_p['O1_ml'].min()), 2)
    best_o1_ad = round(float(df_p['O1_adapt'].min()), 2)
    best_o2 = round(float(df_p['O2'].min()), 2)

    r3_o1_ml = None
    r3_o2 = None
    if not df_base.empty:
        r3_rows = df_base[df_base['design_id'] == 'R3_Code_Compliant']
        if not r3_rows.empty:
            r3_o1_ml = round(float(r3_rows.iloc[0]['O1_ml']), 2)
            r3_o2 = round(float(r3_rows.iloc[0]['O2']), 2)

    beats_r3_o1 = bool(best_o1_ml < r3_o1_ml) if (r3_o1_ml is not None) else False
    beats_r3_o2 = bool(best_o2 < r3_o2) if (r3_o2 is not None) else False

    zone_source = CITY_ZONE_SOURCE.get(city, "STANDARD")

    best_o2_row = df_p.loc[df_p['O2'].idxmin()]
    top_lt_5 = int(best_o2_row.get('top_lt_5', 0))
    top_gt_35 = int(best_o2_row.get('top_gt_35', 0))

    inv_share = float(df_p['invalid_share_adapt'].iloc[0]) if 'invalid_share_adapt' in df_p.columns else 0.0
    valid_hrs = int(round(8760 * (1.0 - inv_share / 100.0)))

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

def append_batch_log(row_dict, log_path=FLAGSHIP_LOG_CSV):
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    header = not os.path.exists(log_path) or os.path.getsize(log_path) == 0
    df_row = pd.DataFrame([row_dict])[LOG_COLUMNS]
    df_row.to_csv(log_path, mode='a', index=False, header=header)

    print("\n" + "=" * 140)
    print("FLAGSHIP BATCH LOG ENTRY RECORDED:")
    print("=" * 140)
    for k in LOG_COLUMNS:
        print(f"  {k:<32}: {row_dict.get(k, '')}")
    print("=" * 140 + "\n")

def run_flagship_batch():
    parser = argparse.ArgumentParser(description="Flagship Cities Batch Runner (2011-2025 EPWs)")
    parser.add_argument("--cities", type=str, default="", help="Comma-separated city list")
    parser.add_argument("--max-hours", type=float, default=4.0, help="Max hours allowed before stopping")
    parser.add_argument("--output-base-dir", type=str, default=DEFAULT_BASE_DIR, help="Base output directory")
    parser.add_argument("--log-path", type=str, default=FLAGSHIP_LOG_CSV, help="Log CSV path")
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",")] if args.cities else FLAGSHIP_CITIES
    base_dir = os.path.abspath(args.output_base_dir)

    print("=" * 90)
    print("STARTING FLAGSHIP CITIES BATCH RUNNER (2011-2025 EPWs)")
    print("=" * 90)
    print(f"Cities:          {cities}")
    print(f"Output Base Dir: {base_dir}")
    print(f"Max Hours Guard: {args.max_hours} h")
    print(f"Disk Guard:      >= {DISK_GUARD_GB} GB free required")
    print(f"Log CSV File:    {args.log_path}")
    print("=" * 90 + "\n")

    t_batch_start = time.time()

    for idx, city in enumerate(cities, start=1):
        elapsed_hours = (time.time() - t_batch_start) / 3600.0
        if args.max_hours is not None and elapsed_hours >= args.max_hours:
            print(f"TIME GUARD: Elapsed time {elapsed_hours:.2f} h >= --max-hours {args.max_hours:.2f} h. Halting cleanly.")
            break

        disk_ok, free_gb = check_disk_space()
        if not disk_ok:
            print(f"CRITICAL DISK GUARD: Free disk space {free_gb:.2f} GB < {DISK_GUARD_GB} GB threshold! Halting cleanly.")
            break

        print(f"\n{'#'*80}\n[{idx}/{len(cities)}] PROCESSING FLAGSHIP CITY: {city.upper()}\n{'#'*80}")
        t_city_start = time.time()
        start_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        city_batch_dir = os.path.join(base_dir, city)
        markers_dir = os.path.join(city_batch_dir, "stage_markers")
        done_marker = os.path.join(markers_dir, "stage_7_baselines_and_summary.done")

        if os.path.exists(done_marker):
            print(f"Flagship city '{city}' is already completed (found {done_marker}). Resuming: marking SKIPPED.")
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)
            metrics = extract_city_metrics(city, city_batch_dir)
            row = {'city': city, 'status': 'SKIPPED', 'start': start_str, 'end': end_str, 'minutes': minutes, **metrics}
            append_batch_log(row, log_path=args.log_path)
            continue

        cmd = [
            sys.executable, "tools/run_city_pipeline.py",
            "--city", city,
            "--batch-dir", city_batch_dir
        ]
        print(f"Executing subprocess: {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)

            if proc.returncode != 0:
                print(f"ERROR: Pipeline failed for '{city}' with returncode {proc.returncode}!")
                err_text = proc.stderr if proc.stderr else proc.stdout
                print(f"Error snippet: {err_text[-500:] if err_text else 'No output'}")
                os.makedirs(os.path.dirname(os.path.abspath(FLAGSHIP_ERRORS_LOG)), exist_ok=True)
                with open(FLAGSHIP_ERRORS_LOG, "a", encoding="utf-8") as ef:
                    ef.write(f"\n{'='*60}\nFAILED: {city} at {end_str}\nCMD: {' '.join(cmd)}\n{err_text}\n")
                failed_row = {
                    'city': city, 'status': 'FAILED', 'start': start_str, 'end': end_str, 'minutes': minutes,
                    'front_size': 0, 'unique_candidates_per_round': "", 'O2_mean_error_pct_per_round': "",
                    'best_O1_ml': "", 'best_O1_adapt': "", 'best_O2': "", 'R3_O1_ml': "", 'R3_O2': "",
                    'beats_R3_O1': False, 'beats_R3_O2': False, 'zone_source': CITY_ZONE_SOURCE.get(city, "STANDARD"),
                    'top_lt_5_best_o2': 0, 'top_gt_35_best_o2': 0, 'valid_adaptive_hours': 0,
                    'at_bound_variables': "None", 'flag_front_size_lt_5': False,
                    'flag_o2_error_rising': False, 'flag_all_rounds_lt_90_unique': False
                }
                append_batch_log(failed_row, log_path=args.log_path)
                continue

            print(f"SUCCESS: Pipeline finished for '{city}' in {minutes} minutes.")
            metrics = extract_city_metrics(city, city_batch_dir)
            success_row = {
                'city': city, 'status': 'SUCCESS', 'start': start_str, 'end': end_str, 'minutes': minutes,
                **metrics
            }
            append_batch_log(success_row, log_path=args.log_path)

        except Exception as e:
            t_city_end = time.time()
            end_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            minutes = round((t_city_end - t_city_start) / 60.0, 2)
            print(f"EXCEPTION encountered for '{city}': {e}")
            tb_str = traceback.format_exc()
            os.makedirs(os.path.dirname(os.path.abspath(FLAGSHIP_ERRORS_LOG)), exist_ok=True)
            with open(FLAGSHIP_ERRORS_LOG, "a", encoding="utf-8") as ef:
                ef.write(f"\n{'='*60}\nEXCEPTION: {city} at {end_str}\n{tb_str}\n")
            failed_row = {
                'city': city, 'status': 'FAILED', 'start': start_str, 'end': end_str, 'minutes': minutes,
                'front_size': 0, 'unique_candidates_per_round': "", 'O2_mean_error_pct_per_round': "",
                'best_O1_ml': "", 'best_O1_adapt': "", 'best_O2': "", 'R3_O1_ml': "", 'R3_O2': "",
                'beats_R3_O1': False, 'beats_R3_O2': False, 'zone_source': CITY_ZONE_SOURCE.get(city, "STANDARD"),
                'top_lt_5_best_o2': 0, 'top_gt_35_best_o2': 0, 'valid_adaptive_hours': 0,
                'at_bound_variables': "None", 'flag_front_size_lt_5': False,
                'flag_o2_error_rising': False, 'flag_all_rounds_lt_90_unique': False
            }
            append_batch_log(failed_row, log_path=args.log_path)

    total_min = round((time.time() - t_batch_start) / 60.0, 2)
    print(f"\nFLAGSHIP BATCH FINISHED in {total_min} minutes.")

if __name__ == '__main__':
    run_flagship_batch()
