"""
Phase 4B: Surrogate Model Training Pipeline for ClimateAdapt-Comfort.
Trains, tunes (Optuna 5-fold CV on train part, 40 trials), evaluates, and serializes
XGBoost regressors for each city and target:
Targets: O1_ml, warm_ml, cool_ml, O1_adapt, O2
Inputs: 8 design variables with wall_mass_class one-hot encoded
Evaluation: Held-out 20% test set (R2, MAE, NMAE, Top-10% ranking overlap, S2 pass/fail)
"""

import os
import sys
import json
import time
import joblib
import optuna
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import r2_score, mean_absolute_error
from xgboost import XGBRegressor

sys.path.insert(0, os.path.abspath("."))

optuna.logging.set_verbosity(optuna.logging.WARNING)

CITIES = ["Jodhpur", "Mumbai", "New_Delhi", "Bengaluru", "Shimla"]
TARGETS = ["O1_ml", "warm_ml", "cool_ml", "O1_adapt", "O2"]

DESIGN_VARS = [
    'roof_insulation_thickness',
    'wall_insulation_thickness',
    'roof_solar_absorptance',
    'wwr',
    'orientation',
    'shading_depth',
    'ventilation_ach'
]

def prepare_features(df_city):
    """Encodes design variables with one-hot encoded wall_mass_class."""
    X_num = df_city[DESIGN_VARS].copy()
    dummies = pd.get_dummies(df_city['wall_mass_class'], prefix='wall_mass', dtype=float)
    # Ensure consistent columns
    for mass in ['heavy', 'light', 'medium']:
        col = f'wall_mass_{mass}'
        if col not in dummies.columns:
            dummies[col] = 0.0
    dummies = dummies[['wall_mass_heavy', 'wall_mass_light', 'wall_mass_medium']]
    X = pd.concat([X_num, dummies], axis=1)
    return X

def compute_top_k_overlap(y_true, y_pred, k_pct=0.10):
    """
    Computes set overlap between true top k% best designs and predicted top k% best designs.
    Best means lowest objective value (minimization).
    """
    n = len(y_true)
    k = max(1, int(np.ceil(n * k_pct)))
    top_true_idx = set(np.argsort(y_true)[:k])
    top_pred_idx = set(np.argsort(y_pred)[:k])
    intersection = len(top_true_idx.intersection(top_pred_idx))
    return float(intersection / k * 100.0)

def tune_surrogate_xgboost(X_train, y_train, n_trials=40, seed=42):
    """
    Tunes XGBoost regressor using 5-fold CV on training set only with Optuna.
    """
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 400),
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.25, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-4, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-4, 10.0, log=True),
            'random_state': seed,
            'n_jobs': 1
        }
        
        kf = KFold(n_splits=5, shuffle=True, random_state=seed)
        cv_scores = []
        for train_idx, val_idx in kf.split(X_train):
            X_tr, y_tr = X_train.iloc[train_idx], y_train[train_idx]
            X_va, y_va = X_train.iloc[val_idx], y_train[val_idx]
            
            model = XGBRegressor(**params)
            model.fit(X_tr, y_tr)
            preds = model.predict(X_va)
            score = r2_score(y_va, preds)
            cv_scores.append(score)
            
        return np.mean(cv_scores)

    study = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    
    best_params = study.best_params
    best_params['random_state'] = seed
    best_params['n_jobs'] = 1
    
    # Fit best model on full training set
    best_model = XGBRegressor(**best_params)
    best_model.fit(X_train, y_train)
    return best_model, best_params, study.best_value

def train_all_surrogates():
    print("="*80)
    print("STARTING PHASE 4B SURROGATE MODEL TRAINING (XGBoost Regressors)")
    print("="*80)
    
    obj_path = "data/processed/objectives.parquet"
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"Missing {obj_path}")
    df_all = pd.read_parquet(obj_path)
    print(f"Loaded objectives dataset: {len(df_all):,} designs across {len(CITIES)} cities.")
    
    os.makedirs("models", exist_ok=True)
    metrics_records = []
    
    t0 = time.time()
    
    for city in CITIES:
        df_city = df_all[df_all['city'] == city].reset_index(drop=True)
        print(f"\n{'='*40}\nCity: {city} ({len(df_city)} designs)\n{'='*40}")
        
        X = prepare_features(df_city)
        
        for target in TARGETS:
            # Check if target is entirely NaN (e.g. invalid adaptive)
            if df_city[target].isna().all():
                print(f"  Target {target:10s} is entirely NaN for {city}. Skipping.")
                metrics_records.append({
                    'city': city,
                    'target': target,
                    'r2': np.nan,
                    'mae': np.nan,
                    'nmae_pct': np.nan,
                    'top10_overlap_pct': np.nan,
                    's2_status': 'N/A',
                    'cv_r2': np.nan
                })
                continue
                
            y = df_city[target].values
            valid_mask = ~np.isnan(y)
            X_valid = X[valid_mask].reset_index(drop=True)
            y_valid = y[valid_mask]
            
            # 80/20 train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X_valid, y_valid, test_size=0.20, random_state=42
            )
            
            # Tune with Optuna 5-fold CV (40 trials)
            best_model, best_params, cv_r2 = tune_surrogate_xgboost(
                X_train, y_train, n_trials=40, seed=42
            )
            
            # Predict on held-out test set
            y_pred = best_model.predict(X_test)
            
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            target_range = float(y_valid.max() - y_valid.min())
            nmae = (mae / target_range * 100.0) if target_range > 0 else 0.0
            top10_overlap = compute_top_k_overlap(y_test, y_pred, k_pct=0.10)
            
            s2_pass = bool(r2 >= 0.95)
            s2_str = "PASS" if s2_pass else "FAIL"
            
            print(f"  Target: {target:10s} | Test R2: {r2:.4f} | MAE: {mae:.3f} | NMAE: {nmae:5.2f}% | Top10 Overlap: {top10_overlap:5.1f}% | S2: {s2_str} (CV R2: {cv_r2:.4f})")
            
            # Save model artifact
            model_save_path = f"models/surrogate_{city}_{target}.joblib"
            artifact = {
                'city': city,
                'target': target,
                'model': best_model,
                'best_params': best_params,
                'feature_names': list(X.columns),
                'metrics': {
                    'r2': float(r2),
                    'mae': float(mae),
                    'nmae_pct': float(nmae),
                    'top10_overlap_pct': float(top10_overlap),
                    's2_status': s2_str,
                    'cv_r2': float(cv_r2)
                }
            }
            joblib.dump(artifact, model_save_path)
            
            metrics_records.append({
                'city': city,
                'target': target,
                'r2': float(r2),
                'mae': float(mae),
                'nmae_pct': float(nmae),
                'top10_overlap_pct': float(top10_overlap),
                's2_status': s2_str,
                'cv_r2': float(cv_r2)
            })
            
    total_time = time.time() - t0
    print(f"\nAll 25 surrogate models tuned and evaluated in {total_time:.1f}s ({total_time/60:.2f} min).")
    
    df_metrics = pd.DataFrame(metrics_records)
    out_csv = "data/processed/surrogate_metrics.csv"
    df_metrics.to_csv(out_csv, index=False)
    print(f"Saved surrogate metrics to {out_csv}")
    
    # Summary Table
    print("\n" + "="*80)
    print("SURROGATE EVALUATION METRICS TABLE (Held-Out 20% Test Set)")
    print("="*80)
    print(df_metrics.to_string(index=False))
    
    return df_metrics

if __name__ == "__main__":
    train_all_surrogates()
