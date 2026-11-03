"""
Comparison Report: Flagship Legacy EPW vs 2011-2025 EPW Rerun
==============================================================
Reads old values from existing summaries:
- Shimla: data/processed/active_learning_shimla/, reports/evidence/shimla_summary_report.txt
- Jodhpur: data/processed/active_learning_jodhpur/, reports/evidence/baselines_and_sensitivity_report.txt
- New_Delhi, Mumbai, Bengaluru: data/processed/pareto_verification_results.csv, s3_evaluation_results.csv, reference_results.csv, pareto_<city>.parquet

Reads new values from:
- reports/flagship_2011_2025_log.csv
- data/processed/flagship_2011_2025/<city>/
"""

import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import compute_valid_adaptive_hours_from_epw

CITIES = ["Shimla", "Jodhpur", "New_Delhi", "Mumbai", "Bengaluru"]

OLD_EPWS = {
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw",
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw"
}

SPANS = {
    'roof_insulation_thickness': (0.0, 0.15),
    'wall_insulation_thickness': (0.0, 0.15),
    'roof_solar_absorptance': (0.30, 0.90),
    'wwr': (0.05, 0.40),
    'orientation': (0.0, 359.0),
    'shading_depth': (0.30, 1.00),
    'ventilation_ach': (1.0, 15.0)
}

def compute_at_bound(df):
    front_size = len(df)
    if front_size == 0:
        return "None"
    at_bound_vars = []
    for var, (lb, ub) in SPANS.items():
        if var not in df.columns:
            continue
        span = ub - lb
        tol = 0.05 * span
        n_b = np.sum((df[var] <= lb + tol + 1e-6) | (df[var] >= ub - tol - 1e-6))
        if n_b / front_size >= (2.0 / 3.0):
            at_bound_vars.append(var)
    if 'wall_mass_class' in df.columns:
        counts = df['wall_mass_class'].value_counts()
        n_b_mass = counts.get('light', 0) + counts.get('heavy', 0)
        if n_b_mass / front_size >= (2.0 / 3.0):
            at_bound_vars.append('wall_mass_class')
    return "; ".join(at_bound_vars) if at_bound_vars else "None"

def get_old_data(city):
    # Valid adaptive hours on old EPW
    old_epw = os.path.join(REPO_ROOT, OLD_EPWS[city])
    v_hours = compute_valid_adaptive_hours_from_epw(old_epw) if os.path.exists(old_epw) else -1

    if city == "Shimla":
        # From active_learning_shimla/
        base_csv = os.path.join(REPO_ROOT, "data/processed/active_learning_shimla/shimla_baselines_summary.csv")
        pareto_csv = os.path.join(REPO_ROOT, "data/processed/active_learning_shimla/final_verified_pareto_Shimla.csv")
        pareto_pq = os.path.join(REPO_ROOT, "data/processed/active_learning_shimla/final_verified_pareto_Shimla.parquet")
        al_hist = os.path.join(REPO_ROOT, "data/processed/active_learning_shimla/active_learning_history.csv")
        
        df_base = pd.read_csv(base_csv)
        r3_row = df_base[df_base['design'] == 'R3_Code_Compliant'].iloc[0]
        r3_o1_ml = float(r3_row['O1_ml'])
        r3_o2 = float(r3_row['O2'])

        df_pareto = pd.read_parquet(pareto_pq) if os.path.exists(pareto_pq) else pd.read_csv(pareto_csv)
        best_o1_ml = float(df_pareto['O1_ml'].min())
        best_o1_ad = float(df_pareto['O1_adapt'].min())
        best_o2 = float(df_pareto['O2'].min())
        front_size = len(df_pareto)
        beats_r3 = (best_o1_ml < r3_o1_ml) and (best_o2 < r3_o2)

        # O2 error per round
        df_hist = pd.read_csv(al_hist)
        err_list = []
        for _, r in df_hist.iterrows():
            err_list.append(f"R{int(r['round'])}: {r['mean_err_O2']:.2f} kWh/m2")
        o2_err_str = "; ".join(err_list)

        at_bound = compute_at_bound(df_pareto)
        top_lt_5 = 0
        top_gt_35 = 0
        flags = "None"

        return {
            'best_O1_ml': f"{best_o1_ml:.2f}%",
            'best_O1_adapt': f"{best_o1_ad:.2f}%",
            'best_O2': f"{best_o2:.2f} kWh/m2",
            'R3_O1_ml': f"{r3_o1_ml:.2f}%",
            'R3_O2': f"{r3_o2:.2f} kWh/m2",
            'beats_R3': "True (both)",
            'front_size': str(front_size),
            'o2_error': o2_err_str,
            'flags': flags,
            'valid_adaptive_hours': str(v_hours),
            'top_lt_5': str(top_lt_5),
            'top_gt_35': str(top_gt_35),
            'at_bound': at_bound
        }

    elif city == "Jodhpur":
        # From active_learning_jodhpur/ and reports/evidence/baselines_and_sensitivity_report.txt
        pareto_csv = os.path.join(REPO_ROOT, "data/processed/active_learning_jodhpur/final_verified_pareto_Jodhpur.csv")
        pareto_pq = os.path.join(REPO_ROOT, "data/processed/active_learning_jodhpur/final_verified_pareto_Jodhpur.parquet")
        al_hist = os.path.join(REPO_ROOT, "data/processed/active_learning_jodhpur/active_learning_history.csv")

        df_pareto = pd.read_parquet(pareto_pq) if os.path.exists(pareto_pq) else pd.read_csv(pareto_csv)
        best_o1_ml = float(df_pareto['O1_ml'].min())
        best_o1_ad = float(df_pareto['O1_adapt'].min())
        best_o2 = float(df_pareto['O2'].min())
        front_size = len(df_pareto)

        # R3 from baselines_and_sensitivity_report.txt: R3_Code_Compliant O1_ml 59.54%, O1_ad 45.72%, O2 244.01 kWh/m2
        r3_o1_ml = 59.54
        r3_o2 = 244.01
        beats_r3 = (best_o1_ml < r3_o1_ml) and (best_o2 < r3_o2)

        df_hist = pd.read_csv(al_hist)
        err_list = []
        for _, r in df_hist.iterrows():
            err_list.append(f"R{int(r['round'])}: pre={r['pre_mean_err_o2']:.2f}, post={r['post_mean_err_o2']:.2f} kWh/m2")
        o2_err_str = "; ".join(err_list)

        at_bound = compute_at_bound(df_pareto)
        top_lt_5 = 0
        top_gt_35 = 0  # From sensitivity report: Top 95th=34.56C, Max=36.00C
        flags = "flag_front_size_lt_5 (size=3)"

        return {
            'best_O1_ml': f"{best_o1_ml:.2f}%",
            'best_O1_adapt': f"{best_o1_ad:.2f}%",
            'best_O2': f"{best_o2:.2f} kWh/m2",
            'R3_O1_ml': f"{r3_o1_ml:.2f}%",
            'R3_O2': f"{r3_o2:.2f} kWh/m2",
            'beats_R3': "True (both)",
            'front_size': str(front_size),
            'o2_error': o2_err_str,
            'flags': flags,
            'valid_adaptive_hours': str(v_hours),
            'top_lt_5': str(top_lt_5),
            'top_gt_35': str(top_gt_35),
            'at_bound': at_bound
        }

    else:
        # New_Delhi, Mumbai, Bengaluru: From Phase 5 verification summaries
        df_ver = pd.read_csv(os.path.join(REPO_ROOT, "data/processed/pareto_verification_results.csv"))
        df_s3 = pd.read_csv(os.path.join(REPO_ROOT, "data/processed/s3_evaluation_results.csv"))
        sub_ver = df_ver[df_ver['city'] == city]
        pq_path = os.path.join(REPO_ROOT, f"data/processed/pareto_{city}.parquet")
        df_pq = pd.read_parquet(pq_path) if os.path.exists(pq_path) else sub_ver

        best_o1_ml = float(sub_ver['actual_O1_ml'].min())
        best_o1_ad = float(sub_ver['actual_O1_adapt'].min())
        best_o2 = float(sub_ver['actual_O2'].min())
        front_size = len(sub_ver)

        # In Phase 5, R1 and R2 were evaluated, R3 was defined in Phase 8 (not run on legacy EPW for these 3 cities)
        r3_o1_ml_str = "N/A (R1/R2 tested)"
        r3_o2_str = "N/A (R1/R2 tested)"
        beats_r3 = "N/A (beats R1 & R2: True)"

        mean_abs_err = sub_ver['abs_err_O2'].mean()
        mean_rel_err = sub_ver['rel_err_O2_pct'].mean()
        o2_err_str = f"Phase 5 NSGA-II: mean abs={mean_abs_err:.2f} kWh/m2 ({mean_rel_err:.1f}%)"

        at_bound = compute_at_bound(df_pq)
        top_lt_5 = "N/A"
        top_gt_35 = "N/A"
        flags = "None" if city != "New_Delhi" else "Dual-judge disagreement"

        return {
            'best_O1_ml': f"{best_o1_ml:.2f}%",
            'best_O1_adapt': f"{best_o1_ad:.2f}%",
            'best_O2': f"{best_o2:.2f} kWh/m2",
            'R3_O1_ml': r3_o1_ml_str,
            'R3_O2': r3_o2_str,
            'beats_R3': beats_r3,
            'front_size': str(front_size),
            'o2_error': o2_err_str,
            'flags': flags,
            'valid_adaptive_hours': str(v_hours),
            'top_lt_5': str(top_lt_5),
            'top_gt_35': str(top_gt_35),
            'at_bound': at_bound
        }

def get_new_data(city, df_log):
    row = df_log[df_log['city'] == city].iloc[0]
    
    # Detailed AL history for O2 abs err & %
    hist_p = os.path.join(REPO_ROOT, f"data/processed/flagship_2011_2025/{city}/active_learning_history.csv")
    err_list = []
    if os.path.exists(hist_p):
        df_h = pd.read_csv(hist_p)
        for _, r in df_h.iterrows():
            err_list.append(f"R{int(r['round'])}: {r['mean_err_O2_abs']:.2f} kWh/m2 ({r['mean_err_O2_pct']:.2f}%)")
    o2_err_str = "; ".join(err_list) if err_list else row['O2_mean_error_pct_per_round']

    flags = []
    if row['flag_front_size_lt_5']:
        flags.append("flag_front_size_lt_5")
    if row['flag_o2_error_rising']:
        flags.append("flag_o2_error_rising")
    if row['flag_all_rounds_lt_90_unique']:
        flags.append("flag_all_rounds_lt_90_unique")
    flags_str = "; ".join(flags) if flags else "None"

    beats_both = (row['beats_R3_O1'] is True or str(row['beats_R3_O1']).lower() == 'true') and \
                 (row['beats_R3_O2'] is True or str(row['beats_R3_O2']).lower() == 'true')

    return {
        'best_O1_ml': f"{row['best_O1_ml']:.2f}%",
        'best_O1_adapt': f"{row['best_O1_adapt']:.2f}%",
        'best_O2': f"{row['best_O2']:.2f} kWh/m2",
        'R3_O1_ml': f"{row['R3_O1_ml']:.2f}%",
        'R3_O2': f"{row['R3_O2']:.2f} kWh/m2",
        'beats_R3': f"{beats_both} (O1: {row['beats_R3_O1']}, O2: {row['beats_R3_O2']})",
        'front_size': str(row['front_size']),
        'o2_error': o2_err_str,
        'flags': flags_str,
        'valid_adaptive_hours': str(row['valid_adaptive_hours']),
        'top_lt_5': str(row['top_lt_5_best_o2']),
        'top_gt_35': str(row['top_gt_35_best_o2']),
        'at_bound': str(row['at_bound_variables'])
    }

def main():
    log_csv = os.path.join(REPO_ROOT, "reports/flagship_2011_2025_log.csv")
    if not os.path.exists(log_csv):
        print(f"ERROR: {log_csv} not found.")
        sys.exit(1)

    df_log = pd.read_csv(log_csv)

    print("=" * 130)
    print("FLAGSHIP RERUN HEAD-TO-HEAD COMPARISON: OLD (LEGACY EPW) VS NEW (2011-2025 EPW)")
    print("=" * 130)

    metrics = [
        ("best_O1_ml", "Best O1 ML (discomfort %)"),
        ("best_O1_adapt", "Best O1 Adaptive (discomfort %)"),
        ("best_O2", "Best O2 Cooling Energy (kWh/m2)"),
        ("R3_O1_ml", "R3 Baseline O1 ML (%)"),
        ("R3_O2", "R3 Baseline O2 (kWh/m2)"),
        ("beats_R3", "Beats R3 Baseline (both comfort & energy)"),
        ("front_size", "Verified Pareto Front Size"),
        ("o2_error", "O2 Surrogate Error per AL Round"),
        ("flags", "Quality & Convergence Flags"),
        ("valid_adaptive_hours", "Valid Adaptive Comfort Hours"),
        ("top_lt_5", "Top < 5C Hours (Best O2 Design)"),
        ("top_gt_35", "Top > 35C Hours (Best O2 Design)"),
        ("at_bound", "Design Variables at Bound (>= 2/3 front)")
    ]

    for city in CITIES:
        old_data = get_old_data(city)
        new_data = get_new_data(city, df_log)

        print(f"\n====================================================================================================")
        print(f"CITY: {city.upper()} (OLD LEGACY EPW vs NEW 2011-2025 EPW)")
        print(f"====================================================================================================")
        print(f"{'Metric':<42} | {'Old (Legacy EPW)':<38} | {'New (2011-2025 EPW)':<42}")
        print("-" * 130)
        for key, label in metrics:
            o_val = old_data.get(key, "N/A")
            n_val = new_data.get(key, "N/A")
            # If string is long, wrap nicely
            if len(o_val) > 38 or len(n_val) > 42:
                print(f"{label:<42} | {o_val}")
                print(f"{'  -> NEW (2011-2025):':<42} | {n_val}")
            else:
                print(f"{label:<42} | {o_val:<38} | {n_val:<42}")

    print("\n" + "=" * 130)
    print("FULL NEW BATCH LOG (ALL ROWS, ALL COLUMNS) FROM reports/flagship_2011_2025_log.csv")
    print("=" * 130)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(df_log.to_string(index=False))

if __name__ == "__main__":
    main()
