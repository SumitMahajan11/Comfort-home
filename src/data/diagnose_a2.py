"""
Diagnostic script for Ablation A2 (cooling_type).
Tests proper OneHotEncoder / categorical alignment on train and test folds.
"""

import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb
from sklearn.metrics import f1_score, recall_score

def diagnose_a2():
    clean_parquet = "data/processed/comfort_clean.parquet"
    splits_json = "data/processed/splits.json"
    
    df_clean = pd.read_parquet(clean_parquet)
    with open(splits_json, 'r') as f:
        splits = json.load(f)
        
    TARGET_MAP = {-1: 0, 0: 1, 1: 2}
    df_clean['target'] = df_clean['tsv_3class'].map(TARGET_MAP)
    
    core_features = ['ta', 'tr', 'rh', 'vel', 'clo', 'met']
    
    print("Distinct cooling_type values in clean dataset:")
    print(df_clean['cooling_type'].value_counts(dropna=False))
    
    # Check Fold 0 with proper OneHotEncoder fitted ON TRAIN ONLY
    f0 = splits["group_kfold_5"]["fold_0"]
    tr_bldgs = f0["train_buildings"]
    te_bldgs = f0["test_buildings"]
    
    tr_df = df_clean[df_clean['building_id'].isin(tr_bldgs)].copy().reset_index(drop=True)
    te_df = df_clean[df_clean['building_id'].isin(te_bldgs)].copy().reset_index(drop=True)
    
    # 1. Buggy way (.loc with reset index)
    cooling_dummies = pd.get_dummies(df_clean['cooling_type'].fillna('unknown'), prefix='cooling', drop_first=True)
    df_clean_a2 = pd.concat([df_clean.reset_index(drop=True), cooling_dummies], axis=1)
    
    # Bug in previous train.py:
    tr_bug = df_clean_a2.loc[tr_df.index]
    print(f"\nBuggy alignment check: Does tr_bug['building_id'] match tr_df['building_id']?")
    print(f"Match percentage: {(tr_bug['building_id'] == tr_df['building_id']).mean()*100:.2f}%")
    
    # 2. Correct way with OneHotEncoder
    ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    ohe_tr = ohe.fit_transform(tr_df[['cooling_type']].fillna('unknown'))
    ohe_te = ohe.transform(te_df[['cooling_type']].fillna('unknown'))
    
    ohe_cols = [f"cooling_{c}" for c in ohe.categories_[0]]
    X_tr_correct = np.hstack([tr_df[core_features].values, ohe_tr])
    X_te_correct = np.hstack([te_df[core_features].values, ohe_te])
    
    # Train XGBoost on correct features
    classes, counts = np.unique(tr_df['target'], return_counts=True)
    total = len(tr_df)
    weight_dict = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
    sample_weight = np.array([weight_dict[c] for c in tr_df['target']])
    
    clf = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, eval_metric='mlogloss', tree_method='hist', n_jobs=-1)
    clf.fit(X_tr_correct, tr_df['target'], sample_weight=sample_weight)
    
    preds = clf.predict(X_te_correct)
    f1_correct = f1_score(te_df['target'], preds, average='macro')
    print(f"\nCorrect A2 Fold 0 Macro-F1: {f1_correct:.4f} (compared to buggy 0.3087)")

if __name__ == "__main__":
    diagnose_a2()
