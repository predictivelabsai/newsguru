from fasthtml.common import *
from monsterui.all import *


def FeedPanel(topic_slug: str = None):
    endpoint = f"/sse/feed/{topic_slug}" if topic_slug else "/sse/feed"
    return Card(
        H4(
            DivLAligned(
                UkIcon("rss", height=18),
                Span("Live Feed"),
            ),
            cls="font-semibold",
        ),
        Div(
            P("Waiting for new articles...", cls=TextPresets.muted_sm, id="feed-placeholder"),
            id="feed-items",
            hx_ext="sse",
            sse_connect=endpoint,
            sse_swap="new-article",
            hx_swap="afterbegin",
            style="max-height: 400px; overflow-y: auto;",
        ),
    )
