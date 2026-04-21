import plotly.express as px


def make_framing_over_time_chart(df, score_cols):
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

    label_map = {
        'kinetic_focus': 'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus': 'Diplomatic',
        'economic_focus': 'Economic',
        'culpability_bias': 'Culpability Bias'
    }
    daily_long['dimension'] = daily_long['dimension'].map(label_map)

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

    chart.update_traces(
        line={'width': 2.5},
        hovertemplate='%{x|%b %d}<br>%{y:.2f}<extra>%{fullData.name}</extra>'
    )

    chart.update_layout(
        height=400,
        yaxis_range=[0.1, 0.7],
        hovermode='x unified',
        legend={
            'orientation': 'h',
            'yanchor': 'top',
            'y': -0.2,
            'xanchor': 'center',
            'x': 0.5
        },
        margin={'l': 40, 'r': 30, 't': 60, 'b': 80}
    )

    return chart
