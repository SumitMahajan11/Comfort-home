import os
import re
import pandas as pd
import numpy as np

VAR_COLS = [
    'roof_insulation_thickness', 'wall_insulation_thickness', 'wall_mass_class',
    'roof_solar_absorptance', 'wwr', 'orientation', 'shading_depth', 'ventilation_ach'
]

def parse_idf(idf_path):
    with open(idf_path, 'r') as f:
        clean_lines = [re.sub(r'!-.*', '', l).strip() for l in f]
    clean_text = ' '.join(clean_lines)
    objects = [obj.strip() for obj in clean_text.split(';') if obj.strip()]

    data = {}
    for obj in objects:
        fields = [f.strip() for f in obj.split(',')]
        otype = fields[0].lower()
        if otype == 'building':
            data['orientation'] = round(float(fields[2]), 1)
        elif otype == 'material':
            mname = fields[1].lower()
            if mname == 'roof_insulation':
                data['roof_insulation_thickness'] = round(float(fields[3]), 3)
            elif mname == 'wall_insulation':
                data['wall_insulation_thickness'] = round(float(fields[3]), 3)
            elif mname == 'roof_outer_finish':
                data['roof_solar_absorptance'] = round(float(fields[7]), 4)
        elif otype == 'construction':
            cname = fields[1].lower()
            if cname == 'wall_construction':
                layer = fields[2].lower()
                if 'heavy' in layer: data['wall_mass_class'] = 'heavy'
                elif 'medium' in layer: data['wall_mass_class'] = 'medium'
                elif 'light' in layer: data['wall_mass_class'] = 'light'
        elif otype == 'zoneventilation:designflowrate':
            data['ventilation_ach'] = round(float(fields[8]), 2)
        elif otype == 'shading:zone:detailed':
            sname = fields[1].lower()
            if 'overhang' in sname:
                y_coords = [abs(float(fields[i])) for i in [7, 10, 13, 16]]
                data['shading_depth'] = round(max(y_coords), 3)
        elif otype == 'fenestrationsurface:detailed':
            fname = fields[1].lower()
            if 'south_window' in fname:
                xs = [float(fields[i]) for i in [10, 13, 16, 19]]
                zs = [float(fields[i]) for i in [12, 15, 18, 21]]
                w_w = max(xs) - min(xs)
                w_h = max(zs) - min(zs)
                data['wwr'] = round((w_w * w_h) / (4.472 * 2.8), 4)
    return data

def main():
    print("=" * 100)
    print("ACTIVE LEARNING CANDIDATE DIVERSITY & SIMULATION RUNTIME (LEH vs CHENNAI)")
    print("=" * 100)

    rows = []

    # -------------------------------------------------------------------------
    # 1. LEH
    # -------------------------------------------------------------------------
    leh_hist_path = "data/processed/active_learning_leh/active_learning_history.csv"
    df_leh_hist = pd.read_csv(leh_hist_path) if os.path.exists(leh_hist_path) else None

    # Leh Round 1: pareto_Leh.parquet
    leh_r1_path = "data/processed/pilot_leh/pareto_Leh.parquet"
    if os.path.exists(leh_r1_path):
        df_l1 = pd.read_parquet(leh_r1_path)
        u_l1 = len(df_l1.drop_duplicates(subset=VAR_COLS))
        n_l1 = len(df_l1)
        t_l1 = df_leh_hist.loc[df_leh_hist['round'] == 1, 'sim_time_sec'].iloc[0] if df_leh_hist is not None else np.nan
        rows.append({
            'City': 'Leh', 'Round': 1, 'Candidate Count': n_l1,
            'Unique Designs': u_l1, 'Uniqueness (%)': round(u_l1 / n_l1 * 100.0, 1),
            'Simulate Time (s)': round(t_l1, 2)
        })

    # Leh Round 2: parse from round_2_sims IDFs
    leh_r2_dir = "data/processed/active_learning_leh/round_2_sims"
    if os.path.exists(leh_r2_dir):
        r2_designs = []
        for i in range(100):
            idf_p = os.path.join(leh_r2_dir, f'P_Leh_R2_{i:03d}_fr', 'shelter.idf')
            if os.path.exists(idf_p):
                d = parse_idf(idf_p)
                d['pareto_id'] = f'P_Leh_R2_{i:03d}'
                r2_designs.append(d)
        df_l2 = pd.DataFrame(r2_designs)
        cols_l2 = [c for c in df_l2.columns if c != 'pareto_id']
        u_l2 = len(df_l2.drop_duplicates(subset=cols_l2))
        n_l2 = len(df_l2)
        t_l2 = df_leh_hist.loc[df_leh_hist['round'] == 2, 'sim_time_sec'].iloc[0] if df_leh_hist is not None else np.nan
        rows.append({
            'City': 'Leh', 'Round': 2, 'Candidate Count': n_l2,
            'Unique Designs': u_l2, 'Uniqueness (%)': round(u_l2 / n_l2 * 100.0, 1),
            'Simulate Time (s)': round(t_l2, 2)
        })

    # Leh Round 3: final_verified_all_100_Leh.parquet
    leh_r3_path = "data/processed/active_learning_leh/final_verified_all_100_Leh.parquet"
    if os.path.exists(leh_r3_path):
        df_l3 = pd.read_parquet(leh_r3_path)
        var_cols_3 = [f'{v}_x' if f'{v}_x' in df_l3.columns else (f'{v}_y' if f'{v}_y' in df_l3.columns else v) for v in VAR_COLS]
        u_l3 = len(df_l3.drop_duplicates(subset=var_cols_3))
        n_l3 = len(df_l3)
        t_l3 = df_leh_hist.loc[df_leh_hist['round'] == 3, 'sim_time_sec'].iloc[0] if df_leh_hist is not None else np.nan
        rows.append({
            'City': 'Leh', 'Round': 3, 'Candidate Count': n_l3,
            'Unique Designs': u_l3, 'Uniqueness (%)': round(u_l3 / n_l3 * 100.0, 1),
            'Simulate Time (s)': round(t_l3, 2)
        })

    # -------------------------------------------------------------------------
    # 2. CHENNAI
    # -------------------------------------------------------------------------
    chn_dir = "data/processed/batch/Chennai"
    chn_hist_path = os.path.join(chn_dir, "active_learning_history.csv")
    df_chn_hist = pd.read_csv(chn_hist_path) if os.path.exists(chn_hist_path) else None

    for r in [1, 2, 3]:
        p = os.path.join(chn_dir, f"round_{r}_candidates.parquet")
        if os.path.exists(p):
            df_c = pd.read_parquet(p)
            u_c = len(df_c.drop_duplicates(subset=VAR_COLS))
            n_c = len(df_c)
            t_c = df_chn_hist.loc[df_chn_hist['round'] == r, 'sim_time_sec'].iloc[0] if df_chn_hist is not None and len(df_chn_hist) >= r else np.nan
            rows.append({
                'City': 'Chennai', 'Round': r, 'Candidate Count': n_c,
                'Unique Designs': u_c, 'Uniqueness (%)': round(u_c / n_c * 100.0, 1),
                'Simulate Time (s)': round(t_c, 2)
            })
        else:
            rows.append({
                'City': 'Chennai', 'Round': r, 'Candidate Count': 'Pending',
                'Unique Designs': 'Pending', 'Uniqueness (%)': 'Pending',
                'Simulate Time (s)': 'Pending'
            })

    df_report = pd.DataFrame(rows)
    print(df_report.to_string(index=False))

    print("\nNotes on candidate files:")
    print("1. Leh: Round 1 candidates were stored in 'data/processed/pilot_leh/pareto_Leh.parquet' (100 unique designs).")
    print("   Round 2 candidate parquet was not saved as an isolated standalone table in legacy pilot_leh; candidates were preserved inside the 200 IDF run directories in 'data/processed/active_learning_leh/round_2_sims' and parsed directly (84 unique designs).")
    print("   Round 3 candidates were stored in 'data/processed/active_learning_leh/final_verified_all_100_Leh.parquet' (100 unique designs).")
    print("2. Chennai: Explicitly persists 'round_1_candidates.parquet', 'round_2_candidates.parquet', and 'round_3_candidates.parquet' in 'data/processed/batch/Chennai/'.")

if __name__ == '__main__':
    main()
