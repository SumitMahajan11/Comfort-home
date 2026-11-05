"""
Closure Pass 3 - Item 5: Verdict Formatting
Removes rho verdict labels ('LOW', 'HIGH', 'STRONG', etc.) and prints Spearman rho and regret only.
"""
from pathlib import Path
import sys
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

REPO_ROOT = Path(__file__).resolve().parent.parent

def compute_spearman(df_front, col_base, col_scen):
    valid = df_front[[col_base, col_scen]].dropna()
    if len(valid) < 5:
        return np.nan
    res = spearmanr(valid[col_base], valid[col_scen])
    return res.statistic

def main():
    lines = []
    lines.append("=" * 120)
    lines.append("PASS 3 - ITEM 5: SPEARMAN RHO & REGRET AUDIT (VERDICT LABELS REMOVED)")
    lines.append("=" * 120)
    lines.append("")

    csv_path = REPO_ROOT / "reports" / "robustness_flagship_details.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}")

    df = pd.read_csv(csv_path)

    # Filter out baselines R1, R2, R3 for Pareto front calculations
    df_front = df[~df['design_id'].str.startswith('R')].copy()

    cities = ["Shimla", "Jodhpur", "New_Delhi", "Mumbai", "Bengaluru"]

    lines.append("TABLE 2 (CLEAN): SPEARMAN RANK CORRELATIONS (RHO) ON PARETO FRONT (NO VERDICT LABELS)")
    lines.append("-" * 120)
    lines.append(f"{'City':<12} | {'Front Size':<10} | {'rho(O1_ml, +1.5C)':<18} | {'rho(O1_ml, +3.0C)':<18} | {'rho(O2, +1.5C)':<15} | {'rho(O2, +3.0C)':<15}")
    lines.append("-" * 120)

    rho_dict = {}

    for c in cities:
        sub = df_front[df_front['city'] == c]
        n = len(sub)
        if n < 5:
            rho_o1_15 = "not testable"
            rho_o1_30 = "not testable"
            rho_o2_15 = "not testable"
            rho_o2_30 = "not testable"
        else:
            r1 = compute_spearman(sub, 'O1_ml_base', 'O1_ml_plus1p5')
            r2 = compute_spearman(sub, 'O1_ml_base', 'O1_ml_plus3p0')
            r3 = compute_spearman(sub, 'O2_base', 'O2_plus1p5')
            r4 = compute_spearman(sub, 'O2_base', 'O2_plus3p0')
            rho_dict[c] = (r1, r2, r3, r4)
            rho_o1_15 = f"{r1:.4f}"
            rho_o1_30 = f"{r2:.4f}"
            rho_o2_15 = f"{r3:.4f}"
            rho_o2_30 = f"{r4:.4f}"
        lines.append(f"{c:<12} | {n:<10} | {rho_o1_15:<18} | {rho_o1_30:<18} | {rho_o2_15:<15} | {rho_o2_30:<15}")

    lines.append("-" * 120)
    lines.append("")

    lines.append("TABLE 3 (CLEAN): REGRET ANALYSIS ON VERIFIED PARETO FRONT (RHO / VERDICT LABELS EXCLUDED)")
    lines.append("-" * 140)
    lines.append(f"{'City':<10} | {'Scenario':<10} | {'BaseBest O1 ID':<20} | {'Achieved O1':<11} | {'ScenBest O1 ID':<20} | {'Min O1':<7} | {'Regret O1':<10} | {'BaseBest O2 ID':<20} | {'Achieved O2':<11} | {'ScenBest O2 ID':<20} | {'Min O2':<7} | {'Regret O2 (kWh)':<15}")
    lines.append("-" * 140)

    for c in cities:
        sub = df_front[df_front['city'] == c].copy()
        if len(sub) == 0:
            continue
        if len(sub) < 5:
            for scen in ["Baseline", "+1.5 C", "+3.0 C"]:
                lines.append(f"{c:<10} | {scen:<10} | {'not testable':<20} | {'--':<11} | {'not testable':<20} | {'--':<7} | {'not testable':<10} | {'not testable':<20} | {'--':<11} | {'not testable':<20} | {'--':<7} | {'not testable':<15}")
            lines.append("-" * 140)
            continue

        # Baseline winners (first occurrence via idxmin)
        base_o1_idx = sub['O1_ml_base'].idxmin()
        base_o2_idx = sub['O2_base'].idxmin()

        b_o1_row = sub.loc[base_o1_idx]
        b_o2_row = sub.loc[base_o2_idx]

        b_o1_id = b_o1_row['design_id']
        b_o2_id = b_o2_row['design_id']

        scenarios = [
            ("Baseline", 'O1_ml_base', 'O2_base'),
            ("+1.5 C", 'O1_ml_plus1p5', 'O2_plus1p5'),
            ("+3.0 C", 'O1_ml_plus3p0', 'O2_plus3p0')
        ]

        for s_label, o1_col, o2_col in scenarios:
            ach_o1 = b_o1_row[o1_col]
            ach_o2 = b_o2_row[o2_col]

            scen_best_o1_idx = sub[o1_col].idxmin()
            scen_best_o2_idx = sub[o2_col].idxmin()

            min_o1 = sub.loc[scen_best_o1_idx, o1_col]
            min_o2 = sub.loc[scen_best_o2_idx, o2_col]

            s_best_o1_id = sub.loc[scen_best_o1_idx, 'design_id']
            s_best_o2_id = sub.loc[scen_best_o2_idx, 'design_id']

            regret_o1 = ach_o1 - min_o1
            regret_o2 = ach_o2 - min_o2

            lines.append(f"{c:<10} | {s_label:<10} | {b_o1_id:<20} | {ach_o1:<11.2f} | {s_best_o1_id:<20} | {min_o1:<7.2f} | {regret_o1:<+10.2f} | {b_o2_id:<20} | {ach_o2:<11.2f} | {s_best_o2_id:<20} | {min_o2:<7.2f} | {regret_o2:<+15.2f}")
        lines.append("-" * 140)

    out_file = REPO_ROOT / "reports" / "pass3_verdict.txt"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_file}")

if __name__ == "__main__":
    main()
