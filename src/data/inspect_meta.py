"""
Inspect actual country and climate strings in db_metadata.csv.
"""

import pandas as pd

df_meta = pd.read_csv("data/raw/ashrae_db_ii/ashrae-db-II-master/v2.1.0/db_metadata.csv")
print("Countries in metadata:", df_meta['country'].unique())
print("\nUK buildings in metadata:")
print(df_meta[df_meta['country'].str.contains('UK|United Kingdom|uk', case=False, na=False)][['building_id', 'country', 'city', 'climate', 'lat', 'lon']])

print("\nMalaysia buildings in metadata:")
print(df_meta[df_meta['country'].str.contains('Malaysia|malaysia', case=False, na=False)][['building_id', 'country', 'city', 'climate', 'lat', 'lon']])

print("\nCanada buildings in metadata:")
print(df_meta[df_meta['country'].str.contains('Canada|canada', case=False, na=False)][['building_id', 'country', 'city', 'climate', 'lat', 'lon']])

print("\nAll distinct climate strings in metadata:")
print(df_meta['climate'].value_counts())
