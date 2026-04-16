"""Generate a clean Plotly treemap of article significance by topic."""
import logging
import html as html_mod
import plotly.graph_objects as go
from db.pool import fetch_all

logger = logging.getLogger(__name__)


def build_significance_treemap() -> str:
    """Build a treemap. Size = article count, color = avg significance.
    Returns HTML div with data-plotly attribute for client-side rendering."""

    rows = fetch_all("""
        SELECT t.name AS topic,
               COUNT(a.id) AS article_count,
               COALESCE(AVG(asig.significance_score), 2) AS avg_sig
        FROM articles a
        JOIN article_topics at2 ON at2.article_id = a.id
        JOIN topics t ON t.id = at2.topic_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.id, t.name
        ORDER BY article_count DESC
    """)

    if not rows:
        return "<p>No scored articles yet. Check back soon.</p>"

    labels = []
    parents = []
    values = []
    colors = []
    hover = []

    for r in rows:
        labels.append(r["topic"])
        parents.append("")
        values.append(int(r["article_count"]))
        colors.append(float(r["avg_sig"]))
        hover.append(f"{r['article_count']} articles<br>Avg significance: {r['avg_sig']:.1f}")

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale=[[0, "#e5e7eb"], [0.3, "#93c5fd"], [0.5, "#fbbf24"], [0.7, "#f97316"], [1, "#dc2626"]],
            cmin=0, cmax=10,
            colorbar=dict(title="Score", thickness=12, len=0.8,
                          tickvals=[0, 3, 5, 7, 10], ticktext=["0", "3", "5", "7", "10"]),
            line=dict(width=2, color="white"),
        ),
        text=hover,
        textinfo="label+value",
        textfont=dict(size=14),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))

    fig.update_layout(
        margin=dict(t=5, l=5, r=5, b=5),
        height=350,
        font=dict(family="system-ui, sans-serif"),
    )

    import base64
    b64 = base64.b64encode(fig.to_json().encode()).decode()
    return f'<div id="treemap-chart" class="plotly-b64" data-plotly-b64="{b64}" style="width:100%;height:350px;border-radius:8px;background:#f9fafb;"></div>'
