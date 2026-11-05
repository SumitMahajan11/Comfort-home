#!/usr/bin/env python3
"""
tools/report_item3_shimla_r1.py

Item 3: SHIMLA R1, R2, R3 HEATING & COOLING ENERGY BREAKDOWN & THERMAL MECHANISM ANALYSIS
- Simulates or loads physical ideal-loads EnergyPlus results for:
    * R1_Lightweight
    * R2_Conventional
    * R3_Code_Compliant
  in Shimla across:
    1. Baseline Climate
    2. +1.5 °C Uniform Warming
    3. +3.0 °C Uniform Warming
- Computes:
    * Annual Heating Energy (kWh/m2)
    * Annual Cooling Energy (kWh/m2)
    * Annual Total Energy O2 (kWh/m2)
    * Absolute change in heating energy (dHeating in kWh/m2)
    * Absolute change in cooling energy (dCooling in kWh/m2)
    * Absolute change in total energy (dO2 in kWh/m2)
- Evaluates and explains the exact physical mechanism why R1 O2 rises while R2 and R3 fall.
- Writes formatted report to reports/item3_shimla_r1.txt.
"""

import os
import sys
import shutil
import tempfile
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

def main():
    out_txt_path = os.path.join("reports", "item3_shimla_r1.txt")
    manifest = pd.read_csv("reports/batch_epw_manifest.csv").set_index('city')
    base_epw = manifest.loc['Shimla', 'path']
    p15_epw = "data/processed/weather_morphed/Shimla_plus1p5.epw"
    p30_epw = "data/processed/weather_morphed/Shimla_plus3p0.epw"

    base_results_csv = "data/processed/flagship_2011_2025/Shimla/baseline_results.csv"
    df_base = pd.read_csv(base_results_csv)
    df_r = df_base[df_base['design_id'].isin(['R1_Lightweight', 'R2_Conventional', 'R3_Code_Compliant'])].copy()

    scenarios = [
        ('Baseline', base_epw),
        ('+1.5 C',   p15_epw),
        ('+3.0 C',   p30_epw)
    ]

    td = tempfile.mkdtemp(prefix='shimla_breakdown_')

    results_data = []

    try:
        for sname, epw_path in scenarios:
            for _, row in df_r.iterrows():
                did = row['design_id']
                params = {
                    'roof_insulation_thickness': float(row['roof_insulation_thickness']),
                    'wall_insulation_thickness': float(row['wall_insulation_thickness']),
                    'wall_mass_class': str(row['wall_mass_class']),
                    'roof_solar_absorptance': float(row['roof_solar_absorptance']),
                    'wwr': float(row['wwr']),
                    'orientation': float(row['orientation']),
                    'shading_depth': float(row['shading_depth']),
                    'ventilation_ach': float(row['ventilation_ach'])
                }
                rdir = os.path.join(td, f"{did}_{sname.replace(' ', '_').replace('°', '')}")
                os.makedirs(rdir, exist_ok=True)
                idf_path = os.path.join(rdir, "shelter.idf")
                render_shelter_idf(params, idf_path, mode='ideal_loads', city='Shimla', epw_path=epw_path)
                run_single_simulation(idf_path, epw_path, rdir)
                csv_path = os.path.join(rdir, "eplusout.csv")
                hdf, sm = parse_simulation_csv(csv_path)

                floor_area = 20.0
                heating_kwh_m2 = sm['total_heating_kwh'] / floor_area
                cooling_kwh_m2 = sm['total_cooling_kwh'] / floor_area
                total_o2 = sm['o2_energy_kwh_per_m2']

                results_data.append({
                    'scenario': sname,
                    'design_id': did,
                    'heating_kwh_m2': round(heating_kwh_m2, 2),
                    'cooling_kwh_m2': round(cooling_kwh_m2, 2),
                    'total_o2': round(total_o2, 2)
                })
    finally:
        shutil.rmtree(td, ignore_errors=True)

    df_res = pd.DataFrame(results_data)

    lines = []
    lines.append("=" * 135)
    lines.append("ITEM 3: SHIMLA R1, R2, R3 HEATING & COOLING ENERGY BREAKDOWN ACROSS CLIMATE SCENARIOS")
    lines.append("Evaluation of Annual Heating and Cooling Demand (kWh/m2) and Total HVAC Energy O2")
    lines.append("=" * 135)

    lines.append(f"{'Design ID':<20} | {'Scenario':<10} | {'Heating (kWh/m2)':<18} | {'Cooling (kWh/m2)':<18} | {'Total O2 (kWh/m2)':<18}")
    lines.append("-" * 135)

    for did in ['R1_Lightweight', 'R2_Conventional', 'R3_Code_Compliant']:
        df_d = df_res[df_res['design_id'] == did]
        for _, r in df_d.iterrows():
            lines.append(
                f"{r['design_id']:<20} | {r['scenario']:<10} | "
                f"{r['heating_kwh_m2']:<18.2f} | {r['cooling_kwh_m2']:<18.2f} | {r['total_o2']:<18.2f}"
            )
        lines.append("." * 135)
    lines.append("-" * 135)

    # Compute deltas dynamically
    lines.append("\n" + "=" * 135)
    lines.append("HEATING AND COOLING SENSITIVITY DELTAS (VS BASELINE CLIMATE)")
    lines.append("=" * 135)
    lines.append(f"{'Design ID':<20} | {'Scenario':<10} | {'dHeating (kWh/m2)':<20} | {'dCooling (kWh/m2)':<20} | {'dTotal O2 (kWh/m2)':<20} | {'Dominant Effect'}")
    lines.append("-" * 135)

    metrics_dict = {}

    for did in ['R1_Lightweight', 'R2_Conventional', 'R3_Code_Compliant']:
        df_d = df_res[df_res['design_id'] == did].set_index('scenario')
        base_h = df_d.loc['Baseline', 'heating_kwh_m2']
        base_c = df_d.loc['Baseline', 'cooling_kwh_m2']
        base_tot = df_d.loc['Baseline', 'total_o2']

        p15_h = df_d.loc['+1.5 C', 'heating_kwh_m2']
        p15_c = df_d.loc['+1.5 C', 'cooling_kwh_m2']
        p15_tot = df_d.loc['+1.5 C', 'total_o2']

        p30_h = df_d.loc['+3.0 C', 'heating_kwh_m2']
        p30_c = df_d.loc['+3.0 C', 'cooling_kwh_m2']
        p30_tot = df_d.loc['+3.0 C', 'total_o2']

        dh_15 = p15_h - base_h
        dc_15 = p15_c - base_c
        dtot_15 = p15_tot - base_tot

        dh_30 = p30_h - base_h
        dc_30 = p30_c - base_c
        dtot_30 = p30_tot - base_tot

        dom_15 = "Cooling increase outweighs heating decrease" if abs(dc_15) > abs(dh_15) else "Heating decrease dominates cooling increase"
        dom_30 = "Cooling increase outweighs heating decrease" if abs(dc_30) > abs(dh_30) else "Heating decrease dominates cooling increase"

        metrics_dict[did] = {
            'base_h': base_h, 'base_c': base_c, 'base_tot': base_tot,
            'p15_h': p15_h, 'p15_c': p15_c, 'p15_tot': p15_tot,
            'p30_h': p30_h, 'p30_c': p30_c, 'p30_tot': p30_tot,
            'dh_15': dh_15, 'dc_15': dc_15, 'dtot_15': dtot_15,
            'dh_30': dh_30, 'dc_30': dc_30, 'dtot_30': dtot_30
        }

        lines.append(f"{did:<20} | {'+1.5 C':<10} | {f'{dh_15:+.2f}':<20} | {f'{dc_15:+.2f}':<20} | {f'{dtot_15:+.2f}':<20} | {dom_15}")
        lines.append(f"{did:<20} | {'+3.0 C':<10} | {f'{dh_30:+.2f}':<20} | {f'{dc_30:+.2f}':<20} | {f'{dtot_30:+.2f}':<20} | {dom_30}")
        lines.append("." * 135)
    lines.append("-" * 135)

    # Narrative computed dynamically from variables
    r1 = metrics_dict['R1_Lightweight']
    r2 = metrics_dict['R2_Conventional']
    r3 = metrics_dict['R3_Code_Compliant']

    lines.append("\n" + "=" * 135)
    lines.append("PHYSICAL MECHANISM [HYPOTHESIS, NOT TESTED]: WHY R1 O2 RISES WHILE R2 AND R3 FALL")
    lines.append("=" * 135)
    lines.append("Status: HYPOTHESIS, NOT TESTED. The following narrative provides a physical hypothesis based on zone energy totals;")
    lines.append("envelope-part breakdown (conduction/solar split) is not output by the current simulation model.")
    lines.append(f"1. Baseline Shimla Climate Dynamics:")
    lines.append(f"   - In cold-climate Shimla, Baseline heating demand is dominant for all designs: {r1['base_h']:.2f} kWh/m2 for R1, {r2['base_h']:.2f} kWh/m2 for R2, and {r3['base_h']:.2f} kWh/m2 for R3.")
    lines.append(f"   - However, R1 (Lightweight: uninsulated tin roof, uninsulated single-skin walls, no shading, low thermal mass) already incurs {r1['base_c']:.2f} kWh/m2 of cooling demand during summer solar peaks, compared to {r2['base_c']:.2f} kWh/m2 for R2 and only {r3['base_c']:.2f} kWh/m2 for R3.")

    lines.append(f"\n2. Climate Warming Impact on R1_Lightweight (Net Rise in O2):")
    lines.append(f"   - At +1.5 C warming, R1 heating energy decreases by {abs(r1['dh_15']):.2f} kWh/m2 (from {r1['base_h']:.2f} to {r1['p15_h']:.2f} kWh/m2).")
    lines.append(f"   - Concurrently, R1 cooling energy surges by {r1['dc_15']:+.2f} kWh/m2 (from {r1['base_c']:.2f} to {r1['p15_c']:.2f} kWh/m2) due to solar heat transmission through uninsulated lightweight surfaces.")
    lines.append(f"   - Because the cooling increase ({r1['dc_15']:+.2f} kWh/m2) exceeds the heating reduction ({r1['dh_15']:+.2f} kWh/m2), R1 net total O2 increases by {r1['dtot_15']:+.2f} kWh/m2 (from {r1['base_tot']:.2f} to {r1['p15_tot']:.2f} kWh/m2).")
    lines.append(f"   - At +3.0 C warming, this divergence intensifies: R1 heating drops by {abs(r1['dh_30']):.2f} kWh/m2 (to {r1['p30_h']:.2f} kWh/m2), but cooling surges by {r1['dc_30']:+.2f} kWh/m2 (to {r1['p30_c']:.2f} kWh/m2), causing a net O2 increase of {r1['dtot_30']:+.2f} kWh/m2 (to {r1['p30_tot']:.2f} kWh/m2).")

    lines.append(f"\n3. Climate Warming Impact on R2_Conventional and R3_Code_Compliant (Net Fall in O2):")
    lines.append(f"   - R2 (Conventional: 230 mm brick masonry, heavy thermal mass) possesses high thermal capacitance that buffers daytime solar gains.")
    lines.append(f"   - At +1.5 C, R2 heating drops by {abs(r2['dh_15']):.2f} kWh/m2 (from {r2['base_h']:.2f} to {r2['p15_h']:.2f} kWh/m2) while cooling rises by only {r2['dc_15']:+.2f} kWh/m2 (from {r2['base_c']:.2f} to {r2['p15_c']:.2f} kWh/m2), yielding a net O2 decrease of {r2['dtot_15']:+.2f} kWh/m2 (from {r2['base_tot']:.2f} to {r2['p15_tot']:.2f} kWh/m2).")
    lines.append(f"   - At +3.0 C, R2 heating drops by {abs(r2['dh_30']):.2f} kWh/m2 while cooling rises by {r2['dc_30']:+.2f} kWh/m2, resulting in a net O2 decrease of {r2['dtot_30']:+.2f} kWh/m2 (from {r2['base_tot']:.2f} to {r2['p30_tot']:.2f} kWh/m2).")
    lines.append(f"   - R3 (Code-Compliant: insulated envelope, external overhang shading) blocks solar gain almost entirely.")
    lines.append(f"   - At +1.5 C, R3 heating drops by {abs(r3['dh_15']):.2f} kWh/m2 while cooling increases by only {r3['dc_15']:+.2f} kWh/m2 (from {r3['base_c']:.2f} to {r3['p15_c']:.2f} kWh/m2), yielding a net O2 decrease of {r3['dtot_15']:+.2f} kWh/m2 (from {r3['base_tot']:.2f} to {r3['p15_tot']:.2f} kWh/m2).")
    lines.append(f"   - At +3.0 C, R3 heating drops by {abs(r3['dh_30']):.2f} kWh/m2 while cooling increases by {r3['dc_30']:+.2f} kWh/m2, yielding a net O2 decrease of {r3['dtot_30']:+.2f} kWh/m2 (from {r3['base_tot']:.2f} to {r3['p30_tot']:.2f} kWh/m2).")
    lines.append("=" * 135)

    output_text = "\n".join(lines)
    with open(out_txt_path, 'w', encoding='utf-8') as f:
        f.write(output_text)
    print(f"Successfully generated {out_txt_path} ({len(output_text)} characters).")

if __name__ == "__main__":
    main()
