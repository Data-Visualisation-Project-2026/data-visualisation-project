import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

CLUSTER_COLORS = {
    0: "#895EFF",
    1: "#59A14F",
    2: "#F28E2B",
    3: "#76B7B2",
    4: "#4E79A7",
}

CLUSTER_LABELS = {
    0: "Cluster 0 — Mainstream/Wire",
    1: "Cluster 1 — Left-leaning",
    2: "Cluster 2 — Centre/Regional",
    3: "Cluster 3 — Financial/Intl",
    4: "Cluster 4 — Right-leaning",
}

NON_US_OUTLETS = {
    "tehrantimes.com":     "Iran",
    "aljazeera.com":       "Qatar",
    "bbc.com":             "UK",
    "reuters.com":         "UK",
    "theguardian.com":     "UK",
    "theconversation.com": "Australia/Intl",
}

FONT_FAMILY = "'Source Sans Pro', sans-serif"
TRANSPARENT = "rgba(0,0,0,0)"

TOGGLE_STYLE = dict(
    bgcolor="#f4f4f4",
    bordercolor="#d0d0d0",
    borderwidth=1,
    font=dict(family="'Roboto', sans-serif", size=11, color="#263746"),
    pad=dict(l=0, r=0, t=0, b=0),
)

PX_PER_BAR  = 18   # pixel height allocated per outlet row
GREY_TICK   = "rgba(180,180,180,0.7)"
NON_US_SET  = set(NON_US_OUTLETS.keys())


def _ticktext(sort_order: list, grey_names: set) -> list:
    """Return ticktext list: grey HTML span for outlets in grey_names, plain otherwise."""
    out = []
    for name in sort_order:
        if name in grey_names:
            out.append(f'<span style="color:{GREY_TICK}">{name}</span>')
        else:
            out.append(name)
    return out


def _load_data():
    base = Path(__file__).parent.parent
    pq_root = pd.read_parquet(base / "iran_war_media_framing_scores_clustered.parquet", engine="pyarrow")
    pq_5    = pd.read_parquet(base / "iran_war_media_framing_scores2_clustered.parquet", engine="pyarrow")
    pq_avg  = pd.read_parquet(base / "iran_war_outlet_averages_clustered.parquet", engine="pyarrow")

    pq_root["date"] = pd.to_datetime(pq_root["indexed_date"], errors="coerce")
    pq_5["date"]    = pd.to_datetime(pq_5["indexed_date"].astype(str), errors="coerce")

    # pq_5 outlets (BBC, Al Jazeera, Reuters) have null indexed_date — fill from scraped_articles.csv
    csv_path = base / "scraped_articles.csv"
    if csv_path.exists():
        csv_dates = pd.read_csv(csv_path, usecols=["url", "published_datetime"])
        csv_dates["csv_date"] = pd.to_datetime(
            csv_dates["published_datetime"].str.replace(r"Z$", "", regex=True),
            format="mixed",
            errors="coerce",
        )
        # Al Jazeera has no published_datetime — extract date from URL path (/news/YYYY/M/D/)
        aj_mask = csv_dates["url"].str.contains("aljazeera.com", na=False) & csv_dates["csv_date"].isna()
        aj_dates = csv_dates.loc[aj_mask, "url"].str.extract(r"/(\d{4})/(\d{1,2})/(\d{1,2})/")
        csv_dates.loc[aj_mask, "csv_date"] = pd.to_datetime(
            aj_dates[0] + "-" + aj_dates[1] + "-" + aj_dates[2], errors="coerce"
        )
        csv_dates = csv_dates.drop(columns=["published_datetime"])
        pq_5 = pq_5.merge(csv_dates, on="url", how="left")
        pq_5["date"] = pq_5["date"].fillna(pq_5["csv_date"])
        pq_5 = pq_5.drop(columns=["csv_date"])

    pq_root["country"] = pq_root["media_name"].map(NON_US_OUTLETS).fillna("US")
    pq_5["country"]    = pq_5["media_name"].map(NON_US_OUTLETS).fillna("US")

    combined = pd.concat([
        pq_root[["media_name", "date", "country"]],
        pq_5[["media_name", "date", "country"]],
    ], ignore_index=True)

    cluster_map = pq_avg.set_index("media_name")["media_cluster"].to_dict()
    combined["cluster"] = combined["media_name"].map(cluster_map).fillna(-1).astype(int)

    # Tehran Times coverage starts Feb 28 — drop earlier articles
    combined = combined[
        ~((combined["media_name"] == "tehrantimes.com") & (combined["date"] < pd.Timestamp("2026-02-28")))
    ].copy()

    return combined


def _cluster_color(cluster: int) -> str:
    return CLUSTER_COLORS.get(cluster, "#AAAAAA")


def _toggle_menu(buttons: list, y: float = 1.05) -> dict:
    return dict(
        type="buttons",
        direction="right",
        x=0, xanchor="left",
        y=y, yanchor="bottom",
        showactive=True,
        **TOGGLE_STYLE,
        buttons=buttons,
    )


# ── Articles per outlet ──────────────────────────────────────────────────────

def make_article_count_chart(combined: pd.DataFrame) -> go.Figure:
    summary = (
        combined.groupby(["media_name", "cluster", "country"])
        .size()
        .reset_index(name="articles")
    )

    # Fixed global y-axis order: grouped by cluster, then ascending by article count
    sort_order = summary.sort_values(["cluster", "articles"])["media_name"].tolist()
    n = len(sort_order)

    us_names  = set(sort_order) - NON_US_SET
    tt_all    = sort_order
    tt_us     = _ticktext(sort_order, NON_US_SET)   # grey non-US ticks
    tt_non_us = _ticktext(sort_order, us_names)      # grey US ticks

    fig = go.Figure()

    mc_all_list    = []
    mc_us_list     = []
    mc_non_us_list = []
    added_legend   = set()

    for cluster_id in sorted(summary["cluster"].unique()):
        sub   = summary[summary["cluster"] == cluster_id].copy()
        color = _cluster_color(cluster_id)
        label = CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}")
        show  = label not in added_legend
        added_legend.add(label)

        mc_all    = [color] * len(sub)
        mc_us     = [color     if r == "US" else TRANSPARENT for r in sub["country"]]
        mc_non_us = [TRANSPARENT if r == "US" else color     for r in sub["country"]]

        fig.add_trace(go.Bar(
            y=sub["media_name"],
            x=sub["articles"],
            orientation="h",
            marker=dict(color=mc_all),
            name=label,
            legendgroup=str(cluster_id),
            showlegend=show,
            hovertemplate="%{y}: %{x} articles<extra></extra>",
        ))
        mc_all_list.append(mc_all)
        mc_us_list.append(mc_us)
        mc_non_us_list.append(mc_non_us)

    # method="update" → first arg is trace props (restyle), second is layout props (relayout)
    buttons = [
        dict(label="All",         method="update",
             args=[{"marker.color": mc_all_list},    {"yaxis.ticktext": tt_all}]),
        dict(label="US only",     method="update",
             args=[{"marker.color": mc_us_list},     {"yaxis.ticktext": tt_us}]),
        dict(label="Non-US only", method="update",
             args=[{"marker.color": mc_non_us_list}, {"yaxis.ticktext": tt_non_us}]),
    ]

    fig.update_layout(
        title=dict(text="Articles per outlet", font=dict(family=FONT_FAMILY, size=15)),
        height=n * PX_PER_BAR + 200,
        margin=dict(l=180, r=40, t=80, b=130),
        barmode="overlay",
        updatemenus=[_toggle_menu(buttons)],
        legend=dict(orientation="h", y=-0.07, x=0, font=dict(family=FONT_FAMILY, size=11)),
        yaxis=dict(
            categoryorder="array",
            categoryarray=sort_order,
            tickmode="array",
            tickvals=sort_order,
            ticktext=tt_all,
            tickfont=dict(size=10, family=FONT_FAMILY),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=FONT_FAMILY),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor="#eeeeee",
        title_text="Number of articles",
        tickfont=dict(family=FONT_FAMILY),
    )
    fig.update_yaxes(showgrid=False)
    return fig


# ── Coverage window (Gantt) ──────────────────────────────────────────────────

def make_gantt_chart(combined: pd.DataFrame, date_range=None) -> go.Figure:
    gantt = (
        combined.dropna(subset=["date"])
        .groupby(["media_name", "cluster", "country"])["date"]
        .agg(earliest="min", latest="max", articles="count")
        .reset_index()
    )

    # Fixed global y-axis order: grouped by cluster, then ascending by article count
    cluster_map    = combined.groupby("media_name")["cluster"].first()
    article_counts = combined.groupby("media_name").size().rename("articles")
    outlet_meta    = pd.concat([cluster_map, article_counts], axis=1).reset_index()
    sort_order     = outlet_meta.sort_values(["cluster", "articles"])["media_name"].tolist()
    n = len(sort_order)

    us_names  = set(sort_order) - NON_US_SET
    tt_all    = sort_order
    tt_us     = _ticktext(sort_order, NON_US_SET)
    tt_non_us = _ticktext(sort_order, us_names)

    fig = go.Figure()

    lc_all = []; mc_all = []
    lc_us  = []; mc_us  = []
    lc_non = []; mc_non = []
    added_legend = set()

    gantt = gantt.set_index("media_name").reindex(
        [o for o in sort_order if o in gantt["media_name"].values]
    ).reset_index()

    for _, row in gantt.iterrows():
        cluster_id = int(row["cluster"])
        color  = _cluster_color(cluster_id)
        label  = CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}")
        is_us  = row["country"] == "US"
        show   = label not in added_legend
        added_legend.add(label)

        # Spanner line — thin with circle end-caps
        fig.add_trace(go.Scatter(
            x=[row["earliest"], row["latest"]],
            y=[row["media_name"], row["media_name"]],
            mode="lines+markers",
            line=dict(color=color, width=1.5),
            marker=dict(color=color, size=7, symbol="circle"),
            name=label,
            legendgroup=str(cluster_id),
            showlegend=show,
            hovertemplate=(
                f"<b>{row['media_name']}</b><br>"
                f"{row['earliest'].strftime('%b %d')} → "
                f"{row['latest'].strftime('%b %d, %Y')}<br>"
                f"{int(row['articles'])} articles<extra></extra>"
            ),
        ))
        lc_all.append(color);  mc_all.append(color);  mc_all.append(color)
        lc_us.append(color  if is_us else TRANSPARENT); mc_us.append(color  if is_us else TRANSPARENT);  mc_us.append(color  if is_us else TRANSPARENT)
        lc_non.append(TRANSPARENT if is_us else color);  mc_non.append(TRANSPARENT if is_us else color);  mc_non.append(TRANSPARENT if is_us else color)

    buttons = [
        dict(label="All",         method="update",
             args=[{"line.color": lc_all, "marker.color": mc_all}, {"yaxis.ticktext": tt_all}]),
        dict(label="US only",     method="update",
             args=[{"line.color": lc_us,  "marker.color": mc_us},  {"yaxis.ticktext": tt_us}]),
        dict(label="Non-US only", method="update",
             args=[{"line.color": lc_non, "marker.color": mc_non}, {"yaxis.ticktext": tt_non_us}]),
    ]

    xaxis_cfg = dict(
        showgrid=True, gridcolor="#eeeeee",
        tickformat="%b %d", dtick=7 * 24 * 60 * 60 * 1000,
        tickfont=dict(family=FONT_FAMILY),
    )
    if date_range:
        xaxis_cfg["range"] = date_range

    fig.update_layout(
        title=dict(text="Coverage window per outlet", font=dict(family=FONT_FAMILY, size=15)),
        height=n * 12 + 200,
        margin=dict(l=180, r=40, t=80, b=130),
        updatemenus=[_toggle_menu(buttons)],
        legend=dict(orientation="h", y=-0.07, x=0, font=dict(family=FONT_FAMILY, size=11)),
        yaxis=dict(
            categoryorder="array",
            categoryarray=sort_order,
            tickmode="array",
            tickvals=sort_order,
            ticktext=tt_all,
            tickfont=dict(size=10, family=FONT_FAMILY),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=FONT_FAMILY),
    )
    fig.update_xaxes(**xaxis_cfg)
    fig.update_yaxes(showgrid=False)
    return fig


# ── Daily volume over time ───────────────────────────────────────────────────

def make_articles_over_time_chart(combined: pd.DataFrame, date_range=None) -> go.Figure:
    df = combined.dropna(subset=["date"]).copy()
    df["date_only"] = df["date"].dt.normalize()

    GREY_LINE = "rgba(180,180,180,0.45)"
    GREY_FILL = "rgba(180,180,180,0.07)"
    US_LINE   = "#888888"
    US_FILL   = "rgba(150,150,150,0.15)"

    fig = go.Figure()

    # Accumulate restyle color arrays as traces are added
    lc_all = [];  fc_all = [];  mc_all = []   # all visible
    lc_us  = [];  fc_us  = [];  mc_us  = []   # US active, non-US greyed
    lc_non = [];  fc_non = [];  mc_non = []   # non-US active, US greyed

    # ── US aggregate (shaded area) ───────────────────────────────────────────
    us_daily = (
        df[df["country"] == "US"]
        .groupby("date_only").size()
        .reset_index(name="count")
        .sort_values("date_only")
    )
    fig.add_trace(go.Scatter(
        x=us_daily["date_only"], y=us_daily["count"],
        mode="lines",
        fill="tozeroy",
        line=dict(color=US_LINE, width=1.5),
        fillcolor=US_FILL,
        name="US outlets (aggregate)",
        hovertemplate="US outlets: %{y} articles on %{x|%b %d}<extra></extra>",
    ))
    lc_all.append(US_LINE);  fc_all.append(US_FILL);  mc_all.append(US_LINE)
    lc_us.append(US_LINE);   fc_us.append(US_FILL);   mc_us.append(US_LINE)
    lc_non.append(GREY_LINE); fc_non.append(GREY_FILL); mc_non.append(GREY_LINE)

    # ── Non-US individual lines ──────────────────────────────────────────────
    non_us_outlets = df[df["country"] != "US"]["media_name"].unique()
    for outlet in sorted(non_us_outlets):
        cluster_id = int(df[df["media_name"] == outlet]["cluster"].iloc[0])
        color = _cluster_color(cluster_id)
        daily = (
            df[df["media_name"] == outlet]
            .groupby("date_only").size()
            .reset_index(name="count")
            .sort_values("date_only")
        )
        fig.add_trace(go.Scatter(
            x=daily["date_only"], y=daily["count"],
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=4, color=color),
            name=outlet,
            hovertemplate=f"{outlet}: %{{y}} articles on %{{x|%b %d}}<extra></extra>",
        ))
        lc_all.append(color);     fc_all.append(TRANSPARENT); mc_all.append(color)
        lc_us.append(GREY_LINE);  fc_us.append(TRANSPARENT);  mc_us.append(GREY_LINE)
        lc_non.append(color);     fc_non.append(TRANSPARENT);  mc_non.append(color)

    # Toggle via restyle — greyed out rather than hidden
    buttons = [
        dict(label="All",         method="restyle",
             args=[{"line.color": lc_all, "fillcolor": fc_all, "marker.color": mc_all}]),
        dict(label="US only",     method="restyle",
             args=[{"line.color": lc_us,  "fillcolor": fc_us,  "marker.color": mc_us}]),
        dict(label="Non-US only", method="restyle",
             args=[{"line.color": lc_non, "fillcolor": fc_non, "marker.color": mc_non}]),
    ]

    # ── Event markers ────────────────────────────────────────────────────────
    events = [
        ("2026-02-28", "Opening strikes"),
        ("2026-03-09", "New Leader elected"),
        ("2026-03-18", "Energy escalation"),
        ("2026-03-27", "Iran strikes US base in Saudi Arabia"),
        ("2026-04-08", "Ceasefire declared"),
    ]
    for date_str, label in events:
        ts = pd.Timestamp(date_str)
        fig.add_vline(x=ts, line_width=1, line_dash="dash",
                      line_color="rgba(80,80,80,0.4)")
        fig.add_annotation(
            x=ts, y=1.04, xref="x", yref="paper",
            text=label, showarrow=False,
            xanchor="left", yanchor="bottom",
            font=dict(size=9.5, color="rgba(60,60,60,0.85)", family=FONT_FAMILY),
            textangle=-30,
        )

    xaxis_cfg = dict(
        showgrid=True, gridcolor="#eeeeee",
        tickformat="%b %d", dtick=7 * 24 * 60 * 60 * 1000,
        tickfont=dict(family=FONT_FAMILY),
    )
    if date_range:
        xaxis_cfg["range"] = date_range

    # Match l=180, r=40 of the Gantt so date ticks align pixel-perfectly
    fig.update_layout(
        title=dict(text="Daily article volume over time", font=dict(family=FONT_FAMILY, size=15)),
        height=500,
        margin=dict(l=180, r=40, t=80, b=130),
        xaxis_title="",
        yaxis=dict(
            title="",
            tickfont=dict(family=FONT_FAMILY),
        ),
        updatemenus=[_toggle_menu(buttons)],
        legend=dict(orientation="h", y=-0.07, x=0,
                    font=dict(family=FONT_FAMILY, size=11)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        font=dict(family=FONT_FAMILY),
    )
    fig.update_xaxes(**xaxis_cfg)
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")

    # "Articles published" as a top-left label (horizontal, not rotated)
    fig.add_annotation(
        x=0, y=1.0,
        xref="paper", yref="paper",
        text="Articles published",
        showarrow=False,
        xanchor="left", yanchor="bottom",
        font=dict(size=11, family=FONT_FAMILY, color="#5a7185"),
    )

    return fig


# ── Export / Streamlit entry points ─────────────────────────────────────────

def build_dataset_overview_html() -> str:
    combined   = _load_data()
    dates      = combined["date"].dropna()
    date_range = [
        (dates.min() - pd.Timedelta(days=2)).isoformat(),
        (dates.max() + pd.Timedelta(days=2)).isoformat(),
    ]

    bar_html   = make_article_count_chart(combined).to_html(full_html=False, include_plotlyjs=False)
    gantt_html = make_gantt_chart(combined, date_range=date_range).to_html(full_html=False, include_plotlyjs=False)
    time_html  = make_articles_over_time_chart(combined, date_range=date_range).to_html(full_html=False, include_plotlyjs=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Dataset Overview — Iran War Media Coverage</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Source Sans Pro', sans-serif;
            background: #f9fafb; margin: 0; padding: 24px 32px; color: #263746; }}
    h1   {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
    p.sub {{ color: #5a7185; font-size: 0.95rem; margin-top: 0; margin-bottom: 28px; }}
    .stat-row {{ display: flex; gap: 36px; margin-bottom: 32px; flex-wrap: wrap; align-items: baseline; }}
    .stat .n {{ font-size: 2rem; font-weight: 700; color: #263746;
                font-family: Georgia, 'Times New Roman', serif; }}
    .stat .l {{ font-size: 0.78rem; color: #5a7185; text-transform: uppercase;
                letter-spacing: .06em; margin-top: 1px; }}
    .chart-wrap {{ background: white; border: 1px solid #dde4ea; border-radius: 8px;
                   padding: 8px; margin-bottom: 28px; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>Iran War — Media Coverage Dataset</h1>
  <p class="sub">Overview of all outlets, article volumes, and coverage windows used in the framing analysis.</p>

  <div class="stat-row">
    <div class="stat"><div class="n">82</div><div class="l">Outlets</div></div>
    <div class="stat"><div class="n">2,867</div><div class="l">Articles</div></div>
    <div class="stat"><div class="n">76</div><div class="l">US outlets</div></div>
    <div class="stat"><div class="n">6</div><div class="l">Non-US outlets</div></div>
    <div class="stat"><div class="n">Feb 27 – Apr 20</div><div class="l">Date range</div></div>
  </div>

  <div class="chart-wrap">{bar_html}</div>
  <div class="chart-wrap">{gantt_html}</div>
  <div class="chart-wrap">{time_html}</div>
</body>
</html>"""


def render_dataset_overview():
    """Render the three dataset overview charts inside Streamlit."""
    import streamlit as st

    combined   = _load_data()
    dates      = combined["date"].dropna()
    date_range = [
        (dates.min() - pd.Timedelta(days=2)).isoformat(),
        (dates.max() + pd.Timedelta(days=2)).isoformat(),
    ]

    st.markdown("### Articles per outlet")
    st.plotly_chart(make_article_count_chart(combined), use_container_width=True)

    st.markdown("### Coverage window per outlet")
    st.plotly_chart(make_gantt_chart(combined, date_range=date_range), use_container_width=True)

    st.markdown("### Daily article volume over time")
    st.plotly_chart(make_articles_over_time_chart(combined, date_range=date_range), use_container_width=True)
