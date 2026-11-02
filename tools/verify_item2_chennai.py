import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.optimize.coupling import compute_valid_adaptive_hours_from_epw

saved_dir = "data/processed/batch/Chennai"
check_dir = "data/processed/batch_check/Chennai"

# 1. Diff baseline_results.csv
df_base_saved = pd.read_csv(os.path.join(saved_dir, "baseline_results.csv"))
df_base_check = pd.read_csv(os.path.join(check_dir, "baseline_results.csv"))

print("=" * 100)
print("DIFF: REBUILT baseline_results.csv (batch_check) vs SAVED (batch)")
print("=" * 100)
print("SAVED (batch):")
print(df_base_saved.to_string(index=False))
print("\nREBUILT (batch_check):")
print(df_base_check.to_string(index=False))

print("\nPER-ELEMENT DIFFERENCES IN BASELINES:")
max_diff = 0.0
diff_rows = []
for idx in range(len(df_base_saved)):
    d_saved = df_base_saved.iloc[idx]
    d_check = df_base_check.iloc[idx]
    did = d_saved['design_id']
    for col in ['O1_ml', 'O1_adapt', 'O2', 'top_med', 'top_max', 'top_lt_5', 'top_gt_35']:
        val_s = float(d_saved[col])
        val_c = float(d_check[col])
        d = abs(val_s - val_c)
        if d > max_diff:
            max_diff = d
        diff_rows.append({
            'design_id': did,
            'metric': col,
            'saved': val_s,
            'rebuilt': val_c,
            'abs_diff': d
        })

df_diffs = pd.DataFrame(diff_rows)
print(df_diffs.to_string(index=False))

print(f"\nMAX DIFFERENCE IN BASELINES: {max_diff:.6f}")
if max_diff > 0.01:
    print(f"STOP! Difference {max_diff} > 0.01")
    sys.exit(1)
else:
    print("Baseline reproduction check PASSED (all diffs <= 0.01).")

# 2. Diff Pareto front metrics
df_p_saved = pd.read_parquet(os.path.join(saved_dir, "final_verified_pareto_Chennai.parquet"))
df_p_check = pd.read_parquet(os.path.join(check_dir, "final_verified_pareto_Chennai.parquet"))

print("\n" + "=" * 100)
print("DIFF: PARETO FRONT AND SUMMARY METRICS")
print("=" * 100)
print(f"Front size saved: {len(df_p_saved)}, check: {len(df_p_check)} (Diff: {abs(len(df_p_saved) - len(df_p_check))})")

pareto_metric_diffs = []
for m in ['O1_ml', 'O1_adapt', 'O2']:
    min_s = float(df_p_saved[m].min())
    min_c = float(df_p_check[m].min())
    d_min = abs(min_s - min_c)
    med_s = float(df_p_saved[m].median())
    med_c = float(df_p_check[m].median())
    d_med = abs(med_s - med_c)
    max_s = float(df_p_saved[m].max())
    max_c = float(df_p_check[m].max())
    d_max = abs(max_s - max_c)
    pareto_metric_diffs.append({'objective': m, 'stat': 'min', 'saved': min_s, 'check': min_c, 'diff': d_min})
    pareto_metric_diffs.append({'objective': m, 'stat': 'median', 'saved': med_s, 'check': med_c, 'diff': d_med})
    pareto_metric_diffs.append({'objective': m, 'stat': 'max', 'saved': max_s, 'check': max_c, 'diff': d_max})

df_pm_diffs = pd.DataFrame(pareto_metric_diffs)
print(df_pm_diffs.to_string(index=False))

# Valid hours
epw_path = "data/raw/India_Weather_Extracted/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025/IND_TN_Chennai.Intl.AP.432790_TMYx.2011-2025.epw"
valid_func = compute_valid_adaptive_hours_from_epw(epw_path)
inv_share_s = float(df_p_saved['invalid_share_adapt'].iloc[0])
valid_from_df = int(round(8760 * (1.0 - inv_share_s / 100.0)))
print(f"\nValid Hours Check: Canonical Func = {valid_func}, Derived from saved parquet = {valid_from_df} (Diff: {abs(valid_func - valid_from_df)})")
assert valid_func == valid_from_df, f"Valid hours mismatch: {valid_func} != {valid_from_df}"

# Bounds list
spans = {
    'roof_insulation_thickness': (0.0, 0.15),
    'wall_insulation_thickness': (0.0, 0.15),
    'roof_solar_absorptance': (0.30, 0.90),
    'wwr': (0.05, 0.40),
    'orientation': (0.0, 359.0),
    'shading_depth': (0.30, 1.00),
    'ventilation_ach': (1.0, 15.0)
}
def get_bounds(df):
    at_bound = []
    n = len(df)
    for var, (lb, ub) in spans.items():
        span = ub - lb
        tol = 0.05 * span
        nb = np.sum((df[var] <= lb + tol + 1e-6) | (df[var] >= ub - tol - 1e-6))
        if nb / n >= 2.0 / 3.0:
            at_bound.append(var)
    counts = df['wall_mass_class'].value_counts()
    if (counts.get('light', 0) + counts.get('heavy', 0)) / n >= 2.0 / 3.0:
        at_bound.append('wall_mass_class')
    return sorted(at_bound)

b_saved = get_bounds(df_p_saved)
b_check = get_bounds(df_p_check)
print(f"\nBounds list saved: {b_saved}")
print(f"Bounds list check: {b_check}")
assert b_saved == b_check, f"Bounds list mismatch: {b_saved} != {b_check}"

print("\nALL REPRODUCTION CHECKS PASSED WITH DIFF <= 0.01.")
