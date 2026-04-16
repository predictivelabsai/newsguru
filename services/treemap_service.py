"""Generate treemap data for client-side Plotly rendering + top headlines."""
import json
import logging
import base64
from db.pool import fetch_all

logger = logging.getLogger(__name__)


def build_treemap_data() -> dict:
    """Return raw data for client-side Plotly.newPlot(). No server-side plotly needed."""
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
        return None

    labels = [r["topic"] for r in rows]
    values = [int(r["article_count"]) for r in rows]
    colors = [round(float(r["avg_sig"]), 1) for r in rows]
    hover = [f"{r['article_count']} articles<br>Avg: {r['avg_sig']:.1f}" for r in rows]

    return {"labels": labels, "values": values, "colors": colors, "hover": hover}


def build_top_headlines(limit: int = 8) -> list[dict]:
    """Get top headlines sorted by significance for display below treemap."""
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
    """Build the complete treemap HTML: chart div + top headlines."""
    data = build_treemap_data()
    if not data:
        return "<p>No scored articles yet. Check back soon.</p>"

    # Encode data as base64 JSON for safe SSE transport
    chart_json = json.dumps(data)
    b64 = base64.b64encode(chart_json.encode()).decode()

    # Top headlines
    headlines = build_top_headlines(8)
    hl_html = ""
    if headlines:
        hl_items = []
        for h in headlines:
            color = "#dc2626" if h["sig_score"] >= 7 else "#f59e0b" if h["sig_score"] >= 5 else "#3b82f6" if h["sig_score"] >= 3 else "#9ca3af"
            sent_cls = {"positive": "color:#10b981", "negative": "color:#ef4444"}.get(h.get("sentiment", ""), "color:#6b7280")
            hl_items.append(
                f'<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:4px;">'
                f'<span style="background:{color};color:white;font-size:0.6rem;padding:1px 5px;border-radius:4px;font-weight:700;min-width:28px;text-align:center;">{h["sig_score"]:.1f}</span>'
                f'<a href="{h["url"]}" target="_blank" style="font-size:0.8rem;text-decoration:none;">{h["title"][:70]}</a>'
                f'<span style="font-size:0.65rem;{sent_cls};">{h.get("source_name", "")}</span>'
                f'</div>'
            )
        hl_html = '<div style="margin-top:12px;"><p style="font-size:0.75rem;font-weight:600;color:#374151;margin-bottom:6px;">Top Stories by Significance</p>' + "".join(hl_items) + '</div>'

    return (
        f'<div id="treemap-chart" class="treemap-pending" data-treemap="{b64}" '
        f'style="width:100%;height:320px;border-radius:8px;background:#f9fafb;"></div>'
        f'{hl_html}'
    )
