gsap.registerPlugin(ScrollTrigger);

(async () => {
    const [timeline, events, meta, usEvents, eventClusterArticles] = await Promise.all([
    fetch("data/timeline.json").then(res => res.json()),
    fetch("data/events.json").then(res => res.json()),
    fetch("data/meta.json").then(res => res.json()),
    fetch("data/us_events.json").then(res => res.json()).catch(() => []),
    fetch("data/event_cluster_articles.json").then(res => res.json()).catch(() => []),
]);

// Tracks which outlet lines are currently hidden (toggled off by the legend).
let hiddenOutlets = new Set();

// --- Dimension Setup ---
const MARGIN = { top: 112, right: 20, bottom: 76, left: 48 };
const VH = Math.round(window.innerHeight * 0.82);
const DAY_WIDTH = Math.ceil(window.innerWidth * 4 / timeline.length);
const chartH = VH - MARGIN.top - MARGIN.bottom;
const totalW = timeline.length * DAY_WIDTH;
const svgW = totalW + MARGIN.left + MARGIN.right;
const svgH = VH;

// --- Scale Setup ---
const parseDate = d3.timeParse("%Y-%m-%d");

const validDates = timeline.map(d => parseDate(d.date)).filter(d => d !== null);
const xScale = d3.scaleTime()
.domain([validDates[0], validDates[validDates.length - 1]])
.range([0, totalW]);

const yScale = d3.scaleLinear()
.domain([0, 1])
.range([chartH, 0]);

// -- SVG Setup ---
const svg = d3.select("#timeline-svg")
.attr("width", svgW)
.attr("height", svgH);

const g = svg.append("g")
.attr("transform", `translate(${MARGIN.left}, ${MARGIN.top})`);

// --- GRID LINES (every 2 weeks) ---
g.append("g")
.attr("class", "grid")
.attr("transform", `translate(0,${chartH})`)
.call(d3.axisBottom(xScale).ticks(d3.timeWeek.every(2)).tickSize(-chartH).tickFormat(""))
.call(ax => ax.select(".domain").remove())
.call(ax => ax.selectAll("line").attr("stroke", "#ebebeb").attr("stroke-dasharray", "3,3"));

// --- AXES ---
g.append("g")
.attr("transform", `translate(0, ${chartH})`)
.call(d3.axisBottom(xScale).ticks(d3.timeWeek.every(2)).tickFormat(d3.timeFormat("%b %d")))
.call(ax => ax.select(".domain").attr("stroke", "#ccc"))
.call(ax => ax.selectAll("text").attr("fill", "#555").attr("font-size", "11px").attr("dy", "1.2em"));

g.append("g")
.call(d3.axisLeft(yScale).ticks(5))
.call(ax => ax.select(".domain").remove())
.call(ax => ax.selectAll("line").attr("stroke", "#e0e0e0"))
.call(ax => ax.selectAll("text").attr("fill", "#555").attr("font-size", "11px").attr("dy", "1.2em"));

// --- LINES: ONE PER OUTLET, switchable by dimension ---
const line = d3.line()
    .x(d => xScale(parseDate(d.date)))
    .y(d => yScale(d.value))
    .defined(d => d.value != null)
    .curve(d3.curveCatmullRom.alpha(0.5));

let activeDim = "kinetic_focus";

const DIMS_ORDER = [
    "kinetic_focus",
    "humanitarian_focus",
    "diplomatic_focus",
    "economic_focus",
    "culpability_bias",
];
const DIM_DISPLAY = {
    kinetic_focus:      "Kinetic",
    humanitarian_focus: "Humanitarian",
    diplomatic_focus:   "Diplomatic",
    economic_focus:     "Economic",
    culpability_bias:   "Culpability",
};
const DIM_PALETTE = {
    kinetic_focus:      '#4E79A7',
    humanitarian_focus: '#F28E2B',
    diplomatic_focus:   '#76B7B2',
    economic_focus:     '#59A14F',
    culpability_bias:   '#E15759',
};

function drawLines(dim) {
    g.selectAll(".outlet-line").remove();
    meta.outlets.forEach(outlet => {
        if (hiddenOutlets.has(outlet)) return;
        const data = timeline
            .filter(d => parseDate(d.date) !== null && d.outlets[outlet])
            .map(d => ({ date: d.date, value: d.outlets[outlet][dim] }));
        g.append("path")
            .datum(data)
            .attr("class", "outlet-line")
            .attr("fill", "none")
            .attr("stroke", meta.outlet_colors[outlet])
            .attr("stroke-width", 2)
            .attr("opacity", 0.85)
            .attr("d", line);
    });
}
drawLines(activeDim);

// Dimension toggle buttons rendered into #dim-buttons (injected into the page)
const btnContainer = document.getElementById("dim-buttons");
if (btnContainer) {
    DIMS_ORDER.forEach(dim => {
        const btn = document.createElement("button");
        btn.textContent = DIM_DISPLAY[dim];
        btn.dataset.dim = dim;
        btn.style.cssText = [
            "margin:0 4px 0 0",
            "padding:4px 10px",
            "border-radius:4px",
            "border:1.5px solid " + DIM_PALETTE[dim],
            "background:" + (dim === activeDim ? DIM_PALETTE[dim] : "transparent"),
            "color:" + (dim === activeDim ? "#fff" : DIM_PALETTE[dim]),
            "font-size:11px",
            "font-family:Roboto,sans-serif",
            "cursor:pointer",
            "transition:background 0.15s,color 0.15s",
        ].join(";");
        btn.addEventListener("click", () => {
            activeDim = dim;
            drawLines(dim);
            btnContainer.querySelectorAll("button").forEach(b => {
                const d = b.dataset.dim;
                b.style.background = d === dim ? DIM_PALETTE[d] : "transparent";
                b.style.color      = d === dim ? "#fff"          : DIM_PALETTE[d];
            });
            rebuildCalloutCards();
        });
        btnContainer.appendChild(btn);
    });
}                                                                                                                                                                                  

// ── Framing bands — dominant dimension per day ────────────────────────────
const DIM_COLORS = {
    kinetic_focus:      '#4E79A7',
    humanitarian_focus: '#F28E2B',
    diplomatic_focus:   '#76B7B2',
    economic_focus:     '#59A14F',
    culpability_bias:   '#E15759',
};
const DIM_LABELS = {
    kinetic_focus:      'Kinetic',
    humanitarian_focus: 'Humanitarian',
    diplomatic_focus:   'Diplomatic',
    economic_focus:     'Economic',
    culpability_bias:   'Culpability',
};
const DIMS = Object.keys(DIM_COLORS);
const BAND_H = 36;
const BAND_GAP = 6;
const BAND_Y_INTL = -(BAND_H + 14);           // international band — closer to chart
const BAND_Y_US   = -(BAND_H * 2 + BAND_GAP + 14); // US band — above international

function drawBand(data, bandY, key) {
    g.append('rect')
        .attr('x', 0).attr('y', bandY)
        .attr('width', totalW).attr('height', BAND_H)
        .attr('fill', '#f9f9f9').attr('rx', 2);
    data.filter(d => d[key]).forEach((d, i) => {
        const x0 = xScale(d.date);
        const x1 = i < data.length - 1 ? xScale(data[i + 1].date) : x0 + DAY_WIDTH;
        g.append('rect')
            .attr('x', x0).attr('y', bandY)
            .attr('width', Math.max(1, x1 - x0)).attr('height', BAND_H)
            .attr('fill', DIM_COLORS[d[key]]).attr('opacity', 1);
    });
}

const allBandData = timeline
    .filter(d => parseDate(d.date) !== null)
    .map(d => ({ date: parseDate(d.date), us_dominant: d.us_dominant, intl_dominant: d.intl_dominant }));

// Draw only the bands listed in meta.bands (["us","intl"] or ["intl"])
const showBands = meta.bands || ['us', 'intl'];
const bandConfig = [
    { key: 'us_dominant',   bandY: BAND_Y_US,   label: 'US'   },
    { key: 'intl_dominant', bandY: BAND_Y_INTL, label: 'INTL' },
];
bandConfig.filter(b => showBands.includes(b.label.toLowerCase())).forEach(b => {
    drawBand(allBandData, b.bandY, b.key);
    g.append('text')
        .attr('x', -MARGIN.left + 4).attr('y', b.bandY + BAND_H / 2 + 4)
        .attr('fill', '#999').attr('font-size', '9px').attr('font-family', 'monospace')
        .text(b.label);
});

// Top of the uppermost visible band — event lines start here
const topBandY = showBands.includes('us') ? BAND_Y_US : BAND_Y_INTL;

// ── Event markers — run through bands and chart ───────────────────────────
events.forEach(event => {
    const x = xScale(parseDate(event.date));
    g.append("line")
        .attr("x1", x).attr("x2", x).attr("y1", topBandY).attr("y2", chartH)
        .attr("stroke", "#555").attr("stroke-width", 1)
        .attr("stroke-dasharray", "4,4").attr("opacity", 0.5);

    const parsedEvtDate = parseDate(event.date);
    const dateStr = d3.timeFormat("%b ")(parsedEvtDate) + parsedEvtDate.getDate();
    g.append("text")
        .attr("x", x + 6).attr("y", topBandY - 4).attr("fill", "#555")
        .attr("font-size", "10px").attr("font-family", "monospace")
        .text(`${dateStr}. ${event.label}`);
});                                                                                                                                                                                  
                                                                                                                                                                                         
// ── Horizontal scroll via position:fixed + scroll listener ───────────────
// #timeline-inner is position:fixed so it never moves vertically.
// #timeline-section is tall enough to scroll the full horizontal distance.
// We show the fixed panel only while scroll is within the section, and
// translate #timeline-track left proportionally to scroll progress.

const scrollDistance = totalW - window.innerWidth + MARGIN.left + MARGIN.right;

const timelineSection = document.getElementById('timeline-section');
const timelineInner   = document.getElementById('timeline-inner');
const track           = document.getElementById('timeline-track');

// Make section tall enough: one viewport of padding + full horizontal travel.
if (timelineSection) timelineSection.style.height = (window.innerHeight + scrollDistance) + 'px';

// Cache section offset — constant unless the page layout changes.
const sectionTop = timelineSection ? timelineSection.offsetTop : 0;

// ── Headline callout panel ─────────────────────────────────────────────────

const CALLOUT_LABELS = {
    'apnews.com':   'AP News',  'reuters.com':  'Reuters',
    'bbc.com':      'BBC',      'aljazeera.com':'Al Jazeera',
    'nytimes.com':  'NYT',      'foxnews.com':  'Fox News',
    'cnn.com':      'CNN',      'bloomberg.com':'Bloomberg',
    'npr.org':      'NPR',      'breitbart.com':'Breitbart',
    'nbcnews.com':  'NBC News', 'usatoday.com': 'USA Today',
};
const CALLOUT_COLORS = Object.assign({
    'apnews.com':   '#2F7F7B', 'reuters.com':  '#2F7F7B',
    'bbc.com':      '#2F7F7B', 'aljazeera.com':'#7A5BA6',
}, meta.outlet_colors || {});

// Inject callout CSS
const _ccStyle = document.createElement('style');
_ccStyle.textContent = `
#callout-panel{
    position:absolute;top:112px;right:20px;width:268px;
    z-index:30;pointer-events:none;opacity:0;
    font-family:Georgia,serif;
}
.cc-card{
    background:rgba(255,255,255,0.97);
    border-left:3px solid #4E79A7;
    border-radius:3px;
    box-shadow:0 2px 16px rgba(0,0,0,0.12);
    padding:13px 15px 11px;
}
.cc-event{
    font-size:11px;font-weight:700;color:#1a1a1a;
    font-family:Roboto,sans-serif;
    text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px;
}
.cc-note{
    font-size:10px;color:#666;line-height:1.5;
    margin-bottom:9px;font-family:Roboto,sans-serif;font-style:italic;
}
.cc-hl{border-top:1px solid #f2f2f2;padding:7px 0 3px;}
.cc-hl:first-of-type{border-top:none;padding-top:0;}
.cc-badge{
    display:inline-block;font-size:11px;font-weight:600;color:#fff;
    border-radius:4px;padding:4px 10px;margin-bottom:5px;
    border:1.5px solid transparent;
    font-family:Roboto,sans-serif;
    line-height:1;
}
.cc-title{
    font-size:10.5px;font-weight:600;color:#1a1a1a;
    line-height:1.4;margin-bottom:2px;
}
.cc-snip{font-size:9.5px;color:#aaa;line-height:1.4;font-family:Roboto,sans-serif;}
.cc-meta{font-size:9px;color:#999;line-height:1.35;font-family:Roboto,sans-serif;margin-top:3px;}
.cc-cluster{
    display:inline-block;font-size:9.5px;font-weight:700;
    font-family:Roboto,sans-serif;text-transform:uppercase;
    letter-spacing:.04em;line-height:1.25;margin-bottom:5px;
}
`;
document.head.appendChild(_ccStyle);

// Build panel DOM
const calloutPanel = document.createElement('div');
calloutPanel.id = 'callout-panel';
if (timelineInner) timelineInner.appendChild(calloutPanel);

// Build a card for a given event + active dimension.
// Handles two formats:
//   us_event_cluster_articles.json → event-window articles closest to cluster centroids
//   us_events.json  → evt.by_dim[dim]  (per-dimension headline lists)
//   events.json     → evt.snippets     (shared headline list, fallback)
const useClusterArticleCards = (eventClusterArticles || []).length > 0;
const clusterArticlesById = {};
const clusterArticlesByDate = {};
(eventClusterArticles || []).forEach(evt => {
    if (evt.id) clusterArticlesById[evt.id] = evt;
    if (evt.date) clusterArticlesByDate[evt.date] = evt;
});

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function buildClusterArticleCard(evt, dim) {
    const source = clusterArticlesById[evt.id] || clusterArticlesByDate[evt.date];
    if (!useClusterArticleCards || !source || !source.clusters || source.clusters.length === 0) {
        return null;
    }

    const dimColor = DIM_PALETTE[dim] || '#4E79A7';
    const dimLabel = DIM_DISPLAY[dim] || dim;
    const clusters = source.clusters.slice(0, 3);
    const clusterHTML = clusters.map(item => {
        const clusterColor = item.cluster_color || '#999';
        const clusterLabel = item.cluster_label || (
            item.cluster_id != null ? `Cluster ${item.cluster_id}` : 'Cluster'
        );
        const outlet = CALLOUT_LABELS[item.outlet] || item.outlet;
        const activeScore = item.scores && item.scores[dim] != null ? item.scores[dim].toFixed(2) : 'n/a';
        return `<div class="cc-hl">
            <div class="cc-cluster" style="color:${clusterColor}">${escapeHtml(clusterLabel)}</div>
            <div class="cc-title">${escapeHtml(item.title)}</div>
            <div class="cc-meta">${escapeHtml(outlet)} · ${escapeHtml(item.date)} · ${escapeHtml(dimLabel)} ${activeScore}</div>
        </div>`;
    }).join('');

    return `<div class="cc-card" style="border-left-color:${dimColor}">
        <div class="cc-event">${escapeHtml(source.label)}</div>
        <div class="cc-note">Closest article examples to cluster centroids within ±${escapeHtml(source.window_days)} days of this event.</div>
        ${clusterHTML}
    </div>`;
}

function buildDimCard(evt, dim) {
    const clusterCard = buildClusterArticleCard(evt, dim);
    if (clusterCard) return clusterCard;

    const dimColor = DIM_PALETTE[dim] || '#4E79A7';
    const dimLabel = DIM_DISPLAY[dim] || dim;
    let items;

    if (evt.by_dim) {
        items = (evt.by_dim[dim] || []).slice(0, 2);
    } else {
        const snippets = evt.snippets || {};
        const seen = new Set();
        items = Object.entries(snippets)
            .flatMap(([outlet, arr]) => arr.map(s => ({ outlet, ...s })))
            .filter(s => { if (seen.has(s.url)) return false; seen.add(s.url); return true; })
            .slice(0, 2);
    }

    const hlHTML = items.map(s => {
        const bg  = CALLOUT_COLORS[s.outlet] || '#999';
        const lbl = CALLOUT_LABELS[s.outlet]  || s.outlet;
        const scoreText = s.score != null ? ` ${Number(s.score).toFixed(2)}` : '';
        return `<div class="cc-hl">
            <span class="cc-badge" style="background:${bg}">${lbl}</span>
            <div class="cc-title">${s.title}</div>
            <div class="cc-meta">${lbl} · ${evt.date || ''} · ${dimLabel}${scoreText}</div>
        </div>`;
    }).join('');

    const note = evt.divergence_note || evt.description || '';
    return `<div class="cc-card" style="border-left-color:${dimColor}">
        <div class="cc-event">${evt.label}</div>
        ${note ? `<div class="cc-note">${note}</div>` : ''}
        ${hlHTML || '<div class="cc-snip" style="color:#ccc;font-style:italic">No coverage data for this period.</div>'}
    </div>`;
}

// calloutCards is rebuilt whenever the active dimension changes.
let calloutCards = [];

function rebuildCalloutCards() {
    // Prefer us_events (per-dim headlines) if available, else fall back to intl events.
    const src = (usEvents && usEvents.length) ? usEvents : events;
    calloutCards = src.map(evt => ({
        x:    xScale(parseDate(evt.date)),
        html: buildDimCard(evt, activeDim),
    }));
    _activeIdx = -1;
    updateCallout(window.scrollY);
}

let _activeIdx = -1;

function updateCallout(sy) {
    if (!calloutPanel) return;
    if (sy < sectionTop || sy > sectionTop + scrollDistance) {
        if (_activeIdx !== -1) {
            gsap.to(calloutPanel, { opacity: 0, duration: 0.25 });
            _activeIdx = -1;
        }
        return;
    }
    // screen_x of chart point = xScale(date) + MARGIN.left − scrollDistance * p
    // card triggers when event marker passes 35% from left:
    //   xScale(date) + MARGIN.left − scrollDistance*p = 0.35 * W
    //   => xScale(date) < 0.35*W − MARGIN.left + scrollDistance*p
    const p = (sy - sectionTop) / scrollDistance;
    const threshold = 0.35 * window.innerWidth - MARGIN.left + scrollDistance * p;

    let newIdx = -1;
    for (let i = calloutCards.length - 1; i >= 0; i--) {
        if (calloutCards[i].x < threshold) { newIdx = i; break; }
    }

    if (newIdx === _activeIdx) return;
    _activeIdx = newIdx;

    if (newIdx === -1) {
        gsap.to(calloutPanel, { opacity: 0, duration: 0.25 });
    } else {
        gsap.to(calloutPanel, {
            opacity: 0, duration: 0.15,
            onComplete: () => {
                calloutPanel.innerHTML = calloutCards[newIdx].html;
                gsap.to(calloutPanel, { opacity: 1, duration: 0.35 });
            },
        });
    }
}

// Build cards for the initial active dimension.
rebuildCalloutCards();

// ── Outlet toggle legend — grouped by cluster ─────────────────────────────
// Outlets are grouped by their cluster color with a "Cluster N" label.
// Selected (line visible): filled — white text on cluster color.
// Unselected (line hidden): outlined — cluster color text on transparent.

const COLOR_TO_CLUSTER = {
    '#7A5BA6': 'Cluster 0: The Mainstream Center',
    '#B65F6F': 'Cluster 1: The Dissident/Resistance Wing',
    '#4E6FAE': 'Cluster 2: The Diplomatic/Humanitarian Focus',
    '#2F7F7B': 'Cluster 3: The Economic Lens',
    '#B88A3D': 'Cluster 4: The Military/Right-Wing Faction',
};

// Build cluster groups preserving order of first appearance.
const clusterOrder = [];
const clusterGroups = {};
meta.outlets.forEach(outlet => {
    const color = meta.outlet_colors[outlet] || '#999';
    if (!clusterGroups[color]) {
        clusterGroups[color] = [];
        clusterOrder.push(color);
    }
    clusterGroups[color].push(outlet);
});

const outletLegend = document.createElement('div');
outletLegend.id = 'outlet-legend';
outletLegend.style.cssText = [
    'position:absolute',
    'bottom:14px',
    'left:' + MARGIN.left + 'px',
    'right:' + MARGIN.right + 'px',
    'z-index:10',
    'display:flex',
    'flex-wrap:wrap',
    'align-items:flex-start',
    'justify-content:space-between',
    'gap:12px 18px',
].join(';');
if (timelineInner) timelineInner.appendChild(outletLegend);

clusterOrder.forEach((color, ci) => {
    const outlets = clusterGroups[color];
    const clusterName = COLOR_TO_CLUSTER[color] || ('Cluster ' + ci);

    const clusterGroup = document.createElement('div');
    clusterGroup.style.cssText = [
        'display:flex',
        'flex-direction:column',
        'align-items:flex-start',
        'gap:5px',
        'flex:1 1 0',
        'max-width:190px',
        'min-width:140px',
    ].join(';');

    // Cluster label
    const lbl = document.createElement('span');
    lbl.textContent = clusterName;
    lbl.style.cssText = [
        'font-size:9px',
        'color:' + color,
        'font-family:Roboto,sans-serif',
        'text-transform:uppercase',
        'letter-spacing:.06em',
        'line-height:1.25',
        'min-height:22px',
        'font-weight:700',
    ].filter(Boolean).join(';');
    clusterGroup.appendChild(lbl);

    const pillsWrap = document.createElement('div');
    pillsWrap.style.cssText = [
        'display:flex',
        'flex-wrap:wrap',
        'align-items:flex-start',
        'gap:4px',
    ].join(';');

    // Outlet pills in this cluster
    outlets.forEach(outlet => {
        const label = (meta.outlet_labels && meta.outlet_labels[outlet]) || outlet;
        const pill = document.createElement('button');
        pill.textContent = label;
        pill.dataset.outlet = outlet;

        function applyPillStyle(selected) {
            pill.style.cssText = [
                'padding:4px 10px',
                'border-radius:4px',
                'border:1.5px solid ' + color,
                'background:' + (selected ? color : 'transparent'),
                'color:' + (selected ? '#fff' : color),
                'font-size:11px',
                'font-family:Roboto,sans-serif',
                'cursor:pointer',
                'transition:background 0.15s,color 0.15s',
                'line-height:1',
            ].join(';');
        }

        applyPillStyle(true);

        pill.addEventListener('click', () => {
            const nowHidden = hiddenOutlets.has(outlet);
            if (nowHidden) {
                hiddenOutlets.delete(outlet);
                applyPillStyle(true);
            } else {
                hiddenOutlets.add(outlet);
                applyPillStyle(false);
            }
            drawLines(activeDim);
        });

        pillsWrap.appendChild(pill);
    });

    clusterGroup.appendChild(pillsWrap);
    outletLegend.appendChild(clusterGroup);
});

// ─────────────────────────────────────────────────────────────────────────────

function updateTrack() {
    const sy = window.scrollY;
    if (sy < sectionTop || sy > sectionTop + scrollDistance) {
        if (timelineInner) timelineInner.style.visibility = 'hidden';
    } else {
        if (timelineInner) timelineInner.style.visibility = 'visible';
        const progress = (sy - sectionTop) / scrollDistance;
        if (track) track.style.transform = `translateX(${-scrollDistance * progress}px)`;
    }
    updateCallout(sy);
}

window.addEventListener('scroll', updateTrack, { passive: true });
updateTrack();

})();
