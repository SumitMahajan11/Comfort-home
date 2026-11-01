import pandas as pd
import numpy as np

# 1. Negative energy predictions in pareto sets
cities = ['Jodhpur', 'Mumbai', 'New_Delhi', 'Bengaluru', 'Shimla']
print("================================================================================")
print("1. NEGATIVE ENERGY PREDICTIONS ON PARETO SETS")
print("================================================================================")
total_neg = 0
for c in cities:
    df = pd.read_parquet(f'data/processed/pareto_{c}.parquet')
    neg_o2 = (df['pred_O2'] < 0).sum()
    min_o2 = df['pred_O2'].min()
    total_neg += neg_o2
    print(f"City {c:10s}: {neg_o2:2d} / {len(df)} negative pred_O2 predictions (min pred_O2 = {min_o2:.4f} kWh/m2)")
print(f"Total negative predictions across all 500 Pareto designs: {total_neg}")

# 2. Pareto verification relative and absolute errors
ver = pd.read_csv('data/processed/pareto_verification_results.csv')
print("\n================================================================================")
print("2. PARETO VERIFICATION ERROR SUMMARY (10% RELATIVE ERROR THRESHOLD)")
print("================================================================================")
for c in cities:
    v_c = ver[ver['city'] == c]
    print(f"\nCity: {c}")
    for obj in ['O1_ml', 'O1_adapt', 'O2']:
        mae = v_c[f'abs_err_{obj}'].mean()
        mre = v_c[f'rel_err_{obj}_pct'].mean()
        max_re = v_c[f'rel_err_{obj}_pct'].max()
        pct_within_10 = (v_c[f'rel_err_{obj}_pct'] <= 10.0).mean() * 100
        n_within_10 = (v_c[f'rel_err_{obj}_pct'] <= 10.0).sum()
        print(f"  {obj:10s}: Mean Abs Err = {mae:6.3f}, Mean Rel Err = {mre:6.2f}%, Max Rel Err = {max_re:6.2f}%, Within <=10% Rel Err = {n_within_10}/10 ({pct_within_10:.1f}%)")

# 3. Judge disagreement in Jodhpur and New Delhi
obj_df = pd.read_parquet('data/processed/objectives.parquet')
print("\n================================================================================")
print("3. JUDGE DISAGREEMENT ANALYSIS (JODHPUR & NEW DELHI)")
print("================================================================================")
for c in ['Jodhpur', 'New_Delhi', 'Mumbai', 'Bengaluru', 'Shimla']:
    c_df = obj_df[obj_df['city'] == c]
    print(f"\nCity: {c}")
    print(f"  O1_ml: mean={c_df['O1_ml'].mean():.2f}%, min={c_df['O1_ml'].min():.2f}%, max={c_df['O1_ml'].max():.2f}%")
    print(f"  O1_adapt: mean={c_df['O1_adapt'].mean():.2f}%, min={c_df['O1_adapt'].min():.2f}%, max={c_df['O1_adapt'].max():.2f}%")
    print(f"  warm_ml: mean={c_df['warm_ml'].mean():.2f}% vs hot_adapt: mean={c_df['hot_adapt'].mean():.2f}%")
    print(f"  cool_ml: mean={c_df['cool_ml'].mean():.2f}% vs cold_adapt: mean={c_df['cold_adapt'].mean():.2f}%")
    print(f"  Spearman corr (O1_ml vs O1_adapt): {c_df['O1_ml'].corr(c_df['O1_adapt'], method='spearman'):.4f}")
    print(f"  Pearson corr (warm_ml vs hot_adapt): {c_df['warm_ml'].corr(c_df['hot_adapt']):.4f}")
    print(f"  Pearson corr (cool_ml vs cold_adapt): {c_df['cool_ml'].corr(c_df['cold_adapt']):.4f}")

# 4. Applicability Table and Confidence Tiers (D-017)
app_df = pd.read_csv('data/processed/applicability.csv')
print("\n================================================================================")
print("4. APPLICABILITY & CONFIDENCE TIERS (D-017)")
print("================================================================================")
print(app_df.to_string(index=False))

print("\n--- Confidence Summary Table ---")
for c in cities:
    row = app_df[app_df['city'] == c].iloc[0]
    all_in = row['all_features_in_envelope_pct']
    adapt_val = row['adaptive_90_valid_pct']
    spearman_r = obj_df[obj_df['city'] == c]['O1_ml'].corr(obj_df[obj_df['city'] == c]['O1_adapt'], method='spearman')
    tier = "Medium" if (spearman_r >= 0.8 and adapt_val >= 80.0) else "Low"
    print(f"{c:12s} | DB II Envelope: {all_in:5.2f}% | Adapt Valid: {adapt_val:5.2f}% | Spearman r_s: {spearman_r:6.3f} | Tier: {tier}")
