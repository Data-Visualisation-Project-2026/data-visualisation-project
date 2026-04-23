import pandas as pd
import streamlit as st

from visualizations.embedded_visuals import render_outlet_event_timeline
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
        background-color: #557086 !important;
        border-color: #557086 !important;
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
df = pd.read_parquet('iran_war_media_framing_scores_clustered.parquet', engine='pyarrow')
df_five_sources = pd.read_parquet('iran_war_media_framing_scores2_clustered.parquet', engine='pyarrow')

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

st.sidebar.markdown('## Navigation')
page = st.sidebar.radio(
    'Navigation',
    ['Overview', 'Detailed Framing Timeline', 'Distinctive Phrases by Cluster'],
    label_visibility='collapsed',
    key='main_navigation_v3'
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

    st.subheader('Average Framing Scores Over Time')
    st.caption('Feb 27–Mar 30, 2026 · Based on 1,925 articles from 77 media outlets')

    # Choose which framing dimensions to highlight in the chart.
    highlighted_dimensions = st.multiselect(
        'Use the dropdown to show or hide dimensions:',
        options=list(score_labels.values()),
        default=list(score_labels.values())
    )

    # Build and display the framing-over-time chart.
    chart = make_framing_over_time_chart(df, score_cols, score_labels, highlighted_dimensions)
    st.plotly_chart(chart, use_container_width=True)

    st.markdown(
        """
        This chart shows that Kinetic and Culpability Bias were the most prominent framing dimensions throughout the period, suggesting that coverage focused most strongly on military action and the assignment of responsibility. By contrast, Humanitarian and Diplomatic scores remained lower on average, indicating that these perspectives were present but were not the dominant narrative frames in overall coverage.

        Over time, Diplomatic framing shows a clear spike at the beginning of the period, then drops quickly and remains relatively low afterward. This suggests that early coverage may have paid more attention to international reactions, official statements, and interactions among political actors, before shifting toward other forms of framing. Economic framing also rises somewhat in the later part of the period, suggesting growing attention to the war’s broader economic and energy-related consequences.

        Culpability Bias is also notable not only because it stays consistently high, but because it shows several sharp peaks over time. This suggests that coverage was often not purely descriptive, but frequently used language that more strongly assigned blame or responsibility. Overall, the five dimensions do not move in parallel, which suggests that media framing shifted over time rather than following one fixed narrative pattern.
        """
    )

elif page == 'Detailed Framing Timeline':
    # Display the embedded outlet event timeline.
    render_outlet_event_timeline()

elif page == 'Distinctive Phrases by Cluster':
    st.subheader('Distinctive Phrases by Media Cluster')
    st.write(
        'These charts show the top c-TF-IDF bigrams for each article cluster. '
        'Higher-scoring phrases are more distinctive to that cluster relative to the others.'
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

    st.subheader('Outlet-Level Framing Heatmap')
    st.write(
        'This heatmap compares average framing scores across the five major outlets '
        'included in the focused article dataset.'
    )
    st.plotly_chart(make_outlet_framing_heatmap(df_five_sources), use_container_width=True)
