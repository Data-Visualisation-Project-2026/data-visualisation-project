import re
from pathlib import Path

import streamlit.components.v1 as components


def render_media_clusters():
    """Render the self-contained media cluster network HTML inside Streamlit."""
    html = Path('media_cluster_3d_pca.html').read_text(encoding='utf-8')
    html = _build_media_clusters_html(html)
    components.html(html, height=950, scrolling=False)


def _build_media_clusters_html(html):
    """Patch the exported Plotly HTML so the graph fills a taller embed area."""
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
  height: 950px;
}

.plotly-graph-div {
  width: 100% !important;
  height: 950px !important;
}
</style>
"""

    relayout_script = ""
    if graph_id:
        relayout_script = f"""
<script>
window.addEventListener('load', function () {{
  const gd = document.getElementById('{graph_id}');
  if (gd && window.Plotly) {{
    Plotly.relayout(gd, {{
      height: 950
    }});
  }}
}});
</script>
"""

    html = html.replace('</head>', f'{iframe_css}</head>', 1)
    html = html.replace('</body>', f'{relayout_script}</body>', 1)

    return html
