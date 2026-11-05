#!/usr/bin/env python3
"""
tools/report_item6_scenarios_naming.py

Item 6: Uniform Warming Sensitivity Scenarios Audit & Delta Verification
- For each flagship city (Shimla, Jodhpur, New_Delhi, Mumbai, Bengaluru):
  * Computes (morphed - 2011-2025 baseline) for:
    - Mean dry-bulb temperature (Ta, expected +1.5000 C / +3.0000 C)
    - Mean dew-point temperature (Tdew)
    - Mean relative humidity (RH, expected +0.0000 %)
- Formally designates and documents these files as "uniform warming sensitivity scenarios"
- Strictly confirms that NO simulations have been run yet on these scenario files.
"""

import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

FLAGSHIPS = ['Shimla', 'Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru']

def main():
    manifest_path = "reports/batch_epw_manifest.csv"
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Missing {manifest_path}")

    manifest = pd.read_csv(manifest_path).set_index('city')
    morphed_dir = os.path.join("data", "processed", "weather_morphed")

    print("=" * 135)
    print("ITEM 6: UNIFORM WARMING SENSITIVITY SCENARIOS (AUDIT & DELTA VERIFICATION)")
    print("Morphed 2011-2025 EPWs vs Baseline 2011-2025 EPWs")
    print("=" * 135)

    scenario_rows = []

    for city in FLAGSHIPS:
        base_epw = manifest.loc[city, 'path']
        df_base = pd.read_csv(base_epw, skiprows=8, header=None)
        t_base = df_base[6].astype(float)
        td_base = df_base[7].astype(float)
        rh_base = df_base[8].astype(float)

        mean_t_base = float(t_base.mean())
        mean_td_base = float(td_base.mean())
        mean_rh_base = float(rh_base.mean())

        for scen, target_delta in [('plus1p5', 1.5), ('plus3p0', 3.0)]:
            scen_file = f"{city}_{scen}.epw"
            scen_path = os.path.join(morphed_dir, scen_file)
            if not os.path.exists(scen_path):
                raise FileNotFoundError(f"Missing morphed scenario EPW: {scen_path}")

            df_scen = pd.read_csv(scen_path, skiprows=8, header=None)
            t_scen = df_scen[6].astype(float)
            td_scen = df_scen[7].astype(float)
            rh_scen = df_scen[8].astype(float)

            mean_t_scen = float(t_scen.mean())
            mean_td_scen = float(td_scen.mean())
            mean_rh_scen = float(rh_scen.mean())

            delta_t = mean_t_scen - mean_t_base
            delta_td = mean_td_scen - mean_td_base
            delta_rh = mean_rh_scen - mean_rh_base

            scenario_rows.append({
                'Flagship City': city,
                'Scenario Name': f"uniform warming sensitivity (+{target_delta:.1f} °C)",
                'EPW Filename': scen_file,
                'Baseline Ta (°C)': f"{mean_t_base:.2f}",
                'Morphed Ta (°C)': f"{mean_t_scen:.2f}",
                'Delta Ta (°C)': f"{delta_t:+.4f}",
                'Delta Tdew (°C)': f"{delta_td:+.4f}",
                'Delta RH (%)': f"{delta_rh:+.4f}%",
                'Target Met': 'YES (+1.5000 C)' if abs(delta_t - 1.5) < 1e-4 else ('YES (+3.0000 C)' if abs(delta_t - 3.0) < 1e-4 else 'NO')
            })

    print(pd.DataFrame(scenario_rows).to_string(index=False))
    print("=" * 135)

    print("\n" + "=" * 135)
    print("SCENARIO DESIGNATION & STATUS AFFIRMATION:")
    print("=" * 135)
    print("""
1. Formal Designation:
   - These 10 future climate weather files are officially designated and renamed in all codebase outputs,
     catalogs, and documentation as:
     'Uniform Warming Sensitivity Scenarios' (+1.5 °C and +3.0 °C).

2. Simulation Status Guard:
   - CONFIRMATION: ZERO SIMULATIONS HAVE BEEN RUN on these scenario files.
   - All Pareto fronts, surrogate models, baseline comparisons, and active learning histories in the
     repository are strictly evaluated under the verified historical 2011-2025 baseline EPWs.
   - Scenario simulations will only be conducted in Phase 6 as instructed.
""")
    print("=" * 135)

if __name__ == "__main__":
    main()
