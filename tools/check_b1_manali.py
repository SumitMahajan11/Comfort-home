import os
import pandas as pd
import numpy as np

stations = {
    'Manali': 'data/raw/India_Weather_Extracted/IND_HP_Manali.420650_TMYx.2011-2025/IND_HP_Manali.420650_TMYx.2011-2025.epw',
    'Bhuntar': 'data/raw/India_Weather_Extracted/IND_HP_Bhuntar.420810_TMYx.2011-2025/IND_HP_Bhuntar.420810_TMYx.2011-2025.epw',
    'Kullu.Manali': 'data/raw/India_Weather_Extracted/IND_HP_Kullu.Manali.427051_TMYx.2011-2025/IND_HP_Kullu.Manali.427051_TMYx.2011-2025.epw',
    'Shimla': 'data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx/IND_HP_Shimla.420830_TMYx.epw',
    'Leh': 'data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw'
}

shimla_2011 = 'data/raw/India_Weather_Extracted/IND_HP_Shimla.420830_TMYx.2011-2025/IND_HP_Shimla.420830_TMYx.2011-2025.epw'
if os.path.exists(shimla_2011):
    stations['Shimla'] = shimla_2011

rows = []
for name, p in stations.items():
    if not os.path.exists(p):
        print(f"MISSING: {name} at {p}")
        continue
    with open(p, 'r', encoding='latin-1') as f:
        header = f.readline().split(',')
        lat = float(header[6])
        lon = float(header[7])
        elev = float(header[9])
    
    df = pd.read_csv(p, skiprows=8, header=None, encoding='latin-1')
    month = df[1].values
    tdb = df[6].values
    
    ann_mean = float(np.mean(tdb))
    monthly_means = [float(np.mean(tdb[month == m])) for m in range(1, 13)]
    
    rows.append({
        'Station': name,
        'Lat': lat,
        'Lon': lon,
        'Elev (m)': elev,
        'Ann Mean Tdb (C)': round(ann_mean, 2),
        'Jan': round(monthly_means[0], 2),
        'Feb': round(monthly_means[1], 2),
        'Mar': round(monthly_means[2], 2),
        'Apr': round(monthly_means[3], 2),
        'May': round(monthly_means[4], 2),
        'Jun': round(monthly_means[5], 2),
        'Jul': round(monthly_means[6], 2),
        'Aug': round(monthly_means[7], 2),
        'Sep': round(monthly_means[8], 2),
        'Oct': round(monthly_means[9], 2),
        'Nov': round(monthly_means[10], 2),
        'Dec': round(monthly_means[11], 2),
    })

res_df = pd.DataFrame(rows)
print(res_df.to_string(index=False))

# Rule check:
# Rule: Manali is in the HIGHER-elevation cold-zone group and must be
# warmer than Leh (annual mean) and colder than Bhuntar.
# If Manali fails this rule, switch the city to Bhuntar, update the manifest
# and climate table, and print "MANALI REJECTED". If it passes, print "MANALI OK".

manali_ann = res_df.loc[res_df['Station'] == 'Manali', 'Ann Mean Tdb (C)'].values[0]
leh_ann = res_df.loc[res_df['Station'] == 'Leh', 'Ann Mean Tdb (C)'].values[0]
bhuntar_ann = res_df.loc[res_df['Station'] == 'Bhuntar', 'Ann Mean Tdb (C)'].values[0]

print("\n--- RULE EVALUATION ---")
print(f"Leh Ann Mean:     {leh_ann} C")
print(f"Manali Ann Mean:  {manali_ann} C")
print(f"Bhuntar Ann Mean: {bhuntar_ann} C")

passes = (manali_ann > leh_ann) and (manali_ann < bhuntar_ann)
print(f"Condition (Manali > Leh): {manali_ann > leh_ann}")
print(f"Condition (Manali < Bhuntar): {manali_ann < bhuntar_ann}")

if passes:
    print("RESULT: MANALI OK")
else:
    print("RESULT: MANALI REJECTED")
