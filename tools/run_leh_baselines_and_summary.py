"""
tools/run_leh_baselines_and_summary.py

Post-run evaluation and synthesis for LEH under Decision D-035:
1. Simulates R1, R2, R3 baselines for Leh in both modes (free_running + ideal_loads).
2. Simulates the 100 verified candidate designs in free_running mode to compute complete empirical T_op distribution
   and safety metrics (hours Top < 5 C and > 35 C).
3. Generates by code and prints:
   - Table 1: Baselines R1/R2/R3 vs final verified Pareto front vs 100 candidates (best/median/worst),
     including safety metrics (hours Top < 5 C and > 35 C).
   - Table 2: Per-round mean and max surrogate errors reported as absolute AND as % of median O2.
   - Table 3: Final non-dominated Pareto front under verified physical objectives only.
   - Table 4: Bound positioning analysis for the best designs relative to their bounds (flagging any at a bound).
4. Outputs all tables to reports/evidence/leh_summary_report.txt and data/processed/active_learning_leh/leh_baselines_summary.csv.
"""

import os
import sys
import time
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

STATION_NAME = "Leh"
EPW_PATH = "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
ACTIVE_DIR = "data/processed/active_learning_leh"
SUMMARY_REPORT = "reports/evidence/leh_summary_report.txt"
SUMMARY_CSV = "data/processed/active_learning_leh/leh_baselines_summary.csv"
WORK_ROOT = "data/processed/runs_leh_summary"
MAX_WORKERS = 6

BOUNDS = {
    'roof_insulation_thickness': (0.0, 0.150),
    'wall_insulation_thickness': (0.0, 0.150),
    'roof_solar_absorptance': (0.30, 0.90),
    'wwr': (0.05, 0.40),
    'orientation': (0.0, 359.0),
    'shading_depth': (0.30, 1.00),
    'ventilation_ach': (1.00, 15.00)
}

def _sim_worker(task):
    tag = task['tag']
    mode = task['mode']
    params = task['params']
    rdir = task['run_dir']
    epw = task['epw_path']

    os.makedirs(rdir, exist_ok=True)
    idf_path = os.path.join(rdir, "shelter.idf")
    render_shelter_idf(params, idf_path, mode=mode, city=STATION_NAME, epw_path=epw)

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

    if os.path.exists(rdir):
        for f in os.listdir(rdir):
            if f not in ["eplusout.err", "shelter.idf"]:
                fp = os.path.join(rdir, f)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                    elif os.path.isdir(fp):
                        shutil.rmtree(fp, ignore_errors=True)
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

    hours_lt_5 = int(np.sum(top < 5.0))
    hours_gt_35 = int(np.sum(top > 35.0))

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
        'T_op_lt_5': hours_lt_5,
        'T_op_gt_35': hours_gt_35,
        'O1_ml': round(float(ml_res['O1_ml']), 2),
        'O1_adapt': round(float(adapt_res['O1_adapt']), 2),
        'O2': round(o2_val, 2)
    }

def analyze_variable_bound_position(val, var_name, tol=1e-3):
    lb, ub = BOUNDS[var_name]
    if abs(val - lb) <= tol:
        return f"{val:.3f} [AT LOWER BOUND {lb:.3f}]"
    elif abs(val - ub) <= tol:
        return f"{val:.3f} [AT UPPER BOUND {ub:.3f}]"
    else:
        pct = (val - lb) / (ub - lb) * 100.0
        return f"{val:.3f} (Interior, {pct:.1f}% span)"

def main():
    champ_model = load_champion_model()
    os.makedirs(WORK_ROOT, exist_ok=True)

    r1_p = dict(REFERENCE_R1)
    r1_p['city'] = STATION_NAME
    r2_p = dict(REFERENCE_R2)
    r2_p['city'] = STATION_NAME
    r3_p = dict(REFERENCE_R3_PER_CITY[STATION_NAME])
    r3_p['city'] = STATION_NAME

    baseline_configs = {
        'R1_Lightweight': r1_p,
        'R2_Conventional': r2_p,
        'R3_Code_Compliant': r3_p
    }

    df_100_path = os.path.join(ACTIVE_DIR, f"final_verified_all_100_{STATION_NAME}.parquet")
    df_pareto_path = os.path.join(ACTIVE_DIR, f"final_verified_pareto_{STATION_NAME}.parquet")
    history_csv = os.path.join(ACTIVE_DIR, "active_learning_history.csv")

    df_100 = pd.read_parquet(df_100_path)
    df_pareto = pd.read_parquet(df_pareto_path)
    df_hist = pd.read_csv(history_csv)

    def normalize_cols(df):
        rename_map = {}
        for c in df.columns:
            if c.endswith('_x'):
                base = c[:-2]
                if base not in df.columns:
                    rename_map[c] = base
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    df_100 = normalize_cols(df_100)
    df_pareto = normalize_cols(df_pareto)

    tasks = []
    # Baselines
    for b_name, b_p in baseline_configs.items():
        for mode in ['free_running', 'ideal_loads']:
            tasks.append({
                'tag': f"base_{b_name}",
                'mode': mode,
                'params': b_p,
                'run_dir': os.path.join(WORK_ROOT, f"baseline_{b_name}_{mode}"),
                'epw_path': EPW_PATH
            })

    # 100 candidates free_running to get exact Top distribution & safety metrics
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
            'city': STATION_NAME
        }
        tasks.append({
            'tag': f"cand100_{did}",
            'mode': 'free_running',
            'params': p,
            'run_dir': os.path.join(WORK_ROOT, f"cand_{did}_fr"),
            'epw_path': EPW_PATH
        })

    results = {}
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_worker, t) for t in tasks]
        for f in as_completed(futures):
            tag, mode, status, sm, h_dict = f.result()
            results[(tag, mode)] = (status, sm, h_dict)

    baseline_records = []
    for b_name in baseline_configs.keys():
        tag = f"base_{b_name}"
        _, _, fr_h = results[(tag, 'free_running')]
        _, il_sm, _ = results[(tag, 'ideal_loads')]
        m = evaluate_metrics(fr_h, il_sm, champ_model)
        m['design'] = b_name
        baseline_records.append(m)

    pareto_records = []
    for _, row in df_pareto.iterrows():
        did = row['pareto_id']
        tag = f"cand100_{did}"
        _, _, fr_h = results[(tag, 'free_running')]
        il_sm = {'o2_energy_kwh_per_m2': float(row['O2'])}
        m = evaluate_metrics(fr_h, il_sm, champ_model)
        m['design'] = did
        pareto_records.append(m)

    top_meds, top_95ths, top_maxs, top_lt_5s, top_gt_35s = [], [], [], [], []
    for _, row in df_100.iterrows():
        did = row['pareto_id']
        tag = f"cand100_{did}"
        _, _, fr_h = results.get((tag, 'free_running'), (None, None, None))
        if fr_h:
            top = (fr_h['ta'] + fr_h['tr']) / 2.0
            top_meds.append(float(np.median(top)))
            top_95ths.append(float(np.percentile(top, 95)))
            top_maxs.append(float(np.max(top)))
            top_lt_5s.append(int(np.sum(top < 5.0)))
            top_gt_35s.append(int(np.sum(top > 35.0)))

    cand100_summary = {
        'best': {
            'design': '100_Candidates_Best (Min)',
            'O1_ml': round(float(df_100['O1_ml'].min()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].min()), 2),
            'O2': round(float(df_100['O2'].min()), 2),
            'T_op_med': round(float(np.min(top_meds)), 2),
            'T_op_95th': round(float(np.min(top_95ths)), 2),
            'T_op_max': round(float(np.min(top_maxs)), 2),
            'T_op_lt_5': int(np.min(top_lt_5s)),
            'T_op_gt_35': int(np.min(top_gt_35s))
        },
        'median': {
            'design': '100_Candidates_Median',
            'O1_ml': round(float(df_100['O1_ml'].median()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].median()), 2),
            'O2': round(float(df_100['O2'].median()), 2),
            'T_op_med': round(float(np.median(top_meds)), 2),
            'T_op_95th': round(float(np.median(top_95ths)), 2),
            'T_op_max': round(float(np.median(top_maxs)), 2),
            'T_op_lt_5': int(np.median(top_lt_5s)),
            'T_op_gt_35': int(np.median(top_gt_35s))
        },
        'worst': {
            'design': '100_Candidates_Worst (Max)',
            'O1_ml': round(float(df_100['O1_ml'].max()), 2),
            'O1_adapt': round(float(df_100['O1_adapt'].max()), 2),
            'O2': round(float(df_100['O2'].max()), 2),
            'T_op_med': round(float(np.max(top_meds)), 2),
            'T_op_95th': round(float(np.max(top_95ths)), 2),
            'T_op_max': round(float(np.max(top_maxs)), 2),
            'T_op_lt_5': int(np.max(top_lt_5s)),
            'T_op_gt_35': int(np.max(top_gt_35s))
        }
    }

    # Save summary CSV
    df_base_out = pd.DataFrame(baseline_records + pareto_records)
    df_base_out.to_csv(SUMMARY_CSV, index=False)

    lines = []
    lines.append("=" * 135)
    lines.append(f"LEH COMPREHENSIVE SYNTHESIS REPORT UNDER DECISION D-035 PHYSICS")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 135)
    lines.append("")
    lines.append("TABLE 1: BASELINES (R1/R2/R3) vs VERIFIED PARETO FRONT vs 100 CANDIDATES (BEST/MEDIAN/WORST)")
    lines.append("-" * 135)
    lines.append(f"{'Design / Benchmark':<28} {'O1_ml (%)':<10} {'O1_ad (%)':<10} {'O2 (kWh/m2)':<12} {'Top Med (C)':<12} {'Top 95th (C)':<13} {'Top Max (C)':<12} {'Top<5C (h)':<11} {'Top>35C (h)':<11}")
    lines.append("-" * 135)
    for b in baseline_records:
        lines.append(f"{b['design']:<28} {b['O1_ml']:<10.2f} {b['O1_adapt']:<10.2f} {b['O2']:<12.2f} {b['T_op_med']:<12.2f} {b['T_op_95th']:<13.2f} {b['T_op_max']:<12.2f} {b['T_op_lt_5']:<11d} {b['T_op_gt_35']:<11d}")
    lines.append("-" * 135)
    for p in pareto_records:
        lines.append(f"{p['design']:<28} {p['O1_ml']:<10.2f} {p['O1_adapt']:<10.2f} {p['O2']:<12.2f} {p['T_op_med']:<12.2f} {p['T_op_95th']:<13.2f} {p['T_op_max']:<12.2f} {p['T_op_lt_5']:<11d} {p['T_op_gt_35']:<11d}")
    lines.append("-" * 135)
    for k in ['best', 'median', 'worst']:
        c = cand100_summary[k]
        lines.append(f"{c['design']:<28} {c['O1_ml']:<10.2f} {c['O1_adapt']:<10.2f} {c['O2']:<12.2f} {c['T_op_med']:<12.2f} {c['T_op_95th']:<13.2f} {c['T_op_max']:<12.2f} {c['T_op_lt_5']:<11d} {c['T_op_gt_35']:<11d}")
    lines.append("-" * 135)
    lines.append("")

    lines.append("TABLE 2: ACTIVE LEARNING PER-ROUND MEAN AND MAX SURROGATE ERRORS (LEH)")
    lines.append("-" * 135)
    lines.append(f"{'Round':<8} {'TrainSize':<10} {'O1_ml Mean':<11} {'O1_ml Max':<11} {'O1_ad Mean':<11} {'O1_ad Max':<11} {'O2 Mean(abs)':<13} {'O2 Max(abs)':<13} {'O2 Mean(%)':<12} {'O2 Max(%)':<12} {'WallTime':<10}")
    lines.append("-" * 135)
    for _, r in df_hist.iterrows():
        wt_str = f"{r['wall_time_min']:.2f}m"
        lines.append(
            f"Round {int(r['round']):<2} {int(r['train_size']):<10} "
            f"{r['mean_err_O1_ml']:<11.2f} {r['max_err_O1_ml']:<11.2f} "
            f"{r['mean_err_O1_adapt']:<11.2f} {r['max_err_O1_adapt']:<11.2f} "
            f"{r['mean_err_O2_abs']:<13.2f} {r['max_err_O2_abs']:<13.2f} "
            f"{r['mean_err_O2_pct']:<12.2f}% {r['max_err_O2_pct']:<12.2f}% {wt_str:<10}"
        )
    lines.append("-" * 135)
    lines.append("")

    lines.append("TABLE 3: FINAL NON-DOMINATED PARETO FRONT UNDER VERIFIED PHYSICAL OBJECTIVES ONLY (LEH)")
    lines.append("-" * 135)
    lines.append(f"{'Design ID':<20} {'O1_ml (%)':<10} {'O1_ad (%)':<10} {'O2 (kWh/m2)':<12} {'RoofIns':<9} {'WallIns':<9} {'Mass':<8} {'Absorp':<8} {'WWR':<7} {'Shade':<7} {'ACH':<7}")
    lines.append("-" * 135)
    for _, r in df_pareto.iterrows():
        lines.append(
            f"{r['pareto_id']:<20} {r['O1_ml']:<10.2f} {r['O1_adapt']:<10.2f} {r['O2']:<12.2f} "
            f"{r['roof_insulation_thickness']:<9.3f} {r['wall_insulation_thickness']:<9.3f} {r['wall_mass_class']:<8} "
            f"{r['roof_solar_absorptance']:<8.4f} {r['wwr']:<7.4f} {r['shading_depth']:<7.3f} {r['ventilation_ach']:<7.2f}"
        )
    lines.append("-" * 135)
    lines.append("")

    lines.append("TABLE 4: DESIGN VARIABLE BOUND POSITIONING ANALYSIS FOR BEST DESIGNS (LEH)")
    lines.append("-" * 135)
    
    # Identify representative best designs on verified Pareto front
    best_o1_ml = df_pareto.sort_values('O1_ml').iloc[0]
    best_o1_ad = df_pareto.sort_values('O1_adapt').iloc[0]
    best_o2 = df_pareto.sort_values('O2').iloc[0]
    # Knee point: normalized Euclidean distance to ideal point (min O1_ml, min O1_ad, min O2)
    f_norm = df_pareto[['O1_ml', 'O1_adapt', 'O2']].copy()
    for col in f_norm.columns:
        c_min = f_norm[col].min()
        c_max = f_norm[col].max()
        f_norm[col] = (f_norm[col] - c_min) / (c_max - c_min + 1e-9)
    dist = np.sqrt((f_norm**2).sum(axis=1))
    knee_idx = dist.idxmin()
    knee_design = df_pareto.loc[knee_idx]

    best_selection = [
        ("Best_O1_ml (Comfort ML Champion)", best_o1_ml),
        ("Best_O1_adapt (Adaptive 90% Champion)", best_o1_ad),
        ("Best_O2 (Lowest Energy Consumption)", best_o2),
        ("Knee_Point (Balanced Compromise)", knee_design)
    ]

    for role_name, des in best_selection:
        lines.append(f"\nDesign Role: {role_name} [{des['pareto_id']}]")
        lines.append(f"Physical Objectives: O1_ml = {des['O1_ml']:.2f}% | O1_adapt = {des['O1_adapt']:.2f}% | O2 = {des['O2']:.2f} kWh/m2")
        lines.append(f"Envelope Parameters & Bound Status:")
        for var_name, (lb, ub) in BOUNDS.items():
            val = float(des[var_name])
            pos_str = analyze_variable_bound_position(val, var_name)
            lines.append(f"  * {var_name:<28}: {pos_str}")
        lines.append(f"  * {'wall_mass_class':<28}: {des['wall_mass_class']} (Categorical)")
    lines.append("-" * 135)

    report_text = "\n".join(lines)
    with open(SUMMARY_REPORT, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nWritten summary report to {SUMMARY_REPORT}")
    print("\n" + report_text)

if __name__ == '__main__':
    main()
