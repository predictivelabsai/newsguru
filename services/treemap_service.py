"""Generate treemap as a self-contained HTML page for iframe embedding."""
import json
import logging
from db.pool import fetch_all

logger = logging.getLogger(__name__)


def build_treemap_page() -> str:
    """Return a complete HTML page with Plotly treemap. Flat layout (topics only)."""

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
        return "<html><body><p>No data yet.</p></body></html>"

    labels = [r["topic"] for r in rows]
    values = [int(r["article_count"]) for r in rows]
    colors = [round(float(r["avg_sig"]), 1) for r in rows]
    parents = ["" for _ in rows]
    hover = [f"{r['article_count']} articles<br>Avg significance: {r['avg_sig']:.1f}" for r in rows]

    data_json = json.dumps({"labels": labels, "parents": parents, "values": values, "colors": colors, "hover": hover})

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>body{{margin:0;padding:0;overflow:hidden;font-family:system-ui,sans-serif;background:#f9fafb;}}</style>
</head><body>
<div id="chart" style="width:100%;height:100vh;"></div>
<script>
var d = {data_json};
Plotly.newPlot('chart', [{{
    type: 'treemap',
    labels: d.labels,
    parents: d.parents,
    values: d.values,
    text: d.hover,
    textinfo: 'label+value',
    textfont: {{size: 16, color: '#1f2937'}},
    hovertemplate: '<b>%{{label}}</b><br>%{{text}}<extra></extra>',
    marker: {{
        colors: d.colors,
        colorscale: [[0,'#dbeafe'],[0.3,'#93c5fd'],[0.5,'#fbbf24'],[0.7,'#f97316'],[1,'#dc2626']],
        cmin: 0,
        cmax: 10,
        colorbar: {{
            title: {{text: 'Score', font: {{size: 11}}}},
            thickness: 14,
            len: 0.85,
            tickvals: [0, 3, 5, 7, 10],
            ticktext: ['0', '3', '5', '7', '10']
        }},
        line: {{width: 2, color: 'white'}}
    }}
}}], {{
    margin: {{t: 8, l: 8, r: 8, b: 8}},
    font: {{family: 'system-ui, sans-serif'}},
    paper_bgcolor: '#f9fafb'
}}, {{responsive: true, displayModeBar: false}});
</script></body></html>"""


def build_top_headlines(limit: int = 8) -> list[dict]:
    return fetch_all("""
        SELECT a.title, a.url, s.name AS source_name,
               COALESCE(asig.significance_score, 0) AS sig_score
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
          AND asig.significance_score IS NOT NULL
        ORDER BY asig.significance_score DESC
        LIMIT :limit
    """, {"limit": limit})


def build_treemap_chat_html() -> str:
    """Build the HTML for the chat: iframe + top headlines."""
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
        hl_html = '<div style="margin-top:8px;"><p style="font-size:0.75rem;font-weight:600;color:#374151;margin-bottom:6px;">Top Stories by Significance</p>' + "".join(hl_items) + '</div>'

    return (
        f'<iframe src="/treemap-chart" style="width:100%;height:320px;border:none;border-radius:8px;" loading="lazy"></iframe>'
        f'{hl_html}'
    )
