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
        --primary-color: #2f4a5f;
    }

    .stApp {
        color: #263746;
    }

    [data-testid="stSidebar"] {
        background: #edf3f8;
        border-right: 1px solid #c4d2de;
    }

    [data-testid="stSidebar"] h2 {
        color: #2f4a5f;
        font-size: 1rem;
        margin-bottom: 0.75rem;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 0.45rem;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: #f8fafc;
        border: 1px solid #c4d2de;
        border-radius: 999px;
        color: #2f4a5f;
        margin-bottom: 0.45rem;
        padding: 0.55rem 0.85rem;
        transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #2f4a5f;
        border-color: #2f4a5f;
        color: #ffffff;
        font-weight: 700;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        border-color: #2f4a5f;
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

    div[data-baseweb="tag"] {
        background-color: #557086 !important;
    }

    div[data-baseweb="tag"] span {
        color: #ffffff !important;
    }

    div[data-baseweb="tag"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
    }

    div[data-baseweb="tag"] path {
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

    [data-testid="stSidebar"] [data-baseweb="radio"] div:first-child {
        background-color: #6f8fa8 !important;
        border-color: #6f8fa8 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="radio"] div:first-child::before,
    [data-testid="stSidebar"] [data-baseweb="radio"] div:first-child::after {
        background-color: #6f8fa8 !important;
        border-color: #6f8fa8 !important;
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
    st.write(
        'This project explores how media outlets framed the 2026 Iran War across time, '
        'media sources, and narrative dimensions. We analyze how coverage varies in '
        'kinetic, humanitarian, diplomatic, economic, and culpability framing.'
    )

    st.subheader('Average Framing Scores Over Time')

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
