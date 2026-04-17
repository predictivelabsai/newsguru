"""Render story clusters as HTML cards for chat responses — same visual style as live feed."""

_SENT_COLORS = {"positive": "#10b981", "negative": "#ef4444", "neutral": "#6b7280"}


def _sig_color(score):
    if score is None: return "#9ca3af"
    if score >= 7: return "#dc2626"
    if score >= 5: return "#f59e0b"
    if score >= 3: return "#3b82f6"
    return "#9ca3af"


def render_clusters_html(clusters: list[dict]) -> str:
    """Render topic clusters as HTML matching the live feed article card style."""
    if not clusters:
        return "<p style='color:#6b7280;font-size:0.85rem;'>No clustered stories found yet.</p>"

    sections = []
    for c in clusters:
        label = c.get("cluster_label", "")
        summary = c.get("summary", "")
        articles = c.get("articles", [])
        # Skip unclustered/single-source and empty clusters
        if not articles or len(articles) < 2:
            continue
        if "unclustered" in label.lower():
            continue
        # Limit to 4 articles per cluster for brevity
        articles = articles[:4]

        # Cluster header
        header = (
            f'<div style="margin-bottom:4px;">'
            f'<span style="font-size:0.85rem;font-weight:600;color:#1f2937;">{label}</span> '
            f'<span style="font-size:0.65rem;color:#9ca3af;">({len(articles)} sources)</span>'
            f'</div>'
        )
        if summary:
            header += f'<p style="font-size:0.75rem;color:#6b7280;margin:0 0 6px;">{summary}</p>'

        # Article items — same style as feed-item
        items = []
        for a in articles:
            title = a.get("title", "")[:80]
            url = a.get("url", "#")
            source = a.get("source_name", "")
            sent_score = a.get("sentiment_score")
            sent_label = a.get("sentiment_label", "")
            sent_color = _SENT_COLORS.get(sent_label, "#6b7280")

            sent_html = ""
            if sent_score is not None:
                sent_html = f'<span style="font-size:0.65rem;color:{sent_color};font-weight:600;">{sent_score:+.2f}</span>'

            items.append(
                f'<div style="border-left:3px solid #3b82f6;padding-left:8px;margin-bottom:6px;">'
                f'<a href="{url}" target="_blank" style="font-size:0.8rem;font-weight:500;text-decoration:none;color:#1f2937;"'
                f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{title}</a>'
                f'<div style="display:flex;gap:8px;align-items:baseline;margin-top:2px;">'
                f'<span style="font-size:0.65rem;color:#4b5563;font-weight:500;">{source}</span>'
                f'{sent_html}'
                f'</div></div>'
            )

        sections.append(
            f'<div style="margin-bottom:14px;">{header}{"".join(items)}</div>'
        )

    return "".join(sections)


def render_top_articles_html(articles: list[dict]) -> str:
    """Render a flat list of articles as feed-style HTML cards."""
    if not articles:
        return "<p style='color:#6b7280;font-size:0.85rem;'>No articles found.</p>"

    items = []
    for a in articles:
        title = a.get("title", "")[:80]
        url = a.get("url", "#")
        source = a.get("source_name", "")
        sig = a.get("significance_score")
        sent_score = a.get("sentiment_score")
        sent_label = a.get("sentiment_label", "")
        sent_color = _SENT_COLORS.get(sent_label, "#6b7280")

        sig_badge = ""
        if sig is not None:
            color = _sig_color(sig)
            sig_badge = f'<span style="background:{color};color:white;font-size:0.6rem;padding:1px 5px;border-radius:4px;font-weight:700;margin-right:4px;">{sig:.1f}</span>'

        sent_html = ""
        if sent_score is not None:
            sent_html = f'<span style="font-size:0.65rem;color:{sent_color};font-weight:600;">{sent_score:+.2f}</span>'

        items.append(
            f'<div style="border-left:3px solid #3b82f6;padding-left:8px;margin-bottom:6px;">'
            f'<div style="display:flex;align-items:baseline;gap:4px;">'
            f'{sig_badge}'
            f'<a href="{url}" target="_blank" style="font-size:0.8rem;font-weight:500;text-decoration:none;color:#1f2937;"'
            f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{title}</a>'
            f'</div>'
            f'<div style="display:flex;gap:8px;align-items:baseline;margin-top:2px;">'
            f'<span style="font-size:0.65rem;color:#4b5563;font-weight:500;">{source}</span>'
            f'{sent_html}'
            f'</div></div>'
        )

    return "".join(items)
