import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def render_media_clusters():
    """Render the self-contained media cluster network HTML inside Streamlit."""
    components.html(_load_media_clusters_html(), height=850, scrolling=False)


@st.cache_data(show_spinner=False)
def _load_media_clusters_html():
    """Load and patch the exported network HTML once per session."""
    html = Path('network_analysis/media_cluster_3d_pca.html').read_text(encoding='utf-8')
    return _build_media_clusters_html(html)


def _build_media_clusters_html(html):
    """Patch the exported Plotly HTML so the graph fills the embed area cleanly."""
    graph_id_match = re.search(r'<div id="([^"]+)" class="plotly-graph-div"', html)
    graph_id = graph_id_match.group(1) if graph_id_match else None

    iframe_css = """
<style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: #0B1121;
}

body > div {
  height: 850px;
}

.plotly-graph-div {
  width: 100% !important;
  max-width: 100% !important;
  height: 850px !important;
}
</style>
"""

    relayout_script = ""
    if graph_id:
        relayout_script = f"""
<script>
function resizeEmbeddedPlot() {{
  const gd = document.getElementById('{graph_id}');
  if (gd && window.Plotly) {{
    const container = gd.parentElement;
    const width = container ? container.clientWidth : window.innerWidth;
    Plotly.relayout(gd, {{
      width: width,
      height: 850
    }});
    Plotly.Plots.resize(gd);
  }}
}}

window.addEventListener('load', resizeEmbeddedPlot);
window.addEventListener('resize', resizeEmbeddedPlot);
</script>
"""

    html = html.replace('</head>', f'{iframe_css}</head>', 1)
    html = html.replace('</body>', f'{relayout_script}</body>', 1)

    return html
