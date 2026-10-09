import os
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score, confusion_matrix

pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 500)
pd.set_option('display.width', 1000)

print("================================================================================")
print("PHASE 1 EDA: THERMAL COMFORT DATASET COMPUTATIONS (RE-RUN & VERIFIED)")
print("================================================================================")

# 1. Load Data from data/raw only
meas_path = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz'
meta_path = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv'

df_meas = pd.read_csv(meas_path, low_memory=False)
df_meta = pd.read_csv(meta_path, low_memory=False)
df = df_meas.merge(df_meta, on='building_id', how='left')

total_rows = len(df)
print(f"Total Merged Rows: {total_rows:,} across {df['building_id'].nunique()} distinct buildings")

# 2. Target Definition & 3-Class Mapping
def map_to_3class(val):
    if pd.isnull(val):
        return np.nan
    if val < -0.5:
        return 'Cool (-1)'
    elif val <= 0.5:
        return 'Neutral (0)'
    else:
        return 'Warm (+1)'

df['tsv_3class'] = df['thermal_sensation'].apply(map_to_3class)

print("\n" + "="*80)
print("1. TARGET DISTRIBUTION (GLOBAL & PER KÖPPEN CLASS)")
print("="*80)

# Global 3-Class
tsv_counts = df['tsv_3class'].value_counts(dropna=False)
valid_tsv_count = df['tsv_3class'].dropna().count()
print(f"Valid TSV Rows: {valid_tsv_count:,} ({valid_tsv_count/total_rows*100:.2f}%)")
print(f"Missing TSV Rows: {df['tsv_3class'].isnull().sum():,} ({df['tsv_3class'].isnull().sum()/total_rows*100:.2f}%)")

df_tsv_summary = pd.DataFrame({
    'Class': tsv_counts.index.astype(str),
    'Count': tsv_counts.values,
    'Pct_Total': (tsv_counts.values / total_rows * 100).round(2),
    'Pct_Valid': [(v / valid_tsv_count * 100).round(2) if k != 'nan' and pd.notnull(k) else np.nan for k, v in zip(tsv_counts.index, tsv_counts.values)]
})
print("\nGlobal 3-Class Target Distribution:")
print(df_tsv_summary.to_string(index=False))

# Per Köppen Class
print("\nPer Köppen Class 3-Class Breakdown:")
koppen_crosstab = pd.crosstab(df['climate'], df['tsv_3class'].fillna('Missing (NaN)'), margins=True)
print(koppen_crosstab.to_string())

# India 3-Class
df_india = df[df['country'].str.lower() == 'india']
print(f"\nIndia Total Rows: {len(df_india):,}")
in_tsv_counts = df_india['tsv_3class'].value_counts(dropna=False)
in_valid_tsv = df_india['tsv_3class'].dropna().count()
print("India 3-Class Distribution:")
for k, v in in_tsv_counts.items():
    print(f"  {str(k):15s}: {v:6,d} rows ({v/len(df_india)*100:5.2f}% total | {v/in_valid_tsv*100:5.2f}% valid if non-null)")

print("\n" + "="*80)
print("2. PHYSICAL VARIABLES: MIN / MAX / PERCENTILES & OUTLIERS")
print("="*80)

phys_vars = ['ta', 'tr', 'rh', 'vel', 'clo', 'met']
stat_records = []

for var in phys_vars:
    s = df[var].dropna()
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers_count = int(((s < lower_bound) | (s > upper_bound)).sum())
    
    stat_records.append({
        'Variable': var,
        'Non-Null': len(s),
        'Null': df[var].isnull().sum(),
        'Missing %': f"{df[var].isnull().sum()/total_rows*100:.2f}%",
        'Min': round(s.min(), 3),
        'P01': round(s.quantile(0.01), 3),
        'P05': round(s.quantile(0.05), 3),
        'Q1': round(q1, 3),
        'Median': round(s.median(), 3),
        'Mean': round(s.mean(), 3),
        'Q3': round(q3, 3),
        'P95': round(s.quantile(0.95), 3),
        'P99': round(s.quantile(0.99), 3),
        'Max': round(s.max(), 3),
        'Std': round(s.std(), 3),
        'IQR': round(iqr, 3),
        'IQR Outliers': outliers_count,
        'IQR Outliers %': f"{outliers_count/len(s)*100:.2f}%"
    })

df_stats = pd.DataFrame(stat_records)
print(df_stats.to_string(index=False))

print("\nPhysical Boundary Checks on Raw Data:")
print(f"  ta <= 0 or ta >= 50: {len(df[(df['ta'] <= 0) | (df['ta'] >= 50)])} rows")
print(f"  tr <= 0 or tr >= 60: {len(df[(df['tr'] <= 0) | (df['tr'] >= 60)])} rows")
print(f"  rh <= 0 or rh > 100: {len(df[(df['rh'] <= 0) | (df['rh'] > 100)])} rows (Min rh = {df['rh'].min()})")
print(f"  vel < 0 or vel > 10: {len(df[(df['vel'] < 0) | (df['vel'] > 10)])} rows (Min vel = {df['vel'].min()})")
print(f"  clo <= 0 or clo > 4: {len(df[(df['clo'] <= 0) | (df['clo'] > 4)])} rows (Min clo = {df['clo'].min()})")
print(f"  met <= 0 or met > 6: {len(df[(df['met'] <= 0) | (df['met'] > 6)])} rows (Min met = {df['met'].min()})")

print("\n" + "="*80)
print("3. DISTINCT BUILDINGS AND ROWS PER KÖPPEN CLASS (<3 BUILDINGS FLAGGED)")
print("="*80)

climate_bldg_stats = df.groupby('climate').agg(
    distinct_buildings=('building_id', 'nunique'),
    total_rows=('record_id', 'count'),
    min_rows_per_bldg=('building_id', lambda x: x.value_counts().min()),
    median_rows_per_bldg=('building_id', lambda x: x.value_counts().median()),
    max_rows_per_bldg=('building_id', lambda x: x.value_counts().max())
).reset_index()

climate_bldg_stats['pct_of_total_rows'] = (climate_bldg_stats['total_rows'] / total_rows * 100).round(2)
climate_bldg_stats['flag_few_buildings (<3)'] = climate_bldg_stats['distinct_buildings'] < 3

climate_bldg_stats = climate_bldg_stats.sort_values(by=['distinct_buildings', 'total_rows'], ascending=[False, False])
print(climate_bldg_stats.to_string(index=False))

flagged = climate_bldg_stats[climate_bldg_stats['flag_few_buildings (<3)']]
print(f"\nExact Classes with < 3 Buildings: {len(flagged)} out of 31 classes:")
print(flagged[['climate', 'distinct_buildings', 'total_rows', 'pct_of_total_rows']].to_string(index=False))

print("\n" + "="*80)
print("4. COMPLETE-CASE ROWS PER CANDIDATE FEATURE SET")
print("="*80)

feature_sets = {
    'Set A: 6 Physics + TSV (ta, tr, rh, vel, clo, met, tsv)': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set B: 5 Features (no tr) + TSV (ta, rh, vel, clo, met, tsv)': ['ta', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set C: top + 4 Features + TSV (top, rh, vel, clo, met, tsv)': ['top', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set D: 6 Physics + t_out + TSV': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_out', 'thermal_sensation'],
    'Set E: 6 Physics + t_mot_isd + TSV': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_mot_isd', 'thermal_sensation'],
    'Set F: 6 Physics + TSV + pmv': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 'thermal_sensation', 'pmv']
}

cc_records = []
for name, cols in feature_sets.items():
    m = df[cols].notnull().all(axis=1)
    n_global = int(m.sum())
    n_india = int((m & (df['country'].str.lower() == 'india')).sum())
    n_nv = int((m & (df['cooling_type'] == 'naturally ventilated')).sum())
    
    cc_records.append({
        'Feature Set': name,
        'Global Complete Rows': n_global,
        'Global %': f"{n_global/total_rows*100:.2f}%",
        'India Complete Rows': n_india,
        'India %': f"{n_india/len(df_india)*100:.2f}%",
        'NV Complete Rows': n_nv,
        'NV %': f"{n_nv/len(df[df['cooling_type'] == 'naturally ventilated'])*100:.2f}%"
    })

df_cc_table = pd.DataFrame(cc_records)
print(df_cc_table.to_string(index=False))

# Tropical Major Group True Raw Count
tropical_classes = [
    'tropical wet savanna', 'tropical savanna', 'tropical monsoon',
    'tropical rainforest', 'tropical', 'wet equatorial', 'tropical dry savanna'
]
df_tropical_true = df[df['climate'].isin(tropical_classes)]
print(f"\nTRUE Tropical Raw Rows (from the 7 tropical classes): {len(df_tropical_true):,} ({len(df_tropical_true)/total_rows*100:.2f}%)")
print(df_tropical_true['climate'].value_counts().to_string())

print("\n" + "="*80)
print("5. REFERENCE BASELINES (SCORED ON RAW SUBSETS FOR PHASE 1 RECORD)")
print("="*80)

# PMV baseline on all rows where PMV & TSV exist
df_pmv = df[df['pmv'].notnull() & df['tsv_3class'].notnull()].copy()
df_pmv['pmv_3class'] = df_pmv['pmv'].apply(map_to_3class)
pmv_macro_f1 = f1_score(df_pmv['tsv_3class'], df_pmv['pmv_3class'], average='macro', labels=['Cool (-1)', 'Neutral (0)', 'Warm (+1)'])
pmv_acc = accuracy_score(df_pmv['tsv_3class'], df_pmv['pmv_3class'])
print(f"PMV Baseline (N={len(df_pmv):,}): Macro-F1 = {pmv_macro_f1:.4f}, Accuracy = {pmv_acc:.4f}")

# Adaptive baseline on NV rows where running mean & TSV exist
df['t_outdoor_ref'] = df['t_mot_isd'].fillna(df['t_out'])
df['t_indoor_ref'] = df['top'].fillna((df['ta'] + df['tr']) / 2.0).fillna(df['ta'])
df_adapt = df[df['t_outdoor_ref'].notnull() & df['t_indoor_ref'].notnull() & df['tsv_3class'].notnull()].copy()
df_adapt['t_comf'] = 17.8 + 0.31 * df_adapt['t_outdoor_ref']

def pred_adapt_90(r):
    tin, tc = r['t_indoor_ref'], r['t_comf']
    return 'Cool (-1)' if tin < tc - 2.5 else ('Warm (+1)' if tin > tc + 2.5 else 'Neutral (0)')

df_adapt['adapt_90'] = df_adapt.apply(pred_adapt_90, axis=1)

df_adapt_nv = df_adapt[df_adapt['cooling_type'] == 'naturally ventilated']
adapt_nv_f1 = f1_score(df_adapt_nv['tsv_3class'], df_adapt_nv['adapt_90'], average='macro', labels=['Cool (-1)', 'Neutral (0)', 'Warm (+1)'])
adapt_nv_acc = accuracy_score(df_adapt_nv['tsv_3class'], df_adapt_nv['adapt_90'])
print(f"Adaptive 90% NV (N={len(df_adapt_nv):,}): Macro-F1 = {adapt_nv_f1:.4f}, Accuracy = {adapt_nv_acc:.4f}")

df_adapt_all = df_adapt
adapt_all_f1 = f1_score(df_adapt_all['tsv_3class'], df_adapt_all['adapt_90'], average='macro', labels=['Cool (-1)', 'Neutral (0)', 'Warm (+1)'])
adapt_all_acc = accuracy_score(df_adapt_all['tsv_3class'], df_adapt_all['adapt_90'])
print(f"Adaptive 90% Full (N={len(df_adapt_all):,}): Macro-F1 = {adapt_all_f1:.4f}, Accuracy = {adapt_all_acc:.4f}")
