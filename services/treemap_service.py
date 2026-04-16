"""Generate treemap data for client-side Plotly rendering + top headlines."""
import json
import logging
import base64
from db.pool import fetch_all

logger = logging.getLogger(__name__)


def build_treemap_data() -> dict:
    """Return hierarchical treemap data: Topic -> Publication.
    Two-level hierarchy with significance coloring."""

    # Topic-level aggregation
    topic_rows = fetch_all("""
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
    if not topic_rows:
        return None

    # Topic -> Publication breakdown
    pub_rows = fetch_all("""
        SELECT t.name AS topic, s.name AS source,
               COUNT(a.id) AS article_count,
               COALESCE(AVG(asig.significance_score), 2) AS avg_sig
        FROM articles a
        JOIN article_topics at2 ON at2.article_id = a.id
        JOIN topics t ON t.id = at2.topic_id
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.name, s.name
        ORDER BY t.name, article_count DESC
    """)

    labels = []
    parents = []
    values = []
    colors = []
    hover = []

    # Add topic-level nodes (parent = "")
    for r in topic_rows:
        labels.append(r["topic"])
        parents.append("")
        values.append(0)  # Plotly computes from children with branchvalues=total
        colors.append(round(float(r["avg_sig"]), 1))
        hover.append(f"{r['article_count']} articles<br>Avg: {r['avg_sig']:.1f}")

    # Add publication nodes under each topic
    for r in pub_rows:
        source = r["source"] or "Other"
        label = f"{source}"
        # Avoid duplicate labels by appending topic if needed
        full_label = f"{source} ({r['topic'][:3]})"
        labels.append(full_label)
        parents.append(r["topic"])
        values.append(int(r["article_count"]))
        colors.append(round(float(r["avg_sig"]), 1))
        hover.append(f"{source}<br>{r['article_count']} articles<br>Avg: {r['avg_sig']:.1f}")

    return {"labels": labels, "values": values, "colors": colors, "hover": hover, "parents": parents}


def build_top_headlines(limit: int = 8) -> list[dict]:
    """Top headlines by significance."""
    return fetch_all("""
        SELECT a.title, a.url, s.name AS source_name,
               COALESCE(asig.significance_score, 0) AS sig_score,
               asent.label AS sentiment
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
          AND asig.significance_score IS NOT NULL
        ORDER BY asig.significance_score DESC
        LIMIT :limit
    """, {"limit": limit})


def build_treemap_html() -> str:
    """Build treemap HTML: chart div + top headlines."""
    data = build_treemap_data()
    if not data:
        return "<p>No scored articles yet. Check back soon.</p>"

    chart_json = json.dumps(data)
    b64 = base64.b64encode(chart_json.encode()).decode()

    headlines = build_top_headlines(8)
    hl_html = ""
    if headlines:
        hl_items = []
        for h in headlines:
            color = "#dc2626" if h["sig_score"] >= 7 else "#f59e0b" if h["sig_score"] >= 5 else "#3b82f6" if h["sig_score"] >= 3 else "#9ca3af"
            hl_items.append(
                f'<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:4px;">'
                f'<span style="background:{color};color:white;font-size:0.6rem;padding:1px 5px;border-radius:4px;font-weight:700;min-width:28px;text-align:center;">{h["sig_score"]:.1f}</span>'
                f'<a href="{h["url"]}" target="_blank" style="font-size:0.8rem;text-decoration:none;">{h["title"][:70]}</a>'
                f'<span style="font-size:0.65rem;color:#6b7280;">{h.get("source_name", "")}</span>'
                f'</div>'
            )
        hl_html = '<div style="margin-top:12px;"><p style="font-size:0.75rem;font-weight:600;color:#374151;margin-bottom:6px;">Top Stories by Significance</p>' + "".join(hl_items) + '</div>'

    return (
        f'<div id="treemap-chart" class="treemap-pending" data-treemap="{b64}" '
        f'style="width:100%;height:320px;border-radius:8px;background:#f9fafb;"></div>'
        f'{hl_html}'
    )
