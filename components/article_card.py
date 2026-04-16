from fasthtml.common import *
from monsterui.all import *

_FLAGS = {"en": "\U0001f1ec\U0001f1e7", "et": "\U0001f1ea\U0001f1ea"}

_SENT_COLORS = {"positive": "#10b981", "negative": "#ef4444", "neutral": "#6b7280"}


def _sig_color(score):
    if score is None: return "#9ca3af"
    if score >= 7: return "#dc2626"
    if score >= 5: return "#f59e0b"
    if score >= 3: return "#3b82f6"
    return "#9ca3af"


def _get_display_title(article: dict, lang: str = "en") -> str:
    article_lang = article.get("language", "en")
    if article_lang == lang:
        return article.get("title", "Untitled")
    translated = article.get(f"title_{lang}")
    return translated if translated else article.get("title", "Untitled")


def ArticleCard(article: dict, lang: str = "en"):
    sentiment = article.get("sentiment_label", "")
    score = article.get("sentiment_score")
    sentiment_cls = {
        "positive": "sentiment-positive",
        "negative": "sentiment-negative",
        "neutral": "sentiment-neutral",
    }.get(sentiment, "sentiment-neutral")

    source_name = article.get("source_name", "")
    author = article.get("author", "")
    pub_date = article.get("published_at", "")
    if pub_date and hasattr(pub_date, "strftime"):
        pub_date = pub_date.strftime("%H:%M")

    article_lang = article.get("language", "en")
    flag = _FLAGS.get(article_lang, "")
    title = _get_display_title(article, lang)

    sig = article.get("significance_score")
    sig_badge = None
    if sig is not None:
        color = _sig_color(sig)
        sig_badge = Span(
            f"{sig:.1f}",
            style=f"background:{color}; color:white; font-size:0.6rem; padding:1px 5px; border-radius:4px; font-weight:700;",
        )

    # Related coverage from other sources (if clustered)
    related = article.get("related_coverage", [])
    related_el = None
    if related:
        chips = []
        for r in related[:3]:
            s_color = _SENT_COLORS.get(r.get("sentiment_label", ""), "#6b7280")
            s_score = r.get("sentiment_score")
            s_text = f"{s_score:+.1f}" if s_score is not None else ""
            chips.append(
                A(
                    Span(f"{r['source_name']} {s_text}", style=f"font-size:0.6rem; color:{s_color};"),
                    href=r.get("url", "#"), target="_blank",
                    cls="no-underline hover:underline",
                )
            )
        related_el = DivLAligned(
            Span("Also:", style="font-size:0.6rem; color:#9ca3af;"),
            *chips,
            cls="gap-2 mt-0.5",
        )

    return Div(
        DivLAligned(
            sig_badge,
            A(
                Strong(f"{flag} {title}" if flag else title, cls="text-sm"),
                href=article.get("url", "#"), target="_blank",
                cls="no-underline hover:underline",
            ),
            cls="gap-2",
        ),
        DivLAligned(
            Small(source_name, cls="feed-meta") if source_name else None,
            Small(f"by {author}", cls="feed-meta") if author else None,
            Small(pub_date, cls="feed-meta") if pub_date else None,
            Small(f"{score:+.2f}" if score is not None else "", cls=sentiment_cls) if score is not None else None,
            cls="gap-2 mt-1 flex-wrap",
        ),
        related_el,
        cls="feed-item",
    )
