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
    tsv_file = "data/processed/comfort_tsv_all.parquet"
    clean_file = "data/processed/comfort_clean.parquet"
    
    assert os.path.exists(splits_file), f"Splits file not found: {splits_file}"
    if not os.path.exists(tsv_file) or not os.path.exists(clean_file):
        with open(splits_file, "r") as f:
            splits = json.load(f)
        gkf_folds = splits["group_kfold_5"]
        assert len(gkf_folds) == 5, f"Expected 5 folds, found {len(gkf_folds)}"
        all_test_bldgs = []
        for fold_name, fold_data in gkf_folds.items():
            train_bldgs = set(fold_data["train_buildings"])
            test_bldgs = set(fold_data["test_buildings"])
            assert len(train_bldgs.intersection(test_bldgs)) == 0, f"Building leakage in {fold_name}"
            all_test_bldgs.extend(list(test_bldgs))
        assert len(all_test_bldgs) == len(set(all_test_bldgs)), "Duplicate test buildings across folds!"
        logo_folds = splits["leave_one_group_out"]
        assert len(logo_folds) == 4, f"Expected 4 groups, found {len(logo_folds)}"
        for holdout_name, holdout_data in logo_folds.items():
            train_bldgs = set(holdout_data["train_buildings"])
            test_bldgs = set(holdout_data["test_buildings"])
            assert len(train_bldgs.intersection(test_bldgs)) == 0, f"Building leakage in {holdout_name}"
        pytest.skip("Large DB II raw parquets not bundled in distribution; verified splits.json structure and zero building leakage.")
        return

    with open(splits_file, "r") as f:
        splits = json.load(f)
        
    df_tsv = pd.read_parquet(tsv_file)
    df_clean = pd.read_parquet(clean_file)
    
    total_tsv_rows = len(df_tsv)
    total_clean_rows = len(df_clean)
    total_bldgs = df_tsv['building_id'].nunique()
    
    assert splits["metadata"]["total_tsv_rows"] == total_tsv_rows, "Total TSV rows mismatch!"
    assert splits["metadata"]["total_complete_case_rows"] == total_clean_rows, "Total complete case rows mismatch!"
    assert splits["metadata"]["distinct_buildings"] == total_bldgs, "Total buildings mismatch!"
    
    print("\n" + "="*80)
    print("NO-LEAKAGE AND EVALUATION INTEGRITY ASSERTION TESTS ON SPLITS")
    print("="*80)
    print(f"Total TSV rows: {total_tsv_rows:,} | Total Complete-Case rows: {total_clean_rows:,} | Distinct Buildings: {total_bldgs}")
    
    # 1. Test 5-Fold GroupKFold
    print("\n--- 1. Testing 5-Fold GroupKFold (by building_id) ---")
    gkf_folds = splits["group_kfold_5"]
    assert len(gkf_folds) == 5, f"Expected 5 folds, found {len(gkf_folds)}"
    
    all_test_buildings = []
    total_eval_cc_rows = 0
    
    for fold_name, fold_data in gkf_folds.items():
        train_bldgs = set(fold_data["train_buildings"])
        test_bldgs = set(fold_data["test_buildings"])
        
        # Verify counts in json match actual building list lengths
        assert len(train_bldgs) == fold_data["n_train_buildings"], f"Train building count mismatch in {fold_name}"
        assert len(test_bldgs) == fold_data["n_test_buildings"], f"Test building count mismatch in {fold_name}"
        
        # Building non-overlap
        bldg_overlap = train_bldgs.intersection(test_bldgs)
        assert len(bldg_overlap) == 0, f"CRITICAL: building_id leakage in {fold_name}: {bldg_overlap}"
        
        # Verify data rows matching these buildings
        train_tsv_rows = len(df_tsv[df_tsv['building_id'].isin(train_bldgs)])
        test_cc_rows = len(df_clean[df_clean['building_id'].isin(test_bldgs)])
        
        assert train_tsv_rows == fold_data["n_train_all_tsv_rows"], f"Train TSV row count mismatch in {fold_name}"
        assert test_cc_rows == fold_data["n_test_complete_case_rows"], f"Test CC row count mismatch in {fold_name}"
        
        # Verify zero row leakage between train and test
        df_train_idx = set(df_tsv[df_tsv['building_id'].isin(train_bldgs)]['record_id'])
        df_test_idx = set(df_clean[df_clean['building_id'].isin(test_bldgs)]['record_id'])
        assert len(df_train_idx.intersection(df_test_idx)) == 0, f"Record ID leakage in {fold_name}!"
        
        all_test_buildings.extend(list(test_bldgs))
        total_eval_cc_rows += test_cc_rows
        
        print(f"  [PASS] {fold_name}: Train={len(train_bldgs)} bldgs ({train_tsv_rows:,} TSV rows) | Test={len(test_bldgs)} bldgs ({test_cc_rows:,} complete cases) | Overlap={len(bldg_overlap)}")
        
    assert len(all_test_buildings) == total_bldgs, "K-Fold test building union does not equal total buildings!"
    assert len(set(all_test_buildings)) == total_bldgs, "Duplicate test buildings across K-Fold splits!"
    assert total_eval_cc_rows == total_clean_rows, f"Total evaluated complete cases ({total_eval_cc_rows}) != {total_clean_rows}"
    print(f"  [PASS] 5-Fold GroupKFold cleanly partitions exact {total_bldgs} buildings and {total_clean_rows:,} complete-case test rows.")
    
    # 2. Test Leave-One-Group-Out
    print("\n--- 2. Testing Leave-One-Köppen-Major-Group-Out ---")
    logo_folds = splits["leave_one_group_out"]
    assert len(logo_folds) == 4, f"Expected 4 major groups, found {len(logo_folds)}"
    
    for holdout_name, holdout_data in logo_folds.items():
        grp = holdout_data["held_out_group"]
        grp_name = holdout_data["held_out_name"]
        
        train_bldgs = set(holdout_data["train_buildings"])
        test_bldgs = set(holdout_data["test_buildings"])
        
        # Building non-overlap
        bldg_overlap = train_bldgs.intersection(test_bldgs)
        assert len(bldg_overlap) == 0, f"CRITICAL: building_id leakage in {holdout_name}: {bldg_overlap}"
        
        # Verify correct Köppen group isolation
        test_df = df_clean[df_clean['building_id'].isin(test_bldgs)]
        train_df = df_tsv[df_tsv['building_id'].isin(train_bldgs)]
        
        test_groups = set(test_df['koppen_group'].dropna())
        train_groups = set(train_df['koppen_group'].dropna())
        
        assert test_groups == {grp}, f"Test set in {holdout_name} contains wrong groups: {test_groups}"
        assert grp not in train_groups, f"Train set in {holdout_name} contains test group {grp}!"
        
        test_cc_rows = len(test_df)
        train_tsv_rows = len(train_df)
        
        print(f"  [PASS] {holdout_name} (Group {grp}: {grp_name}): Train={len(train_bldgs)} bldgs ({train_tsv_rows:,} TSV rows) | Test={len(test_bldgs)} bldgs ({test_cc_rows:,} complete cases) | Overlap={len(bldg_overlap)}")
        
    print("  [PASS] All 4 Leave-One-Group-Out holdout sets strictly isolated with zero building leakage.")
    print("\nALL SPLIT ASSERTION CHECKS PASSED SUCCESSFULLY (0 FAILURES).")

if __name__ == "__main__":
    test_splits_integrity()
