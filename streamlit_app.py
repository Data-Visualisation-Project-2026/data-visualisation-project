from pathlib import Path
from html import escape
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from visualizations.embedded_visuals import (
    render_outlet_event_timeline_lab,
    render_us_outlet_event_timeline_lab,
)
from visualizations.embedded_network import render_media_clusters
from visualizations.framing_charts import (
    make_framing_over_time_chart,
    make_international_framing_chart,
    make_us_framing_band_chart,
    make_intl_framing_band_chart,
    make_stacked_dominant_framing_comparison_html,
)
from visualizations.text_analysis import (
    get_top_cluster_bigrams,
    make_cluster_bigram_charts,
    make_outlet_framing_heatmap,
    get_cluster_representative_articles,
    render_cluster_representative_articles_html,
)
from visualizations.dataset_overview import make_article_count_chart, make_gantt_chart, _load_data

# Set up the Streamlit page and main title.
st.set_page_config(layout='wide')

DATA_DIR = Path(__file__).resolve().parent / 'data'


CLUSTER_TEXT_COLORS = {
    0: '#7A5BA6',
    1: '#B65F6F',
    2: '#4E6FAE',
    3: '#2F7F7B',
    4: '#B88A3D',
}


CLUSTER_LABELS = {
    0: 'Cluster 0: The Mainstream Center',
    1: 'Cluster 1: The Dissident/Resistance Wing',
    2: 'Cluster 2: The Diplomatic/Humanitarian Focus',
    3: 'Cluster 3: The Economic Lens',
    4: 'Cluster 4: The Military/Right-Wing Faction',
}


def cluster_label_span(cluster_id: int) -> str:
    """Return a colored HTML span for a cluster label."""
    return (
        f'<span style="color:{CLUSTER_TEXT_COLORS[cluster_id]};font-weight:700;">'
        f'{CLUSTER_LABELS[cluster_id]}</span>'
    )


def color_cluster_mentions(text: str) -> str:
    """Color full cluster-label mentions in markdown/HTML text."""
    for cluster_id, label in CLUSTER_LABELS.items():
        text = text.replace(label, cluster_label_span(cluster_id))
    return text


def render_next_page_button(next_page: str):
    """Render a subtle next-page link that opens the next page at the top."""
    href = f'?page={quote_plus(next_page)}#top'
    st.markdown(
        f"""
        <div class="next-page-wrap">
          <a class="next-page-link" href="{href}" target="_self"
             onclick="try {{ window.parent.location.assign('{href}'); }} catch (e) {{ window.location.assign('{href}'); }} return false;">
             Next → {escape(next_page)}
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_navigation(pages: list[str], active_page: str):
    """Render top-level page navigation below the project author line."""
    nav_cols = st.columns([2.1, 2.3, 2.8, 2.5, 1.3], gap="small")
    for idx, nav_page in enumerate(pages):
        button_type = 'primary' if nav_page == active_page else 'secondary'
        if nav_cols[idx].button(
            nav_page,
            key=f'top_nav_{idx}',
            type=button_type,
            use_container_width=True,
        ):
            if nav_page != active_page:
                st.query_params['page'] = nav_page
                st.rerun()


@st.cache_data(show_spinner=False)
def load_us_framing_chart_data():
    """Load only columns needed for the main US framing charts."""
    return pd.read_parquet(
        DATA_DIR / 'iran_war_media_framing_scores_clustered.parquet',
        columns=['indexed_date', 'media_name', *score_cols],
        engine='fastparquet',
    )


@st.cache_data(show_spinner=False)
def load_bigram_article_data():
    """Load only article text and cluster labels needed for bigram analysis."""
    return pd.read_parquet(
        DATA_DIR / 'iran_war_media_framing_scores_clustered.parquet',
        columns=['article_text', 'article_cluster'],
        engine='fastparquet',
    )


@st.cache_data(show_spinner=False)
def load_representative_article_data():
    """Load only columns needed to choose and display representative articles."""
    return pd.read_parquet(
        DATA_DIR / 'iran_war_media_framing_scores_clustered.parquet',
        columns=['article_cluster', 'title', 'media_name', *score_cols],
        engine='fastparquet',
    )


@st.cache_data(show_spinner=False)
def load_outlet_heatmap_data():
    """Load only columns needed for the five-outlet heatmap."""
    return pd.read_parquet(
        DATA_DIR / 'iran_war_media_framing_scores2_clustered.parquet',
        columns=['media_name', *score_cols],
        engine='fastparquet',
    )


@st.cache_data(show_spinner=False)
def make_cluster_bigram_charts_cached():
    """Build cluster bigram charts once instead of on every page rerun."""
    cluster_palette_version = 'richer-reassigned-cluster-palette-v1'
    data = load_bigram_article_data()
    _ = cluster_palette_version
    top_bigrams = get_top_cluster_bigrams(data, top_n=10)
    return make_cluster_bigram_charts(top_bigrams)


@st.cache_data(show_spinner=False)
def get_cluster_representative_articles_cached(n=5):
    """Cache representative articles because Streamlit reruns on navigation."""
    cluster_palette_version = 'richer-reassigned-cluster-palette-v1'
    data = load_representative_article_data()
    _ = cluster_palette_version
    return get_cluster_representative_articles(data, n=n)


@st.cache_data(show_spinner=False)
def make_outlet_framing_heatmap_cached():
    """Cache the outlet heatmap figure for repeated Media Differences visits."""
    # Bump this local marker when the cached figure layout changes.
    heatmap_layout_version = 'square-muted-blue-v5'
    data = load_outlet_heatmap_data()
    _ = heatmap_layout_version
    return make_outlet_framing_heatmap(data)


@st.cache_data(show_spinner=False)
def make_dataset_overview_outputs_cached():
    """Cache Data & Methods data and figures across page visits."""
    cluster_palette_version = 'richer-reassigned-cluster-palette-v1'
    combined = _load_data()
    _ = cluster_palette_version
    dates = combined["date"].dropna()
    date_range = [
        (dates.min() - pd.Timedelta(days=2)).isoformat(),
        (dates.max() + pd.Timedelta(days=2)).isoformat(),
    ]
    return (
        date_range,
        make_article_count_chart(combined),
        make_gantt_chart(combined, date_range=date_range),
    )

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

    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none !important;
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

    .analysis-note {
        color: #777777 !important;
        font-family: 'Georgia', serif !important;
        font-size: 0.8rem !important;
        line-height: 1.55 !important;
        max-width: 680px;
    }

    /* Dimension labels in bullet lists */
    .dim-label {
        font-family: 'Roboto', sans-serif !important;
        font-weight: 400 !important;
        font-size: 1.0rem !important;
    }

    .project-author {
        color: #5d6f7e;
        font-size: 1rem;
        margin-top: -0.7rem;
        margin-bottom: 2.2rem;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) {
        align-items: flex-end !important;
        border-bottom: 1px solid #e0e0e0 !important;
        gap: 0 !important;
        margin-bottom: 2rem !important;
        overflow: visible !important;
        position: relative !important;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"])::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        width: 88.2%;
        height: 1px;
        box-shadow: 0 -6px 9px -4px rgba(0, 0, 0, 0.5);
        pointer-events: none;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) > div[data-testid="column"] {
        position: relative !important;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) > div[data-testid="column"]:nth-child(1) {
        z-index: 4 !important;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) > div[data-testid="column"]:nth-child(2) {
        z-index: 3 !important;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) > div[data-testid="column"]:nth-child(3) {
        z-index: 2 !important;
    }

    .stApp div[data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) > div[data-testid="column"]:nth-child(4) {
        z-index: 1 !important;
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
        background-color: #e6e6e6 !important;
        border-color: #bdbdbd !important;
        border-radius: 0 !important;
        box-shadow: 8px 0 8px -5px rgba(0, 0, 0, 0.42) !important;
        color: #263746 !important;
        justify-content: flex-start !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.98rem !important;
        margin-bottom: -1px !important;
        min-height: 3rem !important;
        padding: 0.8rem 0.9rem !important;
        text-align: left !important;
    }

    button[kind="primary"] p,
    button[data-testid="baseButton-primary"] p {
        color: #263746 !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.98rem !important;
        font-weight: 400 !important;
        line-height: 1 !important;
        max-width: none !important;
        text-align: left !important;
        width: 100% !important;
        white-space: nowrap !important;
    }

    button[kind="secondary"] {
        border: 1px solid #d9d9d9 !important;
        background: #ffffff !important;
        color: #5d6f7e !important;
        justify-content: flex-start !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.98rem !important;
        margin-bottom: -1px !important;
        padding: 0.8rem 0.9rem !important;
        min-height: 3rem !important;
        border-radius: 0 !important;
        box-shadow: 8px 0 8px -5px rgba(0, 0, 0, 0.42) !important;
        text-align: left !important;
    }

    button[kind="secondary"]:hover {
        border-color: #b7c4cf !important;
        color: #2f4a5f !important;
        background: #f5f5f5 !important;
    }

    [data-testid="column"] + [data-testid="column"] button[kind="primary"],
    [data-testid="column"] + [data-testid="column"] button[kind="secondary"] {
        border-left-width: 0 !important;
    }

    button[kind="secondary"] p {
        color: inherit !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.98rem !important;
        font-weight: 400 !important;
        line-height: 1 !important;
        max-width: none !important;
        text-align: left !important;
        width: 100% !important;
        white-space: nowrap !important;
    }

    a {
        color: #2f5f86;
    }

    .next-page-wrap {
        margin-top: 1.75rem;
        margin-bottom: 0.25rem;
    }

    .next-page-link {
        display: inline-block;
        border: 1px solid #d9d9d9;
        background: #ffffff;
        color: #5d6f7e !important;
        font-family: 'Roboto', sans-serif !important;
        font-size: 0.88rem !important;
        padding: 0.35rem 0.9rem;
        border-radius: 999px;
        text-decoration: none !important;
        box-shadow: none;
        transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
    }

    .next-page-link:hover {
        border-color: #b7c4cf;
        color: #2f4a5f !important;
        background: #ffffff;
        text-decoration: none !important;
    }

    /* ── Dimension toggle pills ────────────────────────────────────────────
       Streamlit 1.45.x uses data-testid="stBaseButton-pills" (unselected)
       and data-testid="stBaseButton-pillsActive" (selected).               */
    .stApp [data-testid="stBaseButton-pills"],
    .stApp [data-testid="stBaseButton-pillsActive"] {
        border-radius: 4px !important;
        font-size: 11px !important;
        font-family: 'Roboto', sans-serif !important;
        font-weight: 400 !important;
        padding: 4px 10px !important;
        min-height: 0 !important;
        height: auto !important;
        line-height: 1 !important;
        border-width: 1.5px !important;
        border-style: solid !important;
        transition: background 0.15s, color 0.15s !important;
        box-shadow: none !important;
    }
    .stApp [data-testid="stBaseButton-pills"]       { background: #ffffff !important; }
    .stApp [data-testid="stBaseButton-pillsActive"] { color: #ffffff !important; }
    .stApp [data-testid="stBaseButton-pills"] *,
    .stApp [data-testid="stBaseButton-pillsActive"] * {
        font-family: 'Roboto', sans-serif !important;
        font-size: 11px !important;
        font-weight: 400 !important;
        line-height: 1 !important;
        color: inherit !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Inject JS via zero-height iframe to style st.pills using inline styles.
# CSS selectors can't reliably override Streamlit's Emotion CSS-in-JS at runtime,
# but inline styles set via JS always win.
components.html("""
<script>
(function () {
  // Streamlit 1.45.x: pill kind="pills" -> data-testid="stBaseButton-pills" (unselected)
  //                   kind="pillsActive" -> data-testid="stBaseButton-pillsActive" (selected)
  const COLORS = ['#E15759', '#4E79A7', '#59A14F', '#76B7B2', '#F28E2B'];

  function stylePill(btn, color, selected) {
    const s = btn.style;
    s.setProperty('border-radius',  '4px',                           'important');
    s.setProperty('font-size',      '11px',                          'important');
    s.setProperty('font-family',    '"Roboto", sans-serif',           'important');
    s.setProperty('font-weight',    '400',                           'important');
    s.setProperty('padding',        '4px 10px',                      'important');
    s.setProperty('min-height',     '0',                             'important');
    s.setProperty('height',         'auto',                          'important');
    s.setProperty('line-height',    '1',                             'important');
    s.setProperty('border',         '1.5px solid ' + color,          'important');
    s.setProperty('box-shadow',     'none',                          'important');
    s.setProperty('cursor',         'pointer',                       'important');
    s.setProperty('transition',     'background 0.15s, color 0.15s', 'important');
    const textColor = selected ? '#ffffff' : color;
    if (selected) {
      s.setProperty('background', color, 'important');
    } else {
      s.setProperty('background', '#ffffff', 'important');
    }
    s.setProperty('color', textColor, 'important');
    btn.querySelectorAll('*').forEach(function(child) {
      child.style.setProperty('font-family', '"Roboto", sans-serif', 'important');
      child.style.setProperty('font-size', '11px', 'important');
      child.style.setProperty('font-weight', '400', 'important');
      child.style.setProperty('line-height', '1', 'important');
      child.style.setProperty('color', textColor, 'important');
    });
  }

  function applyAll() {
    try {
      const doc = window.parent.document;
      // Collect all pill buttons across all st.pills widgets on the page
      const all = [...doc.querySelectorAll('[data-testid^="stBaseButton-pills"]')];

      // Group by immediate parent container (one parent = one st.pills widget)
      const groups = new Map();
      all.forEach(function(btn) {
        const p = btn.parentElement;
        if (!groups.has(p)) groups.set(p, []);
        groups.get(p).push(btn);
      });

      groups.forEach(function(btns) {
        // Sort by DOM position within the parent
        btns.sort(function(a, b) {
          return a.compareDocumentPosition(b) & 4 ? -1 : 1;
        });
        btns.forEach(function(btn, i) {
          const selected = btn.getAttribute('data-testid') === 'stBaseButton-pillsActive';
          stylePill(btn, COLORS[i] || '#666', selected);
        });
      });
    } catch(e) {}
  }

  try {
    const obs = new MutationObserver(applyAll);
    obs.observe(window.parent.document.body, {
      subtree: true, childList: true,
      attributes: true, attributeFilter: ['data-testid']
    });
  } catch(e) {}

  applyAll();
  setTimeout(applyAll, 400);
  setTimeout(applyAll, 1200);
})();
</script>
""", height=0, scrolling=False)

pages = ['Media framing', 'Media Clusters', 'Media Differences', 'Data & Methods']
query_page = st.query_params.get('page')
if isinstance(query_page, list):
    query_page = query_page[0] if query_page else None
page = query_page if query_page in pages else pages[0]
if query_page != page:
    st.query_params['page'] = page

st.title('Media Framing of the 2026 Iran War')
st.markdown('<div id="top"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="project-author">By Adeline Setiawan, Maximilian Chelminski, and Yixiao Liu</div>',
    unsafe_allow_html=True
)
render_top_navigation(pages, page)

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

dimension_order = [
    'Culpability Bias',
    'Kinetic',
    'Economic',
    'Diplomatic',
    'Humanitarian'
]

if page == 'Media framing':
    with st.spinner('Loading framing data...'):
        df = load_us_framing_chart_data()
        df = df.copy()
        df['publish_date'] = pd.to_datetime(df['indexed_date'])

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
    us_selected_lab = st.pills('', options=dimension_order, default=dimension_order, selection_mode='multi', key='lab_us_dims', label_visibility='collapsed')
    us_chart_lab = make_framing_over_time_chart(df, score_cols, score_labels, us_selected_lab or dimension_order)
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
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What US media outlets focused on most:</h1>', unsafe_allow_html=True)
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
    intl_selected_lab = st.pills('', options=dimension_order, default=dimension_order, selection_mode='multi', key='lab_intl_dims', label_visibility='collapsed')
    intl_chart_lab = make_international_framing_chart('iran-war-framing/data/timeline.json', intl_selected_lab or dimension_order)
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
    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">What non-US media outlets focused on most</h1>', unsafe_allow_html=True)
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

    st.divider()

    st.markdown('<h1 style="font-family:Georgia,serif; font-weight:bold; color:#1a1a1a;">Dominant framing moments, side by side</h1>', unsafe_allow_html=True)
    st.write(
        'This compact view stacks the daily dominant framing bars for US and non-US outlets. '
        'Hover near the event tick marks to compare which frame led each media group at the same moment.'
    )
    stacked_comparison_html = make_stacked_dominant_framing_comparison_html(
        df,
        score_cols,
        'iran-war-framing/data/timeline.json',
        'iran-war-framing/data/events.json',
        'iran-war-framing/data/us_event_cluster_articles.json',
        'iran-war-framing/data/event_cluster_articles.json',
    )
    components.html(stacked_comparison_html, height=720, scrolling=True)

    render_next_page_button('Media Clusters')

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

    st.markdown(
        color_cluster_mentions(Path('network_analysis/networkvis_interpretation.md').read_text()),
        unsafe_allow_html=True,
    )

    render_next_page_button('Media Differences')

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
    with st.spinner('Loading cluster language charts...'):
        bigram_charts = make_cluster_bigram_charts_cached()

    chart_items = list(bigram_charts.items())

    for row_start in range(0, len(chart_items), 2):
        columns = st.columns(2)

        for column, (_, chart) in zip(columns, chart_items[row_start:row_start + 2]):
            with column:
                st.plotly_chart(chart, use_container_width=True)

    st.markdown(
        f"""
        These unique phrases show what each media cluster tends to bring into focus.

        - {cluster_label_span(0)} reads like broad general coverage. It touches regional conflict through phrases like “southern Lebanon” and “backed Hezbollah,” but also brings in oil and energy through phrases like “million barrels” and “Brent crude.” This makes the cluster feel wide-ranging rather than driven by one clear storyline.

        - {cluster_label_span(1)} focuses strongly on military harm and U.S. involvement. Phrases like “troops killed,” “killed injured,” and “American forces” make the costs of military action more visible. Compared with Cluster 0, this cluster feels more focused on consequence and responsibility.

        - {cluster_label_span(2)} is the least centered on one clear war theme. Phrases such as “religious freedom,” “Iranian hackers,” and “early elections” suggest that these outlets often connect the war to wider political, social, and security issues.

        - {cluster_label_span(3)} has the clearest angle. Phrases like “Brent crude,” “barrels oil,” “Dow Jones,” and “Nasdaq composite” show that this cluster mainly treats the war as an oil, energy, and market-risk story.

        - {cluster_label_span(4)} makes the war more personal and military-centered. Names and places like “Declan Coady,” “Noah Tietjens,” and “West Moines” point to coverage of U.S. service members killed in the conflict, while phrases like “American forces” and “army reserve” keep the focus on military service and sacrifice.

        Overall, the phrases make the cluster differences easier to feel: some outlets turn the war into a market story, some into a military-cost story, and some into a broader political event.

        
        <div class="analysis-note"><em>Note: these phrases do not reveal what caused the LLM to assign specific framing scores since the LLM's reasoning is a black box. The bigram analysis is a separate NLP step which identifies vocabulary statistically distinctive to each cluster, serving as cross-validation of the cluster labels. Some clusters, particularly Clusters 2 and 4, surface proper nouns and publication-specific boilerplate (e.g. "Noah Tietjens," "legal notices") rather than genuine framing signals. This is a known limitation of c-TF-IDF when a cluster is dominated by a small number of outlets with distinctive writing styles.</em></div>

        ---
        """,
        unsafe_allow_html=True,
    )
    

    st.subheader('Representative Articles by Media Cluster')
    st.write(
        'These examples are the articles closest to each cluster centroid, based on the five framing scores.'
    )
    with st.spinner('Loading representative articles...'):
        representative_articles = get_cluster_representative_articles_cached(n=5)
    st.markdown(
        render_cluster_representative_articles_html(representative_articles),
        unsafe_allow_html=True,
    )

    st.subheader('How Framing Differs Across Major Media Outlets')
    st.caption('Based on 1,736 articles from 5 major media outlets')
    
    st.plotly_chart(make_outlet_framing_heatmap_cached(), use_container_width=False)

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

    render_next_page_button('Data & Methods')

elif page == 'Data & Methods':
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
    with st.spinner('Loading dataset overview...'):
        date_range, article_count_chart, gantt_chart = make_dataset_overview_outputs_cached()

    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # ── Split methodology at two seams ───────────────────────────────────────
    methodology = Path('methodology.md').read_text()
    before_extraction, from_extraction = methodology.split('#### Article Extraction', 1)
    extraction_body, after_extraction  = from_extraction.split('#### AI Scoring and Dimensionality', 1)

    # Data Preparation header (just the ### line)
    st.markdown(before_extraction)

    # Articles per outlet chart — between "Data Preparation" and "Article Extraction"
    st.plotly_chart(article_count_chart, use_container_width=True)

    # Article Extraction text
    st.markdown('#### Article Extraction' + extraction_body)

    # Coverage window chart — after Article Extraction, before AI Scoring
    st.plotly_chart(gantt_chart, use_container_width=True)

    # Rest of methodology
    st.markdown('#### AI Scoring and Dimensionality' + after_extraction)
