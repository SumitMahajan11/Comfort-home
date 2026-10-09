"""
Dataset splitting module for ClimateAdapt-Comfort.
Constructs strict group-held-out splits:
1. 5-fold GroupKFold grouped by building_id (seed 42).
2. Leave-One-Köppen-Major-Group-Out (A: Tropical, B: Arid, C: Temperate, D: Continental).
Outputs data/processed/splits.json with index mappings and building metadata.
"""

import json
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold

def generate_splits(
    clean_parquet_path="data/processed/comfort_clean.parquet",
    output_splits_json="data/processed/splits.json"
):
    df = pd.read_parquet(clean_parquet_path)
    print(f"Loaded {len(df):,} cleaned rows for splitting.")
    
    splits_dict = {
        "metadata": {
            "total_rows": len(df),
            "distinct_buildings": int(df['building_id'].nunique()),
            "seed": 42,
            "groups": ["A", "B", "C", "D"],
            "features_complete": ["ta", "tr", "rh", "vel", "clo", "met"]
        },
        "group_kfold_5": {},
        "leave_one_group_out": {}
    }
    
    # 1. 5-Fold GroupKFold by building_id
    gkf = GroupKFold(n_splits=5)
    groups = df['building_id'].values
    indices = np.arange(len(df))
    
    for fold, (train_idx, test_idx) in enumerate(gkf.split(df, groups=groups)):
        train_bldgs = sorted(list(set(df.iloc[train_idx]['building_id'].tolist())))
        test_bldgs = sorted(list(set(df.iloc[test_idx]['building_id'].tolist())))
        
        # Immediate assertion
        overlap = set(train_bldgs).intersection(set(test_bldgs))
        assert len(overlap) == 0, f"Fold {fold} has building_id leakage: {overlap}"
        
        splits_dict["group_kfold_5"][f"fold_{fold}"] = {
            "fold": fold,
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "n_train_buildings": len(train_bldgs),
            "n_test_buildings": len(test_bldgs),
            "train_indices": train_idx.tolist(),
            "test_indices": test_idx.tolist(),
            "train_buildings": train_bldgs,
            "test_buildings": test_bldgs
        }
        print(f"GroupKFold Fold {fold}: Train={len(train_idx):,} rows ({len(train_bldgs)} bldgs), Test={len(test_idx):,} rows ({len(test_bldgs)} bldgs)")

    # 2. Leave-One-Köppen-Major-Group-Out
    for grp in ["A", "B", "C", "D"]:
        test_mask = (df['koppen_group'] == grp)
        train_mask = ~test_mask
        
        train_idx = np.where(train_mask)[0]
        test_idx = np.where(test_mask)[0]
        
        train_bldgs = sorted(list(set(df.iloc[train_idx]['building_id'].tolist())))
        test_bldgs = sorted(list(set(df.iloc[test_idx]['building_id'].tolist())))
        
        # Immediate assertion
        overlap = set(train_bldgs).intersection(set(test_bldgs))
        assert len(overlap) == 0, f"Group {grp} holdout has building leakage: {overlap}"
        
        group_name_map = {"A": "Tropical", "B": "Arid", "C": "Temperate", "D": "Continental"}
        splits_dict["leave_one_group_out"][f"holdout_{grp}_{group_name_map[grp].lower()}"] = {
            "held_out_group": grp,
            "held_out_name": group_name_map[grp],
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "n_train_buildings": len(train_bldgs),
            "n_test_buildings": len(test_bldgs),
            "train_indices": train_idx.tolist(),
            "test_indices": test_idx.tolist(),
            "train_buildings": train_bldgs,
            "test_buildings": test_bldgs
        }
        print(f"Leave-Group-Out ({grp}: {group_name_map[grp]}): Train={len(train_idx):,} rows ({len(train_bldgs)} bldgs), Test={len(test_idx):,} rows ({len(test_bldgs)} bldgs)")
        
    os.makedirs(os.path.dirname(output_splits_json), exist_ok=True)
    with open(output_splits_json, 'w') as f:
        json.dump(splits_dict, f, indent=2)
    print(f"\nSaved all splits to {output_splits_json}")

if __name__ == "__main__":
    generate_splits()
