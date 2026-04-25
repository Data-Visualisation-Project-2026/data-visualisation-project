from pathlib import Path

import streamlit.components.v1 as components


def render_media_clusters():
    """Render the self-contained media cluster network HTML inside Streamlit."""
    html = Path('media_cluster_3d_pca.html').read_text(encoding='utf-8')
    components.html(html, height=1200, scrolling=False)
