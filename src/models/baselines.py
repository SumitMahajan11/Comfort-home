"""
Baseline models evaluation module for ClimateAdapt-Comfort.
Evaluates PMV and Adaptive comfort baselines on 100% identical test rows
across all 5 GroupKFold splits and 4 Leave-One-Group-Out holdouts.
Computes Macro-F1, per-class recall, confusion matrices, and 95% building-level bootstrap CIs.
"""

import json
import os
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, recall_score, confusion_matrix
from pythermalcomfort.models import pmv_ppd_iso

def compute_pmv_predictions(df):
    """
    Computes ISO 7730 / ASHRAE 55 PMV and maps to 3-class target:
    PMV < -0.5 -> -1 (Cool)
    -0.5 <= PMV <= 0.5 -> 0 (Neutral)
    PMV > 0.5 -> 1 (Warm)
    """
    tdb = df['ta'].values
    tr = df['tr'].values
    vr = df['vel'].values
    rh = df['rh'].values
    met = df['met'].values
    clo = df['clo'].values
    
    # Run vectorized ISO PMV without input truncation
    res = pmv_ppd_iso(tdb=tdb, tr=tr, vr=vr, rh=rh, met=met, clo=clo, limit_inputs=False)
    pmv_arr = np.array(res.pmv, dtype=float)
    
    # Fallback for any numerical singularity
    nan_mask = np.isnan(pmv_arr)
    if np.any(nan_mask):
        pmv_arr[nan_mask & (tdb > 26)] = 1.0
        pmv_arr[nan_mask & (tdb < 20)] = -1.0
        pmv_arr[nan_mask & (tdb >= 20) & (tdb <= 26)] = 0.0
        
    preds = np.zeros(len(df), dtype=int)
    preds[pmv_arr < -0.5] = -1
    preds[pmv_arr > 0.5] = 1
    return preds, pmv_arr

def compute_adaptive_predictions(df, acceptability=80):
    """
    Computes ASHRAE 55 Adaptive comfort predictions:
    T_op = (ta + tr) / 2
    T_comf = 17.8 + 0.31 * T_pma
    Limits: 80% -> +/-3.5 C, 90% -> +/-2.5 C
    """
    delta = 3.5 if acceptability == 80 else 2.5
    top = (df['ta'].values + df['tr'].values) / 2.0
    
    # Prevailing mean outdoor temperature: use t_mot_isd if available, else t_out, else median
    tpma = df['t_mot_isd'].values.copy() if 't_mot_isd' in df.columns else np.full(len(df), np.nan)
    mask_nan = np.isnan(tpma)
    if 't_out' in df.columns:
        tpma[mask_nan] = df['t_out'].values[mask_nan]
    mask_nan2 = np.isnan(tpma)
    tpma[mask_nan2] = np.nanmedian(tpma) if not np.all(mask_nan2) else 25.0
    
    tcomf = 17.8 + 0.31 * tpma
    lower_lim = tcomf - delta
    upper_lim = tcomf + delta
    
    preds = np.zeros(len(df), dtype=int)
    preds[top < lower_lim] = -1
    preds[top > upper_lim] = 1
    return preds

def compute_imac_predictions(df, mode='nv', acceptability=90):
    """
    Computes Indian Model for Adaptive Comfort (IMAC, NBC 2016 / Manu et al. 2016):
    - Naturally Ventilated (NV): T_comf = 0.54 * T_rm + 12.83, 90% band +/- 2.38 C, 80% band +/- 3.46 C
    - Mixed Mode (MM): T_comf = 0.28 * T_rm + 17.87, 90% band +/- 3.46 C
    """
    top = (df['ta'].values + df['tr'].values) / 2.0
    tpma = df['t_mot_isd'].values.copy() if 't_mot_isd' in df.columns else np.full(len(df), np.nan)
    mask_nan = np.isnan(tpma)
    if 't_out' in df.columns:
        tpma[mask_nan] = df['t_out'].values[mask_nan]
    mask_nan2 = np.isnan(tpma)
    tpma[mask_nan2] = np.nanmedian(tpma) if not np.all(mask_nan2) else 25.0
    
    if mode == 'nv':
        tcomf = 0.54 * tpma + 12.83
        delta = 2.38 if acceptability == 90 else 3.46
    else:
        tcomf = 0.28 * tpma + 17.87
        delta = 3.46
        
    lower_lim = tcomf - delta
    upper_lim = tcomf + delta
    
    preds = np.zeros(len(df), dtype=int)
    preds[top < lower_lim] = -1
    preds[top > upper_lim] = 1
    return preds

def building_bootstrap_ci(y_true, y_pred, bldg_ids, n_boot=1000, seed=42):
    """
    Computes 95% building-level cluster bootstrap confidence interval for Macro-F1.
    """
    rng = np.random.RandomState(seed)
    unique_bldgs = np.unique(bldg_ids)
    n_bldgs = len(unique_bldgs)
    
    if n_bldgs <= 1:
        score = f1_score(y_true, y_pred, average='macro', zero_division=0)
        return score, score, score
        
    bldg_to_indices = {b: np.where(bldg_ids == b)[0] for b in unique_bldgs}
    boot_scores = []
    
    for _ in range(n_boot):
        sample_bldgs = rng.choice(unique_bldgs, size=n_bldgs, replace=True)
        sample_indices = np.concatenate([bldg_to_indices[b] for b in sample_bldgs])
        
        y_t_samp = y_true[sample_indices]
        y_p_samp = y_pred[sample_indices]
        boot_scores.append(f1_score(y_t_samp, y_p_samp, average='macro', zero_division=0))
        
    boot_scores = np.sort(boot_scores)
    ci_low = np.percentile(boot_scores, 2.5)
    ci_high = np.percentile(boot_scores, 97.5)
    mean_score = f1_score(y_true, y_pred, average='macro', zero_division=0)
    return mean_score, ci_low, ci_high

def evaluate_baselines(
    clean_parquet="data/processed/comfort_clean.parquet",
    splits_json="data/processed/splits.json",
    output_report_txt="reports/evidence/phase2_baselines_output.txt"
):
    print("="*80)
    print("EVALUATING PHYSICAL BASELINE MODELS (PMV & ADAPTIVE) ON IDENTICAL ROWS")
    print("="*80)
    
    df_clean = pd.read_parquet(clean_parquet)
    with open(splits_json, 'r') as f:
        splits = json.load(f)
        
    print(f"Loaded {len(df_clean):,} clean complete-case evaluation rows across {df_clean['building_id'].nunique()} buildings.")
    
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)
        
    log("="*80)
    log("PHYSICAL BASELINE BENCHMARKS ON COMPLETE-CASE TEST SPLITS")
    log("="*80)
    
    # 1. Evaluate on 5-Fold GroupKFold
    log("\n--- 1. 5-Fold GroupKFold Evaluation ---")
    gkf_results = {"pmv": [], "adapt80": [], "adapt90": [], "imac_nv": [], "imac_mm": []}
    
    for fold_name, fold_data in splits["group_kfold_5"].items():
        test_bldgs = fold_data["test_buildings"]
        test_df = df_clean[df_clean['building_id'].isin(test_bldgs)].copy().reset_index(drop=True)
        
        y_true = test_df['tsv_3class'].values
        bldg_ids = test_df['building_id'].values
        n_rows = len(test_df)
        
        # Predictions
        pmv_preds, _ = compute_pmv_predictions(test_df)
        adapt80_preds = compute_adaptive_predictions(test_df, acceptability=80)
        adapt90_preds = compute_adaptive_predictions(test_df, acceptability=90)
        imac_nv_preds = compute_imac_predictions(test_df, mode='nv', acceptability=90)
        imac_mm_preds = compute_imac_predictions(test_df, mode='mm', acceptability=90)
        
        # Metrics
        f1_pmv, pmv_low, pmv_high = building_bootstrap_ci(y_true, pmv_preds, bldg_ids)
        f1_ad80, ad80_low, ad80_high = building_bootstrap_ci(y_true, adapt80_preds, bldg_ids)
        f1_ad90, ad90_low, ad90_high = building_bootstrap_ci(y_true, adapt90_preds, bldg_ids)
        f1_imac_nv, imac_nv_low, imac_nv_high = building_bootstrap_ci(y_true, imac_nv_preds, bldg_ids)
        f1_imac_mm, imac_mm_low, imac_mm_high = building_bootstrap_ci(y_true, imac_mm_preds, bldg_ids)
        
        rec_pmv = recall_score(y_true, pmv_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_ad80 = recall_score(y_true, adapt80_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_ad90 = recall_score(y_true, adapt90_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_imac_nv = recall_score(y_true, imac_nv_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_imac_mm = recall_score(y_true, imac_mm_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        
        gkf_results["pmv"].append(f1_pmv)
        gkf_results["adapt80"].append(f1_ad80)
        gkf_results["adapt90"].append(f1_ad90)
        gkf_results["imac_nv"].append(f1_imac_nv)
        gkf_results["imac_mm"].append(f1_imac_mm)
        
        log(f"\n[{fold_name.upper()}] (Test Rows: {n_rows:,}, Buildings: {len(test_bldgs)})")
        log(f"  PMV:          Macro-F1 = {f1_pmv:.4f} (95% CI: [{pmv_low:.4f}, {pmv_high:.4f}]) | Recall = [{rec_pmv[0]:.3f}, {rec_pmv[1]:.3f}, {rec_pmv[2]:.3f}]")
        log(f"  Adaptive 80%: Macro-F1 = {f1_ad80:.4f} (95% CI: [{ad80_low:.4f}, {ad80_high:.4f}]) | Recall = [{rec_ad80[0]:.3f}, {rec_ad80[1]:.3f}, {rec_ad80[2]:.3f}]")
        log(f"  Adaptive 90%: Macro-F1 = {f1_ad90:.4f} (95% CI: [{ad90_low:.4f}, {ad90_high:.4f}]) | Recall = [{rec_ad90[0]:.3f}, {rec_ad90[1]:.3f}, {rec_ad90[2]:.3f}]")
        log(f"  IMAC NV 90%:  Macro-F1 = {f1_imac_nv:.4f} (95% CI: [{imac_nv_low:.4f}, {imac_nv_high:.4f}]) | Recall = [{rec_imac_nv[0]:.3f}, {rec_imac_nv[1]:.3f}, {rec_imac_nv[2]:.3f}]")
        log(f"  IMAC MM 90%:  Macro-F1 = {f1_imac_mm:.4f} (95% CI: [{imac_mm_low:.4f}, {imac_mm_high:.4f}]) | Recall = [{rec_imac_mm[0]:.3f}, {rec_imac_mm[1]:.3f}, {rec_imac_mm[2]:.3f}]")
        
    log("\n5-Fold GroupKFold Mean Macro-F1 across folds:")
    log(f"  PMV Mean Macro-F1:          {np.mean(gkf_results['pmv']):.4f} +/- {np.std(gkf_results['pmv']):.4f}")
    log(f"  Adaptive 80% Mean Macro-F1: {np.mean(gkf_results['adapt80']):.4f} +/- {np.std(gkf_results['adapt80']):.4f}")
    log(f"  Adaptive 90% Mean Macro-F1: {np.mean(gkf_results['adapt90']):.4f} +/- {np.std(gkf_results['adapt90']):.4f}")
    log(f"  IMAC NV 90% Mean Macro-F1:  {np.mean(gkf_results['imac_nv']):.4f} +/- {np.std(gkf_results['imac_nv']):.4f}")
    log(f"  IMAC MM 90% Mean Macro-F1:  {np.mean(gkf_results['imac_mm']):.4f} +/- {np.std(gkf_results['imac_mm']):.4f}")
    
    # 2. Evaluate on Leave-One-Group-Out Holdouts
    log("\n--- 2. Leave-One-Köppen-Major-Group-Out Holdouts ---")
    logo_results = {}
    
    for holdout_name, holdout_data in splits["leave_one_group_out"].items():
        grp = holdout_data["held_out_group"]
        grp_name = holdout_data["held_out_name"]
        test_bldgs = holdout_data["test_buildings"]
        test_df = df_clean[df_clean['building_id'].isin(test_bldgs)].copy().reset_index(drop=True)
        
        y_true = test_df['tsv_3class'].values
        bldg_ids = test_df['building_id'].values
        n_rows = len(test_df)
        
        pmv_preds, _ = compute_pmv_predictions(test_df)
        adapt80_preds = compute_adaptive_predictions(test_df, acceptability=80)
        adapt90_preds = compute_adaptive_predictions(test_df, acceptability=90)
        imac_nv_preds = compute_imac_predictions(test_df, mode='nv', acceptability=90)
        imac_mm_preds = compute_imac_predictions(test_df, mode='mm', acceptability=90)
        
        f1_pmv, pmv_low, pmv_high = building_bootstrap_ci(y_true, pmv_preds, bldg_ids)
        f1_ad80, ad80_low, ad80_high = building_bootstrap_ci(y_true, adapt80_preds, bldg_ids)
        f1_ad90, ad90_low, ad90_high = building_bootstrap_ci(y_true, adapt90_preds, bldg_ids)
        f1_imac_nv, imac_nv_low, imac_nv_high = building_bootstrap_ci(y_true, imac_nv_preds, bldg_ids)
        f1_imac_mm, imac_mm_low, imac_mm_high = building_bootstrap_ci(y_true, imac_mm_preds, bldg_ids)
        
        rec_pmv = recall_score(y_true, pmv_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_ad80 = recall_score(y_true, adapt80_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_ad90 = recall_score(y_true, adapt90_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_imac_nv = recall_score(y_true, imac_nv_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        rec_imac_mm = recall_score(y_true, imac_mm_preds, average=None, labels=[-1, 0, 1], zero_division=0)
        
        logo_results[grp] = {
            "pmv": f1_pmv, "pmv_ci": (pmv_low, pmv_high), "rec_pmv": rec_pmv,
            "adapt80": f1_ad80, "ad80_ci": (ad80_low, ad80_high), "rec_ad80": rec_ad80,
            "adapt90": f1_ad90, "ad90_ci": (ad90_low, ad90_high), "rec_ad90": rec_ad90,
            "imac_nv": f1_imac_nv, "imac_nv_ci": (imac_nv_low, imac_nv_high), "rec_imac_nv": rec_imac_nv,
            "imac_mm": f1_imac_mm, "imac_mm_ci": (imac_mm_low, imac_mm_high), "rec_imac_mm": rec_imac_mm,
            "n_rows": n_rows, "n_bldgs": len(test_bldgs)
        }
        
        log(f"\n[Holdout {grp}: {grp_name}] (Test Rows: {n_rows:,}, Buildings: {len(test_bldgs)})")
        log(f"  PMV:          Macro-F1 = {f1_pmv:.4f} (95% CI: [{pmv_low:.4f}, {pmv_high:.4f}]) | Recall = [{rec_pmv[0]:.3f}, {rec_pmv[1]:.3f}, {rec_pmv[2]:.3f}]")
        log(f"  Adaptive 80%: Macro-F1 = {f1_ad80:.4f} (95% CI: [{ad80_low:.4f}, {ad80_high:.4f}]) | Recall = [{rec_ad80[0]:.3f}, {rec_ad80[1]:.3f}, {rec_ad80[2]:.3f}]")
        log(f"  Adaptive 90%: Macro-F1 = {f1_ad90:.4f} (95% CI: [{ad90_low:.4f}, {ad90_high:.4f}]) | Recall = [{rec_ad90[0]:.3f}, {rec_ad90[1]:.3f}, {rec_ad90[2]:.3f}]")
        log(f"  IMAC NV 90%:  Macro-F1 = {f1_imac_nv:.4f} (95% CI: [{imac_nv_low:.4f}, {imac_nv_high:.4f}]) | Recall = [{rec_imac_nv[0]:.3f}, {rec_imac_nv[1]:.3f}, {rec_imac_nv[2]:.3f}]")
        log(f"  IMAC MM 90%:  Macro-F1 = {f1_imac_mm:.4f} (95% CI: [{imac_mm_low:.4f}, {imac_mm_high:.4f}]) | Recall = [{rec_imac_mm[0]:.3f}, {rec_imac_mm[1]:.3f}, {rec_imac_mm[2]:.3f}]")
        
    # Decision D-012 Holdout A & B Mean:
    mean_ab_pmv = (logo_results["A"]["pmv"] + logo_results["B"]["pmv"]) / 2.0
    mean_ab_ad80 = (logo_results["A"]["adapt80"] + logo_results["B"]["adapt80"]) / 2.0
    mean_ab_ad90 = (logo_results["A"]["adapt90"] + logo_results["B"]["adapt90"]) / 2.0
    mean_ab_imac_nv = (logo_results["A"]["imac_nv"] + logo_results["B"]["imac_nv"]) / 2.0
    mean_ab_imac_mm = (logo_results["A"]["imac_mm"] + logo_results["B"]["imac_mm"]) / 2.0
    
    log("\n" + "="*80)
    log("D-012 CRITERION: MEAN MACRO-F1 ON HOLDOUTS A & B (TROPICAL & ARID)")
    log("="*80)
    log(f"  PMV Baseline Mean Holdout A/B Macro-F1:          {mean_ab_pmv:.4f}")
    log(f"  Adaptive 80% Baseline Mean Holdout A/B Macro-F1: {mean_ab_ad80:.4f}")
    log(f"  Adaptive 90% Baseline Mean Holdout A/B Macro-F1: {mean_ab_ad90:.4f}")
    log(f"  IMAC NV 90% Baseline Mean Holdout A/B Macro-F1:  {mean_ab_imac_nv:.4f}")
    log(f"  IMAC MM 90% Baseline Mean Holdout A/B Macro-F1:  {mean_ab_imac_mm:.4f}")
    
    os.makedirs(os.path.dirname(output_report_txt), exist_ok=True)
    with open(output_report_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines) + '\n')
    print(f"\nSaved literal baseline output to {output_report_txt}")
    
    # Save structured baseline results json for training comparison
    with open("data/processed/baseline_results.json", 'w') as f:
        json.dump({
            "gkf_mean": {
                "pmv": float(np.mean(gkf_results['pmv'])),
                "adapt80": float(np.mean(gkf_results['adapt80'])),
                "adapt90": float(np.mean(gkf_results['adapt90']))
            },
            "holdouts": {
                grp: {
                    "pmv": float(logo_results[grp]["pmv"]),
                    "adapt80": float(logo_results[grp]["adapt80"]),
                    "adapt90": float(logo_results[grp]["adapt90"])
                } for grp in ["A", "B", "C", "D"]
            },
            "mean_holdout_ab": {
                "pmv": float(mean_ab_pmv),
                "adapt80": float(mean_ab_ad80),
                "adapt90": float(mean_ab_ad90)
            }
        }, f, indent=2)

if __name__ == "__main__":
    evaluate_baselines()
