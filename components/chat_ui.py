from fasthtml.common import *
from monsterui.all import *
from db.pool import fetch_all


def ChatMessageBubble(role: str, content: str):
    cls = "chat-user" if role == "user" else "chat-assistant"
    return Div(
        Div(NotStr(content) if role == "assistant" else content, cls="text-sm"),
        cls=cls,
    )


def ChatInterface(session: dict, topic: dict):
    session_id = session["id"]
    messages = fetch_all("""
        SELECT role, content FROM chat_messages
        WHERE session_id = :sid ORDER BY created_at ASC
    """, {"sid": str(session_id)})

    msg_bubbles = [ChatMessageBubble(m["role"], m["content"]) for m in messages]

    if not messages:
        msg_bubbles.append(
            Div(
                Div(
                    P(f"Welcome! I'm your {topic['name']} news assistant.", cls="font-semibold text-sm"),
                    P("Ask me about the latest headlines, trends, or any topic. I can search the web using Tavily and Exa, analyze sentiment, and provide context from multiple sources.", cls="text-sm text-muted"),
                    cls="p-3",
                ),
                cls="chat-assistant",
            )
        )

    return Card(
        DivLAligned(
            Span("", style=f"width:12px;height:12px;border-radius:50%;background:{topic['color']};display:inline-block;"),
            H3(f"{topic['name']} Chat", cls="text-lg font-semibold mb-0"),
        ),
        Div(*msg_bubbles, id="chat-messages", cls="space-y-2 mb-4"),
        Form(
            DivFullySpaced(
                Input(
                    name="msg",
                    id="chat-input",
                    placeholder=f"Ask about {topic['name'].lower()} news...",
                    autofocus=True,
                    cls="uk-input uk-width-expand",
                ),
                Button(
                    UkIcon("send", height=16),
                    type="submit",
                    cls=ButtonT.primary,
                ),
                cls="gap-2",
            ),
            hx_post=f"/chat/{session_id}/send",
            hx_target="#chat-messages",
            hx_swap="beforeend",
            hx_on__before_request="document.getElementById('chat-input').disabled=true;",
            hx_on__after_request="this.reset();",
        ),
        cls="h-full",
    )


def ChatSessionList(sessions: list[dict], topic_slug: str, active_id: str = None):
    items = []
    for s in sessions:
        is_active = str(s["id"]) == str(active_id)
        items.append(
            A(
                Div(
                    P(s["title"], cls="text-xs font-medium truncate"),
                    Small(
                        s["created_at"].strftime("%b %d, %H:%M") if hasattr(s["created_at"], "strftime") else str(s["created_at"]),
                        cls="text-muted",
                        style="font-size: 0.65rem;",
                    ),
                    cls="p-1.5 rounded " + ("bg-primary/10" if is_active else "hover:bg-muted/50"),
                ),
                href=f"/chat/{topic_slug}?session={s['id']}",
                cls="no-underline",
            )
        )
    return Card(
        DivFullySpaced(
            H4("Sessions", cls="font-semibold text-sm"),
            A("Back", href="/", cls="uk-button uk-button-text uk-button-small"),
        ),
        Div(*items, cls="space-y-1") if items else P("No sessions yet.", cls=TextPresets.muted_sm),
        cls="text-xs",
    )
