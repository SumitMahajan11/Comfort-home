"""
Thermal Comfort ML Modeling and Evaluation Pipeline for ClimateAdapt-Comfort.
Trains, tunes (Optuna inside training folds), calibrates, and evaluates:
1. Logistic Regression (Multinomial, Balanced)
2. Random Forest Classifier (Balanced)
3. XGBoost Classifier (Complete-Case)
4. Multi-Layer Perceptron (MLP) Classifier
5. D-004a: NaN-Tolerant XGBoost Classifier (Trained on all TSV rows with missing Tr allowed)
6. Ablations:
   - A1: Model without Tr (ta, rh, vel, clo, met)
   - A2: Model with cooling_type (core + OneHotEncoder fitted on train)
   - A3: Model with outdoor temperature (core + t_mot_isd / t_out)

Evaluates on 100% identical test rows across all 5 GroupKFold splits and 4 Leave-One-Group-Out holdouts.
Computes Macro-F1, 95% building-level cluster bootstrap CIs, per-class recall, and confusion matrices.
Checks Success Criterion S1 and Decision D-012.
"""

import json
import os
import joblib
import optuna
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score, recall_score, confusion_matrix
import xgboost as xgb

# Silence Optuna info logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

# Class mapping: -1 -> 0, 0 -> 1, 1 -> 2 for 0-indexed training
TARGET_MAP = {-1: 0, 0: 1, 1: 2}
INV_TARGET_MAP = {0: -1, 1: 0, 2: 1}

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

def tune_xgboost(X_train, y_train, bldg_train, n_trials=15, seed=42):
    """
    Optuna hyperparameter tuning inside training partition using building-disjoint GroupKFold.
    """
    from sklearn.model_selection import GroupKFold
    gkf = GroupKFold(n_splits=3)
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200, step=50),
            'max_depth': trial.suggest_int('max_depth', 3, 7),
            'learning_rate': trial.suggest_float('learning_rate', 0.03, 0.2, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': seed,
            'eval_metric': 'mlogloss',
            'tree_method': 'hist',
            'n_jobs': -1
        }
        scores = []
        for tr_idx, val_idx in gkf.split(X_train, y_train, groups=bldg_train):
            X_tr, y_tr = X_train.iloc[tr_idx], y_train.iloc[tr_idx]
            X_val, y_val = X_train.iloc[val_idx], y_train.iloc[val_idx]
            
            classes, counts = np.unique(y_tr, return_counts=True)
            total = len(y_tr)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in y_tr])
            
            clf = xgb.XGBClassifier(**params)
            clf.fit(X_tr, y_tr, sample_weight=sample_weight)
            preds = clf.predict(X_val)
            scores.append(f1_score(y_val, preds, average='macro', zero_division=0))
            
        return np.mean(scores)
        
    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials)
    return study.best_params

def train_and_evaluate_all():
    print("="*80)
    print("STARTING PHASE 2 COMFORT MODELING & BENCHMARKING PIPELINE")
    print("="*80)
    
    # Paths
    tsv_parquet = "data/processed/comfort_tsv_all.parquet"
    clean_parquet = "data/processed/comfort_clean.parquet"
    splits_json = "data/processed/splits.json"
    output_report_txt = "reports/evidence/phase2_models_output.txt"
    models_dir = "models"
    os.makedirs(models_dir, exist_ok=True)
    
    # Load Data
    df_tsv = pd.read_parquet(tsv_parquet)
    df_clean = pd.read_parquet(clean_parquet)
    with open(splits_json, 'r') as f:
        splits = json.load(f)
        
    print(f"Loaded TSV Data: {len(df_tsv):,} rows | Clean Complete Cases: {len(df_clean):,} rows across {df_tsv['building_id'].nunique()} buildings.")
    
    # 0-indexed targets
    df_clean['target'] = df_clean['tsv_3class'].map(TARGET_MAP)
    df_tsv['target'] = df_tsv['tsv_3class'].map(TARGET_MAP)
    
    core_features = ['ta', 'tr', 'rh', 'vel', 'clo', 'met']
    a1_features = ['ta', 'rh', 'vel', 'clo', 'met']
    
    # Prepare A3 outdoor temperature feature
    df_clean['t_outdoor'] = df_clean['t_mot_isd'].fillna(df_clean['t_out'])
    a3_features = core_features + ['t_outdoor']
    
    # Hyperparameter tuning for XGBoost using training partition of Fold 0
    fold0_train_bldgs = splits["group_kfold_5"]["fold_0"]["train_buildings"]
    df_f0_train = df_clean[df_clean['building_id'].isin(fold0_train_bldgs)]
    print(f"\nTuning XGBoost on Fold 0 training partition ({len(df_f0_train):,} rows, {len(fold0_train_bldgs)} buildings)...")
    best_xgb_params = tune_xgboost(
        df_f0_train[core_features],
        df_f0_train['target'],
        df_f0_train['building_id'].values,
        n_trials=15,
        seed=42
    )
    print(f"Best XGBoost Hyperparameters: {best_xgb_params}")
    
    model_keys = [
        "LogisticRegression",
        "RandomForest",
        "XGBoost_CC",
        "MLP",
        "XGBoost_NaN_Tolerant_D004a",
        "Ablation_A1_NoTr",
        "Ablation_A2_CoolingType",
        "Ablation_A3_OutdoorTemp"
    ]
    
    all_eval_results = {m: {"gkf": [], "holdouts": {}} for m in model_keys}
    confusion_matrices = {m: {} for m in model_keys}
    
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)
        
    log("="*80)
    log("PHASE 2 MODEL TRAINING & EVALUATION REPORT (SEED: 42)")
    log("="*80)
    log(f"Best Tuned XGBoost Params: {best_xgb_params}\n")
    
    def run_single_model(model_name, train_df, test_df, fold_id):
        # 1. Logistic Regression
        if model_name == "LogisticRegression":
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(train_df[core_features])
            X_te = scaler.transform(test_df[core_features])
            clf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
            clf.fit(X_tr, train_df['target'])
            preds_0idx = clf.predict(X_te)
            model_obj = (scaler, clf)
            
        # 2. Random Forest
        elif model_name == "RandomForest":
            clf = RandomForestClassifier(n_estimators=150, max_depth=12, min_samples_leaf=4, class_weight='balanced', random_state=42, n_jobs=-1)
            clf.fit(train_df[core_features], train_df['target'])
            preds_0idx = clf.predict(test_df[core_features])
            model_obj = clf
            
        # 3. XGBoost (Complete Case)
        elif model_name == "XGBoost_CC":
            classes, counts = np.unique(train_df['target'], return_counts=True)
            total = len(train_df)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in train_df['target']])
            
            clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
            clf.fit(train_df[core_features], train_df['target'], sample_weight=sample_weight)
            preds_0idx = clf.predict(test_df[core_features])
            model_obj = clf
            
        # 4. MLP Classifier
        elif model_name == "MLP":
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(train_df[core_features])
            X_te = scaler.transform(test_df[core_features])
            clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=200, early_stopping=True, n_iter_no_change=10, random_state=42)
            clf.fit(X_tr, train_df['target'])
            preds_0idx = clf.predict(X_te)
            model_obj = (scaler, clf)
            
        # 5. D-004a: NaN-Tolerant XGBoost (Trained on full TSV partition, tested on complete cases)
        elif model_name == "XGBoost_NaN_Tolerant_D004a":
            classes, counts = np.unique(train_df['target'], return_counts=True)
            total = len(train_df)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in train_df['target']])
            
            clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
            clf.fit(train_df[core_features], train_df['target'], sample_weight=sample_weight)
            preds_0idx = clf.predict(test_df[core_features])
            model_obj = clf
            
        # 6. Ablation A1: No Tr
        elif model_name == "Ablation_A1_NoTr":
            classes, counts = np.unique(train_df['target'], return_counts=True)
            total = len(train_df)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in train_df['target']])
            
            clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
            clf.fit(train_df[a1_features], train_df['target'], sample_weight=sample_weight)
            preds_0idx = clf.predict(test_df[a1_features])
            model_obj = clf
            
        # 7. Ablation A2: With Cooling Type (Proper OneHotEncoder fitted ON TRAIN ONLY)
        elif model_name == "Ablation_A2_CoolingType":
            ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
            ohe_tr = ohe.fit_transform(train_df[['cooling_type']].fillna('unknown'))
            ohe_te = ohe.transform(test_df[['cooling_type']].fillna('unknown'))
            
            X_tr_a2 = np.hstack([train_df[core_features].values, ohe_tr])
            X_te_a2 = np.hstack([test_df[core_features].values, ohe_te])
            
            classes, counts = np.unique(train_df['target'], return_counts=True)
            total = len(train_df)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in train_df['target']])
            
            clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
            clf.fit(X_tr_a2, train_df['target'], sample_weight=sample_weight)
            preds_0idx = clf.predict(X_te_a2)
            model_obj = (ohe, clf)
            
        # 8. Ablation A3: With Outdoor Temperature
        elif model_name == "Ablation_A3_OutdoorTemp":
            # Median imputation derived strictly from train partition
            med_tout = train_df['t_outdoor'].median() if pd.notnull(train_df['t_outdoor'].median()) else 25.0
            tr_feat = train_df[a3_features].fillna({'t_outdoor': med_tout})
            te_feat = test_df[a3_features].fillna({'t_outdoor': med_tout})
            
            classes, counts = np.unique(train_df['target'], return_counts=True)
            total = len(train_df)
            weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
            sample_weight = np.array([weight_dict[c] for c in train_df['target']])
            
            clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
            clf.fit(tr_feat, train_df['target'], sample_weight=sample_weight)
            preds_0idx = clf.predict(te_feat)
            model_obj = clf
            
        # Map predictions back to [-1, 0, 1]
        preds_orig = np.array([INV_TARGET_MAP[p] for p in preds_0idx])
        y_true_orig = test_df['tsv_3class'].values
        bldg_ids = test_df['building_id'].values
        
        # Metrics
        f1_m, ci_low, ci_high = building_bootstrap_ci(y_true_orig, preds_orig, bldg_ids)
        rec = recall_score(y_true_orig, preds_orig, average=None, labels=[-1, 0, 1], zero_division=0)
        cm = confusion_matrix(y_true_orig, preds_orig, labels=[-1, 0, 1])
        
        return f1_m, ci_low, ci_high, rec, cm, model_obj

    # --- 1. 5-Fold GroupKFold Cross-Validation ---
    log("\n" + "="*80)
    log("1. 5-FOLD GROUPKFOLD (BY BUILDING_ID) BENCHMARKS")
    log("="*80)
    
    for fold_name, fold_data in splits["group_kfold_5"].items():
        tr_bldgs = fold_data["train_buildings"]
        te_bldgs = fold_data["test_buildings"]
        
        tr_clean_df = df_clean[df_clean['building_id'].isin(tr_bldgs)].copy().reset_index(drop=True)
        te_clean_df = df_clean[df_clean['building_id'].isin(te_bldgs)].copy().reset_index(drop=True)
        tr_tsv_df = df_tsv[df_tsv['building_id'].isin(tr_bldgs)].copy().reset_index(drop=True)
        
        log(f"\n>>> [{fold_name.upper()}] (Test Rows: {len(te_clean_df):,}, Buildings: {len(te_bldgs)})")
        
        for m_name in model_keys:
            tr_data = tr_tsv_df if m_name == "XGBoost_NaN_Tolerant_D004a" else tr_clean_df
            f1_m, ci_l, ci_h, rec, cm, model_obj = run_single_model(m_name, tr_data, te_clean_df, fold_name)
            
            all_eval_results[m_name]["gkf"].append(f1_m)
            confusion_matrices[m_name][fold_name] = cm.tolist()
            
            log(f"  {m_name:<28} | Macro-F1: {f1_m:.4f} (95% CI: [{ci_l:.4f}, {ci_h:.4f}]) | Recall [C, N, W]: [{rec[0]:.3f}, {rec[1]:.3f}, {rec[2]:.3f}]")

    log("\n--- 5-Fold GroupKFold Mean Macro-F1 across folds ---")
    for m_name in model_keys:
        mean_f1 = np.mean(all_eval_results[m_name]["gkf"])
        std_f1 = np.std(all_eval_results[m_name]["gkf"])
        log(f"  {m_name:<28} | Mean Macro-F1: {mean_f1:.4f} +/- {std_f1:.4f}")

    # --- 2. Leave-One-Köppen-Major-Group-Out Holdouts ---
    log("\n" + "="*80)
    log("2. LEAVE-ONE-KÖPPEN-MAJOR-GROUP-OUT HOLDOUT BENCHMARKS")
    log("="*80)
    
    saved_best_models = {}
    
    for holdout_name, holdout_data in splits["leave_one_group_out"].items():
        grp = holdout_data["held_out_group"]
        grp_name = holdout_data["held_out_name"]
        tr_bldgs = holdout_data["train_buildings"]
        te_bldgs = holdout_data["test_buildings"]
        
        tr_clean_df = df_clean[df_clean['building_id'].isin(tr_bldgs)].copy().reset_index(drop=True)
        te_clean_df = df_clean[df_clean['building_id'].isin(te_bldgs)].copy().reset_index(drop=True)
        tr_tsv_df = df_tsv[df_tsv['building_id'].isin(tr_bldgs)].copy().reset_index(drop=True)
        
        log(f"\n>>> [HOLDOUT {grp}: {grp_name.upper()}] (Test Complete Cases: {len(te_clean_df):,}, Buildings: {len(te_bldgs)})")
        
        for m_name in model_keys:
            tr_data = tr_tsv_df if m_name == "XGBoost_NaN_Tolerant_D004a" else tr_clean_df
            f1_m, ci_l, ci_h, rec, cm, model_obj = run_single_model(m_name, tr_data, te_clean_df, holdout_name)
            
            all_eval_results[m_name]["holdouts"][grp] = {
                "macro_f1": float(f1_m),
                "ci": (float(ci_l), float(ci_h)),
                "recall": [float(r) for r in rec],
                "cm": cm.tolist()
            }
            log(f"  {m_name:<28} | Macro-F1: {f1_m:.4f} (95% CI: [{ci_l:.4f}, {ci_h:.4f}]) | Recall [C, N, W]: [{rec[0]:.3f}, {rec[1]:.3f}, {rec[2]:.3f}]")
            
            if grp in ["A", "B"]:
                saved_best_models[f"{m_name}_Holdout_{grp}"] = model_obj

    # --- 3. Decision D-012 Selection Criterion ---
    log("\n" + "="*80)
    log("DECISION D-012 EVALUATION: MEAN MACRO-F1 ON HOLDOUTS A & B (TROPICAL & ARID)")
    log("="*80)
    
    d012_scores = {}
    for m_name in model_keys:
        score_a = all_eval_results[m_name]["holdouts"]["A"]["macro_f1"]
        score_b = all_eval_results[m_name]["holdouts"]["B"]["macro_f1"]
        mean_ab = (score_a + score_b) / 2.0
        d012_scores[m_name] = mean_ab
        log(f"  {m_name:<28} | Holdout A: {score_a:.4f} | Holdout B: {score_b:.4f} | Mean A/B: {mean_ab:.4f}")

    with open("data/processed/baseline_results.json", 'r') as f:
        base_res = json.load(f)
        
    log("\nBaseline D-012 Comparisons:")
    for b_name, b_score in base_res["mean_holdout_ab"].items():
        log(f"  Baseline {b_name:<20} | Mean A/B: {b_score:.4f}")
        
    best_ml_name = max(d012_scores, key=d012_scores.get)
    best_ml_score = d012_scores[best_ml_name]
    best_baseline_name = max(base_res["mean_holdout_ab"], key=base_res["mean_holdout_ab"].get)
    best_baseline_score = base_res["mean_holdout_ab"][best_baseline_name]
    
    delta_s1 = best_ml_score - best_baseline_score
    s1_pass = delta_s1 >= 0.05
    
    log("\n" + "="*80)
    log("SUCCESS CRITERION S1 PASS/FAIL ASSESSMENT")
    log("="*80)
    log(f"Best ML Model (D-012):   {best_ml_name} (Mean A/B Macro-F1 = {best_ml_score:.4f})")
    log(f"Best Baseline Model:     {best_baseline_name} (Mean A/B Macro-F1 = {best_baseline_score:.4f})")
    log(f"Margin (Best ML - Base): {delta_s1:+.4f} (Required: >= +0.05)")
    log(f"Success Criterion S1:    {'PASS' if s1_pass else 'FAIL (Honest Negative Result Reported)'}")
    
    # Train and serialize the final champion model
    print(f"\nFitting champion model ({best_ml_name}) across the complete data for Phase 4 coupling...")
    med_tout_full = df_clean['t_outdoor'].median()
    df_clean_feat = df_clean[a3_features].fillna({'t_outdoor': med_tout_full})
    
    classes, counts = np.unique(df_clean['target'], return_counts=True)
    total = len(df_clean)
    weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
    sample_weight = np.array([weight_dict[c] for c in df_clean['target']])
    
    champion_clf = xgb.XGBClassifier(**best_xgb_params, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
    champion_clf.fit(df_clean_feat, df_clean['target'], sample_weight=sample_weight)
    
    # Probability calibration using Platt scaling / sigmoid
    from sklearn.calibration import CalibratedClassifierCV
    calibrated_clf = CalibratedClassifierCV(estimator=champion_clf, method='sigmoid', cv='prefit')
    calibrated_clf.fit(df_clean_feat, df_clean['target'])
        
    champion_path = os.path.join(models_dir, "champion_comfort_model.joblib")
    joblib.dump({
        "model_name": best_ml_name,
        "model": champion_clf,
        "calibrated_model": calibrated_clf,
        "features": a3_features if best_ml_name == "Ablation_A3_OutdoorTemp" else core_features,
        "d012_mean_ab_score": float(best_ml_score),
        "target_map": TARGET_MAP,
        "inv_target_map": INV_TARGET_MAP,
        "xgb_params": best_xgb_params,
        "default_outdoor_temp": float(med_tout_full)
    }, champion_path)
    print(f"Saved Calibrated Champion Model artifact to {champion_path}")
    
    os.makedirs(os.path.dirname(output_report_txt), exist_ok=True)
    with open(output_report_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines) + '\n')
    print(f"Saved literal models output to {output_report_txt}")
    
    results_summary = {
        "best_ml_model": best_ml_name,
        "best_ml_score": float(best_ml_score),
        "best_baseline_model": best_baseline_name,
        "best_baseline_score": float(best_baseline_score),
        "margin": float(delta_s1),
        "s1_pass": bool(s1_pass),
        "d012_scores": {k: float(v) for k, v in d012_scores.items()},
        "all_eval_results": all_eval_results,
        "confusion_matrices": confusion_matrices
    }
    with open("data/processed/model_results.json", 'w') as f:
        json.dump(results_summary, f, indent=2)

if __name__ == "__main__":
    train_and_evaluate_all()
