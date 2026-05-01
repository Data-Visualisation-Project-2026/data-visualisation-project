# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 23:12:44 2026

@author: Max
"""

import pandas as pd
from sklearn.cluster import KMeans
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

# Read the Parquet Files
df1 = pd.read_parquet(DATA_DIR / 'iran_war_media_framing_scores.parquet')
df2 = pd.read_parquet(DATA_DIR / 'iran_war_media_framing_scores2.parquet')

# Clean and Align Headers
df1 = df1.drop(columns=['pos_score', 'neg_score'], errors='ignore')
df2 = df2.drop(columns=['pos_score', 'neg_score'], errors='ignore')

if 'published_datetime' in df2.columns:
    df2 = df2.rename(columns={'published_datetime': 'indexed_date'})
    print("Harmonized date column names.")

df1['indexed_date'] = pd.to_datetime(df1['indexed_date'], errors='coerce').dt.date
df2['indexed_date'] = pd.to_datetime(df2['indexed_date'], errors='coerce').dt.date

common_columns = df1.columns.intersection(df2.columns)

df1 = df1[common_columns]
df2 = df2[common_columns]

# Merge the Dataframes
split_index = len(df1) 
df_merged = pd.concat([df1, df2], ignore_index=True)

# The 5 axes we are clustering on
features = [
    'kinetic_focus', 
    'humanitarian_focus', 
    'diplomatic_focus', 
    'economic_focus', 
    'culpability_bias'
]

# Clustering at article level
kmeans_article = KMeans(n_clusters=5, random_state=5, n_init='auto')
df_merged['article_cluster'] = kmeans_article.fit_predict(df_merged[features])


# Clustering at outlet level, mean of 5 axes for each outlet
df_media = df_merged.groupby('media_name')[features].mean().reset_index()

kmeans_media = KMeans(n_clusters=5, random_state=5, n_init='auto')
df_media['media_cluster'] = kmeans_media.fit_predict(df_media[features])


# Resplitting the datasets and saving
df1_clustered = df_merged.iloc[:split_index].copy()
df2_clustered = df_merged.iloc[split_index:].copy()

df1_clustered.to_parquet(DATA_DIR / 'iran_war_media_framing_scores_clustered.parquet', engine='pyarrow')
df2_clustered.to_parquet(DATA_DIR / 'iran_war_media_framing_scores2_clustered.parquet', engine='pyarrow')

df_media.to_parquet(DATA_DIR / 'iran_war_outlet_averages_clustered.parquet', engine='pyarrow')

print('Success')
