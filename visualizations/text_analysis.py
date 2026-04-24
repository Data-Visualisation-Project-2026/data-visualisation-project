import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS


CLUSTER_NAMES = {
    0: 'Mainstream Generalist Media',
    1: 'Critical / Opposition-Leaning Media',
    2: 'Humanitarian-Diplomatic Media',
    3: 'Economically Focused Media',
    4: 'Militarized / Blame-Oriented Media'
}

CLUSTER_COLORS = {
    'Cluster 0: Mainstream Generalist Media': '#4E79A7',
    'Cluster 1: Critical / Opposition-Leaning Media': '#A0CBE8',
    'Cluster 2: Humanitarian-Diplomatic Media': '#76B7B2',
    'Cluster 3: Economically Focused Media': '#59A14F',
    'Cluster 4: Militarized / Blame-Oriented Media': '#8CD17D'
}

DOMAIN_STOP_WORDS = {
    'said', 'says', 'told', 'according', 'reported', 'reports',
    'news', 'article', 'media', 'people',
    'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years', 'time',
    'new', 'just', 'like', 'including', 'called', 'statement', 'percent',
    'reuters', 'ap',
    'des', 'les',
    'khork', 'cody', 'nicole'
}

BLOCKED_PHRASES = {
    'john yang', 'nick schifrin', 'hegseth caine', 'trump hegseth',
    'cody khork', 'capt cody', 'class nicole', 'sgt class'
}


def get_top_cluster_bigrams(df, top_n=10):
    """Compute top c-TF-IDF bigrams for each article cluster."""
    cluster_docs = _make_cluster_documents(df)
    terms, ctfidf = _compute_bigram_ctfidf(cluster_docs)

    rows = []

    for row_idx, cluster_id in enumerate(cluster_docs['article_cluster']):
        top_indices = []

        for term_idx in np.argsort(ctfidf[row_idx])[::-1]:
            if terms[term_idx] in BLOCKED_PHRASES:
                continue

            top_indices.append(term_idx)

            if len(top_indices) == top_n:
                break

        for term_idx in top_indices:
            rows.append({
                'cluster': _format_cluster_label(cluster_id),
                'term': terms[term_idx],
                'ctfidf_score': ctfidf[row_idx, term_idx]
            })

    return pd.DataFrame(rows)


def make_cluster_bigram_charts(top_terms):
    """Create one bar chart per article cluster from top bigram results."""
    return {
        cluster_label: make_cluster_bigram_chart(cluster_label, top_terms)
        for cluster_label in CLUSTER_COLORS
    }


def make_cluster_bigram_chart(cluster_label, top_terms):
    """Create a horizontal bar chart for one article cluster's top bigrams."""
    chart_data = top_terms[top_terms['cluster'] == cluster_label].sort_values('ctfidf_score')
    short_title = cluster_label.split(': ', 1)[-1]

    fig = px.bar(
        chart_data,
        x='ctfidf_score',
        y='term',
        orientation='h',
        title=short_title,
        labels={
            'ctfidf_score': 'c-TF-IDF Score',
            'term': ''
        },
        height=360
    )

    fig.update_traces(
        marker_color=CLUSTER_COLORS[cluster_label],
        hovertemplate='%{y}: %{x:.4f}<extra></extra>'
    )

    fig.update_layout(
        plot_bgcolor='#f7fafc',
        paper_bgcolor='white',
        showlegend=False,
        bargap=0.32,
        margin={'l': 150, 'r': 35, 't': 60, 'b': 50},
        title={'x': 0.02, 'xanchor': 'left', 'font': {'size': 16, 'color': '#2f4a5f'}},
        font={'color': '#263746'}
    )

    fig.update_xaxes(showgrid=True, gridcolor='#e6edf3', zeroline=False)
    fig.update_yaxes(categoryorder='array', categoryarray=chart_data['term'].tolist())

    return fig


def make_outlet_framing_heatmap(df):
    """Create an outlet-level heatmap of average framing scores for the 5-source dataset."""
    score_cols = [
        'kinetic_focus',
        'humanitarian_focus',
        'diplomatic_focus',
        'economic_focus',
        'culpability_bias'
    ]

    dimension_labels = {
        'kinetic_focus': 'Kinetic',
        'humanitarian_focus': 'Humanitarian',
        'diplomatic_focus': 'Diplomatic',
        'economic_focus': 'Economic',
        'culpability_bias': 'Culpability Bias'
    }

    outlet_labels = {
        'apnews.com': 'AP News',
        'reuters.com': 'Reuters',
        'bbc.com': 'BBC',
        'aljazeera.com': 'Al Jazeera',
        'tehrantimes.com': 'Tehran Times'
    }

    outlet_heatmap_raw = (
        df.groupby('media_name')[score_cols]
        .mean()
        .rename(index=outlet_labels, columns=dimension_labels)
    )

    column_order = outlet_heatmap_raw.mean(axis=0).sort_values(ascending=False).index.tolist()
    row_order = outlet_heatmap_raw.mean(axis=1).sort_values(ascending=False).index.tolist()
    outlet_heatmap = outlet_heatmap_raw.loc[row_order, column_order]

    fig = px.imshow(
        outlet_heatmap,
        color_continuous_scale='Blues',
        text_auto='.2f',
        aspect='auto',
        labels={'x': '', 'y': '', 'color': 'Average Score'}
    )

    fig.update_traces(textfont={'size': 9})

    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin={'l': 40, 'r': 40, 't': 110, 'b': 90},
        font={'color': '#263746'},
        coloraxis_colorbar={'title': 'Average Score'}
    )

    fig.update_xaxes(side='bottom', tickangle=0, automargin=True)

    return fig


def _make_cluster_documents(df):
    """Combine all article text in each cluster into one document."""
    return (
        df.dropna(subset=['article_text', 'article_cluster'])
        .assign(article_cluster=lambda data: data['article_cluster'].astype(int))
        .groupby('article_cluster')['article_text']
        .apply(lambda texts: ' '.join(texts.astype(str)))
        .reset_index(name='cluster_text')
    )


def _compute_bigram_ctfidf(cluster_docs):
    """Compute c-TF-IDF scores for bigrams across cluster documents."""
    stop_words = list(ENGLISH_STOP_WORDS.union(DOMAIN_STOP_WORDS))

    vectorizer = CountVectorizer(
        lowercase=True,
        strip_accents='unicode',
        stop_words=stop_words,
        ngram_range=(2, 2),
        min_df=2,
        max_df=0.75,
        token_pattern=r'(?u)\b[a-zA-Z]{3,}\b'
    )

    count_matrix = vectorizer.fit_transform(cluster_docs['cluster_text'])
    terms = vectorizer.get_feature_names_out()

    term_counts = count_matrix.toarray().astype(float)
    cluster_lengths = term_counts.sum(axis=1, keepdims=True)
    tf = np.divide(
        term_counts,
        cluster_lengths,
        out=np.zeros_like(term_counts),
        where=cluster_lengths != 0
    )

    term_presence = (term_counts > 0).sum(axis=0)
    idf = np.log((1 + len(cluster_docs)) / (1 + term_presence)) + 1
    ctfidf = tf * idf

    return terms, ctfidf


def _format_cluster_label(cluster_id):
    """Create a display label for an article cluster."""
    cluster_id = int(cluster_id)
    return f'Cluster {cluster_id}: {CLUSTER_NAMES.get(cluster_id, "Unnamed")}'
