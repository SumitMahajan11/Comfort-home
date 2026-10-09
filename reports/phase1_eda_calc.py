import os
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score, confusion_matrix, classification_report

# Ensure reproducibility and full print display
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 500)
pd.set_option('display.width', 1000)

print("================================================================================")
print("PHASE 1 EDA: THERMAL COMFORT DATASET COMPUTATIONS")
print("================================================================================")

# 1. Load Data from data/raw only
meas_path = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_measurements_v2.1.0.csv.gz'
meta_path = 'data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv'

df_meas = pd.read_csv(meas_path, low_memory=False)
df_meta = pd.read_csv(meta_path, low_memory=False)
df = df_meas.merge(df_meta, on='building_id', how='left')

print(f"Dataset Loaded Successfully: {df.shape[0]} rows, {df.shape[1]} columns")

# ================================================================================
# SECTION 1: 3-CLASS TARGET DISTRIBUTION (OVERALL AND PER KÖPPEN CLASS)
# ================================================================================
print("\n" + "="*80)
print("SECTION 1: 3-CLASS TARGET DISTRIBUTION")
print("="*80)

# Define 3-class target mapping:
# Cool: TSV < -0.5 (-1)
# Neutral: -0.5 <= TSV <= 0.5 (0)
# Warm: TSV > 0.5 (+1)
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

print("\n--- RAW THERMAL SENSATION VALUE COUNTS ---")
raw_tsv_counts = df['thermal_sensation'].value_counts(dropna=False).sort_index()
print(raw_tsv_counts.to_string())

print("\n--- OVERALL 3-CLASS TARGET DISTRIBUTION ---")
tsv_overall = df['tsv_3class'].value_counts(dropna=False)
total_valid_tsv = df['tsv_3class'].dropna().count()
df_tsv_overall = pd.DataFrame({
    'Class': tsv_overall.index.astype(str),
    'Count': tsv_overall.values,
    'Percentage (of total rows)': (tsv_overall.values / len(df) * 100).round(2),
    'Percentage (of valid TSV)': [(v / total_valid_tsv * 100).round(2) if k != 'nan' and pd.notnull(k) else np.nan for k, v in zip(tsv_overall.index, tsv_overall.values)]
})
print(df_tsv_overall.to_string(index=False))

print("\n--- 3-CLASS DISTRIBUTION PER KÖPPEN CLIMATE CLASS ---")
koppen_3class = pd.crosstab(df['climate'], df['tsv_3class'], margins=True, dropna=False)
koppen_3class_pct = pd.crosstab(df['climate'], df['tsv_3class'], normalize='index', margins=True) * 100
print("\nCounts:")
print(koppen_3class.to_string())
print("\nRow Percentages (%):")
print(koppen_3class_pct.round(2).to_string())

# India 3-class distribution
df_india = df[df['country'].str.lower() == 'india']
print("\n--- INDIA 3-CLASS TARGET DISTRIBUTION ---")
in_tsv = df_india['tsv_3class'].value_counts(dropna=False)
print(in_tsv.to_string())

# ================================================================================
# SECTION 2: MIN / MAX / OUTLIERS & PHYSICALLY IMPOSSIBLE VALUES
# ================================================================================
print("\n" + "="*80)
print("SECTION 2: PHYSICAL VARIABLES SUMMARY & ANOMALY AUDIT")
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
    outliers_count = ((s < lower_bound) | (s > upper_bound)).sum()
    
    stat_records.append({
        'Variable': var,
        'Count': len(s),
        'Nulls': df[var].isnull().sum(),
        'Min': round(s.min(), 3),
        'P01': round(s.quantile(0.01), 3),
        'P05': round(s.quantile(0.05), 3),
        'Q1 (25%)': round(q1, 3),
        'Median': round(s.median(), 3),
        'Mean': round(s.mean(), 3),
        'Q3 (75%)': round(q3, 3),
        'P95': round(s.quantile(0.95), 3),
        'P99': round(s.quantile(0.99), 3),
        'Max': round(s.max(), 3),
        'Std': round(s.std(), 3),
        'IQR': round(iqr, 3),
        'IQR Lower': round(lower_bound, 3),
        'IQR Upper': round(upper_bound, 3),
        'IQR Outliers': outliers_count,
        'IQR Outliers %': round(outliers_count / len(s) * 100, 2)
    })

df_stats = pd.DataFrame(stat_records)
print(df_stats.to_string(index=False))

print("\n--- PHYSICAL BOUNDARY & IMPOSSIBILITY AUDIT ---")
# Domain physical plausibility criteria for indoor environmental & personal variables:
# 1. ta (Air Temp): Indoor range 5°C to 45°C. Impossible: <= 0°C or > 50°C.
# 2. tr (Radiant Temp): Indoor range 5°C to 50°C. Impossible: <= 0°C or > 60°C or |tr - ta| > 20°C.
# 3. rh (Relative Humidity): Standard physical range [0%, 100%]. Impossible: < 0% or > 100%. Indoor extreme warning: < 5% or > 95%.
# 4. vel (Air Velocity): Standard indoor anemometry range [0, 10] m/s. Impossible: < 0 m/s or > 10 m/s. Extreme warning: > 5 m/s.
# 5. clo (Clothing): Standard clothing range [0, 4] clo. Impossible: <= 0 clo (completely nude in office?) or > 3.5 clo (heavy polar arctic gear indoors).
# 6. met (Metabolic Rate): Standard human metabolic range [0.7, 4.0] met. Impossible: <= 0 met (biologically impossible for living subject) or > 6.0 met.

anomalies = []

# ta checks
ta_imp = df[(df['ta'] <= 0) | (df['ta'] >= 50)]
print(f"ta physically impossible (<=0°C or >=50°C): {len(ta_imp)} rows")
if len(ta_imp) > 0:
    print(ta_imp[['building_id', 'country', 'ta', 'tr', 'rh', 'vel', 'thermal_sensation']].head(10))

# tr checks
tr_imp = df[(df['tr'] <= 0) | (df['tr'] >= 60)]
print(f"tr physically impossible (<=0°C or >=60°C): {len(tr_imp)} rows")
if len(tr_imp) > 0:
    print(tr_imp[['building_id', 'country', 'ta', 'tr', 'rh', 'vel', 'thermal_sensation']].head(10))

# |tr - ta| > 20°C
tr_ta_diff = df[df['tr'].notnull() & df['ta'].notnull() & ((df['tr'] - df['ta']).abs() > 20)]
print(f"|tr - ta| > 20°C (extreme sensor drift / radiant anomaly): {len(tr_ta_diff)} rows")
if len(tr_ta_diff) > 0:
    print(tr_ta_diff[['building_id', 'country', 'ta', 'tr', 'rh', 'vel']].head(10))

# rh checks
rh_imp = df[(df['rh'] < 0) | (df['rh'] > 100)]
print(f"rh physically impossible (<0% or >100%): {len(rh_imp)} rows")
rh_extreme = df[(df['rh'] < 5) | (df['rh'] > 98)]
print(f"rh extreme indoor values (<5% or >98%): {len(rh_extreme)} rows")
if len(rh_extreme) > 0:
    print(rh_extreme[['building_id', 'country', 'city', 'ta', 'rh']].head(10))

# vel checks
vel_imp = df[(df['vel'] < 0) | (df['vel'] > 10)]
print(f"vel physically impossible (<0 m/s or >10 m/s): {len(vel_imp)} rows")
vel_extreme = df[df['vel'] > 3.0]
print(f"vel extreme indoor values (>3.0 m/s): {len(vel_extreme)} rows")
if len(vel_extreme) > 0:
    print(vel_extreme[['building_id', 'country', 'cooling_type', 'vel', 'ta']].head(10))

# clo checks
clo_imp = df[(df['clo'] <= 0) | (df['clo'] > 3.5)]
print(f"clo physically impossible / extreme (<=0 or >3.5): {len(clo_imp)} rows")
if len(clo_imp) > 0:
    print(clo_imp[['building_id', 'country', 'clo', 'season', 'ta']].head(10))

# met checks
met_imp = df[(df['met'] <= 0) | (df['met'] > 6.0)]
print(f"met physically impossible / extreme (<=0 or >6.0): {len(met_imp)} rows")
if len(met_imp) > 0:
    print(met_imp[['building_id', 'country', 'met', 'activity_10', 'building_type']].head(10))

# ================================================================================
# SECTION 3: DISTINCT BUILDINGS AND ROWS PER KÖPPEN CLASS & <3 BUILDINGS FLAGGING
# ================================================================================
print("\n" + "="*80)
print("SECTION 3: DISTINCT BUILDINGS & ROWS PER KÖPPEN CLASS")
print("="*80)

climate_bldg_stats = df.groupby('climate').agg(
    distinct_buildings=('building_id', 'nunique'),
    total_rows=('record_id', 'count'),
    min_rows_per_bldg=('building_id', lambda x: x.value_counts().min()),
    median_rows_per_bldg=('building_id', lambda x: x.value_counts().median()),
    max_rows_per_bldg=('building_id', lambda x: x.value_counts().max())
).reset_index()

climate_bldg_stats['pct_of_total_rows'] = (climate_bldg_stats['total_rows'] / len(df) * 100).round(2)
climate_bldg_stats['few_buildings_flag (<3)'] = climate_bldg_stats['distinct_buildings'] < 3

# Sort by distinct_buildings descending, then total_rows descending
climate_bldg_stats = climate_bldg_stats.sort_values(by=['distinct_buildings', 'total_rows'], ascending=[False, False])
print(climate_bldg_stats.to_string(index=False))

flagged_climates = climate_bldg_stats[climate_bldg_stats['few_buildings_flag (<3)']]
print(f"\nTotal Climate Classes with < 3 Buildings: {len(flagged_climates)} out of {len(climate_bldg_stats)}")
print(flagged_climates[['climate', 'distinct_buildings', 'total_rows', 'pct_of_total_rows']].to_string(index=False))

# Also inspect distinct countries per climate class
climate_country_stats = df.groupby('climate')['country'].nunique().reset_index().rename(columns={'country': 'distinct_countries'})
print("\nDistinct Countries per Climate Class:")
print(climate_country_stats.to_string(index=False))

# ================================================================================
# SECTION 4: COMPLETE-CASE ROWS FOR CANDIDATE CORE FEATURE SETS
# ================================================================================
print("\n" + "="*80)
print("SECTION 4: COMPLETE-CASE ANALYSIS FOR CANDIDATE FEATURE SETS")
print("="*80)

feature_sets = {
    'Set A: 6 Standard Physics + TSV': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set B: 5 Features (no tr) + TSV': ['ta', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set C: Top + 4 Features + TSV': ['top', 'rh', 'vel', 'clo', 'met', 'thermal_sensation'],
    'Set D: 6 Physics + Outdoor Temp + TSV': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_out', 'thermal_sensation'],
    'Set E: 6 Physics + Running Mean ISD + TSV': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 't_mot_isd', 'thermal_sensation'],
    'Set F: 6 Physics + TSV + PMV (Baseline subset)': ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 'thermal_sensation', 'pmv']
}

cc_results = []
total_all = len(df)

for name, cols in feature_sets.items():
    cc_mask = df[cols].notnull().all(axis=1)
    n_cc = int(cc_mask.sum())
    pct = n_cc / total_all * 100.0
    
    # Check India subset count
    n_cc_india = int((cc_mask & (df['country'].str.lower() == 'india')).sum())
    pct_india = n_cc_india / len(df_india) * 100.0
    
    # Check NV subset count
    df_nv = df[df['cooling_type'] == 'naturally ventilated']
    n_cc_nv = int((cc_mask & (df['cooling_type'] == 'naturally ventilated')).sum())
    pct_nv = n_cc_nv / len(df_nv) * 100.0
    
    cc_results.append({
        'Feature Set Name': name,
        'Features Count': len(cols),
        'Global Complete Rows': n_cc,
        'Global Retained %': f"{pct:.2f}%",
        'India Complete Rows': n_cc_india,
        'India Retained %': f"{pct_india:.2f}%",
        'NV Complete Rows': n_cc_nv,
        'NV Retained %': f"{pct_nv:.2f}%"
    })

df_cc = pd.DataFrame(cc_results)
print(df_cc.to_string(index=False))

# Breakdown of missingness combinations in Set A
print("\n--- DETAILED MISSINGNESS PATTERNS FOR SET A (6 PHYSICS + TSV) ---")
set_a_cols = ['ta', 'tr', 'rh', 'vel', 'clo', 'met', 'thermal_sensation']
patterns = df[set_a_cols].isnull().value_counts().reset_index()
patterns.columns = list(set_a_cols) + ['Count']
patterns['Percentage'] = (patterns['Count'] / total_all * 100).round(2)
print(patterns.head(10).to_string(index=False))

# ================================================================================
# SECTION 5: PMV AND ADAPTIVE BASELINE MACRO-F1 EVALUATION
# ================================================================================
print("\n" + "="*80)
print("SECTION 5: PMV & ADAPTIVE BASELINE BENCHMARKING")
print("="*80)

# --- 5.1 PMV Baseline ---
# Filter valid cases where both PMV and thermal_sensation exist
df_pmv = df[df['pmv'].notnull() & df['tsv_3class'].notnull()].copy()
print(f"Total Rows with both PMV and TSV available: {len(df_pmv)} rows")

df_pmv['pmv_3class'] = df_pmv['pmv'].apply(map_to_3class)

# True labels and predicted labels
y_true_pmv = df_pmv['tsv_3class']
y_pred_pmv = df_pmv['pmv_3class']

classes = ['Cool (-1)', 'Neutral (0)', 'Warm (+1)']

def compute_metrics(y_true, y_pred, name="Model"):
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average='macro', labels=classes, zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average='weighted', labels=classes, zero_division=0)
    macro_prec = precision_score(y_true, y_pred, average='macro', labels=classes, zero_division=0)
    macro_rec = recall_score(y_true, y_pred, average='macro', labels=classes, zero_division=0)
    
    # Per class F1
    per_class_f1 = f1_score(y_true, y_pred, average=None, labels=classes, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    cm_df = pd.DataFrame(cm, index=[f"True {c}" for c in classes], columns=[f"Pred {c}" for c in classes])
    
    print(f"\n--- {name} Performance ---")
    print(f"Sample Size (N): {len(y_true)}")
    print(f"Accuracy:        {acc:.4f} ({acc*100:.2f}%)")
    print(f"Macro-F1:        {macro_f1:.4f}")
    print(f"Weighted-F1:     {weighted_f1:.4f}")
    print(f"Macro-Precision: {macro_prec:.4f}")
    print(f"Macro-Recall:    {macro_rec:.4f}")
    print(f"Per-Class F1:    Cool (-1): {per_class_f1[0]:.4f} | Neutral (0): {per_class_f1[1]:.4f} | Warm (+1): {per_class_f1[2]:.4f}")
    print("\nConfusion Matrix:")
    print(cm_df.to_string())
    
    return {
        'Model': name,
        'N': len(y_true),
        'Accuracy': round(acc, 4),
        'Macro_F1': round(macro_f1, 4),
        'Weighted_F1': round(weighted_f1, 4),
        'Macro_Precision': round(macro_prec, 4),
        'Macro_Recall': round(macro_rec, 4),
        'F1_Cool': round(per_class_f1[0], 4),
        'F1_Neutral': round(per_class_f1[1], 4),
        'F1_Warm': round(per_class_f1[2], 4)
    }

pmv_metrics_all = compute_metrics(y_true_pmv, y_pred_pmv, name="PMV Baseline (Full Available Data)")

# PMV on AC buildings only
df_pmv_ac = df_pmv[df_pmv['cooling_type'] == 'air conditioned']
pmv_metrics_ac = compute_metrics(df_pmv_ac['tsv_3class'], df_pmv_ac['pmv_3class'], name="PMV Baseline (Air-Conditioned Buildings Only)")

# PMV on Naturally Ventilated buildings only
df_pmv_nv = df_pmv[df_pmv['cooling_type'] == 'naturally ventilated']
pmv_metrics_nv = compute_metrics(df_pmv_nv['tsv_3class'], df_pmv_nv['pmv_3class'], name="PMV Baseline (Naturally Ventilated Buildings Only)")

# PMV on India subset
df_pmv_in = df_pmv[df_pmv['country'].str.lower() == 'india']
pmv_metrics_in = compute_metrics(df_pmv_in['tsv_3class'], df_pmv_in['pmv_3class'], name="PMV Baseline (India Subset)")

# --- 5.2 Adaptive Comfort Baseline ---
# Standard ASHRAE 55 Adaptive Model:
# Neutral Temperature: T_comf = 17.8 + 0.31 * T_mot
# Acceptability Bands:
# 80% acceptability: T_comf +/- 3.5 degC
# 90% acceptability: T_comf +/- 2.5 degC
# Operative temperature Top is compared with T_comf (or Ta if Top is missing).

# First, construct outdoor running mean temperature: use t_mot_isd if available, else t_out
df['t_outdoor_ref'] = df['t_mot_isd'].fillna(df['t_out'])
# Indoor operative temperature: use top if available, else (ta + tr)/2 if tr available, else ta
df['t_indoor_ref'] = df['top'].fillna((df['ta'] + df['tr']) / 2.0).fillna(df['ta'])

# Filter valid rows for adaptive evaluation: requires t_outdoor_ref, t_indoor_ref, and tsv_3class
# Also ASHRAE 55 valid outdoor temp range is 10°C <= T_mot <= 33.5°C
df_adapt = df[df['t_outdoor_ref'].notnull() & df['t_indoor_ref'].notnull() & df['tsv_3class'].notnull()].copy()
df_adapt['t_comf'] = 17.8 + 0.31 * df_adapt['t_outdoor_ref']

# 80% band (+/- 3.5°C)
def predict_adaptive_80(row):
    t_in = row['t_indoor_ref']
    t_c = row['t_comf']
    if t_in < (t_c - 3.5):
        return 'Cool (-1)'
    elif t_in <= (t_c + 3.5):
        return 'Neutral (0)'
    else:
        return 'Warm (+1)'

# 90% band (+/- 2.5°C)
def predict_adaptive_90(row):
    t_in = row['t_indoor_ref']
    t_c = row['t_comf']
    if t_in < (t_c - 2.5):
        return 'Cool (-1)'
    elif t_in <= (t_c + 2.5):
        return 'Neutral (0)'
    else:
        return 'Warm (+1)'

df_adapt['adapt_80_3class'] = df_adapt.apply(predict_adaptive_80, axis=1)
df_adapt['adapt_90_3class'] = df_adapt.apply(predict_adaptive_90, axis=1)

# Evaluate on Naturally Ventilated buildings (primary theoretical validity domain for Adaptive Model)
df_adapt_nv = df_adapt[df_adapt['cooling_type'] == 'naturally ventilated']
adapt_nv_80 = compute_metrics(df_adapt_nv['tsv_3class'], df_adapt_nv['adapt_80_3class'], name="Adaptive 80% Band (Naturally Ventilated Subset)")
adapt_nv_90 = compute_metrics(df_adapt_nv['tsv_3class'], df_adapt_nv['adapt_90_3class'], name="Adaptive 90% Band (Naturally Ventilated Subset)")

# Evaluate on Full Available Data
adapt_all_80 = compute_metrics(df_adapt['tsv_3class'], df_adapt['adapt_80_3class'], name="Adaptive 80% Band (Full Available Data)")
adapt_all_90 = compute_metrics(df_adapt['tsv_3class'], df_adapt['adapt_90_3class'], name="Adaptive 90% Band (Full Available Data)")

# Evaluate on India Naturally Ventilated subset
df_adapt_in_nv = df_adapt[(df_adapt['country'].str.lower() == 'india') & (df_adapt['cooling_type'] == 'naturally ventilated')]
adapt_in_nv_80 = compute_metrics(df_adapt_in_nv['tsv_3class'], df_adapt_in_nv['adapt_80_3class'], name="Adaptive 80% Band (India Naturally Ventilated Subset)")

# Consolidate baseline comparison table
baseline_summary = pd.DataFrame([
    pmv_metrics_all,
    pmv_metrics_ac,
    pmv_metrics_nv,
    pmv_metrics_in,
    adapt_all_80,
    adapt_all_90,
    adapt_nv_80,
    adapt_nv_90,
    adapt_in_nv_80
])

print("\n" + "="*80)
print("BENCHMARK SUMMARY TABLE ACROSS ALL BASELINES")
print("="*80)
print(baseline_summary.to_string(index=False))
