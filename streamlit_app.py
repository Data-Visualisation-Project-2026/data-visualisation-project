from pathlib import Path

import pandas as pd
import streamlit as st

from visualizations.embedded_visuals import (
    render_outlet_event_timeline,
    render_us_outlet_event_timeline,
    render_outlet_event_timeline_lab,
    render_us_outlet_event_timeline_lab,
)
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


def render_next_page_button(next_page: str, key: str):
    """Render a subtle next-page button that updates the sidebar navigation."""
    st.markdown('<div class="next-page-wrap">', unsafe_allow_html=True)
    if st.button(f'Next: {next_page} →', key=key, type='secondary'):
        st.session_state['pending_navigation_v5'] = next_page
        st.session_state['scroll_to_top_v1'] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
        min-width: 15rem !important;
        max-width: 17rem !important;
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

    button[kind="secondary"] {
        border: 1px solid #d9d9d9 !important;
        background: #ffffff !important;
        color: #5d6f7e !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.88rem !important;
        padding: 0.25rem 0.8rem !important;
        min-height: 2rem !important;
        border-radius: 999px !important;
        box-shadow: none !important;
    }

    button[kind="secondary"]:hover {
        border-color: #b7c4cf !important;
        color: #2f4a5f !important;
    }

    a {
        color: #2f5f86;
    }

    .next-page-wrap {
        margin-top: 1.75rem;
        margin-bottom: 0.25rem;
    }

    /* ── Dimension toggle pills — match D3 button style ─────────────────── */
    /* Base overrides — target by Streamlit's stable emotion class targets   */
    button[class*="eacrzsi13"],
    button[class*="eacrzsi14"] {
        border-radius: 4px !important;
        font-size: 11px !important;
        font-family: 'Roboto', sans-serif !important;
        padding: 4px 10px !important;
        min-height: unset !important;
        height: auto !important;
        line-height: 1.2 !important;
        border-width: 1.5px !important;
        border-style: solid !important;
        background: transparent !important;
        transition: background 0.15s, color 0.15s !important;
    }
    /* Per-dimension colors by child position within the pills flex container */
    /* Culpability Bias — 1st */
    button[class*="eacrzsi13"]:nth-child(1) { border-color: #E15759 !important; color: #E15759 !important; }
    button[class*="eacrzsi14"]:nth-child(1) { background: #E15759 !important; border-color: #E15759 !important; color: #fff !important; }
    /* Kinetic — 2nd */
    button[class*="eacrzsi13"]:nth-child(2) { border-color: #4E79A7 !important; color: #4E79A7 !important; }
    button[class*="eacrzsi14"]:nth-child(2) { background: #4E79A7 !important; border-color: #4E79A7 !important; color: #fff !important; }
    /* Economic — 3rd */
    button[class*="eacrzsi13"]:nth-child(3) { border-color: #59A14F !important; color: #59A14F !important; }
    button[class*="eacrzsi14"]:nth-child(3) { background: #59A14F !important; border-color: #59A14F !important; color: #fff !important; }
    /* Diplomatic — 4th */
    button[class*="eacrzsi13"]:nth-child(4) { border-color: #76B7B2 !important; color: #76B7B2 !important; }
    button[class*="eacrzsi14"]:nth-child(4) { background: #76B7B2 !important; border-color: #76B7B2 !important; color: #fff !important; }
    /* Humanitarian — 5th */
    button[class*="eacrzsi13"]:nth-child(5) { border-color: #F28E2B !important; color: #F28E2B !important; }
    button[class*="eacrzsi14"]:nth-child(5) { background: #F28E2B !important; border-color: #F28E2B !important; color: #fff !important; }
    </style>
    """,
    unsafe_allow_html=True
)


st.title('Media Framing of the 2026 Iran War')
st.markdown(
    '<div class="project-author">By Adeline Setiawan, Maximilian Chelminski, and Yixiao Liu</div>',
    unsafe_allow_html=True
)
st.divider()

if 'pending_navigation_v5' in st.session_state:
    st.session_state['main_navigation_v5'] = st.session_state.pop('pending_navigation_v5')

if st.session_state.pop('scroll_to_top_v1', False):
    st.markdown(
        """
        <script>
        window.scrollTo(0, 0);
        if (window.parent) {
            window.parent.scrollTo(0, 0);
        }
        </script>
        """,
        unsafe_allow_html=True,
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
    ['Story Arc', 'Story Arc (Lab)', 'Media Clusters', 'Media Differences', 'Data & Methods'],
    label_visibility='collapsed',
    key='main_navigation_v5'
)

if page == 'Story Arc':
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

    st.divider()

    # ── US aggregate chart ───────────────────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">How US media outlets framed the war</h1>', unsafe_allow_html=True)
    us_selected = st.pills('', options=dimension_order, default=dimension_order, selection_mode='multi', key='story_arc_us_dims', label_visibility='collapsed')
    us_chart = make_framing_over_time_chart(df, score_cols, score_labels, us_selected or dimension_order)
    st.plotly_chart(us_chart, use_container_width=True)

    # ── US framing band ──────────────────────────────────────────────────────
    band_chart = make_us_framing_band_chart(df, score_cols)
    st.plotly_chart(band_chart, use_container_width=True, config={'displayModeBar': False}, key='us_band_aggregate')
    st.markdown(
        '<div style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0; padding-left:55px;">Dominant framing per day — US outlets</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="padding-left:55px;">'
        '<p>The overall pattern suggests coverage was driven mainly by military action and responsibility/blame. '
        'Kinetic framing stayed high for much of the period, while Culpability Bias remained consistently prominent — '
        'many articles framed the war not only through what happened, but also through who was responsible. '
        'Humanitarian framing stayed lower overall, suggesting that civilian suffering and human impacts were '
        'present but less central in the aggregate coverage.</p>'
        '<p>Diplomatic framing was unusually high at the beginning, likely reflecting early attention to official '
        'statements, international reactions, and political responses — then dropped and stayed relatively low. '
        'Economic framing becomes more visible later, especially around moments linked to energy and regional escalation.</p>'
        '<p>Taken together, the five lines show that media framing was not fixed: as the war developed, coverage '
        'moved between military, political, economic, and blame-centered narratives.</p>'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # ── US individual outlet D3 breakdown ────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What US media outlets said about the war:</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding-left:55px;">'
        'Sources: NYT, Fox News, CNN, Bloomberg, NPR, Breitbart, NBC News, USA Today from Feb 27–Mar 30. '
        'American media differed in their individual framing of the war, converging and diverging notably at some moments. '
        'Use the dimension buttons below to switch between framing types, then scroll to follow where the outlets diverged.'
        '</div>',
        unsafe_allow_html=True
    )
    render_us_outlet_event_timeline()

    st.divider()

    # ── International aggregate chart ────────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">Average framing score across non-US media outlets</h1>', unsafe_allow_html=True)
    intl_selected = st.pills('', options=dimension_order, default=dimension_order, selection_mode='multi', key='story_arc_intl_dims', label_visibility='collapsed')
    intl_chart = make_international_framing_chart('iran-war-framing/data/timeline.json', intl_selected or dimension_order)
    st.plotly_chart(intl_chart, use_container_width=True)

    # ── INTL framing band ────────────────────────────────────────────────────
    intl_band = make_intl_framing_band_chart('iran-war-framing/data/timeline.json')
    st.plotly_chart(intl_band, use_container_width=True, config={'displayModeBar': False}, key='intl_band_aggregate')
    st.markdown(
        '<div style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0; padding-left:55px;">Dominant framing per day — international outlets</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # ── INTL individual outlet D3 breakdown ──────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What non-US media outlets said about the war</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding-left:55px;">'
        'The previous chart showed how American media collectively covered the 2026 Iran War. '
        'Here, four international and wire-service outlets — AP, Reuters, BBC, and Al Jazeera — '
        'tell the same story through very different lenses. '
        'Use the dimension buttons below to switch between framing types, then scroll to follow where the outlets diverged.'
        '</div>',
        unsafe_allow_html=True
    )
    render_outlet_event_timeline()

    render_next_page_button('Media Clusters', 'next_story_arc')

elif page == 'Story Arc (Lab)':
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

    st.divider()

    # ── US aggregate chart ───────────────────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">How US media outlets framed the war</h1>', unsafe_allow_html=True)
    us_chart_lab = make_framing_over_time_chart(df, score_cols, score_labels, dimension_order)
    st.plotly_chart(us_chart_lab, use_container_width=True)

    # ── US framing band ──────────────────────────────────────────────────────
    band_chart_lab = make_us_framing_band_chart(df, score_cols)
    st.plotly_chart(band_chart_lab, use_container_width=True, config={'displayModeBar': False}, key='us_band_lab')
    st.markdown(
        '<div style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0; padding-left:55px;">Dominant framing per day — US outlets</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="padding-left:55px;">'
        '<p>The overall pattern suggests coverage was driven mainly by military action and responsibility/blame. '
        'Kinetic framing stayed high for much of the period, while Culpability Bias remained consistently prominent — '
        'many articles framed the war not only through what happened, but also through who was responsible. '
        'Humanitarian framing stayed lower overall, suggesting that civilian suffering and human impacts were '
        'present but less central in the aggregate coverage.</p>'
        '<p>Diplomatic framing was unusually high at the beginning, likely reflecting early attention to official '
        'statements, international reactions, and political responses — then dropped and stayed relatively low. '
        'Economic framing becomes more visible later, especially around moments linked to energy and regional escalation.</p>'
        '<p>Taken together, the five lines show that media framing was not fixed: as the war developed, coverage '
        'moved between military, political, economic, and blame-centered narratives.</p>'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # ── US individual outlet D3 breakdown ────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What US media outlets said about the war:</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding-left:55px;">'
        'Sources: NYT, Fox News, CNN, Bloomberg, NPR, Breitbart, NBC News, USA Today from Feb 27–Mar 30. '
        'American media differed in their individual framing of the war, converging and diverging notably at some moments. '
        'Use the dimension buttons below to switch between framing types, then scroll to follow where the outlets diverged.'
        '</div>',
        unsafe_allow_html=True
    )
    render_us_outlet_event_timeline_lab()

    st.divider()

    # ── International aggregate chart ────────────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">Average framing score across non-US media outlets</h1>', unsafe_allow_html=True)
    intl_chart_lab = make_international_framing_chart('iran-war-framing/data/timeline.json', dimension_order)
    st.plotly_chart(intl_chart_lab, use_container_width=True)

    # ── INTL framing band ────────────────────────────────────────────────────
    intl_band_lab = make_intl_framing_band_chart('iran-war-framing/data/timeline.json')
    st.plotly_chart(intl_band_lab, use_container_width=True, config={'displayModeBar': False}, key='intl_band_lab')
    st.markdown(
        '<div style="font-family:\'Roboto\',sans-serif; font-size:0.72rem; color:#aaa; margin:0 0 1rem 0; padding-left:55px;">Dominant framing per day — international outlets</div>',
        unsafe_allow_html=True
    )

    st.divider()

    # ── INTL individual outlet D3 breakdown ──────────────────────────────────
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What non-US media outlets said about the war</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding-left:55px;">'
        'The previous chart showed how American media collectively covered the 2026 Iran War. '
        'Here, four international and wire-service outlets — AP, Reuters, BBC, and Al Jazeera — '
        'tell the same story through very different lenses. '
        'Use the dimension buttons below to switch between framing types, then scroll to follow where the outlets diverged.'
        '</div>',
        unsafe_allow_html=True
    )
    render_outlet_event_timeline_lab()

elif page == 'Media Clusters':
    st.markdown(
        """
        Framing changed over time, but it also differed across media outlets. Some outlets shared similar patterns across military, humanitarian, diplomatic, economic, and blame-centered coverage, forming clear media clusters.
        """
    )
    st.subheader('Media Clusters')
    st.write(
        'Outlets closer together in the network share more similar framing patterns. '
        'The five colors represent five media clusters.'
    )

    render_media_clusters()

    st.markdown(Path('network_analysis/networkvis_interpretation.md').read_text())

    render_next_page_button('Media Differences', 'next_media_clusters')

elif page == 'Media Differences':
    st.markdown(
        """
        Media differences become clearer when we look more closely. Beyond broad patterns, outlets also differed in the language they used and the parts of the war each of them emphasized.
        """
    )
    st.subheader('How Language Differs Across Media Clusters')
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

    st.markdown(
        """
        These unique phrases show what each media cluster tends to bring into focus.

        - **Cluster 0: Mainstream / Moderate** reads like broad general coverage. It touches regional conflict through phrases like “southern Lebanon” and “backed Hezbollah,” but also brings in oil and energy through phrases like “million barrels” and “Brent crude.” This makes the cluster feel wide-ranging rather than driven by one clear storyline.

        - **Cluster 1: Dissident / Left-Wing** focuses strongly on military harm and U.S. involvement. Phrases like “troops killed,” “killed injured,” and “American forces” make the costs of military action more visible. Compared with Cluster 0, this cluster feels more focused on consequence and responsibility.

        - **Cluster 2: Smaller Mainstream** is the least centered on one clear war theme. Phrases such as “religious freedom,” “Iranian hackers,” and “early elections” suggest that these outlets often connect the war to wider political, social, and security issues.

        - **Cluster 3: Business-Focused** has the clearest angle. Phrases like “Brent crude,” “barrels oil,” “Dow Jones,” and “Nasdaq composite” show that this cluster mainly treats the war as an oil, energy, and market-risk story.

        - **Cluster 4: Right-Wing / Military** makes the war more personal and military-centered. Names and places like “Declan Coady,” “Noah Tietjens,” and “West Moines” point to coverage of U.S. service members killed in the conflict, while phrases like “American forces” and “army reserve” keep the focus on military service and sacrifice.

        Overall, the phrases make the cluster differences easier to feel: some outlets turn the war into a market story, some into a military-cost story, and some into a broader political event.
        """
    )

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

    render_next_page_button('Data & Methods', 'next_media_differences')

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
