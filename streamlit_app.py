import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(layout='wide')

st.title('Media Framing of the 2026 Iran War')

df = pd.read_parquet('iran_war_media_framing_scores.parquet', engine='pyarrow')

score_cols = [
    'kinetic_focus',
    'humanitarian_focus',
    'diplomatic_focus',
    'economic_focus',
    'culpability_bias'
]

df['publish_date'] = pd.to_datetime(df['publish_date'])

daily = df.groupby('publish_date')[score_cols].mean().reset_index()

daily_long = daily.melt(
    id_vars='publish_date',
    value_vars=score_cols,
    var_name='dimension',
    value_name='average_score'
)

label_map = {
    'kinetic_focus': 'Kinetic',
    'humanitarian_focus': 'Humanitarian',
    'diplomatic_focus': 'Diplomatic',
    'economic_focus': 'Economic',
    'culpability_bias': 'Culpability Bias'
}
daily_long['dimension'] = daily_long['dimension'].map(label_map)

chart = alt.Chart(daily_long).mark_line(opacity=0.9).encode(
    x=alt.X(
        'publish_date:T',
        title='Date',
        axis=alt.Axis(
            format='%b %d',
            tickCount=6,
            labelAngle=0,
            grid=False
        )
    ),
    y=alt.Y(
        'average_score:Q',
        title='Average Score',
        axis=alt.Axis(
            tickCount=6,
            grid=False
        ),
        scale=alt.Scale(domain=[0.1, 0.7])
    ),
    color=alt.Color(
        'dimension:N',
        title='Dimension',
        legend=alt.Legend(
            orient='bottom',
            direction='horizontal',
            labelFontSize=12
        ),
        scale=alt.Scale(scheme='tableau10')
    )
).properties(
    height=400,
    title='Framing Scores Over Time'
)

st.altair_chart(chart, width='stretch')
