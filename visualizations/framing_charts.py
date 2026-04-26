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

    events = [
        ('2026-02-28', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-18', 'Energy Escalation'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation Returns'),
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
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.09,
            'xanchor': 'left',
            'x': 0,
        },
        margin={'l': 40, 'r': 20, 't': 100, 'b': 50}
    )

    chart.update_xaxes(
        range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-21')],
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
        ('2026-02-28', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-18', 'Energy Escalation'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation Returns'),
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
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.09, 'xanchor': 'left', 'x': 0},
        margin={'l': 40, 'r': 20, 't': 100, 'b': 50},
    )
    chart.update_xaxes(
        range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-21')],
        dtick=4 * 24 * 60 * 60 * 1000,
        tickformat='%b %d',
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

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dominant['date'].tolist(),
        y=dominant['y'].tolist(),
        marker_color=dominant['color'].tolist(),
        marker_line_width=0,
        hovertemplate='%{customdata}<extra></extra>',
        customdata=dominant['label'].tolist(),
        showlegend=False,
    ))

    fig.update_layout(
        height=36,
        margin=dict(l=40, r=20, t=0, b=0),
        bargap=0,
        bargroupgap=0,
        xaxis=dict(visible=False, range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-21')]),
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
    dominant = daily.idxmax(axis=1).reset_index()
    dominant.columns = ['date', 'dominant_dim']
    dominant = dominant.dropna(subset=['dominant_dim'])
    dominant['color'] = dominant['dominant_dim'].map(DIM_COLORS).fillna('#cccccc')
    dominant['label'] = dominant['dominant_dim'].map(DIM_LABELS).fillna('')
    dominant['y'] = 1

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dominant['date'].tolist(),
        y=dominant['y'].tolist(),
        marker_color=dominant['color'].tolist(),
        marker_line_width=0,
        hovertemplate='%{customdata}<extra></extra>',
        customdata=dominant['label'].tolist(),
        showlegend=False,
    ))

    fig.update_layout(
        height=36,
        margin=dict(l=40, r=20, t=0, b=0),
        bargap=0,
        bargroupgap=0,
        xaxis=dict(visible=False, range=[pd.Timestamp('2026-02-27'), pd.Timestamp('2026-04-21')]),
        yaxis=dict(visible=False, range=[0, 1]),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    return fig


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
        ('2026-02-28', 'Opening Strikes'),
        ('2026-03-08', 'Oil Breaks $100'),
        ('2026-03-18', 'Energy Escalation'),
        ('2026-03-27', 'Iran Strikes Saudi Base'),
        ('2026-04-05', 'Escalation Returns'),
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
    fig.update_yaxes(range=[0, 0.8], showgrid=False)
    # showticklabels=True shows date ticks below both charts (shared_xaxes hides row1 by default)
    fig.update_xaxes(
        showgrid=False,
        tickformat='%b %d',
        dtick=7 * 24 * 60 * 60 * 1000,
        showticklabels=True,
    )

    return fig
