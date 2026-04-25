import json
import re
from pathlib import Path

import streamlit.components.v1 as components


def render_outlet_event_timeline():
    """Render the outlet event timeline inside the Streamlit app."""
    html = _build_outlet_event_timeline_html()
    # Height ~900px acts as the iframe viewport; content scrolls inside it.
    # Scrollbar is hidden via CSS but scrolling is active.
    components.html(html, height=700, scrolling=True)


def _build_outlet_event_timeline_html():
    """Build a self-contained HTML string with GSAP scroll experience intact."""
    base_dir = Path('iran-war-framing')

    index_html = (base_dir / 'index.html').read_text()
    style_css  = (base_dir / 'style.css').read_text()
    main_js    = (base_dir / 'js' / 'main.js').read_text()

    timeline = _load_json_for_script(base_dir / 'data' / 'timeline.json')
    events   = _load_json_for_script(base_dir / 'data' / 'events.json')
    meta     = _load_json_for_script(base_dir / 'data' / 'meta.json')

    # Strip script tags from the original HTML body; we re-add everything inline.
    body_match = re.search(r'<body>(.*)</body>', index_html, flags=re.DOTALL)
    body_html  = body_match.group(1) if body_match else index_html
    body_html  = re.sub(r'<script\b[^>]*>.*?</script>', '', body_html, flags=re.DOTALL)

    # Replace fetch() calls with inline JSON.
    # Use a lambda replacement so re.sub doesn't interpret \u sequences in JSON as regex escapes.
    inline_data = f'const timeline = {timeline};\n  const events = {events};\n  const meta = {meta};'
    main_js = re.sub(
        r'const \[timeline, events, meta\] = await Promise\.all\(\[.*?\]\);',
        lambda _: inline_data,
        main_js,
        flags=re.DOTALL,
    )



    # iframe-specific CSS — hides scrollbar, lets GSAP control layout.
    iframe_css = """
/* Hide scrollbar — scrolling still works, GSAP reads it */
html, body { background: #ffffff !important; }
html { scrollbar-width: none; overflow-y: scroll; }
::-webkit-scrollbar { display: none; }

/* Tighten intro/outro */
#intro  { height: 50vh; min-height: 50vh; }
#outro  { height: 50vh; min-height: 50vh; }

/* Let the page script control section height dynamically. */
#timeline-section {
  position: relative !important;
  overflow: visible !important;
  display: block !important;
}

/* Fixed viewport — stays locked while section scrolls behind it */
#timeline-inner {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100vh !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: center !important;
}

#timeline-track { will-change: transform; }
"""

    # Debug logs — help confirm GSAP has the right dimensions inside the iframe.
    height_fix = """
<script>
window.addEventListener('load', () => {
  console.log('VH:', window.innerHeight, 'innerWidth:', window.innerWidth);
  const ts = document.getElementById('timeline-section');
  const ti = document.getElementById('timeline-inner');
  const svg = document.getElementById('timeline-svg');
  console.log('timeline-section height:', ts ? ts.offsetHeight : 'not found');
  console.log('timeline-inner height:', ti ? ti.offsetHeight : 'not found');
  console.log('svg:', svg ? svg.getAttribute('width') + 'x' + svg.getAttribute('height') : 'not found');
  if (window.ScrollTrigger) {
    window.ScrollTrigger.refresh();
  }
});
</script>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Outlet Event Timeline</title>
  <style>{style_css}</style>
  <style>{iframe_css}</style>
</head>
<body>
{body_html}
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js"></script>
<script>{main_js}</script>
{height_fix}
</body>
</html>
"""


def _load_json_for_script(path: Path) -> str:
    """Load a JSON file and escape it for safe inline embedding in a <script> tag."""
    data = json.loads(path.read_text())
    return json.dumps(data).replace('</', '<\\/')
