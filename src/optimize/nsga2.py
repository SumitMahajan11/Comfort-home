"""
Phase 5: NSGA-II Multi-Objective Optimization, Pareto Frontier Derivation,
Direct EnergyPlus Verification, and S3 Criterion Evaluation.
"""

import os
import sys
import json
import time
import shutil
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed
from sklearn.cluster import KMeans

from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

sys.path.insert(0, os.path.abspath("."))

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

CITIES_EPW = {
    "Jodhpur": "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx/IND_RJ_Jodhpur.423390_TMYx.epw",
    "Mumbai": "data/raw/India_Weather_Extracted/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx/IND_MH_Mumbai-Shivaji.Intl.AP.430030_TMYx.epw",
    "New_Delhi": "data/raw/India_Weather_Extracted/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx/IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.epw",
    "Bengaluru": "data/raw/India_Weather_Extracted/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx/IND_KA_Bengaluru-Hindustan.AP.432960_TMYx.epw",
    "Shimla": "data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw"
}

MASS_CLASSES = ['heavy', 'light', 'medium'] # Map 0->heavy, 1->light, 2->medium

class ShelterOptimizationProblem(ElementwiseProblem):
    def __init__(self, city_name, surrogate_models):
        """
        Decision Variables (8):
        0: roof_insulation_thickness [0.0, 0.15]
        1: wall_insulation_thickness [0.0, 0.15]
        2: roof_solar_absorptance [0.30, 0.90]
        3: wwr [0.05, 0.40]
        4: orientation [0.0, 359.0]
        5: shading_depth [0.0, 1.0]
        6: ventilation_ach [1.0, 15.0]
        7: wall_mass_class (discrete 0=heavy, 1=light, 2=medium) [0.0, 2.999]
        
        Objectives (3 to minimize):
        0: O1_ml
        1: O1_adapt
        2: O2
        """
        self.city_name = city_name
        self.surrogates = surrogate_models
        
        xl = np.array([0.0,  0.0,  0.30, 0.05,   0.0, 0.0,  1.0, 0.0])
        xu = np.array([0.15, 0.15, 0.90, 0.40, 359.0, 1.0, 15.0, 2.999])
        
        super().__init__(n_var=8, n_obj=3, n_ieq_constr=0, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        mass_idx = int(np.floor(x[7]))
        mass_idx = min(2, max(0, mass_idx))
        
        # Build feature dataframe matching surrogate feature_names
        # ['roof_insulation_thickness', 'wall_insulation_thickness', 'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach', 'wall_mass_heavy', 'wall_mass_light', 'wall_mass_medium']
        feat_dict = {
            'roof_insulation_thickness': [float(x[0])],
            'wall_insulation_thickness': [float(x[1])],
            'roof_solar_absorptance': [float(x[2])],
            'wwr': [float(x[3])],
            'orientation': [float(x[4])],
            'shading_depth': [float(x[5])],
            'ventilation_ach': [float(x[6])],
            'wall_mass_heavy': [1.0 if mass_idx == 0 else 0.0],
            'wall_mass_light': [1.0 if mass_idx == 1 else 0.0],
            'wall_mass_medium': [1.0 if mass_idx == 2 else 0.0]
        }
        df_feat = pd.DataFrame(feat_dict)
        
        o1_ml = float(self.surrogates['O1_ml'].predict(df_feat)[0])
        o1_adapt = float(self.surrogates['O1_adapt'].predict(df_feat)[0])
        o2 = float(self.surrogates['O2'].predict(df_feat)[0])
        
        out["F"] = [o1_ml, o1_adapt, o2]

def run_nsga2_for_city(city_name, pop_size=100, n_gen=200, seed=42):
    print(f"\n[NSGA-II] Running optimization for {city_name} (Pop={pop_size}, Gen={n_gen}, Seed={seed})...")
    
    # Load surrogates
    surrogates = {}
    for tgt in ['O1_ml', 'O1_adapt', 'O2', 'warm_ml', 'cool_ml']:
        m_path = f"models/surrogate_{city_name}_{tgt}.joblib"
        art = joblib.load(m_path)
        surrogates[tgt] = art['model']
        
    problem = ShelterOptimizationProblem(city_name, surrogates)
    
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.2, eta=20),
        eliminate_duplicates=True
    )
    
    res = minimize(
        problem,
        algorithm,
        ('n_gen', n_gen),
        seed=seed,
        verbose=False
    )
    
    # Extract Pareto front solutions
    pareto_X = res.X
    pareto_F = res.F
    
    # Check applicability flags
    app_df = pd.read_csv("data/processed/applicability.csv").set_index('city')
    ml_flag = bool(app_df.loc[city_name, 'ml_flagged_under_80pct'])
    adapt_flag = bool(app_df.loc[city_name, 'adaptive_flagged_under_80pct'])
    
    records = []
    for i in range(len(pareto_X)):
        x = pareto_X[i]
        f = pareto_F[i]
        mass_idx = int(np.floor(x[7]))
        mass_idx = min(2, max(0, mass_idx))
        mass_str = MASS_CLASSES[mass_idx]
        
        records.append({
            'city': city_name,
            'pareto_id': f"P_{city_name}_{i:03d}",
            'roof_insulation_thickness': float(x[0]),
            'wall_insulation_thickness': float(x[1]),
            'wall_mass_class': mass_str,
            'roof_solar_absorptance': float(x[2]),
            'wwr': float(x[3]),
            'orientation': float(x[4]),
            'shading_depth': float(x[5]),
            'ventilation_ach': float(x[6]),
            'pred_O1_ml': float(f[0]),
            'pred_O1_adapt': float(f[1]),
            'pred_O2': float(f[2]),
            'ml_confidence_flag': "LOW_CONFIDENCE" if ml_flag else "STANDARD",
            'adaptive_confidence_flag': "LOW_CONFIDENCE" if adapt_flag else "STANDARD"
        })
        
    df_pareto = pd.DataFrame(records)
    out_parquet = f"data/processed/pareto_{city_name}.parquet"
    df_pareto.to_parquet(out_parquet, index=False)
    print(f"  -> Derived {len(df_pareto)} non-dominated Pareto designs for {city_name}. Saved {out_parquet}")
    return df_pareto, surrogates

def select_10_verification_designs(df_pareto):
    """
    Selects 10 representative designs from the Pareto front:
    1. Best O1_ml
    2. Best O1_adapt
    3. Best O2
    4. Knee point (minimum Euclidean distance to normalized utopia point)
    5. 6 evenly spread designs along front via KMeans
    """
    selected_indices = []
    
    # 1. Best O1_ml
    idx_best_ml = int(df_pareto['pred_O1_ml'].idxmin())
    selected_indices.append(idx_best_ml)
    
    # 2. Best O1_adapt
    idx_best_adapt = int(df_pareto['pred_O1_adapt'].idxmin())
    if idx_best_adapt not in selected_indices:
        selected_indices.append(idx_best_adapt)
        
    # 3. Best O2
    idx_best_o2 = int(df_pareto['pred_O2'].idxmin())
    if idx_best_o2 not in selected_indices:
        selected_indices.append(idx_best_o2)
        
    # 4. Knee Point
    F = df_pareto[['pred_O1_ml', 'pred_O1_adapt', 'pred_O2']].values
    f_min = F.min(axis=0)
    f_max = F.max(axis=0)
    denom = np.where(f_max - f_min == 0, 1.0, f_max - f_min)
    F_norm = (F - f_min) / denom
    dist_utopia = np.linalg.norm(F_norm, axis=1)
    idx_knee = int(np.argmin(dist_utopia))
    if idx_knee not in selected_indices:
        selected_indices.append(idx_knee)
        
    # 5. Remaining spread designs via KMeans on F_norm
    n_remain = 10 - len(selected_indices)
    if len(df_pareto) > 10:
        # Cluster the remaining designs
        remain_mask = ~df_pareto.index.isin(selected_indices)
        remain_idx = df_pareto.index[remain_mask].values
        F_remain = F_norm[remain_mask]
        
        kmeans = KMeans(n_clusters=n_remain, random_state=42, n_init=10)
        kmeans.fit(F_remain)
        for c in kmeans.cluster_centers_:
            closest = remain_idx[np.argmin(np.linalg.norm(F_remain - c, axis=1))]
            if closest not in selected_indices:
                selected_indices.append(int(closest))
                
    # If still fewer than 10, fill with evenly spaced
    if len(selected_indices) < 10:
        for idx in df_pareto.index:
            if idx not in selected_indices:
                selected_indices.append(int(idx))
            if len(selected_indices) == 10:
                break
                
    df_selected = df_pareto.loc[selected_indices[:10]].copy()
    df_selected['selection_role'] = [
        'Best_O1_ml', 'Best_O1_adapt', 'Best_O2', 'Knee_Point'
    ] + [f'Spread_{i+1}' for i in range(len(df_selected) - 4)]
    return df_selected

def run_direct_energyplus_verification(df_all_selected):
    print("\n" + "="*80)
    print(f"RUNNING DIRECT ENERGYPLUS VERIFICATION FOR {len(df_all_selected)} SELECTED PARETO DESIGNS")
    print("="*80)
    
    temp_work = "data/processed/temp_pareto_verification"
    os.makedirs(temp_work, exist_ok=True)
    
    model = load_champion_model()
    verified_records = []
    
    for _, row in df_all_selected.iterrows():
        city = row['city']
        p_id = row['pareto_id']
        epw = CITIES_EPW[city]
        
        p = {
            'roof_insulation_thickness': float(row['roof_insulation_thickness']),
            'wall_insulation_thickness': float(row['wall_insulation_thickness']),
            'wall_mass_class': str(row['wall_mass_class']),
            'roof_solar_absorptance': float(row['roof_solar_absorptance']),
            'wwr': float(row['wwr']),
            'orientation': float(row['orientation']),
            'shading_depth': float(row['shading_depth']),
            'ventilation_ach': float(row['ventilation_ach'])
        }
        
        run_dir = os.path.join(temp_work, f"{city}_{p_id}")
        dir_fr = os.path.join(run_dir, "fr")
        dir_il = os.path.join(run_dir, "il")
        os.makedirs(dir_fr, exist_ok=True)
        os.makedirs(dir_il, exist_ok=True)
        
        # 1. Free running
        idf_fr = os.path.join(dir_fr, "shelter.idf")
        render_shelter_idf(p, idf_fr, mode='free_running')
        res_fr = run_single_simulation(idf_fr, epw, dir_fr)
        if res_fr['status'] != 'SUCCESS':
            raise RuntimeError(f"Verification failed on {city} {p_id} free-running: {res_fr.get('error_summary')}")
            
        csv_fr = os.path.join(dir_fr, "eplusout.csv")
        hdf_fr, sm_fr = parse_simulation_csv(csv_fr)
        
        ta = hdf_fr['ta'].values.astype(np.float32)
        tr = hdf_fr['tr'].values.astype(np.float32)
        rh = hdf_fr['rh'].values.astype(np.float32)
        tout = hdf_fr['t_out'].values.astype(np.float32)
        
        # 2. Ideal loads
        idf_il = os.path.join(dir_il, "shelter.idf")
        render_shelter_idf(p, idf_il, mode='ideal_loads')
        res_il = run_single_simulation(idf_il, epw, dir_il)
        if res_il['status'] != 'SUCCESS':
            raise RuntimeError(f"Verification failed on {city} {p_id} ideal-loads: {res_il.get('error_summary')}")
            
        csv_il = os.path.join(dir_il, "eplusout.csv")
        hdf_il, sm_il = parse_simulation_csv(csv_il)
        act_o2 = float(sm_il['o2_energy_kwh_per_m2'])
        
        # Coupling
        daily_tout = calculate_daily_mean_series(tout)
        t_rm_daily = compute_running_mean_outdoor_temperature_db2(daily_tout, alpha=0.8)
        t_rm_hourly = np.repeat(t_rm_daily, 24)
        clo_hourly = compute_clo_schedule_a004(daily_tout)
        
        adapt_res = evaluate_adaptive_90_comfort(ta, tr, t_rm_hourly)
        ml_res = evaluate_ml_champion_comfort(
            model=model, ta=ta, tr=tr, rh=rh,
            t_outdoor_hourly=t_rm_hourly, clo_hourly=clo_hourly,
            met=1.1, vel=0.15
        )
        
        act_o1_ml = ml_res['O1_ml']
        act_o1_adapt = adapt_res['O1_adapt']
        
        pred_o1_ml = float(row['pred_O1_ml'])
        pred_o1_adapt = float(row['pred_O1_adapt'])
        pred_o2 = float(row['pred_O2'])
        
        # Errors
        err_ml = abs(pred_o1_ml - act_o1_ml)
        err_adapt = abs(pred_o1_adapt - act_o1_adapt)
        err_o2 = abs(pred_o2 - act_o2)
        
        rel_ml = (err_ml / act_o1_ml * 100.0) if act_o1_ml > 0 else 0.0
        rel_adapt = (err_adapt / act_o1_adapt * 100.0) if act_o1_adapt > 0 else 0.0
        rel_o2 = (err_o2 / act_o2 * 100.0) if act_o2 > 0 else 0.0
        
        shutil.rmtree(run_dir, ignore_errors=True)
        
        verified_records.append({
            'city': city,
            'pareto_id': p_id,
            'selection_role': row['selection_role'],
            **p,
            'pred_O1_ml': pred_o1_ml,
            'actual_O1_ml': act_o1_ml,
            'abs_err_O1_ml': err_ml,
            'rel_err_O1_ml_pct': rel_ml,
            'pred_O1_adapt': pred_o1_adapt,
            'actual_O1_adapt': act_o1_adapt,
            'abs_err_O1_adapt': err_adapt,
            'rel_err_O1_adapt_pct': rel_adapt,
            'pred_O2': pred_o2,
            'actual_O2': act_o2,
            'abs_err_O2': err_o2,
            'rel_err_O2_pct': rel_o2,
            'ml_confidence_flag': row['ml_confidence_flag'],
            'adaptive_confidence_flag': row['adaptive_confidence_flag']
        })
        
    shutil.rmtree(temp_work, ignore_errors=True)
    df_ver = pd.DataFrame(verified_records)
    out_ver_csv = "data/processed/pareto_verification_results.csv"
    df_ver.to_csv(out_ver_csv, index=False)
    print(f"\nSaved verified Pareto results (50 runs) to {out_ver_csv}")
    return df_ver

def evaluate_s3_criterion(df_verified):
    print("\n" + "="*80)
    print("STEP 4: EVALUATING SUCCESS CRITERION S3 (Beat Both R1 & R2 on All 3 Objectives)")
    print("="*80)
    
    df_refs = pd.read_csv("data/processed/reference_results.csv").set_index(['city', 'reference_name'])
    
    s3_records = []
    
    for city in CITIES_EPW.keys():
        r1_o1_ml = df_refs.loc[(city, 'R1_Lightweight'), 'O1_ml']
        r1_o1_ad = df_refs.loc[(city, 'R1_Lightweight'), 'O1_adapt']
        r1_o2 = df_refs.loc[(city, 'R1_Lightweight'), 'O2']
        
        r2_o1_ml = df_refs.loc[(city, 'R2_Conventional'), 'O1_ml']
        r2_o1_ad = df_refs.loc[(city, 'R2_Conventional'), 'O1_adapt']
        r2_o2 = df_refs.loc[(city, 'R2_Conventional'), 'O2']
        
        # Max of reference baselines (to beat BOTH, design must be strictly lower than min(R1, R2))
        bench_o1_ml = min(r1_o1_ml, r2_o1_ml)
        bench_o1_ad = min(r1_o1_ad, r2_o1_ad)
        bench_o2 = min(r1_o2, r2_o2)
        
        c_ver = df_verified[df_verified['city'] == city]
        
        # Check designs beating both R1 and R2 simultaneously on all 3 objectives
        beat_mask = (
            (c_ver['actual_O1_ml'] < bench_o1_ml) &
            (c_ver['actual_O1_adapt'] < bench_o1_ad) &
            (c_ver['actual_O2'] < bench_o2)
        )
        n_beating = int(beat_mask.sum())
        s3_pass = n_beating >= 1
        
        # Best margin design
        if s3_pass:
            best_d = c_ver[beat_mask].iloc[0]
            margin_ml = bench_o1_ml - best_d['actual_O1_ml']
            margin_ad = bench_o1_ad - best_d['actual_O1_adapt']
            margin_o2 = bench_o2 - best_d['actual_O2']
            best_pid = best_d['pareto_id']
        else:
            best_pid = "None"
            margin_ml = np.nan
            margin_ad = np.nan
            margin_o2 = np.nan
            
        print(f"\nCity: {city:12s} | S3 Status: {'PASS' if s3_pass else 'FAIL'} | Verified Designs Beating Both: {n_beating}/10")
        print(f"  Ref R1 : O1_ml={r1_o1_ml:5.2f}%, O1_ad={r1_o1_ad:5.2f}%, O2={r1_o2:6.2f} kWh/m2")
        print(f"  Ref R2 : O1_ml={r2_o1_ml:5.2f}%, O1_ad={r2_o1_ad:5.2f}%, O2={r2_o2:6.2f} kWh/m2")
        print(f"  Target Benchmark (Min R1,R2): O1_ml={bench_o1_ml:5.2f}%, O1_ad={bench_o1_ad:5.2f}%, O2={bench_o2:6.2f} kWh/m2")
        if s3_pass:
            print(f"  Best Pareto Design {best_pid}: Actual O1_ml={best_d['actual_O1_ml']:5.2f}% (-{margin_ml:.2f}%), O1_ad={best_d['actual_O1_adapt']:5.2f}% (-{margin_ad:.2f}%), O2={best_d['actual_O2']:6.2f} (-{margin_o2:.2f} kWh/m2)")
            
        s3_records.append({
            'city': city,
            's3_status': 'PASS' if s3_pass else 'FAIL',
            'n_designs_beating_both': n_beating,
            'best_pareto_id': best_pid,
            'ref_min_O1_ml': bench_o1_ml,
            'ref_min_O1_adapt': bench_o1_ad,
            'ref_min_O2': bench_o2,
            'margin_O1_ml_pct': margin_ml,
            'margin_O1_adapt_pct': margin_ad,
            'margin_O2_kwh_per_m2': margin_o2
        })
        
    df_s3 = pd.DataFrame(s3_records)
    df_s3.to_csv("data/processed/s3_evaluation_results.csv", index=False)
    return df_s3

def generate_pareto_plots(df_verified, df_refs):
    print("\n" + "="*80)
    print("STEP 6: GENERATING PARETO FRONTIER PLOTS (PNG)")
    print("="*80)
    os.makedirs("reports/figures", exist_ok=True)
    
    for city in CITIES_EPW.keys():
        pareto_parquet = f"data/processed/pareto_{city}.parquet"
        df_p = pd.read_parquet(pareto_parquet)
        c_ver = df_verified[df_verified['city'] == city]
        c_refs = df_refs[df_refs['city'] == city]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
        
        # Plot 1: O1_ml vs O2
        ax1 = axes[0]
        ax1.scatter(df_p['pred_O1_ml'], df_p['pred_O2'], c='steelblue', alpha=0.6, s=40, label='Pareto Front (Predicted)')
        ax1.scatter(c_ver['actual_O1_ml'], c_ver['actual_O2'], c='crimson', edgecolors='black', s=80, marker='o', label='Verified Pareto (Actual E+)')
        for _, r in c_refs.iterrows():
            marker = 's' if 'R1' in r['reference_name'] else '^'
            color = 'darkorange' if 'R1' in r['reference_name'] else 'purple'
            ax1.scatter(r['O1_ml'], r['O2'], c=color, s=120, marker=marker, edgecolors='black', label=r['reference_name'])
            
        ax1.set_xlabel('O1 (ML Champion Discomfort %)', fontsize=11)
        ax1.set_ylabel('O2 (Annual HVAC Energy, kWh/m²)', fontsize=11)
        ax1.set_title(f'{city} - ML Champion vs Energy', fontsize=12, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='best', fontsize=9)
        
        # Plot 2: O1_adapt vs O2
        ax2 = axes[1]
        ax2.scatter(df_p['pred_O1_adapt'], df_p['pred_O2'], c='teal', alpha=0.6, s=40, label='Pareto Front (Predicted)')
        ax2.scatter(c_ver['actual_O1_adapt'], c_ver['actual_O2'], c='crimson', edgecolors='black', s=80, marker='o', label='Verified Pareto (Actual E+)')
        for _, r in c_refs.iterrows():
            marker = 's' if 'R1' in r['reference_name'] else '^'
            color = 'darkorange' if 'R1' in r['reference_name'] else 'purple'
            ax2.scatter(r['O1_adapt'], r['O2'], c=color, s=120, marker=marker, edgecolors='black', label=r['reference_name'])
            
        ax2.set_xlabel('O1 (Adaptive 90% Discomfort %)', fontsize=11)
        ax2.set_ylabel('O2 (Annual HVAC Energy, kWh/m²)', fontsize=11)
        ax2.set_title(f'{city} - Adaptive 90% vs Energy', fontsize=12, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='best', fontsize=9)
        
        plt.tight_layout()
        fig_path = f"reports/figures/pareto_{city}.png"
        plt.savefig(fig_path)
        plt.close()
        print(f"  -> Saved {fig_path}")

def run_full_optimization_pipeline():
    # 1. Run Reference Shelters
    from src.optimize.references import run_reference_simulations
    df_refs = run_reference_simulations()
    
    # 2. Run NSGA-II per city
    selected_designs = []
    for city in CITIES_EPW.keys():
        df_p, _ = run_nsga2_for_city(city, pop_size=100, n_gen=200, seed=42)
        df_10 = select_10_verification_designs(df_p)
        selected_designs.append(df_10)
        
    df_all_selected = pd.concat(selected_designs, ignore_index=True)
    
    # 3. Direct EnergyPlus verification (50 runs)
    df_verified = run_direct_energyplus_verification(df_all_selected)
    
    # 4. S3 Criterion Evaluation
    df_s3 = evaluate_s3_criterion(df_verified)
    
    # 5. Generate Pareto Plots
    generate_pareto_plots(df_verified, df_refs)
    
    # Summary of verification errors
    print("\n" + "="*80)
    print("SURROGATE VERIFICATION ERROR SUMMARY (50 Verified Designs)")
    print("="*80)
    err_summary = df_verified.groupby('city')[['abs_err_O1_ml', 'rel_err_O1_ml_pct', 'abs_err_O1_adapt', 'rel_err_O1_adapt_pct', 'abs_err_O2', 'rel_err_O2_pct']].mean().reset_index()
    print(err_summary.to_string(index=False))
    
    # Save evidence file
    evidence_txt = "reports/evidence/phase5_optimization_output.txt"
    with open(evidence_txt, "w", encoding="utf-8") as f:
        f.write("PHASE 5 OPTIMIZATION EVIDENCE OUTPUT\n")
        f.write("="*80 + "\n\n")
        f.write("S3 EVALUATION TABLE:\n")
        f.write(df_s3.to_string(index=False) + "\n\n")
        f.write("VERIFICATION ERRORS (Mean by City):\n")
        f.write(err_summary.to_string(index=False) + "\n\n")
        f.write("REFERENCE SHELTER RESULTS:\n")
        f.write(df_refs.to_string(index=False) + "\n\n")
        f.write("50 VERIFIED DESIGNS FULL METRICS:\n")
        f.write(df_verified.to_string(index=False) + "\n")
        
    print(f"\nSaved Phase 5 evidence to {evidence_txt}")
    return df_verified, df_s3, df_refs

if __name__ == "__main__":
    run_full_optimization_pipeline()
