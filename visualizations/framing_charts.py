import json
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def make_framing_over_time_chart(df, score_cols, score_labels, highlighted_dimensions):
    """Create an interactive line chart showing average framing scores over time."""
    # Aggregate each framing score by publication date.
    daily = df.groupby('publish_date')[score_cols].mean().reset_index()

    # Reshape the data so Plotly can draw one line per framing dimension.
    daily_long = daily.melt(
        id_vars='publish_date',
        value_vars=score_cols,
        var_name='dimension',
        value_name='average_score'
    )

    daily_long['dimension'] = daily_long['dimension'].map(score_labels)

    # Keep colors and legend order consistent across the chart.
    color_map = {
        'Kinetic': '#4E79A7',
        'Humanitarian': '#F28E2B',
        'Diplomatic': '#76B7B2',
        'Economic': '#59A14F',
        'Culpability Bias': '#E15759'
    }

    legend_order = [
        'Culpability Bias',
        'Kinetic',
        'Economic',
        'Diplomatic',
        'Humanitarian'
    ]

    # Define the interactive line chart and its visual settings.
    chart = px.line(
        daily_long,
        x='publish_date',
        y='average_score',
        color='dimension',
        labels={
            'publish_date': '',
            'average_score': 'Avg. framing score (0 = absent, 1 = present)',
            'dimension': 'Dimension'
        },
        color_discrete_map=color_map,
        category_orders={'dimension': legend_order}
    )

    # Highlight selected dimensions while keeping the rest visible for context.
    for trace in chart.data:
        is_highlighted = trace.name in highlighted_dimensions
        trace.update(
            line={'width': 3.5 if is_highlighted else 1.5},
            opacity=1.0 if is_highlighted else 0.25,
            hovertemplate=f'{trace.name}: %{{y:.2f}}<extra></extra>'
        )

    events = [
        ('2026-03-01', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation'),
        ('2026-04-08', 'Ceasefire'),
    ]

    for event_date, event_label in events:
        event_date = pd.Timestamp(event_date)

        chart.add_shape(
            type='line',
            xref='x',
            yref='paper',
            x0=event_date,
            x1=event_date,
            y0=0,
            y1=1,
            line={
                'width': 1,
                'dash': 'dash',
                'color': 'rgba(90, 90, 90, 0.55)'
            }
        )

        chart.add_annotation(
            x=event_date,
            y=1.02,
            xref='x',
            yref='paper',
            text=event_label,
            showarrow=False,
            xanchor='left',
            yanchor='bottom',
            font={
                'size': 11,
                'color': 'rgba(70, 70, 70, 0.9)'
            }
        )

    chart.update_layout(
        height=550,
        yaxis_range=[0, 0.7],
        hovermode='x unified',
        title_text='',
        showlegend=False,
        margin={'l': 55, 'r': 20, 't': 60, 'b': 80}
    )

    event_dates_ts = [pd.Timestamp(d) for d, _ in events]
    event_tick_labels = [f"{pd.Timestamp(d).strftime('%b')} {pd.Timestamp(d).day}" for d, _ in events]

    chart.update_xaxes(
        range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-20')],
        tickvals=event_dates_ts,
        ticktext=event_tick_labels,
        showgrid=False
    )

    chart.update_yaxes(showgrid=False, automargin=False)

    return chart


def make_international_framing_chart(timeline_path, highlighted_dimensions):
    """5-dimension line chart averaged across the 4 international/wire outlets."""
    with open(timeline_path) as f:
        timeline = json.load(f)

    DIMS = ['kinetic_focus', 'humanitarian_focus', 'diplomatic_focus',
            'economic_focus', 'culpability_bias']
    OUTLETS = ['apnews.com', 'reuters.com', 'bbc.com', 'aljazeera.com']

    rows = []
    for entry in timeline:
        date = pd.Timestamp(entry['date'])
        outlet_vals = [entry['outlets'][o] for o in OUTLETS if o in entry['outlets'] and entry['outlets'][o]]
        if not outlet_vals:
            continue
        avg = {dim: sum(o[dim] for o in outlet_vals if o.get(dim) is not None) /
                    max(1, sum(1 for o in outlet_vals if o.get(dim) is not None))
               for dim in DIMS}
        avg['date'] = date
        rows.append(avg)

    daily = pd.DataFrame(rows).set_index('date')

    score_labels = {
        'kinetic_focus': 'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus': 'Diplomatic',
        'economic_focus': 'Economic',
        'culpability_bias': 'Culpability Bias',
    }
    color_map = {
        'Kinetic': '#4E79A7',
        'Humanitarian': '#F28E2B',
        'Diplomatic': '#76B7B2',
        'Economic': '#59A14F',
        'Culpability Bias': '#E15759',
    }
    legend_order = ['Culpability Bias', 'Kinetic', 'Economic', 'Diplomatic', 'Humanitarian']

    daily_long = daily.reset_index().melt(
        id_vars='date', value_vars=DIMS, var_name='dimension', value_name='average_score'
    )
    daily_long['dimension'] = daily_long['dimension'].map(score_labels)

    chart = px.line(
        daily_long, x='date', y='average_score', color='dimension',
        labels={'date': '', 'average_score': 'Avg. framing score (0 = absent, 1 = present)', 'dimension': 'Dimension'},
        color_discrete_map=color_map,
        category_orders={'dimension': legend_order},
    )

    for trace in chart.data:
        is_highlighted = trace.name in highlighted_dimensions
        trace.update(
            line={'width': 3.5 if is_highlighted else 1.5},
            opacity=1.0 if is_highlighted else 0.25,
            hovertemplate=f'{trace.name}: %{{y:.2f}}<extra></extra>',
        )

    events = [
        ('2026-03-01', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation'),
        ('2026-04-08', 'Ceasefire'),
    ]
    for event_date, label in events:
        ts = pd.Timestamp(event_date)
        chart.add_shape(type='line', xref='x', yref='paper',
                        x0=ts, x1=ts, y0=0, y1=1,
                        line={'width': 1, 'dash': 'dash', 'color': 'rgba(90,90,90,0.55)'})
        chart.add_annotation(x=ts, y=1.02, xref='x', yref='paper',
                             text=label, showarrow=False,
                             xanchor='left', yanchor='bottom',
                             font={'size': 11, 'color': 'rgba(70,70,70,0.9)'})

    chart.update_layout(
        height=450,
        yaxis_range=[0, 0.8],
        hovermode='x unified',
        title_text='',
        showlegend=False,
        margin={'l': 55, 'r': 20, 't': 60, 'b': 80},
    )
    event_dates_ts = [pd.Timestamp(d) for d, _ in events]
    event_tick_labels = [f"{pd.Timestamp(d).strftime('%b')} {pd.Timestamp(d).day}" for d, _ in events]

    chart.update_xaxes(
        range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-20')],
        tickvals=event_dates_ts,
        ticktext=event_tick_labels,
        showgrid=False
    )
    chart.update_yaxes(showgrid=False)

    return chart


def make_us_framing_band_chart(df, score_cols):
    """Thin colored-rectangle strip showing dominant US framing per day."""
    DIMS = score_cols
    DIM_COLORS = {
        'kinetic_focus':      '#4E79A7',
        'humanitarian_focus': '#F28E2B',
        'diplomatic_focus':   '#76B7B2',
        'economic_focus':     '#59A14F',
        'culpability_bias':   '#E15759',
    }
    DIM_LABELS = {
        'kinetic_focus':      'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus':   'Diplomatic',
        'economic_focus':     'Economic',
        'culpability_bias':   'Culpability Bias',
    }

    daily = df.groupby(df['publish_date'].dt.normalize())[DIMS].mean()
    dominant = daily.idxmax(axis=1).reset_index()
    dominant.columns = ['date', 'dominant_dim']
    dominant = dominant.dropna(subset=['dominant_dim'])
    dominant['color'] = dominant['dominant_dim'].map(DIM_COLORS).fillna('#cccccc')
    dominant['label'] = dominant['dominant_dim'].map(DIM_LABELS).fillna('')
    dominant['y'] = 1

    DAY_MS = 86_400_000

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dominant['date'].tolist(),
        y=dominant['y'].tolist(),
        marker_color=dominant['color'].tolist(),
        marker_line_width=0,
        width=DAY_MS,
        offset=0,
        hovertemplate='%{customdata}<extra></extra>',
        customdata=dominant['label'].tolist(),
        showlegend=False,
    ))

    fig.update_layout(
        height=20,
        margin=dict(l=55, r=20, t=0, b=0),
        bargap=0,
        bargroupgap=0,
        xaxis=dict(
            visible=False,
            type='date',
            range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-20')],
        ),
        yaxis=dict(visible=False, range=[0, 1]),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig


def make_intl_framing_band_chart(timeline_path):
    """Thin strip showing dominant international framing per day (AP/Reuters/BBC/AJ)."""
    DIMS = ['kinetic_focus', 'humanitarian_focus', 'diplomatic_focus',
            'economic_focus', 'culpability_bias']
    OUTLETS = ['apnews.com', 'reuters.com', 'bbc.com', 'aljazeera.com']
    DIM_COLORS = {
        'kinetic_focus':      '#4E79A7',
        'humanitarian_focus': '#F28E2B',
        'diplomatic_focus':   '#76B7B2',
        'economic_focus':     '#59A14F',
        'culpability_bias':   '#E15759',
    }
    DIM_LABELS = {
        'kinetic_focus':      'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus':   'Diplomatic',
        'economic_focus':     'Economic',
        'culpability_bias':   'Culpability Bias',
    }

    with open(timeline_path) as f:
        timeline = json.load(f)

    rows = []
    for entry in timeline:
        date = pd.Timestamp(entry['date'])
        outlet_vals = [entry['outlets'][o] for o in OUTLETS
                       if o in entry['outlets'] and entry['outlets'][o]]
        if not outlet_vals:
            continue
        avg = {
            dim: sum(o[dim] for o in outlet_vals if o.get(dim) is not None) /
                 max(1, sum(1 for o in outlet_vals if o.get(dim) is not None))
            for dim in DIMS
        }
        avg['date'] = date
        rows.append(avg)

    daily = pd.DataFrame(rows).set_index('date')
    date_min = daily.index.min()
    date_max = daily.index.max()
    # Forward-fill missing calendar dates so the band has no white gaps
    full_range = pd.date_range(date_min, date_max, freq='D')
    daily = daily.reindex(full_range).ffill()
    dominant = daily.idxmax(axis=1).reset_index()
    dominant.columns = ['date', 'dominant_dim']
    dominant = dominant.dropna(subset=['dominant_dim'])
    dominant['color'] = dominant['dominant_dim'].map(DIM_COLORS).fillna('#cccccc')
    dominant['label'] = dominant['dominant_dim'].map(DIM_LABELS).fillna('')
    dominant['y'] = 1

    DAY_MS = 86_400_000

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dominant['date'].tolist(),
        y=dominant['y'].tolist(),
        marker_color=dominant['color'].tolist(),
        marker_line_width=0,
        width=DAY_MS,
        offset=0,
        hovertemplate='%{customdata}<extra></extra>',
        customdata=dominant['label'].tolist(),
        showlegend=False,
    ))

    fig.update_layout(
        height=20,
        margin=dict(l=55, r=20, t=0, b=0),
        bargap=0,
        bargroupgap=0,
        xaxis=dict(
            visible=False,
            type='date',
            range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-20')],
        ),
        yaxis=dict(visible=False, range=[0, 1]),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig


def make_stacked_dominant_framing_bars(
    df,
    score_cols,
    timeline_path,
    events_path,
    us_articles_path,
    intl_articles_path,
):
    """Compare dominant framing per day for US and non-US outlets in one stacked view."""
    dim_colors = {
        'kinetic_focus': '#4E79A7',
        'humanitarian_focus': '#F28E2B',
        'diplomatic_focus': '#76B7B2',
        'economic_focus': '#59A14F',
        'culpability_bias': '#E15759',
    }
    dim_labels = {
        'kinetic_focus': 'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus': 'Diplomatic',
        'economic_focus': 'Economic',
        'culpability_bias': 'Culpability Bias',
    }
    dim_order = list(dim_colors)
    dim_to_id = {dim: idx for idx, dim in enumerate(dim_order)}

    us_daily = df.groupby(df['publish_date'].dt.normalize())[score_cols].mean()
    us_dominant = us_daily.idxmax(axis=1).rename('dominant_dim').reset_index()
    us_dominant = us_dominant.rename(columns={'publish_date': 'date'})

    with open(timeline_path) as f:
        timeline = json.load(f)

    rows = []
    intl_outlets = ['apnews.com', 'reuters.com', 'bbc.com', 'aljazeera.com']
    for entry in timeline:
        outlet_vals = [
            entry['outlets'][outlet]
            for outlet in intl_outlets
            if outlet in entry['outlets'] and entry['outlets'][outlet]
        ]
        if not outlet_vals:
            continue
        avg = {
            dim: sum(outlet[dim] for outlet in outlet_vals if outlet.get(dim) is not None) /
                 max(1, sum(1 for outlet in outlet_vals if outlet.get(dim) is not None))
            for dim in dim_order
        }
        avg['date'] = pd.Timestamp(entry['date'])
        rows.append(avg)
    intl_daily = pd.DataFrame(rows).set_index('date')
    full_range = pd.date_range(intl_daily.index.min(), intl_daily.index.max(), freq='D')
    intl_daily = intl_daily.reindex(full_range).ffill()
    intl_dominant = intl_daily.idxmax(axis=1).rename('dominant_dim').reset_index()
    intl_dominant = intl_dominant.rename(columns={'index': 'date'})

    start = pd.Timestamp('2026-02-27')
    end = pd.Timestamp('2026-04-20')
    date_index = pd.date_range(start, end, freq='D')

    def align_dominant(data):
        aligned = data.set_index('date').reindex(date_index).ffill()
        return aligned['dominant_dim'].tolist()

    us_dims = align_dominant(us_dominant)
    intl_dims = align_dominant(intl_dominant)

    with open(events_path) as f:
        events = json.load(f)
    event_by_date = {
        pd.Timestamp(event['date']).normalize(): event.get('label', '')
        for event in events
    }

    with open(us_articles_path) as f:
        us_article_events = json.load(f)
    with open(intl_articles_path) as f:
        intl_article_events = json.load(f)

    outlet_labels = {
        'apnews.com': 'AP News',
        'reuters.com': 'Reuters',
        'bbc.com': 'BBC',
        'aljazeera.com': 'Al Jazeera',
        'nytimes.com': 'New York Times',
        'foxnews.com': 'Fox News',
        'cnn.com': 'CNN',
        'bloomberg.com': 'Bloomberg',
        'npr.org': 'NPR',
        'breitbart.com': 'Breitbart',
        'nbcnews.com': 'NBC News',
        'usatoday.com': 'USA Today',
    }

    def event_lookup(article_events):
        lookup = {}
        for event in article_events:
            event_date = pd.Timestamp(event['date']).normalize()
            window_days = int(event.get('window_days', 2))
            for offset in range(-window_days, window_days + 1):
                lookup[event_date + pd.Timedelta(days=offset)] = event
        return lookup

    us_events_by_window = event_lookup(us_article_events)
    intl_events_by_window = event_lookup(intl_article_events)

    def article_panel(group_name, dim, date, article_event):
        frame_label = dim_labels.get(dim, '')
        frame_color = dim_colors.get(dim, '#777777')
        header = (
            f'<span style="color:{frame_color};font-size:18px">▌</span> '
            f'<b>{escape(group_name)}</b><br>'
            f'{date:%b %d, %Y}<br>'
            f'Dominant frame: {escape(frame_label)}'
        )
        if not article_event:
            return f'{header}<br><span style="color:#999">No event panel for this date.</span>'

        parts = [
            header,
            f'<br><b>Event: {escape(article_event.get("label", ""))}</b>',
            '<br><span style="color:#777">Closest article examples to cluster centroids within '
            f'±{escape(str(article_event.get("window_days", 2)))} days.</span>',
        ]
        for item in article_event.get('clusters', []):
            outlet = outlet_labels.get(item.get('outlet'), item.get('outlet', ''))
            score = item.get('scores', {}).get(dim)
            score_text = f' · {escape(frame_label)} {score:.2f}' if score is not None else ''
            parts.append(
                '<br><br>'
                f'<b>{escape(item.get("cluster_label", ""))}</b><br>'
                f'{escape(item.get("title", ""))}<br>'
                f'<span style="color:#888">{escape(outlet)} · {escape(item.get("date", ""))}{score_text}</span>'
            )
        return ''.join(parts)

    z = [
        [dim_to_id.get(dim) for dim in us_dims],
        [dim_to_id.get(dim) for dim in intl_dims],
    ]
    customdata = [
        [
            article_panel('US outlets', dim, date, us_events_by_window.get(date))
            for date, dim in zip(date_index, us_dims)
        ],
        [
            article_panel('Non-US outlets', dim, date, intl_events_by_window.get(date))
            for date, dim in zip(date_index, intl_dims)
        ],
    ]

    colorscale = []
    last_idx = len(dim_order) - 1
    for idx, dim in enumerate(dim_order):
        left = idx / last_idx if last_idx else 0
        right = (idx + 0.999) / last_idx if last_idx else 1
        colorscale.extend([[left, dim_colors[dim]], [min(right, 1), dim_colors[dim]]])

    fig = go.Figure(
        data=go.Heatmap(
            x=date_index,
            y=[1, 0],
            z=z,
            customdata=customdata,
            colorscale=colorscale,
            zmin=0,
            zmax=last_idx,
            showscale=False,
            ygap=36,
            hovertemplate='%{customdata}<extra></extra>',
        )
    )

    for event_date, event_label in event_by_date.items():
        fig.add_vline(
            x=event_date,
            line_width=1,
            line_dash='dash',
            line_color='rgba(70,70,70,0.55)',
        )
        fig.add_annotation(
            x=event_date,
            y=1.08,
            xref='x',
            yref='paper',
            text=event_label,
            showarrow=False,
            xanchor='left',
            yanchor='bottom',
            font={'size': 10, 'color': 'rgba(60,60,60,0.9)'},
        )

    fig.update_layout(
        height=360,
        margin={'l': 115, 'r': 30, 't': 70, 'b': 55},
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        hoverlabel={
            'bgcolor': 'rgba(255,255,255,0.98)',
            'bordercolor': 'rgba(0,0,0,0.12)',
            'font': {'family': 'Roboto, sans-serif', 'size': 11, 'color': '#263746'},
            'align': 'left',
        },
        xaxis={
            'type': 'date',
            'range': [start, end],
            'showgrid': False,
            'tickvals': list(event_by_date),
            'ticktext': [
                f"{date.strftime('%b')} {date.day}"
                for date in event_by_date
            ],
        },
        yaxis={
            'showgrid': False,
            'tickmode': 'array',
            'tickvals': [1, 0],
            'ticktext': ['US outlets', 'Non-US outlets'],
            'tickfont': {'size': 12, 'color': '#555555'},
        },
    )

    return fig


def make_stacked_dominant_framing_comparison_html(
    df,
    score_cols,
    timeline_path,
    events_path,
    us_articles_path,
    intl_articles_path,
):
    """Build an interactive HTML comparison of dominant frames and event article panels."""
    dim_colors = {
        'kinetic_focus': '#4E79A7',
        'humanitarian_focus': '#F28E2B',
        'diplomatic_focus': '#76B7B2',
        'economic_focus': '#59A14F',
        'culpability_bias': '#E15759',
    }
    dim_labels = {
        'kinetic_focus': 'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus': 'Diplomatic',
        'economic_focus': 'Economic',
        'culpability_bias': 'Culpability Bias',
    }
    outlet_labels = {
        'apnews.com': 'AP News',
        'reuters.com': 'Reuters',
        'bbc.com': 'BBC',
        'aljazeera.com': 'Al Jazeera',
        'nytimes.com': 'New York Times',
        'foxnews.com': 'Fox News',
        'cnn.com': 'CNN',
        'bloomberg.com': 'Bloomberg',
        'npr.org': 'NPR',
        'breitbart.com': 'Breitbart',
        'nbcnews.com': 'NBC News',
        'usatoday.com': 'USA Today',
    }

    start = pd.Timestamp('2026-02-27')
    end = pd.Timestamp('2026-04-20')
    date_index = pd.date_range(start, end, freq='D')

    us_daily = df.groupby(df['publish_date'].dt.normalize())[score_cols].mean()
    us_dominant = us_daily.idxmax(axis=1).rename('dominant_dim').reset_index()
    us_dominant = us_dominant.rename(columns={'publish_date': 'date'})

    with open(timeline_path) as f:
        timeline = json.load(f)
    intl_rows = []
    intl_outlets = ['apnews.com', 'reuters.com', 'bbc.com', 'aljazeera.com']
    for entry in timeline:
        outlet_vals = [
            entry['outlets'][outlet]
            for outlet in intl_outlets
            if outlet in entry['outlets'] and entry['outlets'][outlet]
        ]
        if not outlet_vals:
            continue
        avg = {
            dim: sum(outlet[dim] for outlet in outlet_vals if outlet.get(dim) is not None) /
                 max(1, sum(1 for outlet in outlet_vals if outlet.get(dim) is not None))
            for dim in dim_colors
        }
        avg['date'] = pd.Timestamp(entry['date'])
        intl_rows.append(avg)
    intl_daily = pd.DataFrame(intl_rows).set_index('date')
    intl_daily = intl_daily.reindex(pd.date_range(intl_daily.index.min(), intl_daily.index.max(), freq='D')).ffill()
    intl_dominant = intl_daily.idxmax(axis=1).rename('dominant_dim').reset_index()
    intl_dominant = intl_dominant.rename(columns={'index': 'date'})

    def align_dominant(data):
        return data.set_index('date').reindex(date_index).ffill()['dominant_dim'].tolist()

    us_dims = align_dominant(us_dominant)
    intl_dims = align_dominant(intl_dominant)

    with open(events_path) as f:
        events = json.load(f)
    with open(us_articles_path) as f:
        us_article_events = json.load(f)
    with open(intl_articles_path) as f:
        intl_article_events = json.load(f)

    us_articles_by_id = {event.get('id'): event for event in us_article_events}
    intl_articles_by_id = {event.get('id'): event for event in intl_article_events}
    us_dim_by_date = {date.strftime('%Y-%m-%d'): dim for date, dim in zip(date_index, us_dims)}
    intl_dim_by_date = {date.strftime('%Y-%m-%d'): dim for date, dim in zip(date_index, intl_dims)}

    def bar_cells(dims):
        cells = []
        for date, dim in zip(date_index, dims):
            label = dim_labels.get(dim, '')
            cells.append(
                '<div class="dominant-cell" '
                f'style="background:{dim_colors.get(dim, "#ccc")};" '
                f'title="{date:%b %d}: {escape(label)}"></div>'
            )
        return ''.join(cells)

    def render_panel(group_name, article_event, dim):
        frame_label = dim_labels.get(dim, '')
        frame_color = dim_colors.get(dim, '#777')
        if not article_event:
            return (
                f'<div class="event-panel" style="border-left-color:{frame_color};">'
                f'<div class="panel-kicker">{escape(group_name)}</div>'
                '<div class="panel-empty">No representative article panel for this event.</div>'
                '</div>'
            )

        parts = [
            f'<div class="event-panel" style="border-left-color:{frame_color};">',
            f'<div class="panel-kicker">{escape(group_name)}</div>',
            f'<div class="panel-frame">Dominant frame: {escape(frame_label)}</div>',
            '<div class="panel-note">Closest article examples to cluster centroids within '
            f'±{escape(str(article_event.get("window_days", 2)))} days.</div>',
        ]
        for item in article_event.get('clusters', []):
            outlet = outlet_labels.get(item.get('outlet'), item.get('outlet', ''))
            score = item.get('scores', {}).get(dim)
            score_text = f' · {escape(frame_label)} {score:.2f}' if score is not None else ''
            cluster_color = item.get('cluster_color', '#444444')
            parts.extend([
                '<div class="panel-article">',
                f'<div class="panel-cluster" style="color:{escape(cluster_color)};">{escape(item.get("cluster_label", ""))}</div>',
                f'<div class="panel-title">{escape(item.get("title", ""))}</div>',
                f'<div class="panel-meta">{escape(outlet)} · {escape(item.get("date", ""))}{score_text}</div>',
                '</div>',
            ])
        parts.append('</div>')
        return ''.join(parts)

    event_payload = {}
    for event in events:
        event_id = event.get('id')
        event_date = pd.Timestamp(event['date'])
        date_key = event_date.strftime('%Y-%m-%d')
        us_dim = us_dim_by_date.get(date_key, 'kinetic_focus')
        intl_dim = intl_dim_by_date.get(date_key, 'kinetic_focus')
        event_payload[event_id] = {
            'label': event.get('label', ''),
            'date': event_date.strftime('%b %d, %Y'),
            'usPanel': render_panel('US Media outlets', us_articles_by_id.get(event_id), us_dim),
            'intlPanel': render_panel('Non-US Media outlets', intl_articles_by_id.get(event_id), intl_dim),
        }

    tickers = []
    total_days = max(1, (end - start).days)
    for event in events:
        event_date = pd.Timestamp(event['date'])
        left_pct = ((event_date - start).days / total_days) * 100
        tickers.append(
            '<button class="event-tick" '
            f'style="left:{left_pct:.4f}%;" '
            f'data-event-id="{escape(event.get("id", ""))}">'
            f'<span>{escape(event.get("label", ""))}</span>'
            '</button>'
        )

    initial_id = events[0].get('id') if events else ''
    payload_json = json.dumps(event_payload).replace('</', '<\\/')

    return f"""
<div class="stacked-dominant-comparison">
  <style>
    .stacked-dominant-comparison {{
      font-family: Roboto, Arial, sans-serif;
      color: #263746;
      padding: 8px 0 18px;
    }}
    .comparison-bars {{
      position: relative;
      margin: 42px 24px 22px 92px;
      padding-top: 24px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: repeat({len(date_index)}, 1fr);
      height: 26px;
      margin-bottom: 22px;
      border-radius: 2px;
      overflow: hidden;
      box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06);
    }}
    .bar-label {{
      position: absolute;
      left: -92px;
      width: 78px;
      font-size: 11px;
      color: #666;
      text-align: right;
      line-height: 26px;
    }}
    .bar-label.us {{ top: 24px; }}
    .bar-label.intl {{ top: 72px; }}
    .dominant-cell {{ min-width: 1px; }}
    .event-tick {{
      position: absolute;
      top: 0;
      height: 122px;
      border: 0;
      border-left: 1px dashed rgba(70,70,70,0.65);
      background: transparent;
      padding: 0;
      cursor: pointer;
    }}
    .event-tick span {{
      position: absolute;
      top: -22px;
      left: 6px;
      white-space: nowrap;
      font-size: 10px;
      color: #555;
      font-family: Roboto, Arial, sans-serif;
    }}
    .event-tick.active,
    .event-tick:hover {{
      border-left-color: #222;
    }}
    .comparison-event-title {{
      margin: 0 24px 12px 92px;
      font-family: Roboto, Arial, sans-serif;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .06em;
      text-transform: uppercase;
      color: #1a1a1a;
    }}
    .comparison-panels {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
      margin: 0 24px 0 92px;
    }}
    .event-panel {{
      background: rgba(255,255,255,0.98);
      border-left: 4px solid #999;
      border-radius: 4px;
      box-shadow: 0 2px 16px rgba(0,0,0,0.12);
      padding: 14px 16px 12px;
      max-height: 420px;
      overflow-y: auto;
    }}
    .panel-kicker {{
      font-size: 16px;
      font-weight: 700;
      letter-spacing: .02em;
      color: #1a1a1a;
      margin-bottom: 6px;
    }}
    .panel-frame,
    .panel-note,
    .panel-meta {{
      font-size: 10px;
      color: #777;
      line-height: 1.45;
      margin-bottom: 6px;
    }}
    .panel-note {{
      font-style: italic;
      margin-bottom: 10px;
    }}
    .panel-article {{
      border-top: 1px solid #f0f0f0;
      padding: 9px 0 4px;
    }}
    .panel-article:first-of-type {{
      border-top: none;
    }}
    .panel-cluster {{
      font-size: 10px;
      font-weight: 700;
      font-family: Roboto, Arial, sans-serif;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 4px;
    }}
    .panel-title {{
      font-family: Georgia, serif;
      font-size: 13px;
      font-weight: 700;
      line-height: 1.3;
      color: #1a1a1a;
      margin-bottom: 3px;
    }}
    .panel-empty {{
      font-size: 11px;
      color: #999;
      font-style: italic;
    }}
  </style>
  <div class="comparison-bars">
    <div class="bar-label us">US outlets</div>
    <div class="bar-label intl">Non-US outlets</div>
    <div class="bar-row">{bar_cells(us_dims)}</div>
    <div class="bar-row">{bar_cells(intl_dims)}</div>
    {"".join(tickers)}
  </div>
  <div id="comparison-event-title" class="comparison-event-title"></div>
  <div class="comparison-panels">
    <div id="comparison-us-panel"></div>
    <div id="comparison-intl-panel"></div>
  </div>
  <script>
    const comparisonEvents = {payload_json};
    const initialEventId = {json.dumps(initial_id)};
    const titleEl = document.getElementById('comparison-event-title');
    const usPanelEl = document.getElementById('comparison-us-panel');
    const intlPanelEl = document.getElementById('comparison-intl-panel');
    const ticks = Array.from(document.querySelectorAll('.event-tick'));

    function showEvent(eventId) {{
      const event = comparisonEvents[eventId];
      if (!event) return;
      titleEl.textContent = event.label + ' · ' + event.date;
      usPanelEl.innerHTML = event.usPanel;
      intlPanelEl.innerHTML = event.intlPanel;
      ticks.forEach(tick => tick.classList.toggle('active', tick.dataset.eventId === eventId));
    }}

    ticks.forEach(tick => {{
      tick.addEventListener('mouseenter', () => showEvent(tick.dataset.eventId));
      tick.addEventListener('focus', () => showEvent(tick.dataset.eventId));
      tick.addEventListener('click', () => showEvent(tick.dataset.eventId));
    }});
    showEvent(initialEventId);
  </script>
</div>
"""


def make_combined_aggregate_chart(df, score_cols, score_labels, timeline_path):
    """US (top) and international (bottom) aggregate as a shared-x subplot."""
    from plotly.subplots import make_subplots

    DIMS = ['kinetic_focus', 'humanitarian_focus', 'diplomatic_focus',
            'economic_focus', 'culpability_bias']
    OUTLETS = ['apnews.com', 'reuters.com', 'bbc.com', 'aljazeera.com']

    color_map = {
        'Kinetic':         '#4E79A7',
        'Humanitarian':    '#F28E2B',
        'Diplomatic':      '#E15759',
        'Economic':        '#76B7B2',
        'Culpability Bias':'#59A14F',
    }

    # ── US daily ──────────────────────────────────────────────────────────
    daily_us = df.groupby('publish_date')[score_cols].mean().reset_index()

    # ── International daily ────────────────────────────────────────────────
    with open(timeline_path) as f:
        timeline = json.load(f)

    rows = []
    for entry in timeline:
        date = pd.Timestamp(entry['date'])
        outlet_vals = [entry['outlets'][o] for o in OUTLETS
                       if o in entry['outlets'] and entry['outlets'][o]]
        if not outlet_vals:
            continue
        avg = {
            dim: sum(o[dim] for o in outlet_vals if o.get(dim) is not None) /
                 max(1, sum(1 for o in outlet_vals if o.get(dim) is not None))
            for dim in DIMS
        }
        avg['date'] = date
        rows.append(avg)
    daily_intl = pd.DataFrame(rows)

    # vertical_spacing=0.28 → row1 y=[0.64, 1.0], row2 y=[0, 0.36], gap y=[0.36, 0.64]
    # Enough gap for event markers + legend above each chart and date ticks below each.
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.28,
    )

    for dim in score_cols:
        label = score_labels[dim]
        color = color_map[label]

        fig.add_trace(go.Scatter(
            x=daily_us['publish_date'], y=daily_us[dim],
            name=label, legendgroup=label, showlegend=True,
            line=dict(color=color, width=2.0), opacity=1.0,
            hovertemplate=f'{label}: %{{y:.2f}}<extra></extra>',
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=daily_intl['date'], y=daily_intl[dim],
            name=label, legendgroup=f'{label}_intl', showlegend=True,
            legend='legend2',
            line=dict(color=color, width=2.0), opacity=1.0,
            hovertemplate=f'{label}: %{{y:.2f}}<extra></extra>',
        ), row=2, col=1)

    # ── Side titles — vertical text, left of each chart ─────────────────────
    # Row midpoints: row1=(0.64+1.0)/2=0.82, row2=(0+0.36)/2=0.18
    for y_mid, text in [
        (0.82, '77 US Outlets — domestic media'),
        (0.18, 'AP · Reuters · BBC · Al Jazeera'),
    ]:
        fig.add_annotation(
            x=-0.09, y=y_mid,
            xref='paper', yref='paper',
            text=text,
            showarrow=False,
            textangle=-90,
            xanchor='center', yanchor='middle',
            font={'size': 14, 'color': '#111111'},
        )

    # ── Event markers — dashed vlines with labels just ABOVE each chart ──────
    # All labels anchored left (text to the RIGHT of each vertical line).
    # Row 1 domain top = 1.0  → markers at y=1.01
    # Row 2 domain top = 0.36 → markers at y=0.365
    events = [
        ('2026-03-01', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation'),
        ('2026-04-08', 'Ceasefire'),
    ]

    for event_date, label in events:
        ts = pd.Timestamp(event_date)
        fig.add_vline(
            x=ts,
            line_width=1, line_dash='dash',
            line_color='rgba(90,90,90,0.45)',
        )
        # Just above row 1
        fig.add_annotation(
            x=ts, y=1.01, xref='x', yref='paper',
            text=label, showarrow=False,
            xanchor='left', yanchor='bottom',
            textangle=0,
            font={'size': 11, 'color': 'rgba(60,60,60,0.9)'},
        )
        # Just above row 2 (in the gap)
        fig.add_annotation(
            x=ts, y=0.365, xref='x', yref='paper',
            text=label, showarrow=False,
            xanchor='left', yanchor='bottom',
            textangle=0,
            font={'size': 11, 'color': 'rgba(60,60,60,0.9)'},
        )

    fig.update_layout(
        height=1100,
        hovermode='x unified',
        # Legend for US chart — below row-1 date ticks, in the gap
        legend={
            'orientation': 'h',
            'yanchor': 'top', 'y': 0.60,
            'xanchor': 'left', 'x': 0,
        },
        # Legend for international chart — below row-2 date ticks, in bottom margin
        legend2={
            'orientation': 'h',
            'yanchor': 'top', 'y': -0.03,
            'xanchor': 'left', 'x': 0,
        },
        margin={'l': 130, 'r': 40, 't': 100, 'b': 80},
    )
    event_dates_ts = [pd.Timestamp(d) for d, _ in events]
    event_tick_labels = [f"{pd.Timestamp(d).strftime('%b')} {pd.Timestamp(d).day}" for d, _ in events]

    fig.update_yaxes(range=[0, 0.8], showgrid=False)
    fig.update_xaxes(
        showgrid=False,
        tickvals=event_dates_ts,
        ticktext=event_tick_labels,
        showticklabels=True,
    )

    return fig
