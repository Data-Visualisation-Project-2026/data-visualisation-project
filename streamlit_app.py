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

df['publish_date'] = pd.to_datetime(df['publish_date'])

# Build and display the framing-over-time chart.
chart = make_framing_over_time_chart(df, score_cols)
st.plotly_chart(chart, use_container_width=True)
