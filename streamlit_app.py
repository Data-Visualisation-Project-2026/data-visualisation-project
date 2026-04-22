import pandas as pd
import streamlit as st

from embedded_visuals import render_outlet_event_timeline
from framing_charts import make_framing_over_time_chart

# Set up the Streamlit page and main title.
st.set_page_config(layout='wide')

st.markdown(
    """
    <style>
    :root {
        --primary-color: #34495e;
    }

    .stApp {
        color: #24303f;
    }

    [data-testid="stSidebar"] {
        background: #eef2f6;
        border-right: 1px solid #c9d3df;
    }

    [data-testid="stSidebar"] h2 {
        color: #2f4054;
        font-size: 1rem;
        margin-bottom: 0.75rem;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 0.45rem;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: #f8fafc;
        border: 1px solid #c9d3df;
        border-radius: 999px;
        color: #34495e;
        margin-bottom: 0.45rem;
        padding: 0.55rem 0.85rem;
        transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #34495e;
        border-color: #34495e;
        color: #ffffff;
        font-weight: 700;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        border-color: #34495e;
    }

    [data-testid="stSidebar"] input[type="radio"] {
        accent-color: #34495e;
    }

    .project-author {
        color: #5b6775;
        font-size: 1rem;
        margin-top: -0.7rem;
        margin-bottom: 2rem;
    }

    div[data-baseweb="select"] > div {
        border-color: #c9d3df;
    }

    div[data-baseweb="tag"] {
        background-color: #34495e;
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
    ['Overview', 'Outlet Event Timeline'],
    label_visibility='collapsed'
)

if page == 'Overview':
    # Intro section for the project overview page.
    st.subheader('Intro')

    # Choose which framing dimensions to highlight in the chart.
    highlighted_dimensions = st.multiselect(
        'Highlight framing dimensions',
        options=list(score_labels.values()),
        default=list(score_labels.values())
    )

    # Build and display the framing-over-time chart.
    chart = make_framing_over_time_chart(df, score_cols, score_labels, highlighted_dimensions)
    st.plotly_chart(chart, use_container_width=True)

else:
    # Display the embedded outlet event timeline.
    render_outlet_event_timeline()
