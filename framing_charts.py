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

    # Define the interactive line chart and its visual settings.
    chart = px.line(
        daily_long,
        x='publish_date',
        y='average_score',
        color='dimension',
        title='Framing Scores Over Time',
        labels={
            'publish_date': 'Date',
            'average_score': 'Average Score',
            'dimension': 'Dimension'
        },
        color_discrete_sequence=px.colors.qualitative.T10
    )

    # Highlight selected dimensions while keeping the rest visible for context.
    for trace in chart.data:
        is_highlighted = trace.name in highlighted_dimensions
        trace.update(
            line={'width': 3.5 if is_highlighted else 1.5},
            opacity=1.0 if is_highlighted else 0.25,
            hovertemplate=f'{trace.name}: %{{y:.2f}}<extra></extra>'
        )

    chart.update_layout(
        height=550,
        yaxis_range=[0.1, 0.7],
        hovermode='x unified',
        legend={
            'orientation': 'v',
            'yanchor': 'top',
            'y': 1,
            'xanchor': 'left',
            'x': 1.02
        },
        margin={'l': 40, 'r': 140, 't': 60, 'b': 50}
    )

    return chart
