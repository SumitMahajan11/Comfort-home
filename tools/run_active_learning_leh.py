"""
tools/run_active_learning_leh.py

Autonomous Active-Learning Loop (3 Rounds) for LEH under Decision D-035.
- Station: Leh
- EPW: data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw
- Reads initial 1,000 LHS simulation results from data/processed/pilot_leh/
- In each round:
  1. Simulates all 100 Pareto candidate designs (200 physical EnergyPlus runs)
  2. Compares surrogate predictions vs actual simulated values (mean & max errors)
     Reports errors both as absolute AND as % of the median O2.
  3. Evaluates stopping criteria (< 3.0 pp and < 3.0 kWh/m2)
  4. Augments training pool (1,000 -> 1,100 -> 1,200 designs)
  5. Retrains 5 XGBoost surrogate models with Optuna 40 trials & 5-fold CV (multi-seed 42, 43, 44 audited)
  6. Re-runs NSGA-II optimization (Pop=100, Gen=200, Seed=42) with objective clamping to produce next candidate front
  7. Tracks and logs per-stage wall clock times (simulate 100 designs, retrain surrogates, NSGA-II, verify).
- Post-Round 3:
  Extracts true non-dominated Pareto front based on verified physical objectives only.
  Saves all artifacts into data/processed/active_learning_leh/
"""

import os
import sys
import time
import shutil
import psutil
import joblib
import optuna
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.model_selection import KFold, train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

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
from src.models.train_surrogates import (
    prepare_features,
    compute_top_k_overlap,
    tune_surrogate_xgboost,
    TARGETS
)
from src.optimize.nsga2 import MASS_CLASSES

optuna.logging.set_verbosity(optuna.logging.WARNING)

DISK_GUARD_GB = 5.0
MAX_WORKERS = 6
STATION_NAME = "Leh"
EPW_PATH = "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"
ACTIVE_DIR = "data/processed/active_learning_leh"
REPORT_PATH = "reports/evidence/leh_active_learning_report.txt"

def check_disk_guard(stage_name=""):
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    if free_gb < DISK_GUARD_GB:
        raise RuntimeError(
            f"DISK GUARD TRIGGERED during {stage_name}: Free disk space is {free_gb:.2f} GB, "
            f"which is below the mandatory {DISK_GUARD_GB:.1f} GB safety threshold. Aborting execution."
        )
    return free_gb

def get_peak_ram_gb():
    return psutil.virtual_memory().used / (1024**3)

def _sim_worker(task):
    did = task['design_id']
    mode = task['mode']
    rdir = task['run_dir']
    epw = task['epw_path']
    params = task['params']

    os.makedirs(rdir, exist_ok=True)
    idf_path = os.path.join(rdir, "shelter.idf")
    render_shelter_idf(params, idf_path, mode=mode, epw_path=epw)

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
            except Exception as e:
                res['status'] = 'PARSE_ERROR'
                res['error_msg'] = str(e)

    # Prune bulky files
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

    return did, mode, res['status'], summary_dict, hourly_dict

def simulate_designs_batch(df_designs, sim_tag, epw_path, base_sim_dir, champ_model):
    """Runs free_running + ideal_loads simulations for a batch of designs."""
    tasks = []
    for _, row in df_designs.iterrows():
        did = row['pareto_id'] if 'pareto_id' in row else row['design_id']
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
        dir_fr = os.path.join(base_sim_dir, f"{did}_fr")
        dir_il = os.path.join(base_sim_dir, f"{did}_il")
        tasks.append({
            'design_id': did, 'mode': 'free_running', 'run_dir': dir_fr,
            'epw_path': epw_path, 'params': params
        })
        tasks.append({
            'design_id': did, 'mode': 'ideal_loads', 'run_dir': dir_il,
            'epw_path': epw_path, 'params': params
        })

    results = {}
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_sim_worker, t) for t in tasks]
        for f in as_completed(futures):
            did, mode, status, sm, h_dict = f.result()
            if did not in results:
                results[did] = {}
            results[did][mode] = (status, sm, h_dict)

    paired_rows = []
    for _, row in df_designs.iterrows():
        did = row['pareto_id'] if 'pareto_id' in row else row['design_id']
        fr_res = results.get(did, {}).get('free_running')
        il_res = results.get(did, {}).get('ideal_loads')

        if not fr_res or not il_res:
            continue
        fr_stat, _, fr_h = fr_res
        il_stat, il_sm, _ = il_res

        if fr_stat != 'SUCCESS' or il_stat != 'SUCCESS' or fr_h is None or il_sm is None:
            continue

        ta = fr_h['ta']
        tr = fr_h['tr']
        rh = fr_h['rh']
        tout = fr_h['t_out']

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
        o2_val = float(il_sm['o2_energy_kwh_per_m2'])

        paired_rows.append({
            'city': STATION_NAME,
            'design_id': did,
            'roof_insulation_thickness': float(row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(row['wall_insulation_thickness']),
            'roof_solar_absorptance': float(row['roof_solar_absorptance']),
            'wwr': float(row['wwr']),
            'orientation': float(row['orientation']),
            'shading_depth': float(row['shading_depth']),
            'ventilation_ach': float(row['ventilation_ach']),
            'wall_mass_class': str(row['wall_mass_class']),
            'O1_ml': ml_res['O1_ml'],
            'warm_ml': ml_res['warm_ml'],
            'cool_ml': ml_res['cool_ml'],
            'O1_adapt': adapt_res['O1_adapt'],
            'hot_adapt': adapt_res['hot_adapt'],
            'cold_adapt': adapt_res['cold_adapt'],
            'invalid_share_adapt': adapt_res['invalid_share_adapt'],
            'O2': o2_val
        })
    return pd.DataFrame(paired_rows)

def train_surrogate_models(df_train, seed=42):
    """Trains XGBoost surrogate models with Optuna 40 trials & 5-fold CV for all 5 targets."""
    X = prepare_features(df_train)
    surrogates = {}
    metrics = {}
    X_train, X_test, df_tr, df_te = train_test_split(X, df_train, test_size=0.20, random_state=seed)

    for target in TARGETS:
        y_train = df_tr[target].values
        y_test = df_te[target].values
        best_model, best_params, cv_r2 = tune_surrogate_xgboost(X_train, y_train, n_trials=40, seed=seed)
        preds_test = best_model.predict(X_test)
        r2 = float(r2_score(y_test, preds_test))
        mae = float(mean_absolute_error(y_test, preds_test))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))

        surrogates[target] = best_model
        metrics[target] = {
            'r2': r2,
            'mae': mae,
            'rmse': rmse,
            'cv_r2': float(cv_r2),
            'best_params': best_params
        }
    return surrogates, metrics

def evaluate_multi_seed_surrogates(df_train, seeds=[42, 43, 44]):
    """Evaluates multi-seed stability across seeds 42, 43, 44."""
    X = prepare_features(df_train)
    multi_seed_metrics = {t: {} for t in TARGETS}
    for s in seeds:
        X_train, X_test, df_tr, df_te = train_test_split(X, df_train, test_size=0.20, random_state=s)
        for target in TARGETS:
            y_train = df_tr[target].values
            y_test = df_te[target].values
            m = XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.08, random_state=s, n_jobs=2)
            m.fit(X_train, y_train)
            pred = m.predict(X_test)
            r2 = float(r2_score(y_test, pred))
            multi_seed_metrics[target][s] = r2
    return multi_seed_metrics

class ClampedActiveLearningNSGA2Problem(ElementwiseProblem):
    def __init__(self, surrogates):
        self.surrogates = surrogates
        xl = np.array([0.0,  0.0,  0.30, 0.05,   0.0, 0.3,  1.0, 0.0])
        xu = np.array([0.15, 0.15, 0.90, 0.40, 359.0, 1.0, 15.0, 2.999])
        super().__init__(n_var=8, n_obj=3, n_ieq_constr=0, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        mass_idx = int(np.floor(x[7]))
        mass_idx = min(2, max(0, mass_idx))
        roof_ins = round(float(x[0]) / 0.025) * 0.025
        wall_ins = round(float(x[1]) / 0.025) * 0.025
        shading = max(0.3, float(x[5]))

        feat_dict = {
            'roof_insulation_thickness': [roof_ins],
            'wall_insulation_thickness': [wall_ins],
            'roof_solar_absorptance': [float(x[2])],
            'wwr': [float(x[3])],
            'orientation': [float(x[4])],
            'shading_depth': [shading],
            'ventilation_ach': [float(x[6])],
            'wall_mass_heavy': [1.0 if mass_idx == 0 else 0.0],
            'wall_mass_light': [1.0 if mass_idx == 1 else 0.0],
            'wall_mass_medium': [1.0 if mass_idx == 2 else 0.0],
        }
        df_feat = pd.DataFrame(feat_dict)
        pred_o1_ml = float(np.clip(self.surrogates['O1_ml'].predict(df_feat)[0], 0.0, 100.0))
        pred_o1_adapt = float(np.clip(self.surrogates['O1_adapt'].predict(df_feat)[0], 0.0, 100.0))
        pred_o2 = float(max(0.0, self.surrogates['O2'].predict(df_feat)[0]))
        out["F"] = [pred_o1_ml, pred_o1_adapt, pred_o2]

def run_nsga2_optimization(surrogates, seed=42):
    problem = ClampedActiveLearningNSGA2Problem(surrogates)
    algorithm = NSGA2(
        pop_size=100,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=1.0/8.0, eta=20),
        eliminate_duplicates=True
    )
    res = minimize(problem, algorithm, ('n_gen', 200), seed=seed, verbose=False)
    opt_X = res.X
    opt_F = res.F

    pareto_designs = []
    for i in range(len(opt_X)):
        x_vec = opt_X[i]
        f_vec = opt_F[i]
        m_idx = min(2, max(0, int(np.floor(x_vec[7]))))
        wall_mass = MASS_CLASSES[m_idx]
        roof_ins = round(float(x_vec[0]) / 0.025) * 0.025
        wall_ins = round(float(x_vec[1]) / 0.025) * 0.025
        shading = max(0.30, float(x_vec[5]))

        pareto_designs.append({
            'city': STATION_NAME,
            'pareto_id': f"P_{STATION_NAME}_R_cand_{i:03d}",
            'roof_insulation_thickness': round(roof_ins, 3),
            'wall_insulation_thickness': round(wall_ins, 3),
            'wall_mass_class': wall_mass,
            'roof_solar_absorptance': round(float(x_vec[2]), 4),
            'wwr': round(float(x_vec[3]), 4),
            'orientation': round(float(x_vec[4]), 1),
            'shading_depth': round(shading, 3),
            'ventilation_ach': round(float(x_vec[6]), 2),
            'pred_O1_ml': float(f_vec[0]),
            'pred_O1_adapt': float(f_vec[1]),
            'pred_O2': float(f_vec[2])
        })
    return pd.DataFrame(pareto_designs)

def compute_non_dominated_front(df):
    """Computes Pareto non-dominated subset under true verified physical objectives."""
    F = df[['O1_ml', 'O1_adapt', 'O2']].values
    n = len(F)
    is_dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i != j:
                if (F[j] <= F[i]).all() and (F[j] < F[i]).any():
                    is_dominated[i] = True
                    break
    return df[~is_dominated].copy()

def main():
    os.makedirs(ACTIVE_DIR, exist_ok=True)
    report_lines = []
    def log(msg=""):
        print(msg)
        report_lines.append(msg)

    log("="*90)
    log(f"ACTIVE-LEARNING & SURROGATE VERIFICATION: {STATION_NAME.upper()}")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*90)

    champ_model = load_champion_model()

    initial_obj_path = f"data/processed/pilot_{STATION_NAME.lower()}/objectives_{STATION_NAME}.parquet"
    initial_pareto_path = f"data/processed/pilot_{STATION_NAME.lower()}/pareto_{STATION_NAME}.parquet"
    df_current_pool = pd.read_parquet(initial_obj_path)
    current_pareto_designs = pd.read_parquet(initial_pareto_path)

    log(f"Initial training dataset size: {len(df_current_pool)} LHS designs")
    log(f"Initial Pareto candidate front: {len(current_pareto_designs)} designs")

    round_history = []
    final_verified_pareto = None
    all_100_final = None

    for round_idx in range(1, 4):
        log(f"\n{'*'*30} ACTIVE LEARNING ROUND {round_idx} {'*'*30}")
        log(f"Current training pool size: {len(df_current_pool)} designs")
        check_disk_guard(f"Round {round_idx} Start")
        t_round_start = time.time()

        # Step 1: Physical simulation of 100 current Pareto candidates (both modes)
        sim_dir = os.path.join(ACTIVE_DIR, f"round_{round_idx}_sims")
        log(f"[Round {round_idx} Step 1] Simulating {len(current_pareto_designs)} Pareto candidates (200 physical E+ runs)...")
        t_sim_0 = time.time()
        df_simulated_pareto = simulate_designs_batch(
            current_pareto_designs,
            sim_tag=f"R{round_idx}",
            epw_path=EPW_PATH,
            base_sim_dir=sim_dir,
            champ_model=champ_model
        )
        t_sim_elapsed = time.time() - t_sim_0
        log(f"Simulations finished in {t_sim_elapsed:.2f} s ({t_sim_elapsed/60:.2f} min). Valid designs: {len(df_simulated_pareto)}")

        # Step 2: Compare surrogate predictions vs simulated actual
        merged_eval = pd.merge(
            current_pareto_designs[['pareto_id', 'pred_O1_ml', 'pred_O1_adapt', 'pred_O2']],
            df_simulated_pareto[['design_id', 'O1_ml', 'O1_adapt', 'O2']],
            left_on='pareto_id',
            right_on='design_id'
        )

        err_o1_ml = np.abs(merged_eval['pred_O1_ml'] - merged_eval['O1_ml'])
        err_o1_ad = np.abs(merged_eval['pred_O1_adapt'] - merged_eval['O1_adapt'])
        err_o2 = np.abs(merged_eval['pred_O2'] - merged_eval['O2'])

        median_o2 = float(df_simulated_pareto['O2'].median())

        mean_err_o1_ml = float(err_o1_ml.mean())
        max_err_o1_ml = float(err_o1_ml.max())
        mean_err_o1_ad = float(err_o1_ad.mean())
        max_err_o1_ad = float(err_o1_ad.max())
        mean_err_o2 = float(err_o2.mean())
        max_err_o2 = float(err_o2.max())

        mean_err_o2_pct = (mean_err_o2 / median_o2 * 100.0) if median_o2 > 0 else 0.0
        max_err_o2_pct = (max_err_o2 / median_o2 * 100.0) if median_o2 > 0 else 0.0

        log(f"[Round {round_idx} Step 2] Surrogate Verification Errors (Median O2 = {median_o2:.2f} kWh/m2):")
        log(f"  * O1_ml:    Mean Error = {mean_err_o1_ml:.2f} pp | Max Error = {max_err_o1_ml:.2f} pp")
        log(f"  * O1_adapt: Mean Error = {mean_err_o1_ad:.2f} pp | Max Error = {max_err_o1_ad:.2f} pp")
        log(f"  * O2:       Mean Error = {mean_err_o2:.2f} kWh/m2 ({mean_err_o2_pct:.2f}% of median O2) | Max Error = {max_err_o2:.2f} kWh/m2 ({max_err_o2_pct:.2f}% of median O2)")

        # Step 3: Check stopping criteria (< 3.0 pp and < 3.0 kWh/m2)
        criteria_met = (max_err_o1_ml < 3.0) and (max_err_o1_ad < 3.0) and (max_err_o2 < 3.0)
        status_str = "CRITERIA MET (STOP)" if criteria_met else "CRITERIA NOT MET (CONTINUE)"
        log(f"[Round {round_idx} Step 3] Stopping Criteria Assessment: {status_str}")

        if round_idx == 3:
            all_100_final = pd.merge(current_pareto_designs, df_simulated_pareto, left_on='pareto_id', right_on='design_id')
            final_verified_pareto = compute_non_dominated_front(all_100_final)
            log(f"\n[Round 3 Final] Evaluated Pareto front under true physical simulation objectives: {len(final_verified_pareto)} non-dominated designs found out of 100.")
            
            t_round_elapsed = time.time() - t_round_start
            ram_round_peak = get_peak_ram_gb()
            free_disk = check_disk_guard(f"Round {round_idx} End")
            round_history.append({
                'round': round_idx,
                'train_size': len(df_current_pool),
                'sim_time_sec': round(t_sim_elapsed, 2),
                'retrain_time_sec': 0.0,
                'nsga_time_sec': 0.0,
                'verify_time_sec': 0.0,
                'wall_time_sec': round(t_round_elapsed, 2),
                'wall_time_min': round(t_round_elapsed / 60.0, 2),
                'peak_ram_gb': round(ram_round_peak, 2),
                'free_disk_gb': round(free_disk, 2),
                'median_O2': round(median_o2, 2),
                'mean_err_O1_ml': round(mean_err_o1_ml, 2),
                'max_err_O1_ml': round(max_err_o1_ml, 2),
                'mean_err_O1_adapt': round(mean_err_o1_ad, 2),
                'max_err_O1_adapt': round(max_err_o1_ad, 2),
                'mean_err_O2_abs': round(mean_err_o2, 2),
                'max_err_O2_abs': round(max_err_o2, 2),
                'mean_err_O2_pct': round(mean_err_o2_pct, 2),
                'max_err_O2_pct': round(max_err_o2_pct, 2),
                'criteria_met': criteria_met
            })
            break

        # Step 4: Augment pool
        log(f"[Round {round_idx} Step 4] Adding {len(df_simulated_pareto)} verified designs to training pool...")
        df_current_pool = pd.concat([df_current_pool, df_simulated_pareto], ignore_index=True)
        log(f"New pool size: {len(df_current_pool)} designs")

        # Step 5: Retrain surrogate models
        log(f"[Round {round_idx} Step 5] Retraining 5 surrogate models with Optuna 40 trials & 5-fold CV...")
        t_retrain_0 = time.time()
        surrogates, r_metrics = train_surrogate_models(df_current_pool, seed=42)
        multi_seed_res = evaluate_multi_seed_surrogates(df_current_pool, seeds=[42, 43, 44])
        t_retrain_elapsed = time.time() - t_retrain_0
        log(f"Surrogate retraining finished in {t_retrain_elapsed:.2f} s ({t_retrain_elapsed/60:.2f} min)")
        for tgt in TARGETS:
            s42 = multi_seed_res[tgt][42]
            s43 = multi_seed_res[tgt][43]
            s44 = multi_seed_res[tgt][44]
            log(f"  * {tgt:<10s} -> CV R2: {r_metrics[tgt]['cv_r2']:.4f} | Test R2: {r_metrics[tgt]['r2']:.4f} | Test MAE: {r_metrics[tgt]['mae']:.3f} | Multi-Seed R2 (42/43/44): {s42:.4f}/{s43:.4f}/{s44:.4f}")

        # Step 6: NSGA-II optimization (Pop=100, Gen=200, Seed=42)
        log(f"[Round {round_idx} Step 6] Re-running NSGA-II optimization (Pop=100, Gen=200, Seed=42, Clamped)...")
        t_nsga_0 = time.time()
        current_pareto_designs = run_nsga2_optimization(surrogates, seed=42)
        t_nsga_elapsed = time.time() - t_nsga_0
        log(f"NSGA-II completed in {t_nsga_elapsed:.2f} s ({t_nsga_elapsed/60:.2f} min)")

        # Rename IDs for the next round
        for k in range(len(current_pareto_designs)):
            current_pareto_designs.loc[k, 'pareto_id'] = f"P_{STATION_NAME}_R{round_idx+1}_{k:03d}"
        log(f"Generated {len(current_pareto_designs)} candidate designs for Round {round_idx+1}.")

        t_round_elapsed = time.time() - t_round_start
        ram_round_peak = get_peak_ram_gb()
        free_disk = check_disk_guard(f"Round {round_idx} End")

        round_history.append({
            'round': round_idx,
            'train_size': len(df_current_pool),
            'sim_time_sec': round(t_sim_elapsed, 2),
            'retrain_time_sec': round(t_retrain_elapsed, 2),
            'nsga_time_sec': round(t_nsga_elapsed, 2),
            'verify_time_sec': 0.0,
            'wall_time_sec': round(t_round_elapsed, 2),
            'wall_time_min': round(t_round_elapsed / 60.0, 2),
            'peak_ram_gb': round(ram_round_peak, 2),
            'free_disk_gb': round(free_disk, 2),
            'median_O2': round(median_o2, 2),
            'mean_err_O1_ml': round(mean_err_o1_ml, 2),
            'max_err_O1_ml': round(max_err_o1_ml, 2),
            'mean_err_O1_adapt': round(mean_err_o1_ad, 2),
            'max_err_O1_adapt': round(max_err_o1_ad, 2),
            'mean_err_O2_abs': round(mean_err_o2, 2),
            'max_err_O2_abs': round(max_err_o2, 2),
            'mean_err_O2_pct': round(mean_err_o2_pct, 2),
            'max_err_O2_pct': round(max_err_o2_pct, 2),
            'criteria_met': criteria_met
        })

    # Save artifacts
    df_history = pd.DataFrame(round_history)
    history_csv = os.path.join(ACTIVE_DIR, "active_learning_history.csv")
    df_history.to_csv(history_csv, index=False)
    log(f"\nSaved round history to {history_csv}")

    if final_verified_pareto is not None:
        final_parquet = os.path.join(ACTIVE_DIR, f"final_verified_pareto_{STATION_NAME}.parquet")
        final_csv = os.path.join(ACTIVE_DIR, f"final_verified_pareto_{STATION_NAME}.csv")
        final_verified_pareto.to_parquet(final_parquet, index=False)
        final_verified_pareto.to_csv(final_csv, index=False)
        log(f"Saved final verified Pareto front to {final_parquet} and {final_csv}")

    if all_100_final is not None:
        all_100_parquet = os.path.join(ACTIVE_DIR, f"final_verified_all_100_{STATION_NAME}.parquet")
        all_100_final.to_parquet(all_100_parquet, index=False)
        log(f"Saved all 100 evaluated designs to {all_100_parquet}")

    log("\n" + "="*90)
    log(f"ACTIVE-LEARNING COMPLETED FOR {STATION_NAME.upper()}")
    log("="*90)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Active learning evidence written to {REPORT_PATH}")

if __name__ == '__main__':
    main()
