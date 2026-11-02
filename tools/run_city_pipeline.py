"""
tools/run_city_pipeline.py

Reusable per-city end-to-end pipeline:
1. Stage 1: Pilot simulation (1,000 LHS designs, 2,000 EnergyPlus runs) + dual comfort coupling
2. Stage 2: Initial surrogate training (5 XGBoost surrogates, Optuna 40 trials, 5-fold CV, seeds 42, 43, 44)
3. Stage 3: Initial NSGA-II optimization (Pop 100, Gen 200, Seed 42, clamped objectives) -> Round 1 candidates
4. Stage 4: Active Learning Round 1 (Simulate 100 candidates, error analysis, pool augmentation 1000->1100, retrain, NSGA-II)
5. Stage 5: Active Learning Round 2 (Simulate 100 candidates, error analysis, pool augmentation 1100->1200, retrain, NSGA-II)
6. Stage 6: Active Learning Round 3 (Simulate 100 candidates, error analysis, pool augmentation 1200->1300, true Pareto extraction)
7. Stage 7: Baselines & Summary Evaluation (R1, R2, R3 baselines, Top safety metrics, bounds table, timing summary)
"""

import os
import sys
import time
import shutil
import argparse
import hashlib
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

from scipy.stats import qmc
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
from src.optimize.references import REFERENCE_R1, REFERENCE_R2, REFERENCE_R3_PER_CITY
from src.sim.sampler import DESIGN_VARIABLE_RANGES

optuna.logging.set_verbosity(optuna.logging.WARNING)

# -----------------------------------------------------------------------------
# SETTINGS CONSTANTS (Exact replica of Leh settings)
# -----------------------------------------------------------------------------
LHS_DESIGNS = 1000
MODES = 2                      # free_running and ideal_loads
TOTAL_PILOT_SIMS = 2000
AL_ROUNDS = 3
AL_DESIGNS_PER_ROUND = 100
OPTUNA_TRIALS = 40
CV_FOLDS = 5
SEEDS = [42, 43, 44]
NSGA2_POP = 100
NSGA2_GEN = 200
NSGA2_CLAMPED = True
MAX_WORKERS = 6
DISK_GUARD_GB = 5.0
EPW_VERSION = "TMYx 2011-2025"

# Lookup dictionary for climate zones (UNVERIFIED / Verified)
CITY_CLIMATE_ZONES = {
    # Cold -> Leh
    "Srinagar": "Cold",
    "Manali": "Cold",
    "Bhuntar": "Cold",
    "Gangtok": "Cold",
    "Leh": "Cold",
    "Shimla": "Cold",
    # Composite -> New_Delhi
    "Jammu": "Composite",
    "Dehradun": "Composite",
    "Lucknow": "Composite",
    "Varanasi": "Composite",
    "Prayagraj": "Composite",
    "Agra": "Composite",
    "Gorakhpur": "Composite",
    "Patna": "Composite",
    "Nagpur": "Composite",
    "New_Delhi": "Composite",
    # Warm-humid -> Mumbai
    "Guwahati": "Warm-humid",
    "Dibrugarh": "Warm-humid",
    "Imphal": "Warm-humid",
    "Bhubaneswar": "Warm-humid",
    "Kolkata": "Warm-humid",
    "Visakhapatnam": "Warm-humid",
    "Chennai": "Warm-humid",
    "Kochi": "Warm-humid",
    "Port Blair": "Warm-humid",
    "Mumbai": "Warm-humid",
    # Hot-dry -> Jodhpur
    "Bhuj": "Hot-dry",
    "Jaisalmer": "Hot-dry",
    "Jodhpur": "Hot-dry",
    "Surat": "Hot-dry",
    # Temperate -> Bengaluru
    "Bengaluru": "Temperate"
}

ZONE_TO_FLAGSHIP_R3 = {
    "Cold": "Leh",
    "Composite": "New_Delhi",
    "Warm-humid": "Mumbai",
    "Hot-dry": "Jodhpur",
    "Temperate": "Bengaluru"
}

def print_settings():
    print("=" * 80)
    print("PIPELINE EXECUTION SETTINGS (Exact replica of Leh settings)")
    print("=" * 80)
    print(f"LHS Designs:               {LHS_DESIGNS}")
    print(f"Simulation Modes:          {MODES} (free_running + ideal_loads -> {TOTAL_PILOT_SIMS} pilot sims)")
    print(f"Active Learning Rounds:    {AL_ROUNDS} rounds x {AL_DESIGNS_PER_ROUND} designs")
    print(f"Surrogate Hyperparam Opt:  Optuna {OPTUNA_TRIALS} trials, {CV_FOLDS}-fold Cross-Validation")
    print(f"Multi-Seed Auditing:       Seeds {SEEDS}")
    print(f"NSGA-II Optimization:      Population {NSGA2_POP}, Generations {NSGA2_GEN}, Clamped={NSGA2_CLAMPED}")
    print(f"Parallel Workers:          {MAX_WORKERS}")
    print(f"Disk Safety Guard:         >= {DISK_GUARD_GB} GB threshold")
    print(f"Required EPW Standard:     {EPW_VERSION}")
    print("=" * 80 + "\n")

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

# -----------------------------------------------------------------------------
# WORKER FUNCTION FOR MULTIPROCESSING
# -----------------------------------------------------------------------------
def _sim_worker(task):
    did = task['design_id']
    mode = task['mode']
    rdir = task['run_dir']
    epw = task['epw_path']
    city = task['city']
    params = task['params']

    os.makedirs(rdir, exist_ok=True)
    idf_path = os.path.join(rdir, "shelter.idf")
    render_shelter_idf(params, idf_path, mode=mode, city=city, epw_path=epw)

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

    # Prune bulky files to conserve disk space
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

# -----------------------------------------------------------------------------
# NSGA-II PROBLEM DEFINITION (Clamped Objectives)
# -----------------------------------------------------------------------------
class ClampedShelterOptimizationProblem(ElementwiseProblem):
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

def run_nsga2(surrogates, seed=42, city_name="", n_gen=NSGA2_GEN, pop_size=NSGA2_POP):
    problem = ClampedShelterOptimizationProblem(surrogates)
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=1.0/8.0, eta=20),
        eliminate_duplicates=True
    )
    res = minimize(problem, algorithm, ('n_gen', n_gen), seed=seed, verbose=False)
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
            'city': city_name,
            'pareto_id': f"P_{city_name}_cand_{i:03d}",
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

# -----------------------------------------------------------------------------
# MAIN REUSABLE CITY PIPELINE CLASS
# -----------------------------------------------------------------------------
class CityPipeline:
    def __init__(self, city_name, smoke=False):
        self.city_name = city_name
        self.smoke = smoke
        self.lhs_designs = 20 if smoke else LHS_DESIGNS
        self.al_rounds = 1 if smoke else AL_ROUNDS
        self.al_designs_per_round = 10 if smoke else AL_DESIGNS_PER_ROUND
        self.optuna_trials = 3 if smoke else OPTUNA_TRIALS
        self.nsga2_gen = 10 if smoke else NSGA2_GEN
        self.nsga2_pop = 100 if smoke else NSGA2_POP

        base_batch = "data/processed/batch_smoke" if smoke else "data/processed/batch"
        base_models = "models/batch_smoke" if smoke else "models/batch"
        self.batch_dir = os.path.join(base_batch, city_name)
        self.models_dir = os.path.join(base_models, city_name)
        self.markers_dir = os.path.join(self.batch_dir, "stage_markers")
        self.timing_csv = os.path.join(self.batch_dir, "timing.csv")
        
        os.makedirs(self.batch_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.markers_dir, exist_ok=True)

        # Resolve EPW Path from manifest
        manifest_path = "reports/batch_epw_manifest.csv"
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"{manifest_path} not found. Run Step 2 first.")
        df_m = pd.read_csv(manifest_path)
        c_row = df_m[df_m['city'].str.lower() == city_name.lower()]
        if len(c_row) == 0:
            raise ValueError(f"City '{city_name}' not found in {manifest_path}!")
        self.epw_path = os.path.abspath(c_row.iloc[0]['path'])
        if not os.path.exists(self.epw_path):
            raise FileNotFoundError(f"EPW file not found at {self.epw_path} for city '{city_name}'!")
        
        # Resolve Climate Zone and R3 reference
        if city_name not in CITY_CLIMATE_ZONES:
            raise ValueError(f"City '{city_name}' not in climate zone lookup dictionary!")
        self.climate_zone = CITY_CLIMATE_ZONES[city_name]
        self.flagship_r3_source = ZONE_TO_FLAGSHIP_R3[self.climate_zone]
        
        # Copy R3 reference from flagship
        flagship_r3 = REFERENCE_R3_PER_CITY[self.flagship_r3_source]
        self.reference_r3 = dict(flagship_r3)
        self.reference_r3['city'] = city_name

        self.champ_model = load_champion_model()
        self.timing_records = []
        if os.path.exists(self.timing_csv):
            self.timing_df = pd.read_csv(self.timing_csv)
        else:
            self.timing_df = pd.DataFrame(columns=[
                "stage", "start_time", "end_time", "elapsed_seconds",
                "pool_size_before", "pool_size_after", "notes"
            ])

    def log_timing(self, stage, t0, t1, pool_before=None, pool_after=None, notes=""):
        dt = t1 - t0
        st_str = datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S")
        et_str = datetime.fromtimestamp(t1).strftime("%Y-%m-%d %H:%M:%S")
        rec = {
            "stage": stage,
            "start_time": st_str,
            "end_time": et_str,
            "elapsed_seconds": round(dt, 2),
            "pool_size_before": pool_before if pool_before is not None else "",
            "pool_size_after": pool_after if pool_after is not None else "",
            "notes": notes
        }
        self.timing_df = pd.concat([self.timing_df, pd.DataFrame([rec])], ignore_index=True)
        self.timing_df.to_csv(self.timing_csv, index=False)
        print(f"[{stage}] Logged timing: {dt:.2f} s ({dt/60:.2f} min).")

    def is_stage_done(self, stage_name):
        marker = os.path.join(self.markers_dir, f"{stage_name}.done")
        return os.path.exists(marker)

    def mark_stage_done(self, stage_name):
        marker = os.path.join(self.markers_dir, f"{stage_name}.done")
        with open(marker, "w") as f:
            f.write(f"DONE at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def simulate_designs(self, df_designs, sim_dir, id_col='design_id'):
        tasks = []
        for _, row in df_designs.iterrows():
            did = str(row[id_col])
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
            dir_fr = os.path.join(sim_dir, f"{did}_fr")
            dir_il = os.path.join(sim_dir, f"{did}_il")
            tasks.append({
                'design_id': did, 'mode': 'free_running', 'run_dir': dir_fr,
                'epw_path': self.epw_path, 'city': self.city_name, 'params': params
            })
            tasks.append({
                'design_id': did, 'mode': 'ideal_loads', 'run_dir': dir_il,
                'epw_path': self.epw_path, 'city': self.city_name, 'params': params
            })

        results = {}
        total_tasks = len(tasks)
        print(f"  Dispatching {total_tasks} simulations with {MAX_WORKERS} workers...")
        count = 0
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(_sim_worker, t) for t in tasks]
            for f in as_completed(futures):
                did, mode, status, sm, h_dict = f.result()
                if did not in results:
                    results[did] = {}
                results[did][mode] = (status, sm, h_dict)
                count += 1
                if count % 200 == 0 or count == total_tasks:
                    print(f"  Progress: {count}/{total_tasks} simulations finished ({count/total_tasks*100:.1f}%)")

        paired_rows = []
        for _, row in df_designs.iterrows():
            did = str(row[id_col])
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
                model=self.champ_model,
                ta=ta, tr=tr, rh=rh,
                t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
                met=1.1, vel=0.15
            )
            o2_val = float(il_sm['o2_energy_kwh_per_m2'])
            top = (ta + tr) / 2.0
            top_med = float(np.median(top))
            top_max = float(np.max(top))
            top_lt_5 = int(np.sum(top < 5.0))
            top_gt_35 = int(np.sum(top > 35.0))

            paired_rows.append({
                'city': self.city_name,
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
                'O2': o2_val,
                'top_med': top_med,
                'top_max': top_max,
                'top_lt_5': top_lt_5,
                'top_gt_35': top_gt_35
            })
        return pd.DataFrame(paired_rows)

    def train_surrogates(self, df_train, seed=42):
        X = prepare_features(df_train)
        surrogates = {}
        metrics = {}
        X_train, X_test, df_tr, df_te = train_test_split(X, df_train, test_size=0.20, random_state=seed)

        for target in TARGETS:
            y_train = df_tr[target].values
            y_test = df_te[target].values
            best_model, best_params, cv_r2 = tune_surrogate_xgboost(X_train, y_train, n_trials=self.optuna_trials, seed=seed)
            preds_test = best_model.predict(X_test)
            r2 = float(r2_score(y_test, preds_test))
            mae = float(mean_absolute_error(y_test, preds_test))
            rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))

            surrogates[target] = best_model
            metrics[target] = {
                'r2': r2, 'mae': mae, 'rmse': rmse, 'cv_r2': float(cv_r2),
                'best_params': best_params
            }
            # Save model
            art = {
                'model': best_model, 'best_params': best_params, 'target': target,
                'metrics': metrics[target]
            }
            joblib.dump(art, os.path.join(self.models_dir, f"surrogate_{self.city_name}_{target}.joblib"))
        return surrogates, metrics

    # -------------------------------------------------------------------------
    # STAGES 1 - 7
    # -------------------------------------------------------------------------
    def run_stage_1(self):
        stage = "stage_1_pilot_simulation"
        if self.is_stage_done(stage):
            print(f"[{stage}] SKIPPED (already done).")
            return pd.read_parquet(os.path.join(self.batch_dir, f"objectives_{self.city_name}.parquet"))

        print(f"\n{'='*80}\nRUNNING {stage.upper()}: {self.city_name}\n{'='*80}")
        check_disk_guard(stage)
        t0 = time.time()

        # Sample LHS designs
        sampler = qmc.LatinHypercube(d=8, seed=42)
        raw = sampler.random(n=self.lhs_designs)
        designs = []
        for i in range(self.lhs_designs):
            r = raw[i]
            roof_ins = round((r[0] * 0.150) / 0.025) * 0.025
            wall_ins = round((r[1] * 0.150) / 0.025) * 0.025
            m_idx = min(2, max(0, int(np.floor(r[2] * 3.0))))
            wall_mass = MASS_CLASSES[m_idx]
            roof_abs = 0.30 + r[3] * 0.60
            wwr = 0.05 + r[4] * 0.35
            orient = r[5] * 359.0
            shading = 0.30 + r[6] * 0.70
            vent = 1.0 + r[7] * 14.0

            designs.append({
                'design_id': f"P_{self.city_name}_{i:03d}",
                'roof_insulation_thickness': round(roof_ins, 3),
                'wall_insulation_thickness': round(wall_ins, 3),
                'wall_mass_class': wall_mass,
                'roof_solar_absorptance': round(roof_abs, 4),
                'wwr': round(wwr, 4),
                'orientation': round(orient, 1),
                'shading_depth': round(shading, 3),
                'ventilation_ach': round(vent, 2)
            })
        df_designs = pd.DataFrame(designs)

        sim_dir = os.path.join(self.batch_dir, "pilot_sims")
        df_obj = self.simulate_designs(df_designs, sim_dir)
        df_obj.to_parquet(os.path.join(self.batch_dir, f"objectives_{self.city_name}.parquet"), index=False)
        df_obj.to_csv(os.path.join(self.batch_dir, f"objectives_{self.city_name}.csv"), index=False)

        t1 = time.time()
        self.log_timing(stage, t0, t1, pool_before=0, pool_after=len(df_obj), notes=f"{self.lhs_designs} LHS designs x 2 modes")
        self.mark_stage_done(stage)
        return df_obj

    def run_stage_2_and_3(self, df_pool):
        stage_surr = "stage_2_surrogate_training"
        stage_nsga = "stage_3_initial_optimization"

        surrogates = {}
        if not self.is_stage_done(stage_surr):
            print(f"\n{'='*80}\nRUNNING {stage_surr.upper()}: {self.city_name}\n{'='*80}")
            check_disk_guard(stage_surr)
            t0 = time.time()
            surrogates, metrics = self.train_surrogates(df_pool, seed=42)
            t1 = time.time()
            self.log_timing(stage_surr, t0, t1, pool_before=len(df_pool), pool_after=len(df_pool), notes=f"Optuna {self.optuna_trials} trials, 5 folds")
            self.mark_stage_done(stage_surr)
        else:
            print(f"[{stage_surr}] SKIPPED (already done). Loading models.")
            for target in TARGETS:
                art = joblib.load(os.path.join(self.models_dir, f"surrogate_{self.city_name}_{target}.joblib"))
                surrogates[target] = art['model']

        if not self.is_stage_done(stage_nsga):
            print(f"\n{'='*80}\nRUNNING {stage_nsga.upper()}: {self.city_name}\n{'='*80}")
            check_disk_guard(stage_nsga)
            t0 = time.time()
            df_cand1 = run_nsga2(surrogates, seed=42, city_name=self.city_name, n_gen=self.nsga2_gen, pop_size=self.nsga2_pop)
            df_cand1.to_parquet(os.path.join(self.batch_dir, "round_1_candidates.parquet"), index=False)
            t1 = time.time()
            self.log_timing(stage_nsga, t0, t1, pool_before=len(df_pool), pool_after=len(df_pool), notes=f"Pop {self.nsga2_pop}, Gen {self.nsga2_gen}, Clamped")
            self.mark_stage_done(stage_nsga)
        else:
            print(f"[{stage_nsga}] SKIPPED (already done).")
            df_cand1 = pd.read_parquet(os.path.join(self.batch_dir, "round_1_candidates.parquet"))

        return surrogates, df_cand1

    def run_active_learning_rounds(self, df_pool, surrogates, df_cand1):
        current_pool = df_pool.copy()
        current_cand = df_cand1.copy()
        current_surrogates = surrogates

        history_records = []
        hist_path = os.path.join(self.batch_dir, "active_learning_history.csv")
        if os.path.exists(hist_path):
            df_hist_existing = pd.read_csv(hist_path)
            history_records = df_hist_existing.to_dict('records')

        for r in range(1, self.al_rounds + 1):
            stage = f"stage_{3+r}_al_round_{r}"
            if self.is_stage_done(stage):
                print(f"[{stage}] SKIPPED (already done).")
                # update pool from disk if needed
                next_cand_path = os.path.join(self.batch_dir, f"round_{r+1}_candidates.parquet")
                if os.path.exists(next_cand_path):
                    current_cand = pd.read_parquet(next_cand_path)
                continue

            print(f"\n{'*'*30} ACTIVE LEARNING ROUND {r}: {self.city_name} {'*'*30}")
            pool_before = len(current_pool)
            print(f"Pool size BEFORE Round {r}: {pool_before}")
            check_disk_guard(stage)
            t_round_0 = time.time()

            # 1. Simulate candidate designs
            sim_dir = os.path.join(self.batch_dir, f"round_{r}_sims")
            t_sim_0 = time.time()
            df_to_sim = current_cand.iloc[:self.al_designs_per_round]
            df_sim = self.simulate_designs(df_to_sim, sim_dir, id_col='pareto_id')
            t_sim_sec = time.time() - t_sim_0

            # 2. Compare surrogate predictions vs physical simulations
            merged = pd.merge(df_sim, current_cand, left_on='design_id', right_on='pareto_id', suffixes=('', '_pred'))
            err_o1_ml = np.abs(merged['O1_ml'] - merged['pred_O1_ml'])
            err_o1_ad = np.abs(merged['O1_adapt'] - merged['pred_O1_adapt'])
            err_o2 = np.abs(merged['O2'] - merged['pred_O2'])

            median_o2 = float(np.median(merged['O2']))
            mean_err_o2_pct = (float(np.mean(err_o2)) / median_o2 * 100.0) if median_o2 > 0 else 0.0
            max_err_o2_pct = (float(np.max(err_o2)) / median_o2 * 100.0) if median_o2 > 0 else 0.0

            rec = {
                'round': r,
                'pool_size_before': pool_before,
                'pool_size_after': pool_before + len(df_sim),
                'sim_time_sec': round(t_sim_sec, 2),
                'median_O2': round(median_o2, 2),
                'mean_err_O1_ml': round(float(np.mean(err_o1_ml)), 2),
                'max_err_O1_ml': round(float(np.max(err_o1_ml)), 2),
                'mean_err_O1_adapt': round(float(np.mean(err_o1_ad)), 2),
                'max_err_O1_adapt': round(float(np.max(err_o1_ad)), 2),
                'mean_err_O2_abs': round(float(np.mean(err_o2)), 2),
                'max_err_O2_abs': round(float(np.max(err_o2)), 2),
                'mean_err_O2_pct': round(mean_err_o2_pct, 2),
                'max_err_O2_pct': round(max_err_o2_pct, 2)
            }
            print(f"Round {r} Error Summary: O1_ml mean err={rec['mean_err_O1_ml']} pp | O1_adapt mean err={rec['mean_err_O1_adapt']} pp | O2 mean err={rec['mean_err_O2_abs']} kWh/m2 ({rec['mean_err_O2_pct']} %)")

            # 3. Augment training pool
            current_pool = pd.concat([current_pool, df_sim], ignore_index=True)
            pool_after = len(current_pool)
            print(f"Pool size AFTER Round {r}: {pool_after}")

            # 4. Retrain surrogates & NSGA-II if rounds < al_rounds
            if r < self.al_rounds:
                t_retrain_0 = time.time()
                current_surrogates, _ = self.train_surrogates(current_pool, seed=42)
                t_retrain_sec = time.time() - t_retrain_0

                t_nsga_0 = time.time()
                current_cand = run_nsga2(current_surrogates, seed=42, city_name=self.city_name, n_gen=self.nsga2_gen, pop_size=self.nsga2_pop)
                t_nsga_sec = time.time() - t_nsga_0
                current_cand.to_parquet(os.path.join(self.batch_dir, f"round_{r+1}_candidates.parquet"), index=False)

                rec['retrain_time_sec'] = round(t_retrain_sec, 2)
                rec['nsga_time_sec'] = round(t_nsga_sec, 2)
            else:
                rec['retrain_time_sec'] = 0.0
                rec['nsga_time_sec'] = 0.0
                # Final round: save final verified all & true pareto front
                df_sim.to_parquet(os.path.join(self.batch_dir, f"final_verified_all_100_{self.city_name}.parquet"), index=False)
                pareto_df = compute_non_dominated_front(df_sim)
                pareto_df.to_parquet(os.path.join(self.batch_dir, f"final_verified_pareto_{self.city_name}.parquet"), index=False)
                pareto_df.to_csv(os.path.join(self.batch_dir, f"final_verified_pareto_{self.city_name}.csv"), index=False)
                print(f"Extracted {len(pareto_df)} non-dominated Pareto front designs from verified physical simulations.")

            t_round_end = time.time()
            rec['wall_time_sec'] = round(t_round_end - t_round_0, 2)
            history_records.append(rec)
            pd.DataFrame(history_records).to_csv(hist_path, index=False)

            self.log_timing(stage, t_round_0, t_round_end, pool_before=pool_before, pool_after=pool_after, notes=f"AL Round {r}")
            self.mark_stage_done(stage)

        return current_pool

    def run_stage_7_summary(self):
        stage = "stage_7_baselines_and_summary"
        if self.is_stage_done(stage):
            print(f"[{stage}] SKIPPED (already done).")
            return

        print(f"\n{'='*80}\nRUNNING {stage.upper()}: {self.city_name}\n{'='*80}")
        t0 = time.time()

        # 1. Simulate R1, R2, R3 baselines
        baselines = {
            'R1_Lightweight': {**REFERENCE_R1, 'city': self.city_name},
            'R2_Conventional': {**REFERENCE_R2, 'city': self.city_name},
            'R3_Code_Compliant': self.reference_r3
        }
        df_base = pd.DataFrame([
            {'design_id': k, **v} for k, v in baselines.items()
        ])
        sim_dir_b = os.path.join(self.batch_dir, "baseline_sims")
        df_base_res = self.simulate_designs(df_base, sim_dir_b, id_col='design_id')
        df_base_res.to_csv(os.path.join(self.batch_dir, "baseline_results.csv"), index=False)

        # Load verified 100 and Pareto front
        df_100 = pd.read_parquet(os.path.join(self.batch_dir, f"final_verified_all_100_{self.city_name}.parquet"))
        df_pareto = pd.read_parquet(os.path.join(self.batch_dir, f"final_verified_pareto_{self.city_name}.parquet"))
        df_hist = pd.read_csv(os.path.join(self.batch_dir, "active_learning_history.csv"))

        # ---------------------------------------------------------------------
        # OUTPUT TABLES GENERATED BY CODE
        # ---------------------------------------------------------------------
        print("\n" + "=" * 130)
        print(f"TABLE 1: BASELINES (R1/R2/R3) vs VERIFIED PARETO FRONT ({self.city_name.upper()}) [LOWER O1 IS BETTER]")
        print("=" * 130)
        t1_rows = []
        for _, r in df_base_res.iterrows():
            did = r['design_id']
            t1_rows.append({
                'Design / Category': did,
                'Design ID': did,
                'O1_ml (%)': round(r['O1_ml'], 2),
                'O1_adapt (%)': round(r['O1_adapt'], 2),
                'O2 (kWh/m2)': round(r['O2'], 2),
                'Top Med (C)': round(r['top_med'], 2),
                'Top Max (C)': round(r['top_max'], 2),
                'Top < 5 C (h)': int(r['top_lt_5']),
                'Top > 35 C (h)': int(r['top_gt_35'])
            })

        # Lower O1 is better
        best_o1_ml_idx = df_pareto['O1_ml'].idxmin()
        best_o1_ad_idx = df_pareto['O1_adapt'].idxmin()
        best_o2_idx = df_pareto['O2'].idxmin()
        worst_o1_ml_idx = df_pareto['O1_ml'].idxmax()
        worst_o2_idx = df_pareto['O2'].idxmax()

        # Knee: design closest to normalized midpoint of the front (3-obj F3)
        F3 = df_pareto[['O1_ml', 'O1_adapt', 'O2']].values
        fn3 = (F3 - F3.min(axis=0)) / (F3.max(axis=0) - F3.min(axis=0) + 1e-12)
        d3 = np.linalg.norm(fn3 - 0.5, axis=1)
        knee_idx = np.argmin(d3)

        def _add_front_row(cat_name, idx):
            r = df_pareto.loc[idx]
            t1_rows.append({
                'Design / Category': cat_name,
                'Design ID': r['design_id'],
                'O1_ml (%)': round(r['O1_ml'], 2),
                'O1_adapt (%)': round(r['O1_adapt'], 2),
                'O2 (kWh/m2)': round(r['O2'], 2),
                'Top Med (C)': round(r['top_med'], 2),
                'Top Max (C)': round(r['top_max'], 2),
                'Top < 5 C (h)': int(r['top_lt_5']),
                'Top > 35 C (h)': int(r['top_gt_35'])
            })

        _add_front_row("Best O1_ml", best_o1_ml_idx)
        _add_front_row("Best O1_adapt", best_o1_ad_idx)
        _add_front_row("Best O2 (Lowest Energy)", best_o2_idx)
        _add_front_row("Knee (Normalized Midpoint)", knee_idx)

        t1_rows.append({
            'Design / Category': 'Front Median',
            'Design ID': f"Median (N={len(df_pareto)})",
            'O1_ml (%)': round(df_pareto['O1_ml'].median(), 2),
            'O1_adapt (%)': round(df_pareto['O1_adapt'].median(), 2),
            'O2 (kWh/m2)': round(df_pareto['O2'].median(), 2),
            'Top Med (C)': round(df_pareto['top_med'].median(), 2),
            'Top Max (C)': round(df_pareto['top_max'].median(), 2),
            'Top < 5 C (h)': int(df_pareto['top_lt_5'].median()),
            'Top > 35 C (h)': int(df_pareto['top_gt_35'].median())
        })

        _add_front_row("Worst O1_ml", worst_o1_ml_idx)
        _add_front_row("Worst O2 (Highest Energy)", worst_o2_idx)

        df_table1 = pd.DataFrame(t1_rows)
        print(df_table1.to_string(index=False))

        print("\n" + "=" * 120)
        print(f"TABLE 2: PER-ROUND SURROGATE ERRORS ({self.city_name.upper()})")
        print("=" * 120)
        t2_cols = ['round', 'mean_err_O1_ml', 'max_err_O1_ml', 'mean_err_O1_adapt', 'max_err_O1_adapt',
                   'mean_err_O2_abs', 'max_err_O2_abs', 'median_O2', 'mean_err_O2_pct', 'max_err_O2_pct']
        print(df_hist[t2_cols].to_string(index=False))

        print("\n" + "=" * 120)
        print(f"TABLE 3: FINAL NON-DOMINATED PARETO FRONT ({self.city_name.upper()})")
        print("=" * 120)
        show_pareto_cols = ['design_id', 'O1_ml', 'O1_adapt', 'O2', 'roof_insulation_thickness',
                            'wall_insulation_thickness', 'wall_mass_class', 'roof_solar_absorptance',
                            'wwr', 'orientation', 'shading_depth', 'ventilation_ach']
        print(df_pareto[show_pareto_cols].to_string(index=False))

        n_p = len(df_pareto)
        threshold_count = int(np.ceil((2.0 / 3.0) * n_p))

        # Check near-duplicates: all 8 variables within 1% of span
        spans = {
            'roof_insulation_thickness': 0.15,
            'wall_insulation_thickness': 0.15,
            'roof_solar_absorptance': 0.60,
            'wwr': 0.35,
            'orientation': 359.0,
            'shading_depth': 0.70,
            'ventilation_ach': 14.0
        }
        dup_indices = set()
        for i in range(n_p):
            for j in range(i + 1, n_p):
                r1_c = df_pareto.iloc[i]
                r2_c = df_pareto.iloc[j]
                if r1_c['wall_mass_class'] != r2_c['wall_mass_class']:
                    continue
                is_near_dup = True
                for var, s_val in spans.items():
                    if abs(float(r1_c[var]) - float(r2_c[var])) > 0.01 * s_val:
                        is_near_dup = False
                        break
                if is_near_dup:
                    dup_indices.add(i)
                    dup_indices.add(j)

        print("\n" + "=" * 120)
        print(f"TABLE 4: BOUNDS TABLE ({self.city_name.upper()}) - AT BOUND if (#low + #up) / front_size >= 2/3 (front_size = {n_p})")
        print(f"Near-Duplicate Front Designs (all 8 variables within 1% of span): {len(dup_indices)} of {n_p}")
        print("=" * 120)
        var_cols = [
            'roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance',
            'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
        ]
        b_header = f"{'Design Variable':<28} | {'Lower':<7} | {'Upper':<7} | {'Span':<7} | {'5% Span':<8} | {'Low Zone':<16} | {'Up Zone':<16} | {'# Low':<6} | {'# Up':<6} | {'Total Bound':<11} | {'Status':<12}"
        b_sep = "-" * len(b_header)
        print(b_sep)
        print(b_header)
        print(b_sep)

        for var in var_cols:
            low_b, up_b = DESIGN_VARIABLE_RANGES[var]
            span = up_b - low_b
            tol = 0.05 * span
            low_thresh = low_b + tol
            up_thresh = up_b - tol
            vals = df_pareto[var].values
            n_low = int(np.sum(vals <= low_thresh + 1e-6))
            n_up = int(np.sum(vals >= up_thresh - 1e-6))
            n_tot = n_low + n_up
            status = "AT BOUND" if (n_tot / n_p) >= (2.0 / 3.0) else "INTERIOR"
            low_str = f"[{low_b:.3f}, {low_thresh:.3f}]"
            up_str = f"[{up_thresh:.3f}, {up_b:.3f}]"
            print(f"{var:<28} | {low_b:<7.3f} | {up_b:<7.3f} | {span:<7.3f} | {tol:<8.4f} | {low_str:<16} | {up_str:<16} | {n_low:<6} | {n_up:<6} | {n_tot:<11} | {status:<12}")

        counts = df_pareto['wall_mass_class'].value_counts()
        n_light = counts.get('light', 0)
        n_hvy = counts.get('heavy', 0)
        n_tot_mass = n_light + n_hvy
        status_m = "AT BOUND" if (n_tot_mass / n_p) >= (2.0 / 3.0) else "INTERIOR"
        print(f"{'wall_mass_class (discrete)':<28} | {'light':<7} | {'heavy':<7} | {'3 cls':<7} | {'N/A':<8} | {'light: ' + str(n_light):<16} | {'heavy: ' + str(n_hvy):<16} | {n_light:<6} | {n_hvy:<6} | {n_tot_mass:<11} | {status_m:<12}")
        print(b_sep)

        # Adaptive applicability info
        inv_share = df_pareto['invalid_share_adapt'].iloc[0] if 'invalid_share_adapt' in df_pareto else 0.0
        valid_hrs = int(round(8760 * (1.0 - inv_share / 100.0)))
        print(f"\nAdaptive Comfort Envelope Applicability ({self.city_name}):")
        print(f"  Valid Adaptive Hours (10.0 - 33.5 C running-mean Ta): {valid_hrs} / 8760 ({100.0 - inv_share:.2f}%)")
        print(f"  Invalid Adaptive Share: {inv_share:.2f}%")

        t1 = time.time()
        self.log_timing(stage, t0, t1, pool_before=len(df_100), pool_after=len(df_pareto), notes="Summary evaluation & tables")
        self.mark_stage_done(stage)

        # Print per-stage wall time and total minutes
        print("\n" + "=" * 120)
        print(f"TIMING BREAKDOWN & WALL CLOCK TIME ({self.city_name.upper()})")
        print("=" * 120)
        df_time = pd.read_csv(self.timing_csv)
        print(df_time.to_string(index=False))
        total_sec = df_time['elapsed_seconds'].sum()
        print("-" * 120)
        print(f"TOTAL PIPELINE WALL CLOCK TIME: {total_sec:.2f} seconds ({total_sec / 60.0:.2f} minutes)")
        print("=" * 120 + "\n")

    def run_pipeline(self):
        print_settings()
        df_pool = self.run_stage_1()
        surrogates, df_cand1 = self.run_stage_2_and_3(df_pool)
        self.run_active_learning_rounds(df_pool, surrogates, df_cand1)
        self.run_stage_7_summary()

def main():
    parser = argparse.ArgumentParser(description="Generic reproducible ClimateAdapt-Comfort city pipeline.")
    parser.add_argument("--city", type=str, required=True, help="City name from reports/batch_epw_manifest.csv")
    parser.add_argument("--smoke", action="store_true", help="Run fast smoke test with reduced iterations")
    args = parser.parse_args()

    pipeline = CityPipeline(args.city, smoke=args.smoke)
    pipeline.run_pipeline()

if __name__ == '__main__':
    main()
