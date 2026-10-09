"""
Unit tests for data splits assertion (no building_id leakage across folds).
Acceptance check for Phase 2.
"""

import json
import os
import pandas as pd
import pytest

def test_splits_integrity():
    splits_file = "data/processed/splits.json"
    clean_file = "data/processed/comfort_clean.parquet"
    
    assert os.path.exists(splits_file), f"Splits file not found: {splits_file}"
    assert os.path.exists(clean_file), f"Clean parquet file not found: {clean_file}"
    
    with open(splits_file, "r") as f:
        splits = json.load(f)
        
    df = pd.read_parquet(clean_file)
    total_rows = len(df)
    
    assert splits["metadata"]["total_rows"] == total_rows, "Total rows mismatch!"
    
    print("\n" + "="*80)
    print("NO-LEAKAGE ASSERTION TESTS ON SPLITS")
    print("="*80)
    
    # 1. Test 5-Fold GroupKFold
    print("\n--- 1. Testing 5-Fold GroupKFold (by building_id) ---")
    gkf_folds = splits["group_kfold_5"]
    assert len(gkf_folds) == 5, f"Expected 5 folds, found {len(gkf_folds)}"
    
    all_test_indices = []
    
    for fold_name, fold_data in gkf_folds.items():
        train_idx = set(fold_data["train_indices"])
        test_idx = set(fold_data["test_indices"])
        train_bldgs = set(fold_data["train_buildings"])
        test_bldgs = set(fold_data["test_buildings"])
        
        # Row index non-overlap & completeness
        assert len(train_idx.intersection(test_idx)) == 0, f"Index overlap in {fold_name}!"
        assert len(train_idx) + len(test_idx) == total_rows, f"Index count mismatch in {fold_name}!"
        all_test_indices.extend(list(test_idx))
        
        # Building ID non-overlap
        bldg_overlap = train_bldgs.intersection(test_bldgs)
        assert len(bldg_overlap) == 0, f"CRITICAL: building_id leakage in {fold_name}: {bldg_overlap}"
        
        # Verify indices match dataframe building IDs
        df_train_bldgs = set(df.iloc[list(train_idx)]['building_id'])
        df_test_bldgs = set(df.iloc[list(test_idx)]['building_id'])
        assert df_train_bldgs == train_bldgs, f"Train building set mismatch in {fold_name}"
        assert df_test_bldgs == test_bldgs, f"Test building set mismatch in {fold_name}"
        assert len(df_train_bldgs.intersection(df_test_bldgs)) == 0, f"Direct DF building leakage in {fold_name}!"
        
        print(f"  [PASS] {fold_name}: Train={len(train_idx):,} rows ({len(train_bldgs)} bldgs) | Test={len(test_idx):,} rows ({len(test_bldgs)} bldgs) | Overlap={len(bldg_overlap)}")
        
    assert len(all_test_indices) == total_rows, "K-Fold test partition does not cover exact total rows!"
    assert len(set(all_test_indices)) == total_rows, "Duplicate test indices across K-Fold splits!"
    print("  [PASS] 5-Fold GroupKFold partitions exact 58,512 rows with zero building overlap.")
    
    # 2. Test Leave-One-Group-Out
    print("\n--- 2. Testing Leave-One-Köppen-Major-Group-Out ---")
    logo_folds = splits["leave_one_group_out"]
    assert len(logo_folds) == 4, f"Expected 4 major groups, found {len(logo_folds)}"
    
    for holdout_name, holdout_data in logo_folds.items():
        grp = holdout_data["held_out_group"]
        grp_name = holdout_data["held_out_name"]
        train_idx = set(holdout_data["train_indices"])
        test_idx = set(holdout_data["test_indices"])
        train_bldgs = set(holdout_data["train_buildings"])
        test_bldgs = set(holdout_data["test_buildings"])
        
        # Row index non-overlap & completeness
        assert len(train_idx.intersection(test_idx)) == 0, f"Index overlap in {holdout_name}!"
        assert len(train_idx) + len(test_idx) == total_rows, f"Index count mismatch in {holdout_name}!"
        
        # Building non-overlap
        bldg_overlap = train_bldgs.intersection(test_bldgs)
        assert len(bldg_overlap) == 0, f"CRITICAL: building_id leakage in {holdout_name}: {bldg_overlap}"
        
        # Verify correct Köppen group isolation
        test_groups = set(df.iloc[list(test_idx)]['koppen_group'])
        train_groups = set(df.iloc[list(train_idx)]['koppen_group'])
        assert test_groups == {grp}, f"Test set in {holdout_name} contains wrong group: {test_groups}"
        assert grp not in train_groups, f"Train set in {holdout_name} contains test group {grp}!"
        
        print(f"  [PASS] {holdout_name} (Group {grp}: {grp_name}): Train={len(train_idx):,} rows ({len(train_bldgs)} bldgs) | Test={len(test_idx):,} rows ({len(test_bldgs)} bldgs) | Overlap={len(bldg_overlap)}")
        
    print("  [PASS] All 4 Leave-One-Group-Out holdout sets strictly isolated with zero building leakage.")
    print("\nALL SPLIT ASSERTION CHECKS PASSED SUCCESSFULLY (0 FAILURES).")

if __name__ == "__main__":
    test_splits_integrity()
