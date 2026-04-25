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
const MARGIN = { top: 72, right: 20, bottom: 48, left: 48 };
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

// --- LINES: ONE PER OUTLET x DIMENSION ---
const line = d3.line()
.x(d => xScale(parseDate(d.date)))
.y(d => yScale(d.value))
//
.defined(d => d.value != null)                                                                                                                                                       
      .curve(d3.curveCatmullRom.alpha(0.5));
                                                                                                                                                                                           
const FOCUS_DIM = "kinetic_focus"; // start with one dimension visible                                                                                                                 
                                                                                                                                                                                           
meta.outlets.forEach(outlet => {                                                                                                                                                       
    const data = timeline                                                                                                                                                              
    .filter(d => parseDate(d.date) !== null && d.outlets[outlet])                                                                                                                                                
    .map(d => ({ date: d.date, value: d.outlets[outlet][FOCUS_DIM] }));                                                                                                              
                                                                                                                                                                                           
    g.append("path")
    .datum(data)                                                                                                                                                                       
    .attr("class", `line outlet-${outlet.replace(".", "-")}`)                                                                                                                        
    .attr("fill", "none")                                                                                                                                                              
    .attr("stroke", meta.outlet_colors[outlet])
    .attr("stroke-width", 2)                                                                                                                                                           
    .attr("opacity", 0.85)                                                                                                                                                           
    .attr("d", line);                                                                                                                                                                  
 });                                                                                                                                                                                  

// ── Framing band — dominant dimension per day ────────────────────────────
const DIM_COLORS = {
    kinetic_focus:      '#4E79A7',
    humanitarian_focus: '#F28E2B',
    diplomatic_focus:   '#E15759',
    economic_focus:     '#76B7B2',
    culpability_bias:   '#59A14F',
};
const DIM_LABELS = {
    kinetic_focus:      'Kinetic',
    humanitarian_focus: 'Humanitarian',
    diplomatic_focus:   'Diplomatic',
    economic_focus:     'Economic',
    culpability_bias:   'Culpability',
};
const DIMS = Object.keys(DIM_COLORS);
const BAND_H = 40;
const BAND_Y = -(BAND_H + 16); // sits in the top margin, above the chart area

// Average outlet scores per day, find dominant dimension
const bandData = timeline
    .filter(d => parseDate(d.date) !== null)
    .map(d => {
        const outletVals = Object.values(d.outlets).filter(Boolean);
        const avg = {};
        DIMS.forEach(dim => {
            const vals = outletVals.map(o => o[dim]).filter(v => v != null);
            avg[dim] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
        });
        const dominant = DIMS.reduce((a, b) => avg[a] > avg[b] ? a : b);
        return { date: parseDate(d.date), dominant, avg };
    });

// Band background
g.append('rect')
    .attr('x', 0).attr('y', BAND_Y)
    .attr('width', totalW).attr('height', BAND_H)
    .attr('fill', '#f9f9f9').attr('rx', 3);

// Coloured rectangles — one per day
bandData.forEach((d, i) => {
    const x0 = xScale(d.date);
    const x1 = i < bandData.length - 1 ? xScale(bandData[i + 1].date) : x0 + DAY_WIDTH;
    g.append('rect')
        .attr('x', x0).attr('y', BAND_Y)
        .attr('width', Math.max(1, x1 - x0)).attr('height', BAND_H)
        .attr('fill', DIM_COLORS[d.dominant]).attr('opacity', 0.72);
});

// Band label on the left (in the margin)
g.append('text')
    .attr('x', -MARGIN.left + 4).attr('y', BAND_Y + BAND_H / 2 - 5)
    .attr('fill', '#999').attr('font-size', '9px').attr('font-family', 'monospace')
    .text('DOMINANT');
g.append('text')
    .attr('x', -MARGIN.left + 4).attr('y', BAND_Y + BAND_H / 2 + 7)
    .attr('fill', '#999').attr('font-size', '9px').attr('font-family', 'monospace')
    .text('FRAMING');

// Dimension legend — right of outlet legend
const dimLegend = svg.append('g')
    .attr('transform', `translate(${MARGIN.left}, ${svgH - 32})`);
Object.entries(DIM_LABELS).forEach(([dim, label], i) => {
    const lx = i * 130;
    dimLegend.append('rect')
        .attr('x', lx).attr('y', 0).attr('width', 12).attr('height', 12)
        .attr('fill', DIM_COLORS[dim]).attr('rx', 2).attr('opacity', 0.8);
    dimLegend.append('text')
        .attr('x', lx + 18).attr('y', 10)
        .attr('fill', '#666').attr('font-size', '11px').text(label);
});

// ── Event markers — run through band and chart ────────────────────────────
events.forEach(event => {
    const x = xScale(parseDate(event.date));
    g.append("line")
        .attr("x1", x).attr("x2", x).attr("y1", BAND_Y).attr("y2", chartH)
        .attr("stroke", "#555").attr("stroke-width", 1)
        .attr("stroke-dasharray", "4,4").attr("opacity", 0.5);

    g.append("text")
        .attr("x", x + 6).attr("y", BAND_Y - 4).attr("fill", "#555")
        .attr("font-size", "10px").attr("font-family", "monospace")
        .text(event.label);
});

// ── Outlet legend ────────────────────────────────────────────────────────
const legend = svg.append("g").attr("transform", `translate(${MARGIN.left}, ${svgH - 16})`);
meta.outlets.forEach((outlet, i) => {
    const lx = i * 160;
    legend.append("rect").attr("x", lx).attr("y", 0).attr("width", 12).attr("height", 12)
        .attr("fill", meta.outlet_colors[outlet]).attr("rx", 2);
    legend.append("text").attr("x", lx + 18).attr("y", 10)
        .attr("fill", "#444").attr("font-size", "12px")
        .text(meta.outlet_labels[outlet]);
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
