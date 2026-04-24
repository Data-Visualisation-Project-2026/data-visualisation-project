import pandas as pd
import plotly.express as px


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
        'Diplomatic': '#E15759',
        'Economic': '#76B7B2',
        'Culpability Bias': '#59A14F'
    }

    legend_order = list(color_map.keys())

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
        ('2026-03-18', 'Energy Escalation', 'left'),
        ('2026-03-27', 'Saudi Base Attack', 'right')
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
