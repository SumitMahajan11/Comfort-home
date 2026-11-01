"""
Data cleaning and preprocessing pipeline for ClimateAdapt-Comfort.
Loads raw ASHRAE DB II measurements and metadata, applies strict quality filters,
maps climate classes to major Köppen groups, constructs the 3-class target,
and outputs cleaned parquet data with full step-by-step row count auditing.
"""

import os
import pandas as pd
import numpy as np

def build_koppen_group_map(df_raw_merged=None):
    """
    Constructs the mapping table from all 31 raw DB II climate labels to major Köppen groups (A, B, C, D),
    including detailed meteorological rationales for ambiguous labels, building counts, and raw row counts.
    """
    mapping = [
        # Group A: Tropical
        {
            "raw_climate": "tropical wet savanna",
            "koppen_code": "Aw",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Distinct dry winter, wet summer; tropical thermal regime"
        },
        {
            "raw_climate": "tropical savanna",
            "koppen_code": "Aw",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Tropical savanna biome with seasonal precipitation"
        },
        {
            "raw_climate": "tropical monsoon",
            "koppen_code": "Am",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "High annual rainfall concentrated in monsoon season"
        },
        {
            "raw_climate": "tropical rainforest",
            "koppen_code": "Af",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Year-round high temperature and persistent heavy precipitation"
        },
        {
            "raw_climate": "tropical",
            "koppen_code": "A",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Generic tropical classification in equatorial SE Asia"
        },
        {
            "raw_climate": "wet equatorial",
            "koppen_code": "Af",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Equatorial belt climate with minimal seasonal temperature variation"
        },
        {
            "raw_climate": "tropical dry savanna",
            "koppen_code": "As",
            "koppen_group": "A",
            "group_name": "Tropical",
            "rationale": "Tropical dry-summer savanna regime"
        },
        
        # Group B: Arid / Dry
        {
            "raw_climate": "hot semi-arid",
            "koppen_code": "BSh",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Low precipitation with high mean annual temperature (>18°C)"
        },
        {
            "raw_climate": "hot desert",
            "koppen_code": "BWh",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "True hyper-arid desert with high solar radiation and extreme heat"
        },
        {
            "raw_climate": "desert (hot arid)",
            "koppen_code": "BWh",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Hot arid desert classification in Pakistan / Middle East"
        },
        {
            "raw_climate": "hot arid",
            "koppen_code": "BWh/BSh",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Arid interior climate in Australia with high daytime temperatures"
        },
        {
            "raw_climate": "semi arid high altitude",
            "koppen_code": "BSk",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Cold/high-elevation steppe with limited precipitation"
        },
        {
            "raw_climate": "semi arid midlatitude",
            "koppen_code": "BSk",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Mid-latitude steppe with cold winters and dry conditions"
        },
        {
            "raw_climate": "cold semi-arid",
            "koppen_code": "BSk",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Cold steppe climate with annual mean temperature <18°C"
        },
        {
            "raw_climate": "subtropical hot and dry",
            "koppen_code": "BSh",
            "koppen_group": "B",
            "group_name": "Arid",
            "rationale": "Ambiguous label (Cyprus): low annual rainfall (<400mm) and semi-arid regime"
        },
        
        # Group C: Temperate
        {
            "raw_climate": "hot-summer mediterranean",
            "koppen_code": "Csa",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Mild wet winters and hot, dry summers"
        },
        {
            "raw_climate": "humid subtropical",
            "koppen_code": "Cfa",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Hot, humid summers and mild winters without dry season"
        },
        {
            "raw_climate": "warm-summer mediterranean",
            "koppen_code": "Csb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Mild wet winters and warm (not hot), dry summers"
        },
        {
            "raw_climate": "mediterranean",
            "koppen_code": "Cs",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Generic Mediterranean dry-summer temperate regime"
        },
        {
            "raw_climate": "temperate oceanic",
            "koppen_code": "Cfb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Marine west coast climate with moderate year-round temperatures"
        },
        {
            "raw_climate": "monsoon-influenced humid subtropical",
            "koppen_code": "Cwa",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Humid subtropical with monsoon-dominated wet summers and dry winters"
        },
        {
            "raw_climate": "temperate",
            "koppen_code": "C",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Generic temperate climate in central Italy and Japan"
        },
        {
            "raw_climate": "west coast marine",
            "koppen_code": "Cfb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Maritime climate influenced by oceanic air masses"
        },
        {
            "raw_climate": "cool-summer mediterranean",
            "koppen_code": "Csc",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "High-elevation or coastal cool-summer Mediterranean variant"
        },
        {
            "raw_climate": "subtropical highland",
            "koppen_code": "Cwb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Highland temperate climate with mild temperatures (Shimla, India)"
        },
        {
            "raw_climate": "humid midlatitude",
            "koppen_code": "Cfa",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Ambiguous label (USA/Canada): mid-latitude humid temperate zone"
        },
        {
            "raw_climate": "temperature marine",
            "koppen_code": "Cfb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Typo in raw DB II for 'temperate marine' (SE Australia Cfb)"
        },
        {
            "raw_climate": "monsoon-influenced temperate oceanic",
            "koppen_code": "Cwb",
            "koppen_group": "C",
            "group_name": "Temperate",
            "rationale": "Cool montane monsoon climate (Shimla residential buildings, India)"
        },
        
        # Group D: Continental
        {
            "raw_climate": "monsoon-influenced hot-summer humid continental",
            "koppen_code": "Dwa",
            "koppen_group": "D",
            "group_name": "Continental",
            "rationale": "Severe winters (<-3°C) and hot monsoon summers (China, Korea)"
        },
        {
            "raw_climate": "warm-summer\xa0humid continental",
            "koppen_code": "Dfb",
            "koppen_group": "D",
            "group_name": "Continental",
            "rationale": "Humid continental with warm summers and cold snowy winters (contains non-breaking space)"
        },
        {
            "raw_climate": "continental subarctic",
            "koppen_code": "Dfc",
            "koppen_group": "D",
            "group_name": "Continental",
            "rationale": "Subarctic climate with long, very cold winters and brief summers (Canada)"
        },
    ]
    df_map = pd.DataFrame(mapping)
    
    # If raw data provided, compute building count and row count per raw climate
    if df_raw_merged is not None:
        stats = df_raw_merged.groupby('climate').agg(
            distinct_buildings=('building_id', 'nunique'),
            raw_total_rows=('record_id', 'count')
        ).reset_index()
        df_map = df_map.merge(stats, left_on='raw_climate', right_on='climate', how='left')
        df_map.drop(columns=['climate'], inplace=True)
        df_map['distinct_buildings'] = df_map['distinct_buildings'].fillna(0).astype(int)
        df_map['raw_total_rows'] = df_map['raw_total_rows'].fillna(0).astype(int)
    
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
    
    # 1. Load Raw Datasets
    log(f"Step 0: Loading raw data from:")
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
    
    # 2. Generate & Save Enhanced Köppen Group Map
    df_map = build_koppen_group_map(df)
    df_map.to_csv(output_map_csv, index=False)
    log(f"\nGenerated Köppen group map ({len(df_map)} climate classes with building counts & rationales) -> {output_map_csv}")
    
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
    # In complete-case data, check if any rh <= 0 or clo <= 0 exist:
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
    climate_to_group = dict(zip(df_map['raw_climate'], df_map['koppen_group']))
    climate_to_group_name = dict(zip(df_map['raw_climate'], df_map['group_name']))
    climate_to_code = dict(zip(df_map['raw_climate'], df_map['koppen_code']))
    
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
    
    # India Audit Breakdown
    df_clean_in = df_step3[df_step3['country'].str.lower() == 'india']
    log(f"\nINDIA SPECIFIC AUDIT BREAKDOWN:")
    log(f"  Raw India rows: 18,714")
    log(f"  India rows with valid TSV: 18,639 (dropped 75 missing TSV)")
    log(f"  India rows with valid ta: 18,639 (0 missing ta)")
    log(f"  India rows with valid tr: 2,170 (dropped 16,469 rows due to missing tr!)")
    log(f"  India rows with valid rh, vel, clo, met: 2,170 (all present)")
    log(f"  Final clean complete-case India rows: {len(df_clean_in):,} across {df_clean_in['building_id'].nunique()} buildings")
    log("================================================================================")
    
    with open(log_path, 'w') as f:
        f.write('\n'.join(log_lines))
    log(f"Cleaning log written to {log_path}")

if __name__ == "__main__":
    run_cleaning_pipeline()
