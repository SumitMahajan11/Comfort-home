#!/usr/bin/env python3
"""
tools/report_item5_ranks_p2.py

Item 5: SPEARMAN RANK CORRELATION MATHEMATICAL PROVENANCE & DETAILED RANK VECTORS
- Prints complete rank vectors (r_base, r_scen), difference d_i, and squared difference d_i^2:
    * New Delhi O2 at +1.5 C (n=45)
    * New Delhi O2 at +3.0 C (n=45)
    * Jodhpur O2 at +1.5 C (n=26)
    * Jodhpur O2 at +3.0 C (n=26)
- Shows exact analytical Spearman rho formula: rho = 1 - 6*sum(d^2) / (n*(n^2 - 1))
- Compares analytical rho with scipy.stats.spearmanr (verifying exact convergence)
- Explains Bengaluru front size (N=1) and why it is marked "not testable" across Tables 1, 2, and 3
- Documents the computed 4-column Spearman rho verdict rule
Writes report to reports/item5_rank_tables.txt
"""

import os
import pandas as pd
from scipy.stats import rankdata, spearmanr

def main():
    csv_path = os.path.join("reports", "robustness_flagship_details.csv")
    out_txt_path = os.path.join("reports", "item5_rank_tables.txt")
    df = pd.read_csv(csv_path)

    lines = []
    lines.append("=" * 160)
    lines.append("ITEM 5: MATHEMATICAL AUDIT OF SPEARMAN RANK CORRELATIONS & DETAILED RANK VECTORS")
    lines.append("Analytical Verification of Rank Preservation Under +1.5 C and +3.0 C Warming Scenarios")
    lines.append("=" * 160)

    # 1. NEW DELHI O2 AT +1.5 C AND +3.0 C
    df_nd = df[(df['city'] == 'New_Delhi') & (df['is_pareto'] == True)].copy()
    n_nd = len(df_nd)
    r_nd_base = rankdata(df_nd['O2_base'])
    r_nd_p15 = rankdata(df_nd['O2_plus1p5'])
    r_nd_p30 = rankdata(df_nd['O2_plus3p0'])

    d_nd_p15 = r_nd_base - r_nd_p15
    d2_nd_p15 = d_nd_p15 ** 2
    sum_d2_nd_p15 = float(d2_nd_p15.sum())
    rho_nd_p15_ana = 1.0 - (6.0 * sum_d2_nd_p15) / (n_nd * (n_nd**2 - 1))
    rho_nd_p15_sci, _ = spearmanr(df_nd['O2_base'], df_nd['O2_plus1p5'])

    d_nd_p30 = r_nd_base - r_nd_p30
    d2_nd_p30 = d_nd_p30 ** 2
    sum_d2_nd_p30 = float(d2_nd_p30.sum())
    rho_nd_p30_ana = 1.0 - (6.0 * sum_d2_nd_p30) / (n_nd * (n_nd**2 - 1))
    rho_nd_p30_sci, _ = spearmanr(df_nd['O2_base'], df_nd['O2_plus3p0'])

    lines.append("\n" + "=" * 160)
    lines.append(f"SECTION 1: NEW DELHI O2 SPEARMAN RHO AUDIT (n = {n_nd} Verified Pareto Front Designs)")
    lines.append("=" * 160)
    lines.append(f"Analytical Formula: rho = 1 - [6 * sum(d_i^2)] / [n * (n^2 - 1)]")
    lines.append(f"Denominator: n * (n^2 - 1) = {n_nd} * ({n_nd}^2 - 1) = {n_nd} * {n_nd**2 - 1} = {n_nd * (n_nd**2 - 1)}")
    lines.append("-" * 160)
    lines.append(f"Summary Statistics for New Delhi O2:")
    lines.append(f"  * At +1.5 C Scenario: sum(d_i^2) = {sum_d2_nd_p15:.4f} | Analytical rho = {rho_nd_p15_ana:.6f} | Scipy rho = {rho_nd_p15_sci:.6f} (Exact Match: {abs(rho_nd_p15_ana - rho_nd_p15_sci) < 1e-5})")
    lines.append(f"  * At +3.0 C Scenario: sum(d_i^2) = {sum_d2_nd_p30:.4f} | Analytical rho = {rho_nd_p30_ana:.6f} | Scipy rho = {rho_nd_p30_sci:.6f} (Exact Match: {abs(rho_nd_p30_ana - rho_nd_p30_sci) < 1e-5})")
    lines.append("-" * 160)

    lines.append(f"\nDetailed Rank Vectors for New Delhi O2 across all {n_nd} Designs:")
    fmt_nd = "{:<4} | {:<24} | {:<9} | {:<9} | {:<9} | {:<9} | {:<7} | {:<7} | {:<9} | {:<9} | {:<7} | {:<7}"
    lines.append(fmt_nd.format(
        "Idx", "Design ID", "O2 Base", "Rank Base",
        "O2 +1.5C", "Rank +1.5", "d (p15)", "d^2(p15)",
        "O2 +3.0C", "Rank +3.0", "d (p30)", "d^2(p30)"
    ))
    lines.append("-" * 160)

    for i in range(n_nd):
        row_i = df_nd.iloc[i]
        did = row_i['design_id']
        o2_b = float(row_i['O2_base'])
        r_b = r_nd_base[i]
        o2_15 = float(row_i['O2_plus1p5'])
        r_15 = r_nd_p15[i]
        d_15 = d_nd_p15[i]
        d2_15 = d2_nd_p15[i]
        o2_30 = float(row_i['O2_plus3p0'])
        r_30 = r_nd_p30[i]
        d_30 = d_nd_p30[i]
        d2_30 = d2_nd_p30[i]
        lines.append(fmt_nd.format(
            i + 1, did, f"{o2_b:.2f}", f"{r_b:5.1f}",
            f"{o2_15:.2f}", f"{r_15:5.1f}", f"{d_15:+5.1f}", f"{d2_15:6.2f}",
            f"{o2_30:.2f}", f"{r_30:5.1f}", f"{d_30:+5.1f}", f"{d2_30:6.2f}"
        ))
    lines.append("-" * 160)
    lines.append(f"SUM OF SQUARED DIFFERENCES: sum(d^2) at +1.5 C = {sum_d2_nd_p15:.2f} | sum(d^2) at +3.0 C = {sum_d2_nd_p30:.2f}")

    # 2. JODHPUR O2 AT +1.5 C AND +3.0 C
    df_jd = df[(df['city'] == 'Jodhpur') & (df['is_pareto'] == True)].copy()
    n_jd = len(df_jd)
    r_jd_base = rankdata(df_jd['O2_base'])
    r_jd_p15 = rankdata(df_jd['O2_plus1p5'])
    r_jd_p30 = rankdata(df_jd['O2_plus3p0'])

    d_jd_p15 = r_jd_base - r_jd_p15
    d2_jd_p15 = d_jd_p15 ** 2
    sum_d2_jd_p15 = float(d2_jd_p15.sum())
    rho_jd_p15_ana = 1.0 - (6.0 * sum_d2_jd_p15) / (n_jd * (n_jd**2 - 1))
    rho_jd_p15_sci, _ = spearmanr(df_jd['O2_base'], df_jd['O2_plus1p5'])

    d_jd_p30 = r_jd_base - r_jd_p30
    d2_jd_p30 = d_jd_p30 ** 2
    sum_d2_jd_p30 = float(d2_jd_p30.sum())
    rho_jd_p30_ana = 1.0 - (6.0 * sum_d2_jd_p30) / (n_jd * (n_jd**2 - 1))
    rho_jd_p30_sci, _ = spearmanr(df_jd['O2_base'], df_jd['O2_plus3p0'])

    lines.append("\n" + "=" * 160)
    lines.append(f"SECTION 2: JODHPUR O2 SPEARMAN RHO AUDIT (n = {n_jd} Verified Pareto Front Designs)")
    lines.append("=" * 160)
    lines.append(f"Denominator: n * (n^2 - 1) = {n_jd} * ({n_jd}^2 - 1) = {n_jd} * {n_jd**2 - 1} = {n_jd * (n_jd**2 - 1)}")
    lines.append("-" * 160)
    lines.append(f"Summary Statistics for Jodhpur O2:")
    lines.append(f"  * At +1.5 C Scenario: sum(d_i^2) = {sum_d2_jd_p15:.4f} | Analytical rho = {rho_jd_p15_ana:.6f} | Scipy rho = {rho_jd_p15_sci:.6f} (Exact Match: {abs(rho_jd_p15_ana - rho_jd_p15_sci) < 1e-5})")
    lines.append(f"  * At +3.0 C Scenario: sum(d_i^2) = {sum_d2_jd_p30:.4f} | Analytical rho = {rho_jd_p30_ana:.6f} | Scipy rho = {rho_jd_p30_sci:.6f} (Exact Match: {abs(rho_jd_p30_ana - rho_jd_p30_sci) < 1e-5})")
    lines.append("-" * 160)

    lines.append(f"\nDetailed Rank Vectors for Jodhpur O2 across all {n_jd} Designs:")
    fmt_jd = "{:<4} | {:<22} | {:<9} | {:<9} | {:<9} | {:<9} | {:<7} | {:<7} | {:<9} | {:<9} | {:<7} | {:<7}"
    lines.append(fmt_jd.format(
        "Idx", "Design ID", "O2 Base", "Rank Base",
        "O2 +1.5C", "Rank +1.5", "d (p15)", "d^2(p15)",
        "O2 +3.0C", "Rank +3.0", "d (p30)", "d^2(p30)"
    ))
    lines.append("-" * 160)

    for i in range(n_jd):
        row_i = df_jd.iloc[i]
        did = row_i['design_id']
        o2_b = float(row_i['O2_base'])
        r_b = r_jd_base[i]
        o2_15 = float(row_i['O2_plus1p5'])
        r_15 = r_jd_p15[i]
        d_15 = d_jd_p15[i]
        d2_15 = d2_jd_p15[i]
        o2_30 = float(row_i['O2_plus3p0'])
        r_30 = r_jd_p30[i]
        d_30 = d_jd_p30[i]
        d2_30 = d2_jd_p30[i]
        lines.append(fmt_jd.format(
            i + 1, did, f"{o2_b:.2f}", f"{r_b:5.1f}",
            f"{o2_15:.2f}", f"{r_15:5.1f}", f"{d_15:+5.1f}", f"{d2_15:6.2f}",
            f"{o2_30:.2f}", f"{r_30:5.1f}", f"{d_30:+5.1f}", f"{d2_30:6.2f}"
        ))
    lines.append("-" * 160)
    lines.append(f"SUM OF SQUARED DIFFERENCES: sum(d^2) at +1.5 C = {sum_d2_jd_p15:.2f} | sum(d^2) at +3.0 C = {sum_d2_jd_p30:.2f}")

    # 3. BENGALURU VERDICT & FRONT SIZE ANALYSIS
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 3: BENGALURU PARETO FRONT AUDIT (FRONT SIZE N = 1)")
    lines.append("=" * 160)
    df_bg = df[(df['city'] == 'Bengaluru') & (df['is_pareto'] == True)]
    lines.append(f"Total designs on Bengaluru verified Pareto front: {len(df_bg)} (Design ID: {df_bg.iloc[0]['design_id']}).")
    lines.append("Mathematical Reasons for 'not testable' Designation:")
    lines.append("  1. Table 1 (Best Design Rank Preservation): With front size N=1, rank is trivially #1 out of 1 in all scenarios.")
    lines.append("     No rank comparison or rank displacement is possible. Designated 'not testable (front size < 5)'.")
    lines.append("  2. Table 2 (Spearman Rank Correlation): The Spearman rank correlation requires at least N >= 2 points to define a non-zero denominator")
    lines.append("     n*(n^2 - 1). For N=1, the denominator is 1*(1 - 1) = 0 (undefined division by zero). Statistically, Spearman rho requires N >= 5.")
    lines.append("     Designated 'not testable (front size < 5)'.")
    lines.append("  3. Table 3 (Regret Analysis): With only 1 design on the front, that single design is identically both the baseline-best")
    lines.append("     and the scenario-best design. Regret is trivially 0.00 by definition, but offers zero trade-off information.")
    lines.append("     Designated 'not testable (front size < 5)'.")

    # 4. FOUR-COLUMN SPEARMAN RHO VERDICT RULE
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 4: COMPUTED SPEARMAN RHO VERDICT RULE USING ALL FOUR RHO COLUMNS")
    lines.append("=" * 160)
    lines.append("Rule Definition:")
    lines.append("  For each city, extract all 4 Spearman rho values evaluated on the verified Pareto front:")
    lines.append("    * rho_1 = rho(O1_ml, +1.5 C)")
    lines.append("    * rho_2 = rho(O1_ml, +3.0 C)")
    lines.append("    * rho_3 = rho(O2, +1.5 C)")
    lines.append("    * rho_4 = rho(O2, +3.0 C)")
    lines.append("  Compute the minimum across all four columns: min_all_4 = min(rho_1, rho_2, rho_3, rho_4).")
    lines.append("  Classification Thresholds:")
    lines.append("    - If front size N < 5:                           'not testable (front size < 5)'")
    lines.append("    - Elif min_all_4 >= 0.95:                        'HIGH (min rho = {min_all_4:.4f} >= 0.95)'")
    lines.append("    - Elif min_all_4 >= 0.85:                        'STRONG (min rho = {min_all_4:.4f} >= 0.85)'")
    lines.append("    - Elif min_all_4 >= 0.70:                        'MODERATE (min rho = {min_all_4:.4f} >= 0.70)'")
    lines.append("    - Else:                                          'LOW (min rho = {min_all_4:.4f} < 0.70)'")
    lines.append("-" * 160)

    lines.append(f"{'City':<12} | {'Front N':<8} | {'rho(O1, +1.5)':<14} | {'rho(O1, +3.0)':<14} | {'rho(O2, +1.5)':<14} | {'rho(O2, +3.0)':<14} | {'Min All 4':<10} | {'Computed Verdict'}")
    lines.append("-" * 160)

    for city in ["Shimla", "Jodhpur", "New_Delhi", "Mumbai", "Bengaluru"]:
        sub = df[(df['city'] == city) & (df['is_pareto'] == True)]
        n_p = len(sub)
        if n_p >= 5:
            r1, _ = spearmanr(sub['O1_ml_base'], sub['O1_ml_plus1p5'])
            r2, _ = spearmanr(sub['O1_ml_base'], sub['O1_ml_plus3p0'])
            r3, _ = spearmanr(sub['O2_base'], sub['O2_plus1p5'])
            r4, _ = spearmanr(sub['O2_base'], sub['O2_plus3p0'])
            m4 = min(r1, r2, r3, r4)
            if m4 >= 0.95:
                v = f"HIGH (min rho = {m4:.4f} >= 0.95)"
            elif m4 >= 0.85:
                v = f"STRONG (min rho = {m4:.4f} >= 0.85)"
            elif m4 >= 0.70:
                v = f"MODERATE (min rho = {m4:.4f} >= 0.70)"
            else:
                v = f"LOW (min rho = {m4:.4f} < 0.70)"
            lines.append(f"{city:<12} | {n_p:<8} | {r1:<14.4f} | {r2:<14.4f} | {r3:<14.4f} | {r4:<14.4f} | {m4:<10.4f} | {v}")
        else:
            lines.append(f"{city:<12} | {n_p:<8} | {'not testable':<14} | {'not testable':<14} | {'not testable':<14} | {'not testable':<14} | {'N/A':<10} | not testable (front size < 5)")
    lines.append("=" * 160)

    output_text = "\n".join(lines)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"Successfully generated {out_txt_path} ({len(output_text)} characters).")

if __name__ == "__main__":
    main()
