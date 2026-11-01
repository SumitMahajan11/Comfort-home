import sys, os
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from src.models.train_surrogates import prepare_features, tune_surrogate_xgboost, TARGETS

df_obj = pd.read_parquet('data/processed/objectives.parquet')
df_jodhpur_all = df_obj[df_obj['city'] == 'Jodhpur'].copy()
# Baseline designs are D_00000 through D_00999 (990 rows)
df_jodhpur_990 = df_jodhpur_all[df_jodhpur_all['design_id'].apply(lambda x: x.startswith('D_') and int(x.split('_')[1]) < 1000)].copy()
print(f'Jodhpur baseline rows count: {len(df_jodhpur_990)}')

df_comp = pd.read_csv('data/processed/surrogate_metrics_comparison.csv')
old_jodhpur = df_comp[df_comp['city'] == 'Jodhpur'].set_index('target')

X = prepare_features(df_jodhpur_990)

print(f"{'Target':12s} | {'New R2 (990)':14s} | {'Old R2 (Base)':14s} | {'Old R2 (Aug)':14s} | {'Diff vs Base':14s}")
print("-" * 75)

for tgt in TARGETS:
    y = df_jodhpur_990[tgt].values
    valid_mask = ~np.isnan(y)
    X_v = X[valid_mask].reset_index(drop=True)
    y_v = y[valid_mask]
    
    X_tr, X_te, y_tr, y_te = train_test_split(X_v, y_v, test_size=0.20, random_state=42)
    model, params, cv_r2 = tune_surrogate_xgboost(X_tr, y_tr, n_trials=40, seed=42)
    
    y_pred = model.predict(X_te)
    r2 = r2_score(y_te, y_pred)
    
    old_base_r2 = float(old_jodhpur.loc[tgt, 'r2'])
    old_aug_r2 = float(old_jodhpur.loc[tgt, 'r2_aug'])
    diff = r2 - old_base_r2
    print(f"{tgt:12s} | {r2:14.6f} | {old_base_r2:14.6f} | {old_aug_r2:14.6f} | {diff:14.6f}")
