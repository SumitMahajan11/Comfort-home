"""
tools/check_p004_reproduction.py

Runs P_Jodhpur_004 (from pilot_jodhpur_ground18) through the real pipeline renderer
with 18 C ground forced, and checks reproduction of:
O1_ml: 1.12%, O1_adapt: 84.61%, O2: 2.65 kWh/m2
"""

import os
import sys
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv
from src.optimize.coupling import (
    calculate_daily_mean_series,
    compute_running_mean_outdoor_temperature_db2,
    compute_clo_schedule_a004,
    evaluate_adaptive_90_comfort,
    evaluate_ml_champion_comfort,
    load_champion_model
)

def main():
    df = pd.read_csv('data/processed/pilot_jodhpur_ground18/verification_Jodhpur.csv')
    p004_row = df[df['pareto_id'] == 'P_Jodhpur_004'].iloc[0]
    params = p004_row.to_dict()
    print("P_Jodhpur_004 params:")
    cols = ['roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class', 
            'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach']
    for c in cols:
        print(f"  {c}: {params[c]}")

    epw_path = 'data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw'
    champ_model = load_champion_model('models/champion_comfort_model.joblib')

    work_dir_fr = 'data/processed/pjodhpur004_reproduce/fr'
    work_dir_il = 'data/processed/pjodhpur004_reproduce/il'
    os.makedirs(work_dir_fr, exist_ok=True)
    os.makedirs(work_dir_il, exist_ok=True)

    # Free running with 18.0 C fallback forced
    idf_fr = os.path.join(work_dir_fr, 'shelter.idf')
    render_shelter_idf(params, idf_fr, mode='free_running', city='NonExistentCity_Forced18')
    res_fr = run_single_simulation(idf_fr, epw_path, work_dir_fr)
    hdf, _ = parse_simulation_csv(os.path.join(work_dir_fr, 'eplusout.csv'))

    # Ideal loads with 18.0 C fallback forced
    idf_il = os.path.join(work_dir_il, 'shelter.idf')
    render_shelter_idf(params, idf_il, mode='ideal_loads', city='NonExistentCity_Forced18')
    res_il = run_single_simulation(idf_il, epw_path, work_dir_il)
    _, sm_il = parse_simulation_csv(os.path.join(work_dir_il, 'eplusout.csv'))

    ta = hdf['ta'].values.astype(np.float32)
    tr = hdf['tr'].values.astype(np.float32)
    rh = hdf['rh'].values.astype(np.float32)
    tout = hdf['t_out'].values.astype(np.float32)
    top = (ta + tr) / 2.0

    daily_tout = calculate_daily_mean_series(tout)
    t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    clo_hourly = compute_clo_schedule_a004(daily_tout)

    adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
    ml_res = evaluate_ml_champion_comfort(
        model=champ_model, ta=ta, tr=tr, rh=rh,
        t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
        met=1.1, vel=0.15
    )
    o2_val = float(sm_il['o2_energy_kwh_per_m2'])

    print("\nREPRODUCED RESULTS FOR P_Jodhpur_004 with 18 C ground forced through REAL pipeline renderer:")
    print(f"T_op median: {np.median(top):.2f} °C")
    print(f"T_op 95th:   {np.percentile(top, 95):.2f} °C")
    print(f"T_op max:    {np.max(top):.2f} °C")
    print(f"O1_ml:       {ml_res['O1_ml']:.2f}% (Expected Old Verified: 1.12%)")
    print(f"O1_adapt:    {adapt_res['O1_adapt']:.2f}% (Expected Old Verified: 84.61%)")
    print(f"O2:          {o2_val:.2f} kWh/m2 (Expected Old Verified: 2.65 kWh/m2)")

if __name__ == '__main__':
    main()
