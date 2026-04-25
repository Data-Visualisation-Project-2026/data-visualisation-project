# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 21:22:31 2026

@author: Max
"""

import pandas as pd
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

# Load the clustered data
df = pd.read_parquet('iran_war_outlet_averages_clustered.parquet')

# Map Labels and Colors
df['cluster_label'] = 'Cluster ' + df['media_cluster'].astype(str)

color_map = {
    0: '#636EFA',
    1: '#EF553B',
    2: '#00CC96',
    3: '#AB63FA',
    4: '#FFA15A'
}

# Perform PCA 
features = [
    'kinetic_focus', 'humanitarian_focus', 
    'diplomatic_focus', 'economic_focus', 'culpability_bias'
]

pca = PCA(n_components=3)
components = pca.fit_transform(df[features])

df['X'] = components[:, 0]
df['Y'] = components[:, 1]
df['Z'] = components[:, 2]

variance = pca.explained_variance_ratio_ * 100
variance_total = variance.sum()

# Calculate Edges (K-Nearest Neighbors)
nn = NearestNeighbors(n_neighbors=4) 
nn.fit(components)
distances, indices = nn.kneighbors(components)

edge_x = []
edge_y = []
edge_z = []

for i in range(len(df)):
    for j in range(1, 4): 
        neighbor_idx = indices[i, j]
        edge_x.extend([components[i, 0], components[neighbor_idx, 0], None])
        edge_y.extend([components[i, 1], components[neighbor_idx, 1], None])
        edge_z.extend([components[i, 2], components[neighbor_idx, 2], None])

# Build the Plotly 3D Figure
fig = go.Figure()

# LAYER 1: Draw polygons
show_master_legend = True 

for i in range(5):
    cluster_name = f'Cluster {i}'
    group = df[df['media_cluster'] == i]
    color = color_map[i]
    
    if len(group) >= 4:
        fig.add_trace(go.Mesh3d(
            x=group['X'],
            y=group['Y'],
            z=group['Z'],
            alphahull=0,  
            opacity=0.10, 
            color=color,
            legendgroup='polygon_group', 
            name='Toggle all cluster bubbles', 
            showlegend=show_master_legend, 
            hoverinfo='skip'  
        ))
        show_master_legend = False 

# LAYER 2: Draw Edges
fig.add_trace(go.Scatter3d(
    x=edge_x, y=edge_y, z=edge_z,
    mode='lines',
    line=dict(
        color='rgba(255, 255, 255, 0.20)', 
        width=1.5
    ),
    hoverinfo='skip', 
    showlegend=False
))

# LAYER 3: Draw Nodes
for i in range(5):
    cluster_name = f'Cluster {i}'
    group = df[df['media_cluster'] == i]
    color = color_map[i]
    
    fig.add_trace(go.Scatter3d(
        x=group['X'],
        y=group['Y'],
        z=group['Z'],
        mode='markers+text',
        name=cluster_name,
        text=group['media_name'],
        textposition='top center',
        textfont=dict(color='white', size=11),
        marker=dict(
            size=14, 
            color=color, 
            opacity=1.0,
            line=dict(width=1.5, color='white') 
        ),
        customdata=group[features], 
        hovertemplate=(
            '<b>%{text}</b><br>' +
            cluster_name + '<br><br>' +
            'Kinetic: %{customdata[0]:.2f}<br>' +
            'Humanitarian: %{customdata[1]:.2f}<br>' +
            'Diplomatic: %{customdata[2]:.2f}<br>' +
            'Economic: %{customdata[3]:.2f}<br>' +
            'Culpability: %{customdata[4]:.2f}' +
            '<extra></extra>'
        )
    ))

# Format the UI
dark_navy = '#0B1121'

fig.update_layout(
    title=dict(
        text=f"Media Outlet Ideological Clustering (5-Axis PCA Projection)<br><span style='font-size:13px; color:lightgrey;'>Total Variance Captured: {variance_total:.2f}%</span>",
        font=dict(color='white')
    ),
    paper_bgcolor=dark_navy,
    plot_bgcolor=dark_navy,
    scene=dict(
        bgcolor=dark_navy,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        zaxis=dict(visible=False),
    ),
    legend=dict(
        title='Interactive Controls',
        font=dict(color='white'),
        itemsizing='constant',
        traceorder='normal',
        y=0.9
    ),

    margin=dict(l=0, r=280, b=0, t=65),
    hovermode='closest', 
    hoverdistance=100,
    

    annotations=[
        dict(
            x=1.12,
            y=0.45,
            xref='paper',
            yref='paper',
            text=(
                '<b>Cluster Definitions:</b><br><br>'
                '<b>0:</b> Mainstream (Moderate)<br>'
                '<b>1:</b> Dissident/Left Wing (High Culpability)<br>'
                '<b>2:</b> Smaller Mainstream (Diplo/Humanitarian)<br>'
                '<b>3:</b> Business (High Economic)<br>'
                '<b>4:</b> Right Wing/Military (High Kinetic)'
            ),
            showarrow=False,
            align='left',
            font=dict(color='lightgrey', size=12),
            bgcolor='rgba(255, 255, 255, 0.05)', # Subtle translucent background
            bordercolor='rgba(255, 255, 255, 0.2)',
            borderwidth=1,
            borderpad=12
        )
    ]
)

# Save file
html_filename = 'media_cluster_3d_pca.html'
fig.write_html(html_filename)
print('Success')