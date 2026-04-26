from pathlib import Path

import pandas as pd
import streamlit as st

from visualizations.embedded_visuals import render_outlet_event_timeline, render_us_outlet_event_timeline
from visualizations.embedded_network import render_media_clusters
from visualizations.framing_charts import make_framing_over_time_chart, make_international_framing_chart, make_combined_aggregate_chart, make_us_framing_band_chart, make_intl_framing_band_chart
from visualizations.text_analysis import (
    get_top_cluster_bigrams,
    make_cluster_bigram_charts,
    make_outlet_framing_heatmap,
)
from visualizations.dataset_overview import make_article_count_chart, make_gantt_chart, _load_data

# Set up the Streamlit page and main title.
st.set_page_config(layout='wide')

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;600&display=swap');

    :root {
        --primary-color: #2f4a5f;
    }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        font-family: 'Georgia', serif !important;
    }

    .stApp {
        color: #263746;
    }

    /* Main title */
    .stApp h1 {
        font-family: 'Georgia', serif !important;
        font-size: clamp(2rem, 5vw, 4rem) !important;
        font-weight: bold !important;
        line-height: 1.1 !important;
        color: #1a1a1a !important;
        margin-bottom: 1.2rem !important;
    }

    /* Subheaders */
    .stApp h2 {
        font-family: 'Georgia', serif !important;
        font-weight: normal !important;
        color: #1a1a1a !important;
    }

    .stApp h3, .stApp h4 {
        font-family: 'Georgia', serif !important;
        font-weight: bold !important;
        color: #1a1a1a !important;
    }

    /* Body / paragraph text */
    .stApp p, .stMarkdown p, .stMarkdown li {
        font-family: 'Georgia', serif !important;
        font-size: 1.05rem !important;
        color: #555555 !important;
        line-height: 1.7 !important;
        max-width: 680px;
    }

    /* Dimension labels in bullet lists */
    .dim-label {
        font-family: 'Roboto', sans-serif !important;
        font-weight: 600 !important;
        font-size: 1.0rem !important;
    }

    [data-testid="stSidebar"] {
        background: #f2f2f2;
        border-right: 1px solid #d9d9d9;
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
        background: #ffffff;
        border: 1px solid #d9d9d9;
        border-radius: 8px;
        color: #2f4a5f;
        font-size: 1.02rem;
        font-weight: 600;
        margin-bottom: 0.7rem;
        padding: 0.8rem 0.85rem;
        transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #ffffff;
        border-color: #aaaaaa;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
    }

    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #ffffff;
        border-color: #2f4a5f;
        border-left: 4px solid #2f4a5f;
        color: #1a1a1a;
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

    /* Search / select input background and font */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {
        background-color: #f2f2f2 !important;
        border-color: #d9d9d9 !important;
    }

    [data-testid="stMultiSelect"] label,
    [data-testid="stMultiSelect"] span,
    [data-testid="stMultiSelect"] div,
    [data-testid="stMultiSelect"] input,
    [data-testid="stMultiSelect"] p,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] span,
    div[data-baseweb="popover"] div {
        font-family: 'Roboto', sans-serif !important;
    }

    /* Tags */
    div[data-baseweb="select"] div[data-baseweb="tag"],
    div[data-baseweb="popover"] div[data-baseweb="tag"],
    span[data-baseweb="tag"] {
        background: #e0e0e0 !important;
        background-color: #e0e0e0 !important;
        border-color: #cccccc !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] span,
    div[data-baseweb="popover"] div[data-baseweb="tag"] span,
    span[data-baseweb="tag"] span {
        color: #1a1a1a !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] svg,
    div[data-baseweb="popover"] div[data-baseweb="tag"] svg,
    span[data-baseweb="tag"] svg {
        color: #555555 !important;
        fill: #555555 !important;
    }

    div[data-baseweb="select"] div[data-baseweb="tag"] path,
    div[data-baseweb="popover"] div[data-baseweb="tag"] path,
    span[data-baseweb="tag"] path {
        fill: #555555 !important;
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
    ['Overview', 'Narrative Over Time', 'Story Arc', 'Media Clusters', 'Media Differences', 'Data & Methods'],
    label_visibility='collapsed',
    key='main_navigation_v4'
)

if page == 'Overview':
    # Intro section for the project overview page.
    st.markdown(
        """
        This project explores how media outlets framed the 2026 Iran War across time, media sources, and narrative dimensions. We analyze how coverage varies across five framing dimensions:
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <ul style="line-height:2.0; max-width:680px; font-family:'Roboto',sans-serif; font-size:1.0rem; color:#555;">
          <li><span class="dim-label" style="color:#4E79A7;">Kinetic Focus:</span> emphasis on military action, strikes, weapons, and strategy.</li>
          <li><span class="dim-label" style="color:#F28E2B;">Humanitarian Focus:</span> emphasis on civilian suffering, refugees, and casualties.</li>
          <li><span class="dim-label" style="color:#76B7B2;">Diplomatic Focus:</span> emphasis on negotiations, international organizations, and political responses.</li>
          <li><span class="dim-label" style="color:#59A14F;">Economic Focus:</span> emphasis on oil, trade, markets, and broader economic effects.</li>
          <li><span class="dim-label" style="color:#E15759;">Culpability Bias:</span> the extent to which coverage uses strong or active language to assign blame.</li>
        </ul>
        """,
        unsafe_allow_html=True
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
    st.subheader('US Media vs. International Wire Services')
    st.caption('Comparing aggregate framing across two distinct media universes')

    st.markdown('**77 US Outlets** — domestic media aggregate')
    highlighted_us = st.multiselect(
        'Highlight dimensions (US):',
        options=dimension_order,
        default=dimension_order,
        key='us_dimension_selector'
    )
    us_chart = make_framing_over_time_chart(df, score_cols, score_labels, highlighted_us)
    us_chart.update_layout(height=380, margin={'l': 40, 'r': 140, 't': 40, 'b': 50})
    st.plotly_chart(us_chart, use_container_width=True)

    st.markdown('**AP, Reuters, BBC, Al Jazeera** — international wire aggregate')
    highlighted_intl = st.multiselect(
        'Highlight dimensions (International):',
        options=dimension_order,
        default=dimension_order,
        key='intl_dimension_selector'
    )
    intl_chart = make_international_framing_chart(
        'iran-war-framing/data/timeline.json', highlighted_intl
    )
    st.plotly_chart(intl_chart, use_container_width=True)

    st.divider()
    st.markdown('**Individual outlet breakdown** — scroll to follow where the four outlets diverged')
    render_outlet_event_timeline()

elif page == 'Story Arc':
    st.markdown(
        """
        This project explores how media outlets framed the 2026 Iran War across time, media sources, and narrative dimensions. We analyze how coverage varies across five framing dimensions:
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        """
        <ul style="line-height:2.0; max-width:680px; font-family:'Roboto',sans-serif; font-size:1.0rem; color:#555;">
          <li><span class="dim-label" style="color:#4E79A7;">Kinetic Focus:</span> emphasis on military action, strikes, weapons, and strategy.</li>
          <li><span class="dim-label" style="color:#F28E2B;">Humanitarian Focus:</span> emphasis on civilian suffering, refugees, and casualties.</li>
          <li><span class="dim-label" style="color:#76B7B2;">Diplomatic Focus:</span> emphasis on negotiations, international organizations, and political responses.</li>
          <li><span class="dim-label" style="color:#59A14F;">Economic Focus:</span> emphasis on oil, trade, markets, and broader economic effects.</li>
          <li><span class="dim-label" style="color:#E15759;">Culpability Bias:</span> the extent to which coverage uses strong or active language to assign blame.</li>
        </ul>
        """,
        unsafe_allow_html=True
    )

    # ── US aggregate chart ───────────────────────────────────────────────────
    st.subheader('77 US Outlets — Domestic Media')
    st.caption('Feb 27–Apr 20, 2026 · average framing score across 77 US outlets')
    us_chart = make_framing_over_time_chart(df, score_cols, score_labels, dimension_order)
    st.plotly_chart(us_chart, use_container_width=True)

    # ── US framing band ──────────────────────────────────────────────────────
    band_chart = make_us_framing_band_chart(df, score_cols)
    st.plotly_chart(band_chart, use_container_width=True, config={'displayModeBar': False}, key='us_band_aggregate')
    st.markdown(
        '<p style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0;">Dominant framing per day — US outlets</p>',
        unsafe_allow_html=True
    )

    # ── US individual outlet D3 breakdown ────────────────────────────────────
    st.subheader('US Outlets — Individual Breakdown')
    st.caption('Feb 27–Mar 30, 2026 · NYT, Fox News, CNN, Bloomberg, NPR, Breitbart, NBC News, USA Today')
    render_us_outlet_event_timeline()

    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # ── International aggregate chart ────────────────────────────────────────
    st.subheader('AP · Reuters · BBC · Al Jazeera — International Wire Services')
    st.caption('Feb 27–Apr 20, 2026 · average framing score across 4 international outlets')
    intl_chart = make_international_framing_chart('iran-war-framing/data/timeline.json', dimension_order)
    st.plotly_chart(intl_chart, use_container_width=True)

    # ── INTL framing band ────────────────────────────────────────────────────
    intl_band = make_intl_framing_band_chart('iran-war-framing/data/timeline.json')
    st.plotly_chart(intl_band, use_container_width=True, config={'displayModeBar': False}, key='intl_band_aggregate')
    st.markdown(
        '<p style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0;">Dominant framing per day — international outlets</p>',
        unsafe_allow_html=True
    )

    # ── INTL individual outlet D3 breakdown ──────────────────────────────────
    st.subheader('International Wire Services — Individual Breakdown')
    st.caption('Mar 1–Apr 20, 2026 · AP News, Reuters, BBC, Al Jazeera')
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

    st.markdown(
        """
        This chart compares five major outlets across different media contexts and audiences. The key question is: **Did different outlets tell the same war story in the same way?**

        The answer is no. The heatmap shows clear differences in what each outlet brings to the front.

        - **Reuters and BBC** put the strongest weight on economic framing. Their coverage makes the war look especially important as a global market and policy event.
        - **Tehran Times** stands out for culpability framing. Its coverage is more centered on blame, responsibility, and moral judgment.
        - **Al Jazeera** has high scores across several dimensions, especially culpability, military action, and diplomacy. This makes its coverage feel more politically and conflict-focused.
        - **AP News** appears more moderate across the five dimensions, without one frame dominating as strongly.
        - **Humanitarian framing is relatively low across all outlets**, which means civilian suffering is not the main lens in this sample, even though it is still part of the war story.

        In short, the Iran War was not presented as one shared narrative. Across these outlets, the war becomes a different story depending on which frame is pushed forward: a market shock, a political conflict, a question of blame, or a military crisis. The most striking point is that civilian harm appears less central than these broader political and economic angles.
        """
    )

elif page == 'Data & Methods':
    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:0.5rem 0 1.5rem 0;">', unsafe_allow_html=True)

    # ── Dataset stats ────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="display:flex;gap:64px;margin-bottom:28px;flex-wrap:wrap;align-items:baseline;">
          <div>
            <div style="font-size:2rem;font-weight:700;color:#263746;font-family:Georgia,'Times New Roman',serif;">82</div>
            <div style="font-size:0.78rem;color:#5a7185;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;font-family:'Roboto',sans-serif;">Outlets</div>
          </div>
          <div>
            <div style="font-size:2rem;font-weight:700;color:#263746;font-family:Georgia,'Times New Roman',serif;">2,867</div>
            <div style="font-size:0.78rem;color:#5a7185;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;font-family:'Roboto',sans-serif;">Articles</div>
          </div>
          <div>
            <div style="font-size:2rem;font-weight:700;color:#263746;font-family:Georgia,'Times New Roman',serif;">76</div>
            <div style="font-size:0.78rem;color:#5a7185;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;font-family:'Roboto',sans-serif;">US outlets</div>
          </div>
          <div>
            <div style="font-size:2rem;font-weight:700;color:#263746;font-family:Georgia,'Times New Roman',serif;">6</div>
            <div style="font-size:0.78rem;color:#5a7185;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;font-family:'Roboto',sans-serif;">Non-US outlets</div>
          </div>
          <div>
            <div style="font-size:2rem;font-weight:700;color:#263746;font-family:Georgia,'Times New Roman',serif;">Feb 27 – Apr 20</div>
            <div style="font-size:0.78rem;color:#5a7185;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;font-family:'Roboto',sans-serif;">Date range</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load data + shared date range ────────────────────────────────────────
    combined = _load_data()
    dates = combined["date"].dropna()
    import pandas as _pd
    date_range = [
        (dates.min() - _pd.Timedelta(days=2)).isoformat(),
        (dates.max() + _pd.Timedelta(days=2)).isoformat(),
    ]

    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # ── Split methodology at two seams ───────────────────────────────────────
    methodology = Path('methodology.md').read_text()
    before_extraction, from_extraction = methodology.split('#### Article Extraction', 1)
    extraction_body, after_extraction  = from_extraction.split('#### AI Scoring and Dimensionality', 1)

    # Data Preparation header (just the ### line)
    st.markdown(before_extraction)

    # Articles per outlet chart — between "Data Preparation" and "Article Extraction"
    st.plotly_chart(make_article_count_chart(combined), use_container_width=True)

    # Article Extraction text
    st.markdown('#### Article Extraction' + extraction_body)

    # Coverage window chart — after Article Extraction, before AI Scoring
    st.plotly_chart(make_gantt_chart(combined, date_range=date_range), use_container_width=True)

    # Rest of methodology
    st.markdown('#### AI Scoring and Dimensionality' + after_extraction)
