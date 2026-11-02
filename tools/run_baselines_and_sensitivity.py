"""
tools/run_baselines_and_sensitivity.py

Comprehensive evaluation under D-035 physics (EPW 0.5m ground temperature):
1. Baselines (R1, R2, R3) for Jodhpur in both free_running and ideal_loads modes.
2. The 3 final verified Pareto designs (R3_009, R3_026, R3_005).
3. Best, median, worst of the 100 verified candidates across O1_ml, O1_adapt, O2, and T_op (median, 95th, max).
4. One-at-a-time (OAT) sensitivity around P_Jodhpur_R3_009 across 8 design variables at Low/Mid/High levels.
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

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
from src.optimize.references import REFERENCE_R1, REFERENCE_R2, REFERENCE_R3_PER_CITY

EPW_PATH = "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw"
MODEL_PATH = "models/champion_comfort_model.joblib"
VERIF_100_PARQUET = "data/processed/active_learning_jodhpur/final_verified_all_100_Jodhpur.parquet"
OUT_REPORT = "reports/evidence/baselines_and_sensitivity_report.txt"
OUT_CSV = "data/processed/baselines_and_sensitivity.csv"
WORK_ROOT = "data/processed/runs_baselines_sensitivity"
MAX_WORKERS = 6

def _sim_worker(task):
    tag = task['tag']
    mode = task['mode']
    params = task['params']
    rdir = task['run_dir']
    epw = task['epw_path']

    os.makedirs(rdir, exist_ok=True)
    idf_path = os.path.join(rdir, "shelter.idf")
    render_shelter_idf(params, idf_path, mode=mode, city="Jodhpur", epw_path=epw)

    res = run_single_simulation(idf_path, epw, rdir)
    if res['status'] != 'SUCCESS':
        time.sleep(0.5)
        res = run_single_simulation(idf_path, epw, rdir)

    hourly_dict = None
    summary_dict = None

    if res['status'] == 'SUCCESS':
        csv_path = os.path.join(rdir, "eplusout.csv")
        if os.path.exists(csv_path):
            try:
                hdf, sm = parse_simulation_csv(csv_path)
                summary_dict = sm
                if mode == 'free_running':
                    hourly_dict = {
                        'ta': hdf['ta'].values.astype(np.float32),
                        'tr': hdf['tr'].values.astype(np.float32),
                        'rh': hdf['rh'].values.astype(np.float32),
                        't_out': hdf['t_out'].values.astype(np.float32)
                    }
            except Exception:
                pass

    return tag, mode, res['status'], summary_dict, hourly_dict

def evaluate_metrics(fr_hourly, il_summary, champ_model):
    ta = fr_hourly['ta']
    tr = fr_hourly['tr']
    rh = fr_hourly['rh']
    tout = fr_hourly['t_out']

    top = (ta + tr) / 2.0
    top_median = float(np.median(top))
    top_95th = float(np.percentile(top, 95))
    top_max = float(np.max(top))

    daily_tout = calculate_daily_mean_series(tout)
    t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
    t_rm_hourly = np.repeat(t_rm_daily, 24)
    clo_hourly = compute_clo_schedule_a004(daily_tout)

    adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
    ml_res = evaluate_ml_champion_comfort(
        model=champ_model,
        ta=ta,
        tr=tr,
        rh=rh,
        t_outdoor_hourly=t_rm_hourly,
        clo_hourly=clo_hourly,
        met=1.1,
        vel=0.15
    )

    o2_val = float(il_summary['o2_energy_kwh_per_m2']) if il_summary else float('nan')

    return {
        'T_op_med': round(top_median, 2),
        'T_op_95th': round(top_95th, 2),
        'T_op_max': round(top_max, 2),
        'O1_ml': round(float(ml_res['O1_ml']), 2),
        'O1_adapt': round(float(adapt_res['O1_adapt']), 2),
        'O2': round(o2_val, 2)
    }

def main():
    print("=" * 80)
    print("BASELINES & ONE-AT-A-TIME SENSITIVITY UNDER D-035 (JODHPUR)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    champ_model = load_champion_model(MODEL_PATH)
    os.makedirs(WORK_ROOT, exist_ok=True)

    # 1. Prepare Baselines
    r1_params = dict(REFERENCE_R1)
    r1_params['city'] = 'Jodhpur'

    r2_params = dict(REFERENCE_R2)
    r2_params['city'] = 'Jodhpur'

    r3_params = dict(REFERENCE_R3_PER_CITY['Jodhpur'])
    r3_params['city'] = 'Jodhpur'

    baseline_configs = {
        'R1_Lightweight': r1_params,
        'R2_Conventional': r2_params,
        'R3_Code_Compliant': r3_params
    }

    # 2. Load 100 Verified Candidates & 3 Verified Pareto Designs
    df_100 = pd.read_parquet(VERIF_100_PARQUET)
    pareto_ids = ['P_Jodhpur_R3_009', 'P_Jodhpur_R3_026', 'P_Jodhpur_R3_005']
    df_pareto = df_100[df_100['pareto_id'].isin(pareto_ids)].copy()

    # 3. Define OAT Sensitivity Grid around P_Jodhpur_R3_009
    r3_009_row = df_100[df_100['pareto_id'] == 'P_Jodhpur_R3_009'].iloc[0]
    base_params = {
        'roof_insulation_thickness': float(r3_009_row['roof_insulation_thickness']),
        'wall_insulation_thickness': float(r3_009_row['wall_insulation_thickness']),
        'wall_mass_class': str(r3_009_row['wall_mass_class']),
        'roof_solar_absorptance': float(r3_009_row['roof_solar_absorptance']),
        'wwr': float(r3_009_row['wwr']),
        'orientation': float(r3_009_row['orientation']),
        'shading_depth': float(r3_009_row['shading_depth']),
        'ventilation_ach': float(r3_009_row['ventilation_ach']),
        'city': 'Jodhpur'
    }

    sensitivity_vars = {
        'roof_insulation_thickness': [0.000, 0.075, 0.150],
        'wall_insulation_thickness': [0.000, 0.075, 0.150],
        'roof_solar_absorptance': [0.30, 0.60, 0.90],
        'wwr': [0.05, 0.20, 0.40],
        'orientation': [0.0, 90.0, 180.0],
        'shading_depth': [0.0, 0.50, 1.00],
        'ventilation_ach': [1.0, 8.0, 15.0],
        'wall_mass_class': ['light', 'medium', 'heavy']
    }

    # Build full simulation task list
    tasks = []

    # Baselines tasks (both modes)
    for b_name, b_p in baseline_configs.items():
        for mode in ['free_running', 'ideal_loads']:
            tasks.append({
                'tag': f"base_{b_name}",
                'mode': mode,
                'params': b_p,
                'run_dir': os.path.join(WORK_ROOT, f"baseline_{b_name}_{mode}"),
                'epw_path': EPW_PATH
            })

    # 100 verified candidates free_running tasks (to compute complete empirical T_op distribution)
    for _, row in df_100.iterrows():
        did = row['pareto_id']
        p = {
            'roof_insulation_thickness': float(row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(row['wall_insulation_thickness']),
            'wall_mass_class': str(row['wall_mass_class']),
            'roof_solar_absorptance': float(row['roof_solar_absorptance']),
            'wwr': float(row['wwr']),
            'orientation': float(row['orientation']),
            'shading_depth': float(row['shading_depth']),
            'ventilation_ach': float(row['ventilation_ach']),
            'city': 'Jodhpur'
        }
        # Run free_running for all 100 candidates to get T_op distribution
        tasks.append({
            'tag': f"cand100_{did}",
            'mode': 'free_running',
            'params': p,
            'run_dir': os.path.join(WORK_ROOT, f"cand_{did}_fr"),
            'epw_path': EPW_PATH
        })

    # Sensitivity tasks (both modes)
    for var_name, levels in sensitivity_vars.items():
        for lvl in levels:
            p = dict(base_params)
            p[var_name] = lvl
            tag = f"sens_{var_name}_{lvl}"
            for mode in ['free_running', 'ideal_loads']:
                tasks.append({
                    'tag': tag,
                    'mode': mode,
                    'params': p,
                    'run_dir': os.path.join(WORK_ROOT, f"{tag}_{mode}"),
                    'epw_path': EPW_PATH
                })

    print(f"Total simulation tasks to execute: {len(tasks)}")
    t0 = time.time()
    results = {}
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_worker, t) for t in tasks]
        for f in as_completed(futures):
            tag, mode, status, sm, h_dict = f.result()
            results[(tag, mode)] = (status, sm, h_dict)

    elapsed = time.time() - t0
    print(f"Executed {len(tasks)} runs in {elapsed:.2f} s ({elapsed/60:.2f} min).")

    # Process Baselines
    baseline_records = []
    for b_name, b_p in baseline_configs.items():
        tag = f"base_{b_name}"
        fr_stat, _, fr_h = results[(tag, 'free_running')]
        il_stat, il_sm, _ = results[(tag, 'ideal_loads')]
        m = evaluate_metrics(fr_h, il_sm, champ_model)
        m['design'] = b_name
        baseline_records.append(m)

    # Process 3 Final Verified Pareto Designs
    pareto_records = []
    for did in pareto_ids:
        tag = f"cand100_{did}"
        _, _, fr_h = results[(tag, 'free_running')]
        # From df_100, we already have exact EnergyPlus verified O2
        row_100 = df_100[df_100['pareto_id'] == did].iloc[0]
        il_sm = {'o2_energy_kwh_per_m2': float(row_100['O2'])}
        m = evaluate_metrics(fr_h, il_sm, champ_model)
        m['design'] = did
        pareto_records.append(m)

    # Process 100 Verified Candidates T_op distribution
    top_meds, top_95ths, top_maxs = [], [], []
    for _, row in df_100.iterrows():
        did = row['pareto_id']
        tag = f"cand100_{did}"
        _, _, fr_h = results[(tag, 'free_running')]
        if fr_h:
            top = (fr_h['ta'] + fr_h['tr']) / 2.0
            top_meds.append(float(np.median(top)))
            top_95ths.append(float(np.percentile(top, 95)))
            top_maxs.append(float(np.max(top)))

    # Compute 100-candidate statistics:
    # O1_ml, O1_adapt, O2 from df_100 (exact EnergyPlus verified)
    # T_op metrics from simulated free_running hourly series
    cand100_summary = {
        'best': {
            'design': '100_Candidates_Best (Min)',
            'O1_ml': round(float(df_100['O1_ml'].min()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].min()), 2),
            'O2': round(float(df_100['O2'].min()), 2),
            'T_op_med': round(float(np.min(top_meds)), 2),
            'T_op_95th': round(float(np.min(top_95ths)), 2),
            'T_op_max': round(float(np.min(top_maxs)), 2)
        },
        'median': {
            'design': '100_Candidates_Median',
            'O1_ml': round(float(df_100['O1_ml'].median()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].median()), 2),
            'O2': round(float(df_100['O2'].median()), 2),
            'T_op_med': round(float(np.median(top_meds)), 2),
            'T_op_95th': round(float(np.median(top_95ths)), 2),
            'T_op_max': round(float(np.median(top_maxs)), 2)
        },
        'worst': {
            'design': '100_Candidates_Worst (Max)',
            'O1_ml': round(float(df_100['O1_ml'].max()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].max()), 2),
            'O2': round(float(df_100['O2'].max()), 2),
            'T_op_med': round(float(np.max(top_meds)), 2),
            'T_op_95th': round(float(np.max(top_95ths)), 2),
            'T_op_max': round(float(np.max(top_maxs)), 2)
        }
    }

    # Process Sensitivity Grid
    sens_records = []
    for var_name, levels in sensitivity_vars.items():
        for lvl in levels:
            tag = f"sens_{var_name}_{lvl}"
            fr_stat, _, fr_h = results[(tag, 'free_running')]
            il_stat, il_sm, _ = results[(tag, 'ideal_loads')]
            m = evaluate_metrics(fr_h, il_sm, champ_model)
            sens_records.append({
                'variable': var_name,
                'level': str(lvl),
                'O1_ml': m['O1_ml'],
                'O1_adapt': m['O1_adapt'],
                'O2': m['O2'],
                'T_op_med': m['T_op_med'],
                'T_op_95th': m['T_op_95th'],
                'T_op_max': m['T_op_max']
            })

    df_sens = pd.DataFrame(sens_records)
    df_sens.to_csv(OUT_CSV, index=False)

    # Sensitivity range analysis to detect near-zero effects
    var_ranges = []
    for var_name in sensitivity_vars.keys():
        sub = df_sens[df_sens['variable'] == var_name]
        d_o1_ml = sub['O1_ml'].max() - sub['O1_ml'].min()
        d_o1_ad = sub['O1_adapt'].max() - sub['O1_adapt'].min()
        d_o2 = sub['O2'].max() - sub['O2'].min()
        d_top_med = sub['T_op_med'].max() - sub['T_op_med'].min()
        d_top_max = sub['T_op_max'].max() - sub['T_op_max'].min()
        is_near_zero = (d_o1_ml < 0.5) and (d_o1_ad < 0.5) and (d_o2 < 1.0)
        var_ranges.append({
            'variable': var_name,
            'delta_O1_ml': round(d_o1_ml, 2),
            'delta_O1_adapt': round(d_o1_ad, 2),
            'delta_O2': round(d_o2, 2),
            'delta_T_op_med': round(d_top_med, 2),
            'delta_T_op_max': round(d_top_max, 2),
            'near_zero_flag': 'NEAR-ZERO' if is_near_zero else 'SENSITIVE'
        })
    df_ranges = pd.DataFrame(var_ranges)

    # Format text report
    lines = []
    lines.append("=" * 100)
    lines.append("BASELINES AND ONE-AT-A-TIME SENSITIVITY REPORT (JODHPUR, D-035 PHYSICS)")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")
    lines.append("TABLE 1: BASELINES (R1/R2/R3) vs 3 FINAL VERIFIED PARETO vs 100 CANDIDATES (BEST/MEDIAN/WORST)")
    lines.append("-" * 100)
    lines.append(f"{'Design / Benchmark':<32} {'O1_ml (%)':<11} {'O1_ad (%)':<11} {'O2 (kWh/m2)':<13} {'Top Med (C)':<13} {'Top 95th (C)':<13} {'Top Max (C)':<13}")
    lines.append("-" * 100)
    for b in baseline_records:
        lines.append(f"{b['design']:<32} {b['O1_ml']:<11.2f} {b['O1_adapt']:<11.2f} {b['O2']:<13.2f} {b['T_op_med']:<13.2f} {b['T_op_95th']:<13.2f} {b['T_op_max']:<13.2f}")
    lines.append("-" * 100)
    for p in pareto_records:
        lines.append(f"{p['design']:<32} {p['O1_ml']:<11.2f} {p['O1_adapt']:<11.2f} {p['O2']:<13.2f} {p['T_op_med']:<13.2f} {p['T_op_95th']:<13.2f} {p['T_op_max']:<13.2f}")
    lines.append("-" * 100)
    lines.append(f"{cand100_summary['best']['design']:<32} {cand100_summary['best']['O1_ml']:<11.2f} {cand100_summary['best']['O1_adapt']:<11.2f} {cand100_summary['best']['O2']:<13.2f} {cand100_summary['best']['T_op_med']:<13.2f} {cand100_summary['best']['T_op_95th']:<13.2f} {cand100_summary['best']['T_op_max']:<13.2f}")
    lines.append(f"{cand100_summary['median']['design']:<32} {cand100_summary['median']['O1_ml']:<11.2f} {cand100_summary['median']['O1_adapt']:<11.2f} {cand100_summary['median']['O2']:<13.2f} {cand100_summary['median']['T_op_med']:<13.2f} {cand100_summary['median']['T_op_95th']:<13.2f} {cand100_summary['median']['T_op_max']:<13.2f}")
    lines.append(f"{cand100_summary['worst']['design']:<32} {cand100_summary['worst']['O1_ml']:<11.2f} {cand100_summary['worst']['O1_adapt']:<11.2f} {cand100_summary['worst']['O2']:<13.2f} {cand100_summary['worst']['T_op_med']:<13.2f} {cand100_summary['worst']['T_op_95th']:<13.2f} {cand100_summary['worst']['T_op_max']:<13.2f}")
    lines.append("-" * 100)
    lines.append("")
    lines.append("TABLE 2: ONE-AT-A-TIME SENSITIVITY AROUND P_Jodhpur_R3_009")
    lines.append("-" * 100)
    lines.append(f"{'Variable':<28} {'Level':<10} {'O1_ml (%)':<11} {'O1_ad (%)':<11} {'O2 (kWh/m2)':<13} {'Top Med (C)':<13} {'Top 95th (C)':<13} {'Top Max (C)':<13}")
    lines.append("-" * 100)
    for _, r in df_sens.iterrows():
        lines.append(f"{r['variable']:<28} {r['level']:<10} {r['O1_ml']:<11.2f} {r['O1_adapt']:<11.2f} {r['O2']:<13.2f} {r['T_op_med']:<13.2f} {r['T_op_95th']:<13.2f} {r['T_op_max']:<13.2f}")
    lines.append("-" * 100)
    lines.append("")
    lines.append("TABLE 3: SENSITIVITY SPAN & NEAR-ZERO EFFECT SCREENING")
    lines.append("-" * 100)
    lines.append(f"{'Variable':<28} {'Delta O1_ml':<13} {'Delta O1_ad':<13} {'Delta O2':<13} {'Delta TopMed':<14} {'Status':<12}")
    lines.append("-" * 100)
    for _, r in df_ranges.iterrows():
        lines.append(f"{r['variable']:<28} {r['delta_O1_ml']:<13.2f} {r['delta_O1_adapt']:<13.2f} {r['delta_O2']:<13.2f} {r['delta_T_op_med']:<14.2f} {r['near_zero_flag']:<12}")
    lines.append("-" * 100)

    report_content = "\n".join(lines)
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"\nReport written to {OUT_REPORT}")
    print("\n" + report_content)

if __name__ == '__main__':
    main()
