gsap.registerPlugin(ScrollTrigger);

(async () => {
    const [timeline, events, meta] = await Promise.all([
    fetch("data/timeline.json").then(res => res.json()),
    fetch("data/events.json").then(res => res.json()),
    fetch("data/meta.json").then(res => res.json()),
]);

    console.log("timeline days:", timeline.length);
    console.log("events:", events.map(e => e.label));
    console.log("outlets:", meta.outlets);

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
            .attr('fill', DIM_COLORS[d[key]]).attr('opacity', 0.72);
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

// ── Outlet legend — one swatch per cluster, names stacked vertically ─────
const clusterMap = new Map();
meta.outlets.forEach(o => {
    const c = meta.outlet_colors[o];
    if (!clusterMap.has(c)) clusterMap.set(c, []);
    clusterMap.get(c).push(o);
});

const LINE_H     = 15;
const SQ         = 11;
const CLUSTER_W  = 140;
const maxRows    = Math.max(...[...clusterMap.values()].map(a => a.length));
const legendTopY = svgH - maxRows * LINE_H - 6;

const outletLegend = svg.append('g')
    .attr('transform', `translate(${MARGIN.left}, ${legendTopY})`);

[...clusterMap.entries()].forEach(([color, outlets], ci) => {
    const cx = ci * CLUSTER_W;
    outletLegend.append('rect')
        .attr('x', cx).attr('y', 0)
        .attr('width', SQ).attr('height', SQ)
        .attr('fill', color).attr('rx', 2);
    outlets.forEach((outlet, oi) => {
        outletLegend.append('text')
            .attr('x', cx + SQ + 6)
            .attr('y', oi * LINE_H + 10)
            .attr('fill', '#444').attr('font-size', '11px')
            .text(meta.outlet_labels[outlet]);
    });
});

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

function updateTrack() {
    const sy = window.scrollY;
    if (sy < sectionTop || sy > sectionTop + scrollDistance) {
        if (timelineInner) timelineInner.style.visibility = 'hidden';
    } else {
        if (timelineInner) timelineInner.style.visibility = 'visible';
        const progress = (sy - sectionTop) / scrollDistance;
        if (track) track.style.transform = `translateX(${-scrollDistance * progress}px)`;
    }
}

window.addEventListener('scroll', updateTrack, { passive: true });
updateTrack();

})();
