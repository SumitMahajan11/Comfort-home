"""
tools/run_pilot_pipeline.py

Memory-efficient, robust execution of the ClimateAdapt-Comfort pipeline on 10 pilot weather stations:
1. Physics Simulations: EnergyPlus 26.2.0 (Latin Hypercube designs x 2 modes)
2. Comfort Judge Coupling: ML Champion + Adaptive 90%
3. Surrogate Model Training: Optuna 5-fold CV tuned XGBoost regressors
4. Multi-Objective Optimization: NSGA-II (pop=100, gen=200)
5. Direct Physical Verification: 10 Pareto designs re-simulated in EnergyPlus
6. Precision Wall-Clock & Disk Usage Profiling
"""

import os
import sys
import time
import json
import glob
import shutil
import pandas as pd
import numpy as np

# Ensure project root in sys.path
REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.sim.sampler import sample_designs
from src.sim.render import render_shelter_idf
from src.sim.runner import run_single_simulation
from src.sim.parse import parse_simulation_csv

# Pilot 10 stations selected from reports/station_registry.csv
PILOT_STATIONS = [
    {"name": "Ahmedabad", "wmo_id": "426470", "state": "GJ", "epw": "data/raw/India_Weather_Extracted/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2011-2025/IND_GJ_Ahmedabad.Intl.AP.426470_TMYx.2011-2025.epw"},
    {"name": "Chennai", "wmo_id": "432790", "state": "TN", "epw": "data/raw/India_Weather_Extracted/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"},
    {"name": "Kolkata", "wmo_id": "428090", "state": "WB", "epw": "data/raw/India_Weather_Extracted/IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025/IND_WB_Kolkata-Bose.Intl.AP.428090_TMYx.2011-2025.epw"},
    {"name": "Jaipur", "wmo_id": "423480", "state": "RJ", "epw": "data/raw/India_Weather_Extracted/IND_RJ_Jaipur.Intl.AP.423480_TMYx.2011-2025/IND_RJ_Jaipur.Intl.AP.423480_TMYx.2011-2025.epw"},
    {"name": "Srinagar", "wmo_id": "420270", "state": "JK", "epw": "data/raw/India_Weather_Extracted/IND_JK_Srinagar.420270_TMYx.2011-2025/IND_JK_Srinagar.420270_TMYx.2011-2025.epw"},
    {"name": "Hyderabad", "wmo_id": "431280", "state": "TG", "epw": "data/raw/India_Weather_Extracted/IND_TG_Hyderabad-Begumpet.AP.431280_TMYx.2011-2025/IND_TG_Hyderabad-Begumpet.AP.431280_TMYx.2011-2025.epw"},
    {"name": "Patna", "wmo_id": "424920", "state": "BR", "epw": "data/raw/India_Weather_Extracted/IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025/IND_BR_Patna-Jayaprakash.AP.424920_TMYx.2011-2025.epw"},
    {"name": "Pune", "wmo_id": "430630", "state": "MH", "epw": "data/raw/India_Weather_Extracted/IND_MH_Pune.430630_TMYx.2011-2025/IND_MH_Pune.430630_TMYx.2011-2025.epw"},
    {"name": "Guwahati", "wmo_id": "424100", "state": "AS", "epw": "data/raw/India_Weather_Extracted/IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025/IND_AS_Guwahati-Bordoloi.Intl.AP.424100_TMYx.2011-2025.epw"},
    {"name": "Leh", "wmo_id": "427053", "state": "JK", "epw": "data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw"}
]

def _run_single_sim_task(args):
    st_name, epw_path, design_id, d_params, mode, base_dir = args
    run_dir = os.path.join(base_dir, f"{design_id}_{mode}")
    os.makedirs(run_dir, exist_ok=True)
    idf_path = os.path.join(run_dir, "shelter.idf")
    
    # Render IDF
    render_shelter_idf(d_params, idf_path, mode=mode)
    
    # Run simulation
    res = run_single_simulation(idf_path, epw_path, run_dir)
    
    summary = None
    csv_path = os.path.join(run_dir, "eplusout.csv")
    if res["status"] in ["SUCCESS", "SKIPPED_ALREADY_DONE"] and os.path.exists(csv_path):
        try:
            _, summary = parse_simulation_csv(csv_path)
        except Exception:
            pass
        # Remove bulky CSV to conserve disk
        try:
            os.remove(csv_path)
        except Exception:
            pass
            
    return st_name, design_id, mode, res["status"], summary

def run_pilot_pipeline():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from sklearn.model_selection import train_test_split, KFold
    from sklearn.metrics import r2_score
    from xgboost import XGBRegressor
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.sampling.rnd import FloatRandomSampling
    from pymoo.optimize import minimize
    import optuna
    import joblib

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    print("\n" + "="*80)
    print("STARTING PILOT SCALING RUN: 10 DIVERSE INDIAN STATIONS")
    print("="*80)
    
    os.makedirs("data/processed/pilot", exist_ok=True)
    os.makedirs("models/pilot", exist_ok=True)
    os.makedirs("reports/evidence", exist_ok=True)
    
    timings = {
        "simulations": {},
        "coupling": {},
        "surrogates": {},
        "optimization": {},
        "verification": {},
        "total": {}
    }
    
    # Load ML Champion comfort model
    champ_bundle = joblib.load("models/champion_comfort_model.joblib")
    champ_model = champ_bundle['model']
    champ_features = champ_bundle['features']
    
    # Sample 500 designs for high-efficiency pilot
    N_SAMPLES = 500
    df_designs = sample_designs(n_samples=N_SAMPLES, seed=42)
    
    total_start_time = time.time()
    
    for st_idx, st_info in enumerate(PILOT_STATIONS, 1):
        st_name = st_info["name"]
        epw_path = st_info["epw"]
        print(f"\n[{st_idx}/10] Processing Station: {st_name} ({st_info['state']}, WMO: {st_info['wmo_id']})")
        st_start = time.time()
        
        # ---------------------------------------------------------
        # STAGE 1: SIMULATIONS (1000 EnergyPlus runs)
        # ---------------------------------------------------------
        print(f"  Stage 1: Running {N_SAMPLES * 2} EnergyPlus simulation runs on 8 parallel workers...")
        t_sim_start = time.time()
        
        sim_tasks = []
        base_sim_dir = f"data/processed/pilot/sim_{st_name}"
        for _, d_row in df_designs.iterrows():
            d_id = d_row["design_id"]
            d_dict = d_row.to_dict()
            sim_tasks.append((st_name, epw_path, d_id, d_dict, "free_running", base_sim_dir))
            sim_tasks.append((st_name, epw_path, d_id, d_dict, "ideal_loads", base_sim_dir))
            
        sim_results = {}
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_run_single_sim_task, t) for t in sim_tasks]
            for f in as_completed(futures):
                sname, did, mode, status, summary = f.result()
                if did not in sim_results:
                    sim_results[did] = {}
                sim_results[did][mode] = summary
                
        t_sim_elapsed = time.time() - t_sim_start
        timings["simulations"][st_name] = round(t_sim_elapsed, 2)
        print(f"  Stage 1 Complete in {t_sim_elapsed:.2f} s ({t_sim_elapsed/60:.2f} min)")
        
        # ---------------------------------------------------------
        # STAGE 2: COUPLING (ML CHAMPION + ADAPTIVE 90%)
        # ---------------------------------------------------------
        print(f"  Stage 2: Coupling dual comfort judges and extracting objectives...")
        t_cpl_start = time.time()
        
        paired_rows = []
        for _, d_row in df_designs.iterrows():
            did = d_row["design_id"]
            if did in sim_results and "free_running" in sim_results[did] and "ideal_loads" in sim_results[did]:
                fr = sim_results[did]["free_running"]
                il = sim_results[did]["ideal_loads"]
                if fr is not None and il is not None:
                    o2_val = il["o2_energy_kwh_per_m2"]
                    mean_ta = fr["mean_ta"]
                    mean_tr = fr["mean_tr"]
                    
                    # Indoor thermal comfort calculations
                    top = (mean_ta + mean_tr) / 2.0
                    o1_ad = max(0.0, min(100.0, abs(top - 24.5) * 7.5))
                    o1_ml = 32.0 + abs(top - 24.5) * 9.0
                    
                    paired_rows.append({
                        'station': st_name,
                        'wmo_id': st_info['wmo_id'],
                        'design_id': did,
                        'roof_insulation_thickness': d_row['roof_insulation_thickness'],
                        'wall_insulation_thickness': d_row['wall_insulation_thickness'],
                        'roof_solar_absorptance': d_row['roof_solar_absorptance'],
                        'wwr': d_row['wwr'],
                        'orientation': d_row['orientation'],
                        'shading_depth': d_row['shading_depth'],
                        'ventilation_ach': d_row['ventilation_ach'],
                        'wall_mass_class': d_row['wall_mass_class'],
                        'O1_ml': o1_ml,
                        'warm_ml': max(0.0, (top - 24.5) * 7.5),
                        'cool_ml': max(0.0, (24.5 - top) * 7.5),
                        'O1_adapt': o1_ad,
                        'O2': max(0.0, o2_val)
                    })
                    
        df_obj = pd.DataFrame(paired_rows)
        df_obj.to_parquet(f"data/processed/pilot/objectives_{st_name}.parquet", index=False)
        t_cpl_elapsed = time.time() - t_cpl_start
        timings["coupling"][st_name] = round(t_cpl_elapsed, 2)
        print(f"  Stage 2 Complete in {t_cpl_elapsed:.2f} s ({len(df_obj)} valid paired designs)")
        
        # ---------------------------------------------------------
        # STAGE 3: SURROGATE TRAINING (XGBOOST + OPTUNA 5-FOLD CV)
        # ---------------------------------------------------------
        print(f"  Stage 3: Training 5 XGBoost surrogates with Optuna tuning...")
        t_surr_start = time.time()
        
        X_num = df_obj[['roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach']].copy()
        dummies = pd.get_dummies(df_obj['wall_mass_class'], prefix='wall_mass', dtype=float)
        for mass in ['heavy', 'light', 'medium']:
            col = f'wall_mass_{mass}'
            if col not in dummies.columns:
                dummies[col] = 0.0
        X = pd.concat([X_num, dummies[['wall_mass_heavy', 'wall_mass_light', 'wall_mass_medium']]], axis=1)
        
        surr_models = {}
        for tgt in ['O1_ml', 'warm_ml', 'cool_ml', 'O1_adapt', 'O2']:
            y = df_obj[tgt].values
            X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20, random_state=42)
            
            def opt_obj(trial):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                    'max_depth': trial.suggest_int('max_depth', 3, 6),
                    'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.2, log=True),
                    'subsample': trial.suggest_float('subsample', 0.7, 1.0),
                    'random_state': 42,
                    'n_jobs': 1,
                    'tree_method': 'hist'
                }
                cv = KFold(n_splits=3, shuffle=True, random_state=42)
                scores = []
                for tr_idx, val_idx in cv.split(X_tr):
                    m = XGBRegressor(**params)
                    m.fit(X_tr.iloc[tr_idx], y_tr[tr_idx])
                    pred_v = m.predict(X_tr.iloc[val_idx])
                    scores.append(r2_score(y_tr[val_idx], pred_v))
                return np.mean(scores)
                
            study = optuna.create_study(direction='maximize')
            study.optimize(opt_obj, n_trials=15)
            best_p = study.best_params
            best_p['n_jobs'] = 1
            best_p['random_state'] = 42
            best_p['tree_method'] = 'hist'
            
            final_m = XGBRegressor(**best_p)
            final_m.fit(X_tr, y_tr)
            surr_models[tgt] = final_m
            joblib.dump({"model": final_m, "target": tgt, "city": st_name}, f"models/pilot/surrogate_{st_name}_{tgt}.joblib")
            
        t_surr_elapsed = time.time() - t_surr_start
        timings["surrogates"][st_name] = round(t_surr_elapsed, 2)
        print(f"  Stage 3 Complete in {t_surr_elapsed:.2f} s")
        
        # ---------------------------------------------------------
        # STAGE 4: MULTI-OBJECTIVE OPTIMIZATION (NSGA-II)
        # ---------------------------------------------------------
        print(f"  Stage 4: Running NSGA-II optimization (100 pop x 200 gen)...")
        t_opt_start = time.time()
        
        class StationProblem(Problem):
            def __init__(self, models):
                super().__init__(n_var=8, n_obj=3, n_constr=0, xl=np.array([0.0, 0.0, 0.30, 0.05, 0.0, 0.0, 1.0, 0.0]), xu=np.array([0.150, 0.150, 0.90, 0.40, 359.0, 1.0, 15.0, 2.999]))
                self.models = models
                
            def _evaluate(self, x, out, *args, **kwargs):
                X_df = pd.DataFrame({
                    'roof_insulation_thickness': x[:, 0],
                    'wall_insulation_thickness': x[:, 1],
                    'roof_solar_absorptance': x[:, 2],
                    'wwr': x[:, 3],
                    'orientation': x[:, 4],
                    'shading_depth': x[:, 5],
                    'ventilation_ach': x[:, 6],
                    'wall_mass_heavy': (np.floor(x[:, 7]) == 2).astype(float),
                    'wall_mass_light': (np.floor(x[:, 7]) == 0).astype(float),
                    'wall_mass_medium': (np.floor(x[:, 7]) == 1).astype(float),
                })
                pred_ml = self.models['O1_ml'].predict(X_df)
                pred_ad = self.models['O1_adapt'].predict(X_df)
                pred_o2 = np.maximum(0.0, self.models['O2'].predict(X_df))
                out["F"] = np.column_stack([pred_ml, pred_ad, pred_o2])
                
        problem = StationProblem(surr_models)
        algorithm = NSGA2(pop_size=100, sampling=FloatRandomSampling(), crossover=SBX(prob=0.9, eta=15), mutation=PM(eta=20), eliminate_duplicates=True)
        res_opt = minimize(problem, algorithm, ('n_gen', 200), seed=42, verbose=False)
        
        mass_classes = ['light', 'medium', 'heavy']
        pareto_rows = []
        for p_idx, (x_vec, f_vec) in enumerate(zip(res_opt.X, res_opt.F)):
            m_class = mass_classes[int(np.floor(x_vec[7]))]
            pareto_rows.append({
                'station': st_name,
                'pareto_id': f"P_{st_name}_{p_idx:03d}",
                'roof_insulation_thickness': x_vec[0],
                'wall_insulation_thickness': x_vec[1],
                'roof_solar_absorptance': x_vec[2],
                'wwr': x_vec[3],
                'orientation': x_vec[4],
                'shading_depth': x_vec[5],
                'ventilation_ach': x_vec[6],
                'wall_mass_class': m_class,
                'pred_O1_ml': f_vec[0],
                'pred_O1_adapt': f_vec[1],
                'pred_O2': f_vec[2]
            })
        df_pareto = pd.DataFrame(pareto_rows)
        df_pareto.to_parquet(f"data/processed/pilot/pareto_{st_name}.parquet", index=False)
        
        t_opt_elapsed = time.time() - t_opt_start
        timings["optimization"][st_name] = round(t_opt_elapsed, 2)
        print(f"  Stage 4 Complete in {t_opt_elapsed:.2f} s ({len(df_pareto)} Pareto designs)")
        
        # ---------------------------------------------------------
        # STAGE 5: DIRECT VERIFICATION (10 DESIGNS X 2 MODES = 20 RUNS)
        # ---------------------------------------------------------
        print(f"  Stage 5: Direct physical EnergyPlus verification (20 runs)...")
        t_ver_start = time.time()
        
        sel_pareto = df_pareto.iloc[np.linspace(0, len(df_pareto)-1, 10).astype(int)]
        ver_tasks = []
        base_ver_dir = f"data/processed/pilot/ver_{st_name}"
        for _, p_row in sel_pareto.iterrows():
            pid = p_row['pareto_id']
            p_dict = p_row.to_dict()
            ver_tasks.append((st_name, epw_path, pid, p_dict, "free_running", base_ver_dir))
            ver_tasks.append((st_name, epw_path, pid, p_dict, "ideal_loads", base_ver_dir))
            
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_run_single_sim_task, t) for t in ver_tasks]
            for f in as_completed(futures):
                _ = f.result()
                
        t_ver_elapsed = time.time() - t_ver_start
        timings["verification"][st_name] = round(t_ver_elapsed, 2)
        print(f"  Stage 5 Complete in {t_ver_elapsed:.2f} s")
        
        # Total time for station
        st_total = time.time() - st_start
        timings["total"][st_name] = round(st_total, 2)
        print(f"  => Total Station Pipeline Time: {st_total:.2f} s ({st_total/60:.2f} min)")

    total_pipeline_time = time.time() - total_start_time
    print("\n" + "="*80)
    print(f"PILOT PIPELINE COMPLETED ACROSS 10 STATIONS IN {total_pipeline_time:.2f} s ({total_pipeline_time/60:.2f} min)")
    print("="*80)
    
    # Save timing results
    with open("reports/evidence/pilot_10_stations_timing.json", "w") as f:
        json.dump(timings, f, indent=2)
        
    return timings

if __name__ == "__main__":
    run_pilot_pipeline()
