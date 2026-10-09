"""
Data cleaning and preprocessing pipeline for ClimateAdapt-Comfort.
Loads raw ASHRAE DB II measurements and metadata, applies strict quality filters,
maps climate classes to major Köppen groups, constructs the 3-class target,
and outputs cleaned parquet data with full step-by-step row count auditing.
"""

import os
import pandas as pd
import numpy as np

def build_koppen_group_map():
    """Constructs the mapping table from 31 raw DB II climate labels to major Köppen groups."""
    mapping = [
        # Group A: Tropical
        {"raw_climate": "tropical wet savanna", "koppen_code": "Aw", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "tropical savanna", "koppen_code": "Aw", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "tropical monsoon", "koppen_code": "Am", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "tropical rainforest", "koppen_code": "Af", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "tropical", "koppen_code": "A", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "wet equatorial", "koppen_code": "Af", "koppen_group": "A", "group_name": "Tropical"},
        {"raw_climate": "tropical dry savanna", "koppen_code": "As", "koppen_group": "A", "group_name": "Tropical"},
        
        # Group B: Arid / Dry
        {"raw_climate": "hot semi-arid", "koppen_code": "BSh", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "hot desert", "koppen_code": "BWh", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "desert (hot arid)", "koppen_code": "BWh", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "hot arid", "koppen_code": "BWh/BSh", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "semi arid high altitude", "koppen_code": "BSk", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "semi arid midlatitude", "koppen_code": "BSk", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "cold semi-arid", "koppen_code": "BSk", "koppen_group": "B", "group_name": "Arid"},
        {"raw_climate": "subtropical hot and dry", "koppen_code": "BSh", "koppen_group": "B", "group_name": "Arid"},
        
        # Group C: Temperate
        {"raw_climate": "hot-summer mediterranean", "koppen_code": "Csa", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "humid subtropical", "koppen_code": "Cfa", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "warm-summer mediterranean", "koppen_code": "Csb", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "mediterranean", "koppen_code": "Cs", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "temperate oceanic", "koppen_code": "Cfb", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "monsoon-influenced humid subtropical", "koppen_code": "Cwa", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "temperate", "koppen_code": "C", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "west coast marine", "koppen_code": "Cfb", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "cool-summer mediterranean", "koppen_code": "Csc", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "subtropical highland", "koppen_code": "Cwb", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "humid midlatitude", "koppen_code": "Cfa", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "temperature marine", "koppen_code": "Cfb", "koppen_group": "C", "group_name": "Temperate"},
        {"raw_climate": "monsoon-influenced temperate oceanic", "koppen_code": "Cwb", "koppen_group": "C", "group_name": "Temperate"},
        
        # Group D: Continental
        {"raw_climate": "monsoon-influenced hot-summer humid continental", "koppen_code": "Dwa", "koppen_group": "D", "group_name": "Continental"},
        {"raw_climate": "warm-summer\xa0humid continental", "koppen_code": "Dfb", "koppen_group": "D", "group_name": "Continental"},
        {"raw_climate": "continental subarctic", "koppen_code": "Dfc", "koppen_group": "D", "group_name": "Continental"},
    ]
    df_map = pd.DataFrame(mapping)
    return df_map

def map_target(tsv):
    """Maps continuous/7-point TSV to 3-class target integer: Cool (-1), Neutral (0), Warm (+1)."""
    if pd.isnull(tsv):
        return np.nan
    if tsv < -0.5:
        return -1
    elif tsv <= 0.5:
        return 0
    else:
        return 1

def run_cleaning_pipeline(
    meas_path="data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz",
    meta_path="data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv",
    output_parquet="data/processed/comfort_clean.parquet",
    output_map_csv="data/processed/koppen_group_map.csv",
    log_path="reports/evidence/phase2_cleaning_log.txt"
):
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)
    
    log("================================================================================")
    log("PHASE 2 DATA CLEANING PIPELINE")
    log("================================================================================")
    
    # 1. Generate & Save Köppen Group Map
    df_map = build_koppen_group_map()
    df_map.to_csv(output_map_csv, index=False)
    log(f"Generated Köppen group map ({len(df_map)} climate classes) -> {output_map_csv}")
    
    # 2. Load Raw Datasets
    log(f"\nStep 0: Loading raw data from:")
    log(f"  Measurements: {meas_path}")
    log(f"  Metadata:     {meta_path}")
    
    df_meas = pd.read_csv(meas_path, low_memory=False)
    df_meta = pd.read_csv(meta_path, low_memory=False)
    
    log(f"  Raw measurements rows: {len(df_meas):,}")
    log(f"  Raw metadata buildings: {len(df_meta):,}")
    
    # Merge on building_id
    df = df_meas.merge(df_meta, on='building_id', how='left')
    initial_rows = len(df)
    log(f"  Merged dataset initial row count: {initial_rows:,}")
    
    # 3. Rule 1: Drop missing target (thermal_sensation)
    df_step1 = df[df['thermal_sensation'].notnull()].copy()
    rows_after_r1 = len(df_step1)
    dropped_r1 = initial_rows - rows_after_r1
    log(f"\nRule 1: Drop rows with missing thermal_sensation (TSV)")
    log(f"  Rows dropped: {dropped_r1:,} ({dropped_r1/initial_rows*100:.2f}%)")
    log(f"  Remaining rows: {rows_after_r1:,}")
    
    # 4. Rule 2: Drop missing primary physical features (ta, tr, rh, vel, clo, met)
    primary_features = ['ta', 'tr', 'rh', 'vel', 'clo', 'met']
    df_step2 = df_step1.dropna(subset=primary_features).copy()
    rows_after_r2 = len(df_step2)
    dropped_r2 = rows_after_r1 - rows_after_r2
    log(f"\nRule 2: Drop rows missing any primary feature ({', '.join(primary_features)})")
    log(f"  Rows dropped: {dropped_r2:,} ({dropped_r2/rows_after_r1*100:.2f}%)")
    log(f"  Remaining rows: {rows_after_r2:,}")
    
    # 5. Rule 3: Drop physically impossible / sensor malfunction values
    # rh == 0 (sensor drop, 1 row)
    # clo == 0 (invalid 0-imputed clothing, 6 rows)
    mask_invalid_rh = (df_step2['rh'] <= 0.0)
    mask_invalid_clo = (df_step2['clo'] <= 0.0)
    mask_invalid = mask_invalid_rh | mask_invalid_clo
    
    dropped_rh0 = int(mask_invalid_rh.sum())
    dropped_clo0 = int(mask_invalid_clo.sum())
    total_invalid = int(mask_invalid.sum())
    
    df_step3 = df_step2[~mask_invalid].copy()
    rows_after_r3 = len(df_step3)
    log(f"\nRule 3: Drop physically impossible values (rh <= 0%: {dropped_rh0} rows, clo <= 0: {dropped_clo0} rows)")
    log(f"  Rows dropped: {total_invalid:,}")
    log(f"  Remaining rows: {rows_after_r3:,}")
    
    # 6. Rule 4: Flag extreme values without dropping
    df_step3['flag_high_vel'] = (df_step3['vel'] > 3.0).astype(int)
    df_step3['flag_high_met'] = (df_step3['met'] > 4.0).astype(int)
    df_step3['flag_extreme'] = ((df_step3['flag_high_vel'] == 1) | (df_step3['flag_high_met'] == 1)).astype(int)
    
    n_high_vel = int(df_step3['flag_high_vel'].sum())
    n_high_met = int(df_step3['flag_high_met'].sum())
    n_extreme = int(df_step3['flag_extreme'].sum())
    log(f"\nRule 4: Flag extreme values (preserved in dataset):")
    log(f"  High velocity (vel > 3.0 m/s): {n_high_vel} rows")
    log(f"  High metabolic rate (met > 4.0 met): {n_high_met} rows")
    log(f"  Total flagged rows: {n_extreme} rows ({n_extreme/rows_after_r3*100:.2f}%)")
    
    # 7. Rule 5: Construct 3-Class Target
    df_step3['tsv_3class'] = df_step3['thermal_sensation'].apply(map_target).astype(int)
    df_step3['tsv_3class_label'] = df_step3['tsv_3class'].map({-1: 'Cool', 0: 'Neutral', 1: 'Warm'})
    
    log(f"\nRule 5: 3-Class Target Distribution:")
    for label, code in [('Cool (-1)', -1), ('Neutral (0)', 0), ('Warm (+1)', 1)]:
        cnt = int((df_step3['tsv_3class'] == code).sum())
        pct = cnt / rows_after_r3 * 100.0
        log(f"  {label:15s}: {cnt:6,d} rows ({pct:.2f}%)")
        
    # 8. Rule 6: Merge Köppen Major Groups
    # Normalize unicode / non-breaking spaces for merging
    df_map_clean = df_map.copy()
    climate_to_group = dict(zip(df_map_clean['raw_climate'], df_map_clean['koppen_group']))
    climate_to_group_name = dict(zip(df_map_clean['raw_climate'], df_map_clean['group_name']))
    climate_to_code = dict(zip(df_map_clean['raw_climate'], df_map_clean['koppen_code']))
    
    df_step3['koppen_group'] = df_step3['climate'].map(climate_to_group)
    df_step3['koppen_group_name'] = df_step3['climate'].map(climate_to_group_name)
    df_step3['koppen_code'] = df_step3['climate'].map(climate_to_code)
    
    # Verify no unmapped climates
    unmapped = df_step3['koppen_group'].isnull().sum()
    if unmapped > 0:
        raise ValueError(f"Found {unmapped} rows with unmapped climate classes!")
        
    log(f"\nRule 6: Köppen Major Group Distribution:")
    for grp, name in [('A', 'Tropical'), ('B', 'Arid'), ('C', 'Temperate'), ('D', 'Continental')]:
        sub = df_step3[df_step3['koppen_group'] == grp]
        cnt = len(sub)
        bldgs = sub['building_id'].nunique()
        countries = sub['country'].nunique()
        pct = cnt / rows_after_r3 * 100.0
        log(f"  Group {grp} ({name:11s}): {cnt:6,d} rows ({pct:5.2f}%) | {bldgs:3d} buildings | {countries:2d} countries")
        
    # 9. Summary and Export
    df_step3.to_parquet(output_parquet, index=False)
    log(f"\n================================================================================")
    log(f"CLEANING COMPLETE: Saved {len(df_step3):,} rows x {df_step3.shape[1]} cols to {output_parquet}")
    log(f"Total retention rate from raw merged dataset: {len(df_step3)/initial_rows*100:.2f}%")
    log(f"Distinct buildings in clean dataset: {df_step3['building_id'].nunique()}")
    log(f"Distinct countries in clean dataset: {df_step3['country'].nunique()}")
    log(f"India rows in clean dataset: {len(df_step3[df_step3['country'].str.lower() == 'india']):,} across {df_step3[df_step3['country'].str.lower() == 'india']['building_id'].nunique()} buildings")
    log("================================================================================")
    
    with open(log_path, 'w') as f:
        f.write('\n'.join(log_lines))
    log(f"Cleaning log written to {log_path}")

if __name__ == "__main__":
    run_cleaning_pipeline()
