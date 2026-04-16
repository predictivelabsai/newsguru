from fasthtml.common import *
from monsterui.all import *

# Language flag emoji
_FLAGS = {"en": "\U0001f1ec\U0001f1e7", "et": "\U0001f1ea\U0001f1ea"}


def _get_display_title(article: dict, lang: str = "en") -> str:
    """Get the article title in the user's language."""
    # If article is already in user's language, use original title
    article_lang = article.get("language", "en")
    if article_lang == lang:
        return article.get("title", "Untitled")
    # Try translated title
    translated = article.get(f"title_{lang}")
    if translated:
        return translated
    # Fallback to original
    return article.get("title", "Untitled")


def ArticleCard(article: dict, lang: str = "en"):
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

    # Show flag of original language
    article_lang = article.get("language", "en")
    flag = _FLAGS.get(article_lang, "")

    title = _get_display_title(article, lang)

    return Div(
        A(
            Strong(f"{flag} {title}" if flag else title, cls="text-sm"),
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
