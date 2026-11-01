"""
Dataset splitting module for ClimateAdapt-Comfort.
Constructs strict group-held-out splits storing compact building-to-fold assignments:
1. 5-fold GroupKFold grouped by building_id (seed 42).
2. Leave-One-Köppen-Major-Group-Out (A: Tropical, B: Arid, C: Temperate, D: Continental).

Key Design Specification:
- splits.json stores building-to-fold assignments only (compact, human-readable).
- Models map these building IDs to rows:
  * Training sets contain all available TSV rows in the training buildings (all 106,171 TSV rows for NaN-tolerant XGBoost; 58,512 rows for complete-case models).
  * Test sets are strictly restricted to COMPLETE-CASE rows in test buildings, ensuring 100% identical evaluation rows across all ML models and physical baselines (PMV, Adaptive).
"""

import json
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold

def make_all_splits(
    meas_path="data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz",
    meta_path="data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv",
    map_path="data/processed/koppen_group_map.csv",
    output_all_tsv_parquet="data/processed/comfort_tsv_all.parquet",
    output_clean_parquet="data/processed/comfort_clean.parquet",
    output_splits_json="data/processed/splits.json"
):
    print("================================================================================")
    print("BUILDING DATASET SPLITS (BUILDING-TO-FOLD ASSIGNMENTS)")
    print("================================================================================")
    
    # 1. Load raw datasets
    df_meas = pd.read_csv(meas_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False)
    df_map = pd.read_csv(map_path)
    
    df = df_meas.merge(df_meta, on='building_id', how='left')
    print(f"Total raw merged rows: {len(df):,}")
    
    # Filter valid TSV rows
    df_tsv = df[df['thermal_sensation'].notnull()].copy().reset_index(drop=True)
    print(f"Total valid TSV rows: {len(df_tsv):,} across {df_tsv['building_id'].nunique()} buildings")
    
    # Target creation
    def map_target(val):
        if pd.isnull(val):
            return np.nan
        if val < -0.5:
            return -1
        elif val <= 0.5:
            return 0
        else:
            return 1
            
    df_tsv['tsv_3class'] = df_tsv['thermal_sensation'].apply(map_target).astype(int)
    
    # Normalize climate strings for mapping
    df_tsv['clean_climate'] = df_tsv['climate'].astype(str).str.strip().str.lower().str.replace('\xa0', ' ')
    df_map_clean = df_map.copy()
    df_map_clean['clean_climate'] = df_map_clean['raw_climate'].astype(str).str.strip().str.lower().str.replace('\xa0', ' ')
    climate_to_group = dict(zip(df_map_clean['clean_climate'], df_map_clean['koppen_group']))
    climate_to_group_name = dict(zip(df_map_clean['clean_climate'], df_map_clean['group_name']))
    
    df_tsv['koppen_group'] = df_tsv['clean_climate'].map(climate_to_group)
    df_tsv['koppen_group_name'] = df_tsv['clean_climate'].map(climate_to_group_name)
    
    # Core feature completeness
    core_features = ['ta', 'tr', 'rh', 'vel', 'clo', 'met']
    df_tsv['is_complete_case'] = df_tsv[core_features].notnull().all(axis=1)
    
    n_complete = int(df_tsv['is_complete_case'].sum())
    print(f"Complete-case rows (with tr and core features): {n_complete:,} ({n_complete/len(df_tsv)*100:.2f}%)")
    
    # Save both parquet files
    os.makedirs(os.path.dirname(output_all_tsv_parquet), exist_ok=True)
    df_tsv.to_parquet(output_all_tsv_parquet, index=False)
    
    df_clean = df_tsv[df_tsv['is_complete_case']].copy().reset_index(drop=True)
    df_clean.to_parquet(output_clean_parquet, index=False)
    print(f"Saved {output_all_tsv_parquet} ({len(df_tsv):,} rows) and {output_clean_parquet} ({len(df_clean):,} rows)")
    
    splits_dict = {
        "metadata": {
            "total_tsv_rows": int(len(df_tsv)),
            "total_complete_case_rows": int(n_complete),
            "distinct_buildings": int(df_tsv['building_id'].nunique()),
            "seed": 42,
            "groups": ["A", "B", "C", "D"],
            "core_features": core_features,
            "target": "tsv_3class"
        },
        "group_kfold_5": {},
        "leave_one_group_out": {}
    }
    
    # 2. 5-Fold GroupKFold over all buildings
    gkf = GroupKFold(n_splits=5)
    groups = df_tsv['building_id'].values
    
    for fold, (train_idx, test_idx_all) in enumerate(gkf.split(df_tsv, groups=groups)):
        train_bldgs = sorted([int(b) for b in set(df_tsv.iloc[train_idx]['building_id'])])
        test_bldgs = sorted([int(b) for b in set(df_tsv.iloc[test_idx_all]['building_id'])])
        
        # Verify zero building leakage
        overlap_bldgs = set(train_bldgs).intersection(set(test_bldgs))
        assert len(overlap_bldgs) == 0, f"Fold {fold} building leakage: {overlap_bldgs}"
        
        n_train_tsv = len(df_tsv[df_tsv['building_id'].isin(train_bldgs)])
        n_test_tsv = len(df_tsv[df_tsv['building_id'].isin(test_bldgs)])
        n_test_cc = len(df_clean[df_clean['building_id'].isin(test_bldgs)])
        
        splits_dict["group_kfold_5"][f"fold_{fold}"] = {
            "fold": int(fold),
            "n_train_buildings": int(len(train_bldgs)),
            "n_test_buildings": int(len(test_bldgs)),
            "n_train_all_tsv_rows": int(n_train_tsv),
            "n_test_all_tsv_rows": int(n_test_tsv),
            "n_test_complete_case_rows": int(n_test_cc),
            "train_buildings": train_bldgs,
            "test_buildings": test_bldgs
        }
        print(f"GroupKFold Fold {fold}: Train={len(train_bldgs)} bldgs ({n_train_tsv:,} TSV rows) | Test={len(test_bldgs)} bldgs ({n_test_cc:,} complete-case rows)")

    # 3. Leave-One-Köppen-Major-Group-Out
    group_name_map = {"A": "Tropical", "B": "Arid", "C": "Temperate", "D": "Continental"}
    for grp in ["A", "B", "C", "D"]:
        test_mask = (df_tsv['koppen_group'] == grp)
        train_mask = ~test_mask
        
        test_bldgs = sorted([int(b) for b in set(df_tsv[test_mask]['building_id'])])
        train_bldgs = sorted([int(b) for b in set(df_tsv[train_mask]['building_id'])])
        
        # In case some building was associated with multiple groups (e.g. cross-assigned), ensure strict disjointness
        overlap_bldgs = set(train_bldgs).intersection(set(test_bldgs))
        assert len(overlap_bldgs) == 0, f"Group {grp} holdout building leakage: {overlap_bldgs}"
        
        n_train_tsv = len(df_tsv[df_tsv['building_id'].isin(train_bldgs)])
        n_test_tsv = len(df_tsv[df_tsv['building_id'].isin(test_bldgs)])
        n_test_cc = len(df_clean[df_clean['building_id'].isin(test_bldgs)])
        
        splits_dict["leave_one_group_out"][f"holdout_{grp}_{group_name_map[grp].lower()}"] = {
            "held_out_group": grp,
            "held_out_name": group_name_map[grp],
            "n_train_buildings": int(len(train_bldgs)),
            "n_test_buildings": int(len(test_bldgs)),
            "n_train_all_tsv_rows": int(n_train_tsv),
            "n_test_all_tsv_rows": int(n_test_tsv),
            "n_test_complete_case_rows": int(n_test_cc),
            "train_buildings": train_bldgs,
            "test_buildings": test_bldgs
        }
        print(f"Leave-Group-Out ({grp}: {group_name_map[grp]}): Train={len(train_bldgs)} bldgs ({n_train_tsv:,} TSV rows) | Test={len(test_bldgs)} bldgs ({n_test_cc:,} complete-case rows)")
        
    with open(output_splits_json, 'w') as f:
        json.dump(splits_dict, f, indent=2)
    print(f"\nSaved compact splits to {output_splits_json} ({os.path.getsize(output_splits_json):,} bytes)")

if __name__ == "__main__":
    make_all_splits()
