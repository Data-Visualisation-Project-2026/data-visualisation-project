import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS


CLUSTER_NAMES = {
    0: 'Mainstream / Moderate',
    1: 'Dissident / Left-Wing',
    2: 'Smaller Mainstream',
    3: 'Business-Focused',
    4: 'Right-Wing / Military'
}

CLUSTER_COLORS = {
    'Cluster 0: Mainstream / Moderate': '#895EFF',
    'Cluster 1: Dissident / Left-Wing': '#59A14F',
    'Cluster 2: Smaller Mainstream': '#F28E2B',
    'Cluster 3: Business-Focused': '#76B7B2',
    'Cluster 4: Right-Wing / Military': '#4E79A7'
}

SCORE_COLS = [
    'kinetic_focus',
    'humanitarian_focus',
    'diplomatic_focus',
    'economic_focus',
    'culpability_bias',
]

SCORE_LABELS = {
    'kinetic_focus': 'Kinetic',
    'humanitarian_focus': 'Humanitarian',
    'diplomatic_focus': 'Diplomatic',
    'economic_focus': 'Economic',
    'culpability_bias': 'Culpability',
}

SCORE_COLORS = {
    'kinetic_focus': '#4E79A7',
    'humanitarian_focus': '#F28E2B',
    'diplomatic_focus': '#76B7B2',
    'economic_focus': '#59A14F',
    'culpability_bias': '#E15759',
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
    'cody khork', 'capt cody', 'class nicole', 'sgt class', 'episode trump',
    'positive negative', 'group stage'
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
    short_title = cluster_label

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

    fig = go.Figure(
        data=go.Heatmap(
            z=outlet_heatmap.values,
            x=outlet_heatmap.columns.tolist(),
            y=outlet_heatmap.index.tolist(),
            colorscale='Blues',
            zmin=float(outlet_heatmap.values.min()),
            zmax=float(outlet_heatmap.values.max()),
            colorbar={'title': 'Average Score'},
            text=np.round(outlet_heatmap.values, 2),
            texttemplate='%{text:.2f}',
            textfont={'size': 9},
            hovertemplate='%{y}<br>%{x}: %{z:.2f}<extra></extra>'
        )
    )

    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin={'l': 40, 'r': 40, 't': 30, 'b': 90},
        font={'color': '#263746'}
    )

    fig.update_xaxes(
        side='bottom',
        tickangle=0,
        automargin=True,
        showgrid=False,
        ticks=''
    )
    fig.update_yaxes(showgrid=False, ticks='')

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


def get_cluster_representative_articles(df, n=5):
    """Return the n articles per cluster closest to the cluster centroid (Euclidean distance)."""
    clean = df.dropna(subset=SCORE_COLS + ['article_cluster', 'title']).copy()
    clean['article_cluster'] = clean['article_cluster'].astype(int)

    centroids = clean.groupby('article_cluster')[SCORE_COLS].mean()
    rows = []

    for cluster_id, centroid in centroids.iterrows():
        cluster_df = clean[clean['article_cluster'] == cluster_id].copy()
        cluster_df['_dist'] = np.linalg.norm(
            cluster_df[SCORE_COLS].values - centroid.values, axis=1
        )
        # deduplicate by title so identical syndicated articles don't fill the list
        top = (
            cluster_df
            .sort_values('_dist')
            .drop_duplicates(subset=['title'])
            .head(n)
        )
        for _, row in top.iterrows():
            entry = {
                'cluster_id': cluster_id,
                'cluster_label': _format_cluster_label(cluster_id),
                'title': row['title'],
                'media_name': row['media_name'],
                'dist': row['_dist'],
            }
            for col in SCORE_COLS:
                entry[col] = row[col]
            rows.append(entry)

    return pd.DataFrame(rows)


def render_cluster_representative_articles_html(rep_df):
    """Return an HTML string showing representative articles per cluster with score bars."""
    sections = []

    for cluster_id in sorted(rep_df['cluster_id'].unique()):
        label = _format_cluster_label(cluster_id)
        color = CLUSTER_COLORS.get(label, '#888888')
        cluster_rows = rep_df[rep_df['cluster_id'] == cluster_id]

        article_html_parts = []
        for _, row in cluster_rows.iterrows():
            bars = ''.join(
                f'''<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
                      <span style="font-size:10px;color:#888;width:80px;flex-shrink:0;font-family:Roboto,sans-serif;">{SCORE_LABELS[col]}</span>
                      <div style="flex:1;background:#f0f0f0;border-radius:2px;height:7px;max-width:160px;">
                        <div style="width:{int(row[col]*100)}%;background:{SCORE_COLORS[col]};height:7px;border-radius:2px;"></div>
                      </div>
                      <span style="font-size:10px;color:#aaa;width:28px;text-align:right;font-family:Roboto,sans-serif;">{row[col]:.2f}</span>
                    </div>'''
                for col in SCORE_COLS
            )
            article_html_parts.append(
                f'''<div style="border:1px solid #ebebeb;border-radius:6px;padding:12px 14px;margin-bottom:10px;background:#fafafa;">
                      <div style="font-size:13px;font-weight:600;color:#263746;font-family:Georgia,serif;margin-bottom:3px;line-height:1.4;">{row["title"]}</div>
                      <div style="font-size:11px;color:#aaa;font-family:Roboto,sans-serif;margin-bottom:10px;">{row["media_name"]}</div>
                      {bars}
                    </div>'''
            )

        sections.append(
            f'''<div style="margin-bottom:28px;">
                  <div style="font-size:13px;font-weight:700;color:{color};font-family:Roboto,sans-serif;
                              border-left:3px solid {color};padding-left:8px;margin-bottom:10px;letter-spacing:0.02em;">
                    {label}
                  </div>
                  {"".join(article_html_parts)}
                </div>'''
        )

    return f'<div style="max-width:680px;">{"".join(sections)}</div>'
