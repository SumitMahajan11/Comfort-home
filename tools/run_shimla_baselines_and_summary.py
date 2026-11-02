"""
tools/run_shimla_baselines_and_summary.py

Post-run evaluation for Shimla under Decision D-035:
1. Simulates R1, R2, R3 baselines for Shimla in both modes.
2. Simulates the 100 verified candidate designs in free_running mode to compute complete empirical T_op distribution.
3. Generates by code and prints:
   - Baseline R1/R2/R3 vs final verified Pareto front vs 100 candidates best/median/worst.
   - Per-round mean and max surrogate errors.
   - Final non-dominated Pareto front under verified objectives only.
4. Outputs all tables to reports/evidence/shimla_summary_report.txt and data/processed/active_learning_shimla/shimla_baselines_summary.csv.
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

STATION_NAME = "Shimla"
EPW_PATH = "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
ACTIVE_DIR = "data/processed/active_learning_shimla"
SUMMARY_REPORT = "reports/evidence/shimla_summary_report.txt"
SUMMARY_CSV = "data/processed/active_learning_shimla/shimla_baselines_summary.csv"
WORK_ROOT = "data/processed/runs_shimla_summary"
MAX_WORKERS = 6

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

    # Normalize columns if merged with _x / _y suffixes
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

    # 100 candidates free_running to get exact Top distribution
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

    top_meds, top_95ths, top_maxs = [], [], []
    for _, row in df_100.iterrows():
        did = row['pareto_id']
        tag = f"cand100_{did}"
        _, _, fr_h = results.get((tag, 'free_running'), (None, None, None))
        if fr_h:
            top = (fr_h['ta'] + fr_h['tr']) / 2.0
            top_meds.append(float(np.median(top)))
            top_95ths.append(float(np.percentile(top, 95)))
            top_maxs.append(float(np.max(top)))

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

    # Save summary CSV
    df_base_out = pd.DataFrame(baseline_records + pareto_records)
    df_base_out.to_csv(SUMMARY_CSV, index=False)

    lines = []
    lines.append("=" * 110)
    lines.append(f"SHIMLA SUMMARY REPORT UNDER DECISION D-035 PHYSICS")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 110)
    lines.append("")
    lines.append("TABLE 1: BASELINES (R1/R2/R3) vs VERIFIED PARETO FRONT vs 100 CANDIDATES (BEST/MEDIAN/WORST)")
    lines.append("-" * 110)
    lines.append(f"{'Design / Benchmark':<32} {'O1_ml (%)':<11} {'O1_ad (%)':<11} {'O2 (kWh/m2)':<13} {'Top Med (C)':<13} {'Top 95th (C)':<13} {'Top Max (C)':<13}")
    lines.append("-" * 110)
    for b in baseline_records:
        lines.append(f"{b['design']:<32} {b['O1_ml']:<11.2f} {b['O1_adapt']:<11.2f} {b['O2']:<13.2f} {b['T_op_med']:<13.2f} {b['T_op_95th']:<13.2f} {b['T_op_max']:<13.2f}")
    lines.append("-" * 110)
    for p in pareto_records:
        lines.append(f"{p['design']:<32} {p['O1_ml']:<11.2f} {p['O1_adapt']:<11.2f} {p['O2']:<13.2f} {p['T_op_med']:<13.2f} {p['T_op_95th']:<13.2f} {p['T_op_max']:<13.2f}")
    lines.append("-" * 110)
    for k in ['best', 'median', 'worst']:
        c = cand100_summary[k]
        lines.append(f"{c['design']:<32} {c['O1_ml']:<11.2f} {c['O1_adapt']:<11.2f} {c['O2']:<13.2f} {c['T_op_med']:<13.2f} {c['T_op_95th']:<13.2f} {c['T_op_max']:<13.2f}")
    lines.append("-" * 110)
    lines.append("")

    lines.append("TABLE 2: ACTIVE LEARNING PER-ROUND MEAN AND MAX SURROGATE ERRORS (SHIMLA)")
    lines.append("-" * 110)
    lines.append(f"{'Round':<8} {'Train Size':<12} {'O1_ml Mean':<12} {'O1_ml Max':<12} {'O1_ad Mean':<12} {'O1_ad Max':<12} {'O2 Mean':<12} {'O2 Max':<12} {'Wall Time':<12} {'Peak RAM':<10}")
    lines.append("-" * 110)
    for _, r in df_hist.iterrows():
        wt_str = f"{r['wall_time_min']:.2f} min"
        ram_str = f"{r['peak_ram_gb']:.2f} GB"
        lines.append(f"Round {int(r['round']):<2} {int(r['train_size']):<12} {r['mean_err_O1_ml']:<12.2f} {r['max_err_O1_ml']:<12.2f} {r['mean_err_O1_adapt']:<12.2f} {r['max_err_O1_adapt']:<12.2f} {r['mean_err_O2']:<12.2f} {r['max_err_O2']:<12.2f} {wt_str:<12} {ram_str:<10}")
    lines.append("-" * 110)
    lines.append("")

    lines.append("TABLE 3: FINAL NON-DOMINATED PARETO FRONT UNDER VERIFIED PHYSICAL OBJECTIVES ONLY (SHIMLA)")
    lines.append("-" * 110)
    lines.append(f"{'Design ID':<20} {'O1_ml (%)':<11} {'O1_ad (%)':<11} {'O2 (kWh/m2)':<13} {'RoofIns':<10} {'WallIns':<10} {'Mass':<8} {'Absorp':<8} {'WWR':<8} {'Shade':<8} {'ACH':<8}")
    lines.append("-" * 110)
    for _, r in df_pareto.iterrows():
        lines.append(f"{r['pareto_id']:<20} {r['O1_ml']:<11.2f} {r['O1_adapt']:<11.2f} {r['O2']:<13.2f} {r['roof_insulation_thickness']:<10.3f} {r['wall_insulation_thickness']:<10.3f} {r['wall_mass_class']:<8} {r['roof_solar_absorptance']:<8.4f} {r['wwr']:<8.4f} {r['shading_depth']:<8.3f} {r['ventilation_ach']:<8.2f}")
    lines.append("-" * 110)

    report_text = "\n".join(lines)
    with open(SUMMARY_REPORT, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nWritten summary report to {SUMMARY_REPORT}")
    print("\n" + report_text)

if __name__ == '__main__':
    main()
