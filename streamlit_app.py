from pathlib import Path

import pandas as pd
import streamlit as st

from visualizations.embedded_visuals import render_outlet_event_timeline
from visualizations.embedded_network import render_media_clusters
from visualizations.framing_charts import make_framing_over_time_chart
from visualizations.text_analysis import (
    get_top_cluster_bigrams,
    make_cluster_bigram_charts,
    make_outlet_framing_heatmap,
)

# Set up the Streamlit page and main title.
st.set_page_config(layout='wide')

st.markdown(
    """
    <style>
    :root {
        --primary-color: #2f4a5f;
    }

    .stApp {
        color: #263746;
    }

    [data-testid="stSidebar"] {
        background: #dfeaf2;
        border-right: 2px solid #9eb2c3;
        box-shadow: 2px 0 10px rgba(47, 74, 95, 0.08);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
        padding-left: 1.35rem;
        padding-right: 1.35rem;
    }

    [data-testid="stSidebar"] h2 {
        color: #2f4a5f;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.03em;
        margin-bottom: 1rem;
        padding-bottom: 0.7rem;
        border-bottom: 1px solid rgba(47, 74, 95, 0.22);
        text-transform: uppercase;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 0.8rem;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label {
        align-items: center;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid #b4c5d2;
        border-radius: 10px;
        color: #2f4a5f;
        font-size: 1.02rem;
        font-weight: 650;
        margin-bottom: 0.7rem;
        padding: 0.8rem 0.85rem;
        transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #f7fbff;
        border-color: #6f8fa8;
        box-shadow: 0 4px 12px rgba(47, 74, 95, 0.12);
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #eef5fa;
        border-color: #2f4a5f;
        border-left: 5px solid #2f4a5f;
        box-shadow: 0 5px 14px rgba(47, 74, 95, 0.16);
        color: #22394c;
        font-weight: 800;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: inherit;
        font-size: 1.02rem;
    }

    [data-testid="stSidebar"] input[type="radio"] {
        accent-color: #2f4a5f;
    }

    .project-author {
        color: #5d6f7e;
        font-size: 1rem;
        margin-top: -0.7rem;
        margin-bottom: 2rem;
    }

    div[data-baseweb="select"] > div {
        border-color: #c4d2de;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"],
    div[data-baseweb="popover"] div[data-baseweb="tag"],
    span[data-baseweb="tag"] {
        background: #557086 !important;
        background-color: #557086 !important;
        border-color: #557086 !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-of-type(1),
    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-child(1),
    span[data-baseweb="tag"]:nth-of-type(1),
    span[data-baseweb="tag"]:nth-child(1) {
        background: #59A14F !important;
        background-color: #59A14F !important;
        border-color: #59A14F !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-of-type(2),
    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-child(2),
    span[data-baseweb="tag"]:nth-of-type(2),
    span[data-baseweb="tag"]:nth-child(2) {
        background: #4E79A7 !important;
        background-color: #4E79A7 !important;
        border-color: #4E79A7 !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-of-type(3),
    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-child(3),
    span[data-baseweb="tag"]:nth-of-type(3),
    span[data-baseweb="tag"]:nth-child(3) {
        background: #76B7B2 !important;
        background-color: #76B7B2 !important;
        border-color: #76B7B2 !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-of-type(4),
    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-child(4),
    span[data-baseweb="tag"]:nth-of-type(4),
    span[data-baseweb="tag"]:nth-child(4) {
        background: #E15759 !important;
        background-color: #E15759 !important;
        border-color: #E15759 !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-of-type(5),
    div[data-baseweb="select"] div[data-baseweb="tag"]:nth-child(5),
    span[data-baseweb="tag"]:nth-of-type(5),
    span[data-baseweb="tag"]:nth-child(5) {
        background: #F28E2B !important;
        background-color: #F28E2B !important;
        border-color: #F28E2B !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] span,
    div[data-baseweb="popover"] div[data-baseweb="tag"] span,
    span[data-baseweb="tag"] span {
        color: #ffffff !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] svg,
    div[data-baseweb="popover"] div[data-baseweb="tag"] svg,
    span[data-baseweb="tag"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] path,
    div[data-baseweb="popover"] div[data-baseweb="tag"] path,
    span[data-baseweb="tag"] path {
        fill: #ffffff !important;
    }

    div[data-baseweb="checkbox"] label,
    div[role="checkbox"] {
        accent-color: #2f4a5f;
    }

    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background-color: #2f4a5f;
        border-color: #2f4a5f;
    }

    a {
        color: #2f5f86;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title('Media Framing of the 2026 Iran War')
st.markdown(
    '<div class="project-author">By Adeline Setiawan, Maximilian Chelminski, and Yixiao Liu</div>',
    unsafe_allow_html=True
)

# Load the clustered article framing data.
df = pd.read_parquet('iran_war_media_framing_scores_clustered.parquet', engine='fastparquet')
df_five_sources = pd.read_parquet('iran_war_media_framing_scores2_clustered.parquet', engine='fastparquet')

# Columns containing the LLM-generated framing scores.
score_cols = [
    'kinetic_focus',
    'humanitarian_focus',
    'diplomatic_focus',
    'economic_focus',
    'culpability_bias'
]

score_labels = {
    'kinetic_focus': 'Kinetic',
    'humanitarian_focus': 'Humanitarian',
    'diplomatic_focus': 'Diplomatic',
    'economic_focus': 'Economic',
    'culpability_bias': 'Culpability Bias'
}

df['publish_date'] = pd.to_datetime(df['indexed_date'])

dimension_order = [
    'Culpability Bias',
    'Kinetic',
    'Economic',
    'Diplomatic',
    'Humanitarian'
]

st.sidebar.markdown('## Navigation')
page = st.sidebar.radio(
    'Navigation',
    ['Overview', 'Narrative Over Time', 'Media Clusters', 'Media Differences', 'Data & Methods'],
    label_visibility='collapsed',
    key='main_navigation_v4'
)

if page == 'Overview':
    # Intro section for the project overview page.
    st.markdown(
        """
        This project explores how media outlets framed the 2026 Iran War across time, media sources, and narrative dimensions. We analyze how coverage varies across five framing dimensions:

        - **Kinetic Focus:** emphasis on military action, strikes, weapons, and strategy.
        - **Humanitarian Focus:** emphasis on civilian suffering, refugees, and casualties.
        - **Diplomatic Focus:** emphasis on negotiations, international organizations, and political responses.
        - **Economic Focus:** emphasis on oil, trade, markets, and broader economic effects.
        - **Culpability Bias:** the extent to which coverage uses strong or active language to assign blame.
        """
    )

    st.subheader('Overall Framing Trends During the Iran War')
    st.caption('Feb 27–Mar 30, 2026 · Based on 1,925 articles from 77 media outlets')

    # Choose which framing dimensions to highlight in the chart.
    highlighted_dimensions = st.multiselect(
        'Use the dropdown to show or hide dimensions:',
        options=dimension_order,
        default=dimension_order,
        key='overview_dimension_selector_v2'
    )

    # Build and display the framing-over-time chart.
    chart = make_framing_over_time_chart(df, score_cols, score_labels, highlighted_dimensions)
    st.plotly_chart(chart, use_container_width=True)

    st.markdown(
        """
        The overall pattern suggests that coverage was driven mainly by military action and responsibility/blame. Kinetic framing stayed high for much of the period, while Culpability Bias remained consistently prominent, showing that many articles framed the war not only through what happened, but also through who was responsible.
        Humanitarian framing stayed lower overall, suggesting that civilian suffering and human impacts were present but less central in the aggregate coverage.

        Moreover, the emphasis shift over time. Diplomatic framing was unusually high at the beginning, likely reflecting early attention to official statements, international reactions, and political responses. After that, it dropped and stayed relatively low. Later, Economic framing becomes more visible, especially around moments linked to energy and regional escalation.

        Taken together, the five lines show that media framing was not fixed: as the war developed, coverage moved between military, political, economic, and blame-centered narratives.
        """
    )

elif page == 'Narrative Over Time':
    # Display the embedded outlet event timeline.
    render_outlet_event_timeline()

elif page == 'Media Clusters':
    st.subheader('Media Clusters')
    st.write(
        'This 3D network visualization shows how media outlets cluster based on their '
        'average framing patterns across the five narrative dimensions.'
    )

    render_media_clusters()

    st.markdown(Path('network_analysis/networkvis_interpretation.md').read_text())

elif page == 'Media Differences':
    st.subheader('Distinctive Phrases by Media Cluster')
    st.write(
        'These charts show the most unique phrases in each media cluster. '
    )

    # Compute and display cluster-specific bigram charts.
    top_bigrams = get_top_cluster_bigrams(df, top_n=10)
    bigram_charts = make_cluster_bigram_charts(top_bigrams)

    chart_items = list(bigram_charts.items())

    for row_start in range(0, len(chart_items), 2):
        columns = st.columns(2)

        for column, (_, chart) in zip(columns, chart_items[row_start:row_start + 2]):
            with column:
                st.plotly_chart(chart, use_container_width=True)

    st.subheader('How Framing Differs Across Major Media Outlets')
    st.caption('Based on 1,736 articles from 5 major media outlets')
    
    st.plotly_chart(make_outlet_framing_heatmap(df_five_sources), use_container_width=True)

elif page == 'Data & Methods':
    st.markdown(Path('methodology.md').read_text())
