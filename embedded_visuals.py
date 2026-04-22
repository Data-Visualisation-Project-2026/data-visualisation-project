import json
import re
from pathlib import Path

import streamlit.components.v1 as components


def render_outlet_event_timeline():
    """Render the outlet event timeline inside the Streamlit app."""
    html = _build_outlet_event_timeline_html()
    components.html(html, height=1700, scrolling=True)


def _build_outlet_event_timeline_html():
    """Build a self-contained HTML version of the outlet event timeline."""
    base_dir = Path('iran-war-framing')

    index_html = (base_dir / 'index.html').read_text()
    style_css = (base_dir / 'style.css').read_text()
    main_js = (base_dir / 'js' / 'main.js').read_text()

    timeline = _load_json_for_script(base_dir / 'data' / 'timeline.json')
    events = _load_json_for_script(base_dir / 'data' / 'events.json')
    meta = _load_json_for_script(base_dir / 'data' / 'meta.json')

    # Keep the original body markup but remove script tags that rely on local paths.
    body_match = re.search(r'<body>(.*)</body>', index_html, flags=re.DOTALL)
    body_html = body_match.group(1) if body_match else index_html
    body_html = re.sub(r'<script\b[^>]*>.*?</script>', '', body_html, flags=re.DOTALL)

    # Replace local fetch calls with embedded JSON data for the Streamlit iframe.
    fetch_block = """const [timeline, events, meta] = await Promise.all([
    fetch("data/timeline.json").then(res => res.json()),
    fetch("data/events.json").then(res => res.json()),
    fetch("data/meta.json").then(res => res.json()),
]);"""

    embedded_data = f"""const timeline = {timeline};
    const events = {events};
    const meta = {meta};"""

    main_js = main_js.replace(fetch_block, embedded_data)
    main_js = main_js.replace(
        'const VH = window.innerHeight;',
        'const VH = 650;'
    )
    main_js = re.sub(
        r'// ── GSAP horizontal scroll.*?gsap\.to\("#timeline-track", \{.*?\n\s*\}\);',
        '',
        main_js,
        flags=re.DOTALL
    )

    # Preserve the visual style while using a reliable vertical layout in Streamlit.
    embedded_css = """
body {
    min-height: 1600px;
}

#intro {
    height: 430px !important;
    min-height: 430px !important;
}

#timeline-section,
#timeline-inner {
    height: 650px !important;
    min-height: 650px !important;
    position: relative !important;
    top: auto !important;
    display: block !important;
}

#timeline-section {
    overflow-x: auto !important;
    overflow-y: hidden !important;
}

#timeline-inner {
    overflow: visible !important;
}

#timeline-track {
    transform: none !important;
}

#outro {
    height: 430px !important;
    min-height: 430px !important;
}
"""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Outlet Event Timeline</title>
    <style>{style_css}</style>
    <style>{embedded_css}</style>
</head>
<body>
{body_html}
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js"></script>
<script>{main_js}</script>
</body>
</html>
"""


def _load_json_for_script(path):
    """Load JSON and escape it for safe use inside a script tag."""
    data = json.loads(path.read_text())
    return json.dumps(data).replace('</', '<\\/')
