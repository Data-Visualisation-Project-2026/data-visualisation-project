import pandas as pd
import streamlit as st

from framing_charts import make_framing_over_time_chart

# Set up the Streamlit page and main title.
st.set_page_config(layout='wide')

st.title('Media Framing of the 2026 Iran War')

# Load the article framing data.
df = pd.read_parquet('iran_war_media_framing_scores.parquet', engine='pyarrow')

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

df['publish_date'] = pd.to_datetime(df['publish_date'])

# Choose which framing dimensions to highlight in the chart.
highlighted_dimensions = st.multiselect(
    'Highlight framing dimensions',
    options=list(score_labels.values()),
    default=list(score_labels.values())
)

# Build and display the framing-over-time chart.
chart = make_framing_over_time_chart(df, score_cols, score_labels, highlighted_dimensions)
st.plotly_chart(chart, use_container_width=True)
