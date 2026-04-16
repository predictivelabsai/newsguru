from fasthtml.common import *
from monsterui.all import *


def ArticleCard(article: dict):
    sentiment = article.get("sentiment_label", "")
    score = article.get("sentiment_score")
    sentiment_cls = {
        "positive": "sentiment-positive",
        "negative": "sentiment-negative",
        "neutral": "sentiment-neutral",
    }.get(sentiment, "sentiment-neutral")

    sentiment_display = ""
    if score is not None:
        sentiment_display = f" ({score:+.2f})"

    source_name = article.get("source_name", "")
    author = article.get("author", "")
    pub_date = article.get("published_at", "")
    if pub_date and hasattr(pub_date, "strftime"):
        pub_date = pub_date.strftime("%H:%M")

    return Div(
        A(
            Strong(article.get("title", "Untitled"), cls="text-sm"),
            href=article.get("url", "#"),
            target="_blank",
            cls="no-underline hover:underline",
        ),
        DivLAligned(
            Small(source_name, cls="feed-meta") if source_name else None,
            Small(f"by {author}", cls="feed-meta") if author else None,
            Small(pub_date, cls="feed-meta") if pub_date else None,
            Small(
                f"{sentiment}{sentiment_display}",
                cls=sentiment_cls,
            ) if sentiment else None,
            cls="gap-2 mt-1 flex-wrap",
        ),
        cls="feed-item",
    )
