from fasthtml.common import *
from monsterui.all import *


def JournalistPanel(journalists: list[dict]):
    if not journalists:
        return Card(
            H4(
                DivLAligned(UkIcon("pen-tool", height=18), Span("Top Journalists")),
                cls="font-semibold",
            ),
            P("No journalists tracked yet.", cls=TextPresets.muted_sm),
        )
    items = []
    for j in journalists:
        items.append(
            DivFullySpaced(
                Div(
                    Span(j["name"], cls="text-sm font-medium"),
                    Small(f" ({j.get('source_name', '')})", cls="text-muted") if j.get("source_name") else None,
                ),
                Small(f"{j['article_count']} articles", cls=TextPresets.muted_sm),
            )
        )
    return Card(
        H4(
            DivLAligned(UkIcon("pen-tool", height=18), Span("Top Journalists")),
            cls="font-semibold",
        ),
        Div(*items, cls="space-y-2"),
        hx_get="/api/journalists",
        hx_trigger="every 120s",
        hx_swap="outerHTML",
    )
