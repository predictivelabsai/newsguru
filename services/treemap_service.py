"""Generate Plotly treemap of article significance by topic."""
import json
import logging
import plotly.graph_objects as go
from db.pool import fetch_all

logger = logging.getLogger(__name__)


def build_significance_treemap(lang: str = "en") -> str:
    """Build a treemap as a div + inline Plotly.newPlot script.
    Returns HTML string safe for HTMX SSE injection."""

    rows = fetch_all("""
        SELECT t.name AS topic, t.color,
               COUNT(a.id) AS article_count,
               COALESCE(AVG(asig.significance_score), 2) AS avg_significance,
               MAX(asig.significance_score) AS max_significance
        FROM articles a
        JOIN article_topics at2 ON at2.article_id = a.id
        JOIN topics t ON t.id = at2.topic_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.id, t.name, t.color
        ORDER BY article_count DESC
    """)

    if not rows:
        return "<p>No articles with significance scores yet.</p>"

    top_articles = fetch_all("""
        SELECT a.title, t.name AS topic,
               COALESCE(asig.significance_score, 2) AS significance
        FROM articles a
        JOIN article_topics at2 ON at2.article_id = a.id
        JOIN topics t ON t.id = at2.topic_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
          AND asig.significance_score IS NOT NULL
        ORDER BY asig.significance_score DESC
        LIMIT 60
    """)

    # Build hierarchy
    labels = ["All News"]
    parents = [""]
    values = [0]
    colors = [3.0]
    custom_text = [""]

    for row in rows:
        topic = row["topic"]
        labels.append(topic)
        parents.append("All News")
        values.append(int(row["article_count"]))
        colors.append(float(row["avg_significance"]))
        custom_text.append(f"{row['article_count']} articles, avg {row['avg_significance']:.1f}")

    for art in top_articles:
        title_short = art["title"][:45] + ("..." if len(art["title"]) > 45 else "")
        labels.append(title_short)
        parents.append(art["topic"])
        values.append(1)
        colors.append(float(art["significance"]))
        custom_text.append(f"Score: {art['significance']:.1f}")

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#d1d5db"],
                [0.3, "#93c5fd"],
                [0.5, "#fbbf24"],
                [0.7, "#f97316"],
                [1.0, "#dc2626"],
            ],
            cmin=0, cmax=10,
            colorbar=dict(
                title=dict(text="Significance", font=dict(size=11)),
                thickness=12, len=0.6,
                tickvals=[0, 2, 5, 7, 10],
                ticktext=["Routine", "Low", "Moderate", "High", "Critical"],
            ),
            line=dict(width=1.5, color="white"),
        ),
        text=custom_text,
        textposition="middle center",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
        branchvalues="total",
    ))

    fig.update_layout(
        margin=dict(t=10, l=5, r=5, b=5),
        font=dict(family="system-ui, sans-serif"),
        height=420,
    )

    # Serialize to JSON for client-side rendering
    fig_json = fig.to_json()
    # Escape for HTML attribute (replace quotes)
    import html as html_mod
    escaped = html_mod.escape(fig_json, quote=True)

    # Use a data attribute + class marker; a global listener renders it
    return f'<div id="treemap-chart" class="plotly-pending" data-plotly="{escaped}" style="width:100%;height:420px;background:#f9fafb;border-radius:8px;"></div>'


def build_treemap_summary() -> str:
    """Build a text summary of the treemap data for LLM analysis."""
    rows = fetch_all("""
        SELECT t.name AS topic,
               COUNT(a.id) AS article_count,
               COALESCE(AVG(asig.significance_score), 0) AS avg_significance,
               COALESCE(MAX(asig.significance_score), 0) AS max_significance
        FROM articles a
        JOIN article_topics at2 ON at2.article_id = a.id
        JOIN topics t ON t.id = at2.topic_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.id, t.name
        ORDER BY avg_significance DESC
    """)
    if not rows:
        return "No data available."
    lines = ["Topic significance summary (last 24h):"]
    for r in rows:
        lines.append(f"- {r['topic']}: {r['article_count']} articles, avg score {r['avg_significance']:.1f}, max {r['max_significance']:.1f}")
    return "\n".join(lines)
