from fasthtml.common import *
from monsterui.all import *


def TopicCard(topic: dict):
    article_count = topic.get("article_count", 0)
    latest = topic.get("latest_headline")
    return Card(
        DivLAligned(
            UkIcon(topic["icon"], height=28),
            Div(
                H3(topic["name"], cls="text-lg font-semibold mb-0"),
                P(f"{article_count} articles today", cls=TextPresets.muted_sm),
            ),
        ),
        P(latest, cls="line-clamp-2 text-sm mt-2") if latest else P("No articles yet", cls=TextPresets.muted_sm + " mt-2"),
        cls="topic-card",
        style=f"border-left: 4px solid {topic['color']};",
        hx_get=f"/chat/{topic['slug']}",
        hx_target="body",
        hx_push_url="true",
    )


def TopicGrid(topics: list[dict]):
    """Render 3 topic cards in a single row."""
    return Grid(*[TopicCard(t) for t in topics[:3]], cols=3, cls="gap-4")
