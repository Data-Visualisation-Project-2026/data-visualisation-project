import json

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
            'average_score': 'Average Score',
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

    # Mark major war events that help explain shifts in framing.
    events = [
        ('2026-02-28', 'Opening Strikes', 'left'),
        ('2026-03-08', 'Oil Breaks $100', 'right'),
        ('2026-03-18', 'Energy Escalation', 'right'),
        ('2026-03-27', 'Iran Strikes US Base in Saudi Arabia', 'right'),
    ]

    for event_date, event_label, label_anchor in events:
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
            xanchor=label_anchor,
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
        legend={
            'orientation': 'v',
            'yanchor': 'top',
            'y': 1,
            'xanchor': 'left',
            'x': 1.02
        },
        margin={'l': 40, 'r': 140, 't': 60, 'b': 50}
    )

    chart.update_xaxes(
        dtick=4 * 24 * 60 * 60 * 1000,
        tickformat='%b %d',
        showgrid=False
    )

    chart.update_yaxes(showgrid=False)

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
        labels={'date': '', 'average_score': 'Average Score', 'dimension': 'Dimension'},
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
        ('2026-03-01', 'Opening Strikes', 'right'),
        ('2026-03-08', 'Oil Breaks $100', 'right'),
        ('2026-03-27', 'Iran Strikes US Base in Saudi Arabia', 'right'),
        ('2026-04-05', 'Escalation Returns', 'right'),
        ('2026-04-08', 'Ceasefire', 'right'),
    ]
    for event_date, label, anchor in events:
        ts = pd.Timestamp(event_date)
        chart.add_shape(type='line', xref='x', yref='paper',
                        x0=ts, x1=ts, y0=0, y1=1,
                        line={'width': 1, 'dash': 'dash', 'color': 'rgba(90,90,90,0.55)'})
        chart.add_annotation(x=ts, y=1.02, xref='x', yref='paper',
                             text=label, showarrow=False,
                             xanchor=anchor, yanchor='bottom',
                             font={'size': 11, 'color': 'rgba(70,70,70,0.9)'})

    chart.update_layout(
        height=450,
        yaxis_range=[0, 0.8],
        hovermode='x unified',
        title_text='',
        legend={'orientation': 'v', 'yanchor': 'top', 'y': 1, 'xanchor': 'left', 'x': 1.02},
        margin={'l': 40, 'r': 140, 't': 60, 'b': 50},
    )
    chart.update_xaxes(dtick=4 * 24 * 60 * 60 * 1000, tickformat='%b %d', showgrid=False)
    chart.update_yaxes(showgrid=False)

    return chart


def make_combined_aggregate_chart(df, score_cols, score_labels, timeline_path, highlighted_dimensions):
    """US (top) and international (bottom) aggregate as a shared-x subplot — event lines join across both."""
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

    # ── Subplot figure ─────────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=[
            '77 US Outlets — domestic media',
            'AP · Reuters · BBC · Al Jazeera — international wire services',
        ],
    )

    for dim in score_cols:
        label = score_labels[dim]
        is_highlighted = label in highlighted_dimensions
        color  = color_map[label]
        width  = 3.5 if is_highlighted else 1.5
        opacity = 1.0 if is_highlighted else 0.2

        fig.add_trace(go.Scatter(
            x=daily_us['publish_date'], y=daily_us[dim],
            name=label, legendgroup=label, showlegend=True,
            line=dict(color=color, width=width), opacity=opacity,
            hovertemplate=f'{label}: %{{y:.2f}}<extra></extra>',
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=daily_intl['date'], y=daily_intl[dim],
            name=label, legendgroup=label, showlegend=False,
            line=dict(color=color, width=width), opacity=opacity,
            hovertemplate=f'{label}: %{{y:.2f}}<extra></extra>',
        ), row=2, col=1)

    # ── Event lines — span both subplots via paper coordinates ────────────
    events = [
        ('2026-02-28', 'Opening Strikes',                     'left'),
        ('2026-03-08', 'Oil Breaks $100',                     'right'),
        ('2026-03-18', 'Energy Escalation',                   'right'),
        ('2026-03-27', 'Iran Strikes US Base in Saudi Arabia','right'),
        ('2026-04-05', 'Escalation Returns',                  'right'),
        ('2026-04-08', 'Ceasefire',                           'right'),
    ]

    for event_date, label, anchor in events:
        ts = pd.Timestamp(event_date)
        fig.add_vline(
            x=ts,
            line_width=1, line_dash='dash',
            line_color='rgba(90,90,90,0.45)',
        )
        fig.add_annotation(
            x=ts, y=1.04, xref='x', yref='paper',
            text=label, showarrow=False,
            xanchor=anchor, yanchor='bottom',
            font={'size': 10, 'color': 'rgba(70,70,70,0.85)'},
        )

    fig.update_layout(
        height=1150,
        hovermode='x unified',
        legend={
            'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02,
            'xanchor': 'center', 'x': 0.5,
        },
        margin={'l': 40, 'r': 40, 't': 100, 'b': 50},
    )
    fig.update_yaxes(range=[0, 0.8], showgrid=False)
    fig.update_xaxes(showgrid=False, tickformat='%b %d',
                     dtick=7 * 24 * 60 * 60 * 1000)

    return fig
