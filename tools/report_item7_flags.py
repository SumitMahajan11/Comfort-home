#!/usr/bin/env python3
"""
tools/report_item7_flags.py

Item 7: Flag Definitions & Flagged Cities Summary
- flag_error_high: last round O2 mean error % > 5.0%
- flag_error_rising: last abs error > 1.5 * round-1 abs error AND increase > 2.0 kWh/m2
Prints:
- Full 30-city table with round-1 abs error, last round abs error, delta, flag_error_rising, flag_error_high
- Plain list of flagged cities under each criterion
"""

import os
import sys
import pandas as pd
import numpy as np

def main():
    csv_path = "reports/results_30_cities.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}")

    df = pd.read_csv(csv_path)

    rows = []
    high_flagged = []
    rising_flagged = []

    for _, r in df.iterrows():
        city = r['city']
        group = r['group']

        # Parse error abs list
        raw_abs = [float(x.strip()) for x in r['O2_mean_err_abs_per_round'].split(';')]
        raw_pct = [float(x.strip().replace('%', '')) for x in r['O2_mean_error_pct_per_round'].split(';')]

        r1_abs = raw_abs[0]
        last_abs = raw_abs[-1]
        delta_abs = last_abs - r1_abs
        ratio = last_abs / r1_abs if r1_abs > 0 else np.nan

        last_pct = raw_pct[-1]

        f_high = bool(r['flag_error_high'])
        f_rising = bool(r['flag_error_rising'])

        if f_high:
            high_flagged.append(city)
        if f_rising:
            rising_flagged.append(city)

        rows.append({
            'City': city,
            'Group': group,
            'R1 Abs Err': r1_abs,
            'Last Abs Err': last_abs,
            'Ratio (Last/R1)': round(ratio, 2),
            'Delta (kWh/m2)': round(delta_abs, 2),
            'Last Err Pct': f"{last_pct:.2f}%",
            'Flag Rising': "FLAGGED" if f_rising else "OK",
            'Flag High': "FLAGGED" if f_high else "OK"
        })

    df_out = pd.DataFrame(rows)
    print("=" * 115)
    print("ITEM 7: AUDIT FLAGS SUMMARY (flag_error_high AND REVISED flag_error_rising)")
    print("Definitions:")
    print("  1. flag_error_high:   Last round O2 mean error % > 5.0% of median O2")
    print("  2. flag_error_rising: (Last round abs error > 1.5 * Round 1 abs error) AND (Last - R1 > 2.0 kWh/m2)")
    print("=" * 115)
    print(df_out.to_string(index=False))
    print("-" * 115)

    print(f"\n1. CITIES FLAGGED FOR HIGH ERROR (> 5.0%) [Total = {len(high_flagged)}]:")
    for c in high_flagged:
        row_c = df[df['city'] == c].iloc[0]
        raw_pct = [float(x.strip().replace('%', '')) for x in row_c['O2_mean_error_pct_per_round'].split(';')]
        print(f"   - {c:<15} (Last Error = {raw_pct[-1]:.2f}%)")

    print(f"\n2. CITIES FLAGGED FOR RISING ERROR (Ratio > 1.5 AND Delta > 2.0 kWh/m2) [Total = {len(rising_flagged)}]:")
    for c in rising_flagged:
        row_c = df[df['city'] == c].iloc[0]
        raw_abs = [float(x.strip()) for x in row_c['O2_mean_err_abs_per_round'].split(';')]
        print(f"   - {c:<15} (R1 = {raw_abs[0]:.2f} kWh/m2 -> Last = {raw_abs[-1]:.2f} kWh/m2 | Delta = +{raw_abs[-1]-raw_abs[0]:.2f} kWh/m2, Ratio = {raw_abs[-1]/raw_abs[0]:.2f}x)")

    print("=" * 115)

if __name__ == "__main__":
    main()

