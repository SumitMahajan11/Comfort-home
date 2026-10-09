"""
Comprehensive building-to-Köppen group mapper with geographic ground-truth resolution.
"""

import os
import pandas as pd
import numpy as np

def generate_building_group_map():
    meta_path = "data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv"
    label_map_path = "data/processed/koppen_group_map.csv"
    output_path = "data/processed/building_group_map.csv"
    
    df_meta = pd.read_csv(meta_path)
    df_label_map = pd.read_csv(label_map_path)
    
    # Normalize keys in label map
    label_dict = {}
    for _, r in df_label_map.iterrows():
        raw_c = str(r['raw_climate']).strip().lower().replace('\xa0', ' ')
        label_dict[raw_c] = r['koppen_group']
        
    records = []
    
    for _, row in df_meta.iterrows():
        bldg_id = int(row['building_id'])
        raw_c_orig = str(row['climate'])
        raw_c = raw_c_orig.strip().lower().replace('\xa0', ' ') if pd.notnull(row['climate']) else 'unknown'
        
        label_grp = label_dict.get(raw_c, 'Unknown')
        country = str(row['country']).strip().lower() if pd.notnull(row['country']) else ''
        city = str(row['city']).strip().lower() if pd.notnull(row['city']) else ''
        lat = row['lat']
        lon = row['lon']
        
        geo_grp = label_grp
        override_reason = "Agrees with geographical location"
        
        # 1. UK buildings: All UK buildings (London, Oxford, Wales, Scotland) are Cfb -> Group C (Temperate Marine).
        # Any UK building labelled as Continental (D) is a misclassification.
        if country == 'uk' or country == 'united kingdom':
            if label_grp != 'C':
                geo_grp = 'C'
                override_reason = f"UK location ({city}, lat={lat:.2f}) is Marine Temperate (Cfb/Group C), not Continental (Group {label_grp})"
                
        # 2. Malaysia buildings: Located 1° to 6° N (Kuala Lumpur, Sabah, Sarawak) -> Group A (Tropical Rainforest/Monsoon Af/Am).
        # Any Malaysia building labelled as Mediterranean (C) is a misclassification.
        elif country == 'malaysia':
            if label_grp != 'A':
                geo_grp = 'A'
                override_reason = f"Malaysia location ({city}, lat={lat:.2f}) is Equatorial/Tropical (Af/Am/Group A), not Mediterranean (Group {label_grp})"
                
        # 3. Canada buildings (Ottawa, Montreal, etc.): Located 45°+ N -> Group D (Humid Continental Dfb / Subarctic Dfc).
        # Any Canada building labelled as generic Temperate (C) is Continental (D).
        elif country == 'canada':
            if label_grp != 'D':
                geo_grp = 'D'
                override_reason = f"Canada location ({city}, lat={lat:.2f}) is Continental (Dfb/Group D), not Temperate (Group {label_grp})"
                
        # 4. Philippines / Indonesia / Nigeria / Brazil (Tropical locations):
        elif country in ['philippines', 'indonesia', 'nigeria'] and lat is not None and abs(lat) < 15:
            if label_grp != 'A':
                geo_grp = 'A'
                override_reason = f"{country.title()} location ({city}, lat={lat:.2f}) is Tropical (Group A)"
                
        # 5. Typo 'temperature marine' in Melbourne, Australia -> Group C
        elif raw_c == 'temperature marine':
            geo_grp = 'C'
            override_reason = "Typo for temperate marine (Cfb/Group C)"
            
        agreement = (label_grp == geo_grp)
        
        records.append({
            'building_id': bldg_id,
            'country': country,
            'city': city,
            'lat': lat,
            'lon': lon,
            'raw_climate': raw_c_orig,
            'label_based_group': label_grp,
            'geo_override_group': geo_grp,
            'agreement': agreement,
            'override_reason': override_reason
        })
        
    df_out = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_out.to_csv(output_path, index=False)
    
    total = len(df_out)
    agreed = int(df_out['agreement'].sum())
    disagreed = total - agreed
    disagreement_rate = (disagreed / total) * 100
    
    print("="*80)
    print("BUILDING KÖPPEN GROUP MAPPING SUMMARY")
    print("="*80)
    print(f"Total buildings: {total}")
    print(f"Agreed buildings: {agreed} ({agreed/total*100:.2f}%)")
    print(f"Disagreed buildings: {disagreed} ({disagreement_rate:.2f}%)")
    print("\nDisagreed building details:")
    dis_df = df_out[~df_out['agreement']]
    print(dis_df[['building_id', 'country', 'city', 'raw_climate', 'label_based_group', 'geo_override_group', 'override_reason']].to_string(index=False))
    print(f"\nSaved {output_path}")

if __name__ == "__main__":
    generate_building_group_map()
