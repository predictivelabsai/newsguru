from fasthtml.common import *
from monsterui.all import *


def TrendingWidget(topics: list[dict]):
    if not topics:
        return Card(
            H4(
                DivLAligned(UkIcon("trending-up", height=18), Span("Trending")),
                cls="font-semibold",
            ),
            P("No trending topics yet.", cls=TextPresets.muted_sm),
        )
    items = []
    for t in topics:
        items.append(
            DivFullySpaced(
                A(
                    DivLAligned(
                        Span("", style=f"width:10px;height:10px;border-radius:50%;background:{t['color']};display:inline-block;"),
                        Span(t["name"], cls="text-sm"),
                    ),
                    href=f"/chat/{t['slug']}",
                    cls="no-underline",
                ),
                Small(f"{t['cnt']} articles", cls=TextPresets.muted_sm),
            )
        )
    return Card(
        H4(
            DivLAligned(UkIcon("trending-up", height=18), Span("Trending")),
            cls="font-semibold",
        ),
        Div(*items, cls="space-y-2"),
        hx_get="/api/trending",
        hx_trigger="every 60s",
        hx_swap="outerHTML",
    )
