#!/usr/bin/env python3
"""
tools/report_item5_pipeline_gate.py

Item 5: PIPELINE GATE INTEGRITY VERIFICATION
In an isolated temp dir, small city (Bhuntar), reduced settings (50 LHS, 1 AL round, 5 Optuna trials):
a) Confirm active_learning_history and every round_N_verified parquet have the full (not truncated) epw_sha256.
b) For one simulation, parse EnergyPlus's own output files to print the weather file actually used,
   and compare with the manifest path.
Writes formatted report to reports/item5_pipeline_gate.txt.
"""

import os
import sys
import glob
import time
import shutil
import tempfile
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.run_city_pipeline import CityPipeline, compute_file_sha256

TEST_CITY = "Bhuntar"

def parse_eio_location(eio_path):
    """Parses Site:Location line from EnergyPlus eplusout.eio file."""
    if not os.path.exists(eio_path):
        return None
    with open(eio_path, 'r', encoding='latin-1') as f:
        for line in f:
            if line.startswith("Site:Location,"):
                parts = [p.strip() for p in line.strip().split(",")]
                return {
                    'raw_line': line.strip(),
                    'location_name': parts[1] if len(parts) > 1 else "",
                    'latitude': float(parts[2]) if len(parts) > 2 else 0.0,
                    'longitude': float(parts[3]) if len(parts) > 3 else 0.0,
                    'time_zone': float(parts[4]) if len(parts) > 4 else 0.0,
                    'elevation': float(parts[5]) if len(parts) > 5 else 0.0
                }
    return None

def main():
    out_txt_path = os.path.join("reports", "item5_pipeline_gate.txt")
    manifest_orig = os.path.join("reports", "batch_epw_manifest.csv")
    df_manifest = pd.read_csv(manifest_orig)
    orig_row = df_manifest[df_manifest['city'] == TEST_CITY].iloc[0]
    expected_sha = orig_row['sha256']
    manifest_epw_path = orig_row['path']
    computed_epw_sha = compute_file_sha256(manifest_epw_path)

    lines = []
    lines.append("=" * 145)
    lines.append("ITEM 5: PIPELINE GATE INTEGRITY AUDIT IN ISOLATED TEMPORARY ENVIRONMENT")
    lines.append(f"Target City: {TEST_CITY} | Reduced Settings: 50 LHS Designs, 1 AL Round (10 Designs), 5 Optuna Trials")
    lines.append("=" * 145)

    lines.append(f"Target City:            {TEST_CITY}")
    lines.append(f"Manifest EPW Path:      {manifest_epw_path}")
    lines.append(f"Manifest Expected SHA:  {expected_sha}")
    lines.append(f"Disk Computed SHA:      {computed_epw_sha}")
    sha_precheck = (expected_sha == computed_epw_sha)
    lines.append(f"Manifest SHA Pre-check: {'PASS' if sha_precheck else 'FAIL'}")
    lines.append("-" * 145)

    temp_dir = tempfile.mkdtemp(prefix=f"pipeline_gate_{TEST_CITY}_")
    try:
        lines.append(f"\n[PART 1: PIPELINE EXECUTION IN ISOLATED TEMP DIRECTORY]")
        lines.append(f"Temp Working Directory: {temp_dir}")

        temp_manifest = os.path.join(temp_dir, "manifest.csv")
        df_manifest.to_csv(temp_manifest, index=False)

        t0 = time.time()
        pipeline = CityPipeline(
            city_name=TEST_CITY,
            smoke=True,
            smoke_rounds=1,
            batch_dir=temp_dir,
            manifest_path=temp_manifest,
            lhs_designs=50,
            optuna_trials=5
        )
        lines.append(f"Pipeline Initialized: EPW pre-flight verification PASSED.")
        lines.append(f"Pipeline Target SHA-256: {pipeline.epw_sha256}")

        lines.append("Running pipeline stages 1 to 5 (LHS simulations, Baselines, Surrogate Tuning, AL Round 1, Pareto extraction)...")
        pipeline.run_pipeline()
        runtime_sec = time.time() - t0
        lines.append(f"Pipeline Execution Complete in {runtime_sec:.2f} seconds ({runtime_sec/60.0:.2f} minutes).")

        # PART 2: CONFIRM active_learning_history and every round_N_verified parquet have full epw_sha256
        lines.append("\n" + "=" * 145)
        lines.append("PART A: AUDIT OF epw_sha256 COLUMN IN active_learning_history AND round_N_verified PARQUETS")
        lines.append("Checking for full 64-character hexadecimal SHA-256 (not truncated) and exact match with manifest SHA-256")
        lines.append("=" * 145)

        # 1. active_learning_history.csv
        hist_path = os.path.join(temp_dir, "active_learning_history.csv")
        lines.append(f"\n1. active_learning_history.csv:")
        lines.append(f"   File Path: {hist_path}")
        if os.path.exists(hist_path):
            df_hist = pd.read_csv(hist_path)
            lines.append(f"   Row Count: {len(df_hist)}")
            lines.append(f"   Columns: {list(df_hist.columns)}")
            has_sha_col = 'epw_sha256' in df_hist.columns
            lines.append(f"   Contains 'epw_sha256' Column: {has_sha_col}")
            if has_sha_col:
                for idx, r in df_hist.iterrows():
                    val = str(r['epw_sha256'])
                    v_len = len(val)
                    is_full_64 = (v_len == 64)
                    matches_exp = (val == expected_sha)
                    lines.append(f"   - Round {r['round']}: SHA={val} | Length={v_len} chars | IsFull64={is_full_64} | MatchesManifest={matches_exp}")
        else:
            lines.append("   ERROR: active_learning_history.csv was not generated!")

        # 2. round_N_verified parquets and other verified parquets
        lines.append(f"\n2. Output Parquet Files in {temp_dir}:")
        lines.append(f"   {'Parquet Filename':<45} | {'Rows':<8} | {'Has epw_sha256':<15} | {'SHA Length':<12} | {'Is Full 64-char':<16} | {'Matches Manifest'}")
        lines.append("   " + "-" * 135)

        parquet_files = sorted(glob.glob(os.path.join(temp_dir, "*.parquet")))
        for p_file in parquet_files:
            fname = os.path.basename(p_file)
            df_pq = pd.read_parquet(p_file)
            has_sha = 'epw_sha256' in df_pq.columns
            if has_sha and len(df_pq) > 0:
                first_sha = str(df_pq['epw_sha256'].iloc[0])
                sha_len = len(first_sha)
                is_full = (sha_len == 64)
                all_match = bool((df_pq['epw_sha256'] == expected_sha).all())
                lines.append(f"   {fname:<45} | {len(df_pq):<8} | {str(has_sha):<15} | {sha_len:<12} | {str(is_full):<16} | {str(all_match)}")
            else:
                lines.append(f"   {fname:<45} | {len(df_pq):<8} | {str(has_sha):<15} | {'N/A':<12} | {'N/A':<16} | {'N/A'}")
        lines.append("   " + "-" * 135)

        # PART 3: FOR ONE SIMULATION, PARSE ENERGYPLUS'S OWN OUTPUT FILES
        lines.append("\n" + "=" * 145)
        lines.append("PART B: PARSING ENERGYPLUS'S OWN OUTPUT FILES FOR THE WEATHER FILE ACTUALLY USED")
        lines.append("Inspecting eplusout.eio / eplustbl.csv from actual simulation runs and comparing against manifest path")
        lines.append("=" * 145)

        # Find a simulation directory containing eplusout.eio
        sim_dirs = sorted(glob.glob(os.path.join(temp_dir, "*", "*"))) + sorted(glob.glob(os.path.join(temp_dir, "*")))
        eio_found = None
        chosen_sim_dir = None
        for s_dir in sim_dirs:
            candidate_eio = os.path.join(s_dir, "eplusout.eio")
            if os.path.exists(candidate_eio):
                chosen_sim_dir = s_dir
                eio_found = candidate_eio
                break

        if eio_found:
            eio_meta = parse_eio_location(eio_found)
            lines.append(f"Selected Simulation Directory: {os.path.relpath(chosen_sim_dir, temp_dir)}")
            lines.append(f"EnergyPlus Output File:        {os.path.relpath(eio_found, temp_dir)}")
            lines.append(f"Verbatim eplusout.eio Line:    {eio_meta['raw_line']}")
            lines.append(f"  * Weather Location Name:     {eio_meta['location_name']}")
            lines.append(f"  * Simulation Latitude:       {eio_meta['latitude']:.2f} deg")
            lines.append(f"  * Simulation Longitude:      {eio_meta['longitude']:.2f} deg")
            lines.append(f"  * Simulation Time Zone:      {eio_meta['time_zone']:.2f}")
            lines.append(f"  * Simulation Elevation:      {eio_meta['elevation']:.2f} m")

            # Read Manifest EPW Header Line 1
            with open(manifest_epw_path, 'r', encoding='latin-1') as f:
                epw_l1 = f.readline().strip()
            epw_parts = [p.strip() for p in epw_l1.split(",")]
            manifest_station = epw_parts[1]
            manifest_wmo = epw_parts[5]
            manifest_lat = float(epw_parts[6])
            manifest_lon = float(epw_parts[7])
            manifest_elev = float(epw_parts[9])

            lines.append(f"\nManifest EPW Header Line 1:    {repr(epw_l1)}")
            lines.append(f"  * Manifest Station:          {manifest_station}")
            lines.append(f"  * Manifest WMO ID:           {manifest_wmo}")
            lines.append(f"  * Manifest Latitude:         {manifest_lat:.2f} deg")
            lines.append(f"  * Manifest Longitude:        {manifest_lon:.2f} deg")
            lines.append(f"  * Manifest Elevation:        {manifest_elev:.2f} m")

            # Direct comparison
            wmo_in_location = manifest_wmo in eio_meta['location_name']
            station_in_location = manifest_station.lower() in eio_meta['location_name'].lower()
            lat_match = abs(eio_meta['latitude'] - manifest_lat) < 0.05
            lon_match = abs(eio_meta['longitude'] - manifest_lon) < 0.05
            elev_match = abs(eio_meta['elevation'] - manifest_elev) < 1.0

            lines.append("\nVerification Comparison:")
            lines.append(f"  * WMO #{manifest_wmo} present in EnergyPlus Environment Name: {wmo_in_location}")
            lines.append(f"  * Station '{manifest_station}' present in EnergyPlus Environment Name: {station_in_location}")
            lines.append(f"  * Latitude matches ({eio_meta['latitude']:.2f} vs {manifest_lat:.2f}): {lat_match}")
            lines.append(f"  * Longitude matches ({eio_meta['longitude']:.2f} vs {manifest_lon:.2f}): {lon_match}")
            lines.append(f"  * Elevation matches ({eio_meta['elevation']:.2f} vs {manifest_elev:.2f}): {elev_match}")

            overall_match = wmo_in_location and station_in_location and lat_match and lon_match and elev_match
            lines.append(f"  * OVERALL WEATHER FILE MATCH VERDICT: {'CONFIRMED MATCH' if overall_match else 'MISMATCH'}")
        else:
            lines.append(f"ERROR: eplusout.eio not found in any simulation directory under {temp_dir}!")

        lines.append("=" * 145)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    output_text = "\n".join(lines)
    with open(out_txt_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"Successfully generated {out_txt_path} ({len(output_text)} characters).")

if __name__ == "__main__":
    main()

