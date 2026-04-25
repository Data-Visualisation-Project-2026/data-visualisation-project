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

// --- GRID LINES ---
g.append("g")
.attr("class", "grid")
.attr("transform", `translate(0,${chartH})`)
.call(d3.axisBottom(xScale).ticks(d3.timeWeek.every(1)).tickSize(-chartH).tickFormat(""))
.call(ax => ax.select(".domain").remove())
.call(ax => ax.selectAll("line").attr("stroke", "#e0e0e0").attr("stroke-dasharray", "3,3"));

// --- AXES ---
g.append("g")
.attr("transform", `translate(0, ${chartH})`)
.call(d3.axisBottom(xScale).ticks(d3.timeWeek.every(1)).tickFormat(d3.timeFormat("%b %d")))
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

 // ── Event markers ─────────────────────────────────────────────────────────                                                                                                          
events.forEach(event => {
    const x = xScale(parseDate(event.date));                                                                                                                                              
    g.append("line")
    .attr("x1", x).attr("x2", x).attr("y1", 0).attr("y2", chartH)
    .attr("stroke", "#aaa").attr("stroke-width", 1)
    .attr("stroke-dasharray", "4,4").attr("opacity", 0.7);

    g.append("text")
    .attr("x", x + 6).attr("y", -10).attr("fill", "#777")
    .attr("font-size", "11px").attr("font-family", "monospace")
    .text(event.label);
});                                                                                                                                                                                  

// ── Legend ────────────────────────────────────────────────────────────────                                                                                                          
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
