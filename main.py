from fasthtml.common import *
from monsterui.all import *
from dotenv import load_dotenv
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

from utils.config import load_config, get_topics, get_topic_by_slug
from db.pool import get_db, fetch_all, fetch_one, execute_sql

config = load_config()

sse_script = Script(src="https://unpkg.com/htmx-ext-sse@2.2.3/sse.js")
pwa_headers = (
    Meta(name="apple-mobile-web-app-capable", content="yes"),
    Meta(name="apple-mobile-web-app-status-bar-style", content="black-translucent"),
    Meta(name="theme-color", content="#1e40af"),
    Link(rel="manifest", href="/manifest.json"),
)

app, rt = fast_app(
    hdrs=(
        Theme.blue.headers(highlightjs=True),
        sse_script,
        *pwa_headers,
        Style("""
            /* Layout */
            .app-layout { display: flex; gap: 0; height: calc(100vh - 60px); overflow: hidden; }
            .left-pane { width: 240px; min-width: 240px; overflow-y: auto; padding: 12px; border-right: 1px solid #e5e7eb; }
            .center-pane { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
            .right-pane { width: 380px; min-width: 380px; overflow-y: auto; padding: 12px; border-left: 1px solid #e5e7eb; }

            /* Feed area in center */
            .feed-area { flex: 1; overflow-y: auto; padding: 16px; }
            .chat-input-area { padding: 12px 16px; border-top: 1px solid #e5e7eb; }

            /* Chat messages overlay feed when active */
            #chat-messages { overflow-y: auto; padding: 0 16px; }
            #chat-messages:empty { display: none; }

            /* Topic cards in sidebar */
            .sidebar-topic { cursor: pointer; padding: 8px 10px; border-radius: 8px; border-left: 3px solid transparent;
                             transition: background 0.15s, border-color 0.15s; margin-bottom: 4px; }
            .sidebar-topic:hover { background: #f3f4f6; }
            .sidebar-topic.active { background: #eff6ff; border-left-color: #3b82f6; }

            /* Chat bubbles */
            .chat-user { background: #eff6ff; border-radius: 12px; padding: 10px 16px; margin: 6px 0; max-width: 80%; margin-left: auto; }
            .chat-assistant { background: #f8f9fa; border-radius: 12px; padding: 12px 16px; margin: 6px 0; max-width: 90%; }
            .chat-assistant h1, .chat-assistant h2, .chat-assistant h3 { margin-top: 0.75rem; margin-bottom: 0.25rem; font-size: 1rem; font-weight: 600; }
            .chat-assistant ul, .chat-assistant ol { margin: 0.25rem 0; padding-left: 1.25rem; }
            .chat-assistant li { margin-bottom: 0.15rem; }
            .chat-assistant p { margin: 0.25rem 0; }
            .chat-assistant a { color: #2563eb; text-decoration: underline; }
            .chat-assistant strong { font-weight: 600; }

            /* Sentiment */
            .sentiment-positive { color: #10b981; font-weight: 600; }
            .sentiment-negative { color: #ef4444; font-weight: 600; }
            .sentiment-neutral { color: #6b7280; font-weight: 600; }
            .feed-item { border-left: 3px solid #3b82f6; padding-left: 10px; margin-bottom: 10px; }
            .feed-meta { color: #4b5563 !important; font-weight: 500; }

            /* Thinking indicator */
            .thinking-indicator { display: flex; align-items: center; gap: 8px; color: #6b7280; font-size: 0.85rem; padding: 8px 16px; }
            .thinking-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; animation: pulse 1.4s ease-in-out infinite; }
            .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
            .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes pulse { 0%,80%,100% { opacity:0.3; transform:scale(0.8); } 40% { opacity:1; transform:scale(1.2); } }

            /* Navbar */
            .app-nav { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 1px solid #e5e7eb; height: 56px; }

            /* Sidebar sections */
            .sidebar-section { margin-bottom: 16px; }
            .sidebar-section-title { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin-bottom: 6px; padding-left: 10px; }

            /* Mobile */
            @media (max-width: 768px) {
                .left-pane { display: none; }
                .right-pane { display: none; }
                .app-layout { height: calc(100vh - 56px); }
            }
        """),
    ),
    pico=False,
)

shutdown_event = signal_shutdown()

article_queue: asyncio.Queue = asyncio.Queue()
topic_queues: dict[str, asyncio.Queue] = {}

from components.article_card import ArticleCard
from components.chat_ui import ChatMessageBubble

# ===================== ROUTES =====================

@rt
def index():
    """Default view: chat-first layout."""
    sess = _get_or_create_session("general")
    return _app_shell(sess)


@rt("/topic/{topic_slug}")
def topic_view(topic_slug: str):
    """Switch topic — returns the full app shell."""
    sess = _get_or_create_session(topic_slug)
    return _app_shell(sess, active_topic=topic_slug)


@rt("/chat/{session_id}/send", methods=["POST"])
async def chat_send(session_id: str, msg: str):
    # Save user message
    execute_sql("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:sid, 'user', :content)
    """, {"sid": session_id, "content": msg})
    execute_sql("""
        UPDATE chat_sessions SET title = :title, updated_at = NOW()
        WHERE id = :sid AND title = 'New chat'
    """, {"sid": session_id, "title": msg[:60]})

    user_bubble = ChatMessageBubble("user", msg)
    thinking = Div(
        Div(
            Span("", cls="thinking-dot"), Span("", cls="thinking-dot"), Span("", cls="thinking-dot"),
            Span("Thinking...", id="thinking-text"),
            cls="thinking-indicator",
        ),
        id="thinking-indicator",
    )
    response_area = Div(
        id=f"response-{session_id}",
        hx_ext="sse",
        sse_connect=f"/sse/chat/{session_id}",
        sse_swap="token",
        hx_swap="beforeend",
    )
    return Div(user_bubble, thinking, response_area, hx_swap_oob="beforeend:#chat-messages")


# ===================== SSE ENDPOINTS =====================

@rt("/sse/feed")
async def sse_feed():
    return EventStream(_feed_generator())

@rt("/sse/feed/{topic_slug}")
async def sse_feed_topic(topic_slug: str):
    return EventStream(_feed_generator(topic_slug))

@rt("/sse/chat/{session_id}")
async def sse_chat(session_id: str):
    messages = fetch_all("""
        SELECT role, content FROM chat_messages
        WHERE session_id = :sid ORDER BY created_at ASC
    """, {"sid": session_id})
    sess = fetch_one("SELECT topic_slug FROM chat_sessions WHERE id = :sid", {"sid": session_id})
    topic_slug = sess["topic_slug"] if sess else None
    return EventStream(_chat_stream(session_id, messages, topic_slug))


# ===================== SSE GENERATORS =====================

async def _feed_generator(topic_slug: str = None):
    q = topic_queues.get(topic_slug, article_queue) if topic_slug else article_queue
    while not shutdown_event.is_set():
        try:
            article = await asyncio.wait_for(q.get(), timeout=20.0)
            card = ArticleCard(article)
            yield sse_message(card, event="new-article")
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"


async def _chat_stream(session_id: str, messages: list[dict], topic_slug: str = None):
    from services.chat_service import get_chat_response_stream
    full_response = ""
    try:
        async for event in get_chat_response_stream(messages, topic_slug):
            if event["type"] == "status":
                yield sse_message(
                    Script(f"document.getElementById('thinking-text').textContent='{event['text']}';"),
                    event="token",
                )
            elif event["type"] == "token":
                html = event["html"]
                full_response = html
                yield sse_message(
                    Div(
                        Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
                        Div(NotStr(html), cls="chat-assistant text-sm"),
                    ),
                    event="token",
                )
    except Exception as e:
        yield sse_message(
            Div(
                Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
                Div(NotStr(f'<p class="text-red-500">Error: {e}</p>'), cls="chat-assistant"),
            ),
            event="token",
        )
    if full_response:
        execute_sql("""
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (:sid, 'assistant', :content)
        """, {"sid": session_id, "content": full_response})
    yield sse_message(
        Script("document.getElementById('chat-input').disabled=false; document.getElementById('chat-input').focus();"),
        event="token",
    )


# ===================== API ENDPOINTS =====================

@rt("/api/trending")
def api_trending():
    return _trending_widget(_get_trending())

@rt("/api/journalists")
def api_journalists():
    return _journalist_widget(_get_top_journalists())

@rt("/api/sources")
def api_sources():
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)

@rt("/api/sources/add", methods=["POST"])
def api_add_source(name: str, domain: str, rss_url: str, language: str = "en"):
    execute_sql("""
        INSERT INTO sources (name, domain, rss_url, language)
        VALUES (:name, :domain, :rss_url, :language)
        ON CONFLICT (domain) DO UPDATE SET name = EXCLUDED.name, rss_url = EXCLUDED.rss_url
    """, {"name": name, "domain": domain, "rss_url": rss_url, "language": language})
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)

@rt("/api/sources/{source_id}/toggle", methods=["POST"])
def api_toggle_source(source_id: str):
    execute_sql("UPDATE sources SET is_active = NOT is_active WHERE id = :id", {"id": source_id})
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)


# ===================== AUTH ROUTES =====================

@rt("/login")
def login_page():
    return Title("NewsGuru - Login"), _nav_bar(), Div(
        Card(
            DivCentered(UkIcon("newspaper", height=32), H2("NewsGuru", cls="text-2xl font-bold"),
                        P("Sign in to your account", cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label("Email", fr="email"), Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"), cls="space-y-1"),
                Div(Label("Password", fr="password"), Input(name="password", type="password", id="password", placeholder="Password", cls="uk-input"), cls="space-y-1 mt-3"),
                Button("Sign In", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/login", hx_target="body",
            ),
            Div(P("Don't have an account?", cls="text-sm text-center mt-3"), A("Register", href="/register", cls="uk-button uk-button-text"), cls="text-center"),
            cls="max-w-sm mx-auto mt-12",
        ), cls="flex justify-center p-8",
    )

@rt("/register")
def register_page():
    return Title("NewsGuru - Register"), _nav_bar(), Div(
        Card(
            DivCentered(UkIcon("newspaper", height=32), H2("NewsGuru", cls="text-2xl font-bold"),
                        P("Create a new account", cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label("Display Name", fr="dn"), Input(name="display_name", id="dn", placeholder="Your name", cls="uk-input"), cls="space-y-1"),
                Div(Label("Email", fr="email"), Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"), cls="space-y-1 mt-3"),
                Div(Label("Password", fr="password"), Input(name="password", type="password", id="password", placeholder="Password", cls="uk-input"), cls="space-y-1 mt-3"),
                Button("Create Account", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/register", hx_target="body",
            ),
            Div(P("Already have an account?", cls="text-sm text-center mt-3"), A("Sign In", href="/login", cls="uk-button uk-button-text"), cls="text-center"),
            cls="max-w-sm mx-auto mt-12",
        ), cls="flex justify-center p-8",
    )

@rt("/auth/login", methods=["POST"])
def auth_login(email: str, password: str, sess):
    user = fetch_one("SELECT id, email, display_name FROM users WHERE email = :email", {"email": email})
    if not user: return RedirectResponse("/login", status_code=303)
    sess["user_id"] = str(user["id"]); sess["user_email"] = user["email"]; sess["user_name"] = user.get("display_name", email)
    return RedirectResponse("/", status_code=303)

@rt("/auth/register", methods=["POST"])
def auth_register(display_name: str, email: str, password: str, sess):
    existing = fetch_one("SELECT id FROM users WHERE email = :email", {"email": email})
    if existing: return RedirectResponse("/login", status_code=303)
    execute_sql("INSERT INTO users (email, display_name) VALUES (:email, :name)", {"email": email, "name": display_name})
    user = fetch_one("SELECT id, email, display_name FROM users WHERE email = :email", {"email": email})
    sess["user_id"] = str(user["id"]); sess["user_email"] = user["email"]; sess["user_name"] = user.get("display_name", email)
    return RedirectResponse("/", status_code=303)

@rt("/auth/logout")
def auth_logout(sess):
    sess.clear()
    return RedirectResponse("/", status_code=303)


# ===================== LAYOUT BUILDERS =====================

def _nav_bar():
    return Div(
        A(DivLAligned(UkIcon("newspaper", height=22), Span("NewsGuru", cls="text-lg font-bold"), cls="gap-2"), href="/", cls="no-underline"),
        DivLAligned(
            A("Login", href="/login", cls="uk-button uk-button-default uk-button-small"),
            A("Register", href="/register", cls="uk-button uk-button-primary uk-button-small"),
            cls="gap-2",
        ),
        cls="app-nav",
    )


def _app_shell(session: dict, active_topic: str = None):
    """Main 3-pane app shell. Chat-first, no login required."""
    session_id = str(session["id"])
    topic_slug = session.get("topic_slug", "general")
    topics = _get_topics_with_counts()
    grouped = _group_topics(topics)

    # Load existing messages
    messages = fetch_all("SELECT role, content FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC", {"sid": session_id})

    # Recent articles for right pane feed
    recent_articles = _get_recent_articles(20)

    # Build chat bubbles — always show welcome if no messages
    msg_bubbles = [ChatMessageBubble(m["role"], m["content"]) for m in messages]
    if not messages:
        msg_bubbles.append(
            Div(
                Div(
                    P("Welcome to NewsGuru!", cls="font-semibold text-sm"),
                    P("I'm your AI news assistant. Ask me about the latest headlines, search for specific topics, or get analysis on trending stories. I can search the web using Tavily and Exa, and pull from our article database.", cls="text-sm text-muted mt-1"),
                    P("Try: \"What's happening in Ukraine?\", \"Latest tech news\", or \"Summarize today's business headlines\"", cls="text-xs text-muted mt-2 italic"),
                    cls="p-3",
                ),
                cls="chat-assistant",
            )
        )

    return (
        Title("NewsGuru"),
        _nav_bar(),
        Div(
            # ===== LEFT PANE =====
            Div(
                # Topic cards
                Div(
                    Div("Topics", cls="sidebar-section-title"),
                    *[_sidebar_topic(t, active=(t["slug"] == active_topic)) for t in grouped],
                    cls="sidebar-section",
                ),
                # Trending
                Div(
                    Div("Trending", cls="sidebar-section-title"),
                    _trending_widget(_get_trending()),
                    cls="sidebar-section",
                ),
                # Sources (news outlets)
                Div(
                    Div("Sources", cls="sidebar-section-title"),
                    _sources_widget(_get_active_sources()),
                    cls="sidebar-section",
                ),
                # Journalists
                Div(
                    Div("Journalists", cls="sidebar-section-title"),
                    _journalist_widget(_get_top_journalists()),
                    cls="sidebar-section",
                ),
                # Config
                _config_panel(),
                cls="left-pane",
            ),

            # ===== CENTER PANE (always chat) =====
            Div(
                Div(*msg_bubbles, id="chat-messages", cls="feed-area"),
                Div(
                    Form(
                        DivFullySpaced(
                            Input(name="msg", id="chat-input", placeholder="Ask about the news...", autofocus=True, cls="uk-input uk-width-expand"),
                            Button(UkIcon("send", height=16), type="submit", cls=ButtonT.primary),
                            cls="gap-2",
                        ),
                        hx_post=f"/chat/{session_id}/send",
                        hx_target="#chat-messages",
                        hx_swap="beforeend",
                        hx_on__before_request="document.getElementById('chat-input').disabled=true;",
                        hx_on__after_request="this.reset();",
                    ),
                    cls="chat-input-area",
                ),
                cls="center-pane",
            ),

            # ===== RIGHT PANE (always visible — live feed) =====
            Div(
                H4(DivLAligned(UkIcon("rss", height=16), Span("Live Feed", cls="text-sm font-semibold"), cls="gap-2"), cls="mb-2"),
                Div(
                    Div(
                        id="live-feed-items",
                        hx_ext="sse",
                        sse_connect="/sse/feed",
                        sse_swap="new-article",
                        hx_swap="afterbegin",
                    ),
                    *[ArticleCard(a) for a in recent_articles],
                    id="feed-scroll",
                    style="overflow-y: auto; max-height: calc(100vh - 120px);",
                ),
                id="right-pane",
                cls="right-pane",
            ),

            cls="app-layout",
        ),
    )


def _sidebar_topic(topic: dict, active: bool = False):
    count = topic.get("article_count", 0)
    return A(
        DivLAligned(
            UkIcon(topic["icon"], height=18),
            Div(
                Span(topic["name"], cls="text-sm font-medium"),
                Span(f" ({count})", cls="text-xs text-muted"),
            ),
            cls="gap-2",
        ),
        href=f"/topic/{topic['slug']}",
        cls="sidebar-topic no-underline" + (" active" if active else ""),
        style=f"border-left-color: {topic['color']};" if active else "",
    )


def _trending_widget(topics: list[dict]):
    if not topics:
        return P("No trending topics yet.", cls="text-xs text-muted px-2")
    items = []
    for t in topics:
        items.append(
            DivFullySpaced(
                DivLAligned(
                    Span("", style=f"width:8px;height:8px;border-radius:50%;background:{t['color']};display:inline-block;"),
                    A(t["name"], href=f"/topic/{t['slug']}", cls="text-xs no-underline"),
                    cls="gap-1",
                ),
                Span(f"{t['cnt']}", cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items, hx_get="/api/trending", hx_trigger="every 60s", hx_swap="outerHTML")


def _sources_widget(sources: list[dict]):
    """Show active news sources in left pane."""
    if not sources:
        return P("No sources yet.", cls="text-xs text-muted px-2")
    items = []
    for s in sources:
        items.append(
            DivFullySpaced(
                DivLAligned(
                    Span("", style=f"width:6px;height:6px;border-radius:50%;background:#10b981;display:inline-block;"),
                    Span(s["name"], cls="text-xs"),
                    cls="gap-1",
                ),
                Span(str(s.get("article_count", 0)), cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items)


def _journalist_widget(journalists: list[dict]):
    if not journalists:
        return P("No journalists tracked yet.", cls="text-xs text-muted px-2")
    items = []
    for j in journalists[:7]:
        pub = f" ({j['source_name']})" if j.get("source_name") else ""
        items.append(
            DivFullySpaced(
                Span(f"{j['name']}{pub}", cls="text-xs"),
                Span(str(j["article_count"]), cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items, hx_get="/api/journalists", hx_trigger="every 120s", hx_swap="outerHTML")


def _config_panel():
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return Details(
        Summary(
            DivLAligned(UkIcon("settings", height=14), Span("Sources", cls="text-xs font-semibold"), cls="gap-1"),
            cls="cursor-pointer list-none px-2 py-1",
        ),
        Div(
            Form(
                Input(name="name", placeholder="Name", cls="uk-input uk-form-small mb-1"),
                Input(name="domain", placeholder="domain.com", cls="uk-input uk-form-small mb-1"),
                Input(name="rss_url", placeholder="RSS URL", cls="uk-input uk-form-small mb-1"),
                Select(Option("EN", value="en"), Option("ET", value="et"), name="language", cls="uk-select uk-form-small mb-1"),
                Button("Add", type="submit", cls=ButtonT.primary + " uk-button-small uk-width-1-1"),
                hx_post="/api/sources/add", hx_target="#sources-list", hx_swap="outerHTML",
            ),
            _sources_list(sources),
            cls="px-2 mt-2",
        ),
        cls="sidebar-section mt-2",
    )


def _sources_list(sources: list[dict]):
    rows = []
    for s in sources:
        active_cls = "" if s["is_active"] else "opacity-50"
        btn_text = "Off" if s["is_active"] else "On"
        btn_cls = "uk-button-danger" if s["is_active"] else "uk-button-primary"
        rows.append(
            DivFullySpaced(
                Span(s["name"], cls=f"text-xs {active_cls}"),
                Button(btn_text, cls=f"uk-button {btn_cls} uk-button-small", style="padding:2px 8px; font-size:0.65rem;",
                       hx_post=f"/api/sources/{s['id']}/toggle", hx_target="#sources-list", hx_swap="outerHTML"),
                cls="py-0.5",
            )
        )
    return Div(*rows, id="sources-list")


# ===================== HELPERS =====================

def _get_active_sources() -> list[dict]:
    return fetch_all("""
        SELECT s.name, s.domain, COUNT(a.id) AS article_count
        FROM sources s
        LEFT JOIN articles a ON a.source_id = s.id AND a.created_at > NOW() - INTERVAL '24 hours'
        WHERE s.is_active = true
        GROUP BY s.id, s.name, s.domain
        ORDER BY article_count DESC
    """)

def _get_recent_articles(limit: int = 20) -> list[dict]:
    return fetch_all("""
        SELECT a.id, a.title, a.url, a.author, a.published_at,
               s.name AS source_name,
               asent.label AS sentiment_label, asent.score AS sentiment_score
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        ORDER BY a.created_at DESC
        LIMIT :limit
    """, {"limit": limit})

def _group_topics(topics: list[dict]) -> list[dict]:
    groups = {
        "News & Politics": {"slugs": ["politics", "culture"], "icon": "landmark", "color": "#ef4444"},
        "Business & Tech": {"slugs": ["business", "technology"], "icon": "briefcase", "color": "#3b82f6"},
        "Sports & Science": {"slugs": ["sports", "science"], "icon": "trophy", "color": "#10b981"},
    }
    result = []
    topic_map = {t["slug"]: t for t in topics}
    for name, g in groups.items():
        count = sum(topic_map.get(s, {}).get("article_count", 0) for s in g["slugs"])
        result.append({"name": name, "slug": g["slugs"][0], "icon": g["icon"], "color": g["color"],
                        "article_count": count, "sub_slugs": g["slugs"]})
    return result

def _get_topics_with_counts() -> list[dict]:
    return fetch_all("""
        SELECT t.name, t.slug, t.icon, t.color, t.display_order,
               COALESCE(cnt.c, 0) AS article_count
        FROM topics t
        LEFT JOIN (
            SELECT at2.topic_id, COUNT(*) AS c FROM article_topics at2
            JOIN articles a ON a.id = at2.article_id
            WHERE a.created_at > NOW() - INTERVAL '24 hours'
            GROUP BY at2.topic_id
        ) cnt ON cnt.topic_id = t.id
        WHERE t.is_active = true ORDER BY t.display_order
    """)

def _get_trending() -> list[dict]:
    return fetch_all("""
        SELECT t.name, t.slug, t.color, COUNT(at2.article_id) AS cnt
        FROM topics t
        JOIN article_topics at2 ON at2.topic_id = t.id
        JOIN articles a ON a.id = at2.article_id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.id, t.name, t.slug, t.color
        ORDER BY cnt DESC LIMIT 6
    """)

def _get_top_journalists() -> list[dict]:
    return fetch_all("""
        SELECT j.name, j.article_count, s.name AS source_name
        FROM journalists j LEFT JOIN sources s ON s.id = j.source_id
        ORDER BY j.article_count DESC, j.last_seen_at DESC LIMIT 10
    """)

def _get_or_create_session(topic_slug: str) -> dict:
    sess = fetch_one("""
        SELECT id, topic_slug, title, created_at FROM chat_sessions
        WHERE topic_slug = :slug AND created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC LIMIT 1
    """, {"slug": topic_slug})
    if sess: return sess
    execute_sql("INSERT INTO chat_sessions (topic_slug, title) VALUES (:slug, 'New chat')", {"slug": topic_slug})
    return fetch_one("SELECT id, topic_slug, title, created_at FROM chat_sessions WHERE topic_slug = :slug ORDER BY created_at DESC LIMIT 1", {"slug": topic_slug})


# ===================== STARTUP =====================

@app.on_event("startup")
async def on_startup():
    for t in get_topics():
        topic_queues[t["slug"]] = asyncio.Queue()
    from services.feed_scheduler import run_feed_scheduler
    asyncio.create_task(run_feed_scheduler(config, shutdown_event, article_queue, topic_queues))

serve(port=5020)
