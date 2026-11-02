"""
tools/task5_bounds.py
Executes TASK 5: REDO BOUNDS TABLE WITH COMBINED THRESHOLD (# LOW + # UP >= 20 OF 30)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import pandas as pd
import numpy as np
from src.sim.sampler import DESIGN_VARIABLE_RANGES

PARETO_CSV = "data/processed/active_learning_leh/final_verified_pareto_Leh.csv"

def main():
    print("=" * 125)
    print("TASK 5 - REVISED BOUNDS TABLE (# IN LOWER ZONE + # IN UPPER ZONE >= 20 OF 30)")
    print("=" * 125)
    
    df = pd.read_csv(PARETO_CSV)
    n_designs = len(df)
    print(f"\nEvaluating {n_designs} verified non-dominated Pareto front designs for Leh ({PARETO_CSV}).")
    print("Tolerance: 5% of parameter span on lower bound and upper bound.")
    print("Criterion: Mark 'AT BOUND' if (# in lower zone + # in upper zone) >= 20 of 30 designs (>= 66.7%).\n")
    
    var_cols = {
        'roof_insulation_thickness': 'roof_insulation_thickness_y',
        'wall_insulation_thickness': 'wall_insulation_thickness_y',
        'roof_solar_absorptance': 'roof_solar_absorptance_y',
        'wwr': 'wwr_y',
        'orientation': 'orientation_y',
        'shading_depth': 'shading_depth_y',
        'ventilation_ach': 'ventilation_ach_y'
    }
    
    header = f"{'Design Variable':<28} | {'Lower':<7} | {'Upper':<7} | {'Span':<7} | {'5% Span':<8} | {'Low Zone':<16} | {'Up Zone':<16} | {'# Low':<6} | {'# Up':<6} | {'Total Bound':<11} | {'Status':<12}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    
    for var, col in var_cols.items():
        low_b, up_b = DESIGN_VARIABLE_RANGES[var]
        span = up_b - low_b
        tol = 0.05 * span
        
        low_thresh = low_b + tol
        up_thresh = up_b - tol
        
        vals = df[col].values
        n_low = int(np.sum(vals <= low_thresh + 1e-6))
        n_up = int(np.sum(vals >= up_thresh - 1e-6))
        n_tot = n_low + n_up
        
        at_bound = (n_tot >= 20)
        status = "AT BOUND" if at_bound else "INTERIOR"
        
        low_zone_str = f"[{low_b:.3f}, {low_thresh:.3f}]"
        up_zone_str = f"[{up_thresh:.3f}, {up_b:.3f}]"
        
        print(f"{var:<28} | {low_b:<7.3f} | {up_b:<7.3f} | {span:<7.3f} | {tol:<8.4f} | {low_zone_str:<16} | {up_zone_str:<16} | {n_low:<6} | {n_up:<6} | {n_tot:<11} | {status:<12}")
        
    # Discrete wall_mass_class
    counts = df['wall_mass_class_y'].value_counts()
    n_light = counts.get('light', 0)
    n_med = counts.get('medium', 0)
    n_hvy = counts.get('heavy', 0)
    n_tot_mass = n_light + n_hvy
    status_mass = "AT BOUND" if n_tot_mass >= 20 else "INTERIOR"
    print(f"{'wall_mass_class (discrete)':<28} | {'light':<7} | {'heavy':<7} | {'3 cls':<7} | {'N/A':<8} | {'light: ' + str(n_light):<16} | {'heavy: ' + str(n_hvy):<16} | {n_light:<6} | {n_hvy:<6} | {n_tot_mass:<11} | {status_mass:<12}")
    print(sep)
    
    # Also print the 30 front designs table
    print("\nLEH 30 VERIFIED PARETO FRONT DESIGNS TABLE:")
    print("Valid Adaptive Hours: 1224 (13.97%) | Invalid Hours: 7536 (86.03%)")
    p_header = f"{'Design ID':<15} | {'O1_ml (%)':<10} | {'O1_adapt (%)':<12} | {'Valid Adapt (h)':<15} | {'Invalid Share (%)':<17} | {'O2 (kWh/m2)':<12} | {'RoofIns':<8} | {'WallIns':<8} | {'Mass':<7} | {'Absorp':<7} | {'WWR':<7} | {'ACH':<6}"
    p_sep = "-" * len(p_header)
    print(p_sep)
    print(p_header)
    print(p_sep)
    for _, r in df.iterrows():
        did = r['design_id']
        o1_ml = r['O1_ml']
        o1_ad = r['O1_adapt']
        valid_hrs = 1224
        inv_share = r['invalid_share_adapt'] if 'invalid_share_adapt' in r and pd.notnull(r['invalid_share_adapt']) else 86.03
        o2 = r['O2']
        roof_i = r['roof_insulation_thickness_y']
        wall_i = r['wall_insulation_thickness_y']
        mass = r['wall_mass_class_y']
        absrp = r['roof_solar_absorptance_y']
        wwr = r['wwr_y']
        ach = r['ventilation_ach_y']
        print(f"{did:<15} | {o1_ml:<10.2f} | {o1_ad:<12.2f} | {valid_hrs:<15} | {inv_share:<17.2f} | {o2:<12.2f} | {roof_i:<8.3f} | {wall_i:<8.3f} | {mass:<7} | {absrp:<7.4f} | {wwr:<7.4f} | {ach:<6.2f}")
    print(p_sep)

if __name__ == '__main__':
    main()
