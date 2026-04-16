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

# SSE extension
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
            .topic-card { cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
            .topic-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .chat-user { background: #eff6ff; border-radius: 12px; padding: 10px 16px; margin: 6px 0; max-width: 80%; margin-left: auto; }
            .chat-assistant { background: #f8f9fa; border-radius: 12px; padding: 12px 16px; margin: 6px 0; max-width: 90%; }
            .chat-assistant h1, .chat-assistant h2, .chat-assistant h3 { margin-top: 0.75rem; margin-bottom: 0.25rem; font-size: 1rem; font-weight: 600; }
            .chat-assistant ul, .chat-assistant ol { margin: 0.25rem 0; padding-left: 1.25rem; }
            .chat-assistant li { margin-bottom: 0.15rem; }
            .chat-assistant p { margin: 0.25rem 0; }
            .chat-assistant a { color: #2563eb; text-decoration: underline; }
            .chat-assistant strong { font-weight: 600; }
            .sentiment-positive { color: #10b981; font-weight: 600; }
            .sentiment-negative { color: #ef4444; font-weight: 600; }
            .sentiment-neutral { color: #6b7280; font-weight: 600; }
            .feed-item { border-left: 3px solid #3b82f6; padding-left: 10px; margin-bottom: 10px; }
            .feed-meta { color: #4b5563 !important; font-weight: 500; }
            #chat-messages { max-height: 60vh; overflow-y: auto; }
            .thinking-indicator { display: flex; align-items: center; gap: 8px; color: #6b7280; font-size: 0.85rem; padding: 8px 0; }
            .thinking-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; animation: pulse 1.4s ease-in-out infinite; }
            .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
            .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes pulse { 0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1.2); } }
            .config-panel { transition: max-height 0.3s ease; overflow: hidden; }
            .left-pane { min-width: 200px; max-width: 200px; }
            /* Mobile responsive */
            @media (max-width: 768px) {
                .left-pane { display: none; }
                .uk-width-1-4\\@m { display: none; }
                .chat-user, .chat-assistant { max-width: 95%; }
                #chat-messages { max-height: 50vh; }
            }
            @media (max-width: 640px) {
                .uk-width-2-3\\@m, .uk-width-1-3\\@m { width: 100% !important; }
            }
        """),
    ),
    pico=False,
)

shutdown_event = signal_shutdown()

# -- Global SSE queues --
article_queue: asyncio.Queue = asyncio.Queue()
topic_queues: dict[str, asyncio.Queue] = {}

from components.layout import page_shell, NavBar_
from components.topic_cards import TopicCard, TopicGrid
from components.article_card import ArticleCard
from components.feed_panel import FeedPanel
from components.trending import TrendingWidget
from components.journalist_panel import JournalistPanel
from components.chat_ui import ChatInterface, ChatSessionList, ChatMessageBubble

# ===================== ROUTES =====================

@rt
def index():
    topics = _get_topics_with_counts()
    # Merge into 3 groups: News & Politics, Business & Tech, Sports & Culture
    grouped = _group_topics(topics)
    return page_shell(
        Grid(
            Div(
                H2("What's happening in the world?", cls="text-2xl font-bold mb-4"),
                P("Choose a topic to start chatting about the latest news.", cls=TextPresets.muted_sm),
                TopicGrid(grouped),
                Div(id="config-section", cls="mt-6"),
                _config_panel(),
                cls="uk-width-2-3@m",
            ),
            Div(
                FeedPanel(),
                TrendingWidget(_get_trending()),
                JournalistPanel(_get_top_journalists()),
                cls="uk-width-1-3@m space-y-4",
            ),
        ),
        title="NewsGuru",
    )


@rt("/chat/{topic_slug}")
def chat_page(topic_slug: str, session: str = None):
    topic = get_topic_by_slug(topic_slug)
    if not topic:
        return RedirectResponse("/", status_code=303)
    sess = _get_or_create_session(topic_slug)
    sessions = _get_recent_sessions(topic_slug)
    return page_shell(
        Div(
            Div(
                ChatSessionList(sessions, topic_slug, sess["id"]),
                cls="left-pane",
            ),
            Div(
                ChatInterface(sess, topic),
                cls="flex-1",
            ),
            Div(
                FeedPanel(topic_slug),
                cls="uk-width-1-4@m",
            ),
            cls="flex gap-4",
        ),
        title=f"NewsGuru - {topic['name']}",
    )


@rt("/chat/{session_id}/send", methods=["POST"])
async def chat_send(session_id: str, msg: str):
    # Save user message
    execute_sql("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:sid, 'user', :content)
    """, {"sid": session_id, "content": msg})
    # Update session title if first message
    execute_sql("""
        UPDATE chat_sessions SET title = :title, updated_at = NOW()
        WHERE id = :sid AND title = 'New chat'
    """, {"sid": session_id, "title": msg[:60]})

    user_bubble = ChatMessageBubble("user", msg)
    # Thinking indicator + SSE response area
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
    # Get topic slug from session
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
                # Update the thinking indicator text
                yield sse_message(
                    Script(f"document.getElementById('thinking-text').textContent='{event['text']}';"),
                    event="token",
                )
            elif event["type"] == "token":
                html = event["html"]
                full_response = html  # Already full HTML
                # Remove thinking indicator and show response
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
    # Save assistant response (store as HTML)
    if full_response:
        execute_sql("""
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (:sid, 'assistant', :content)
        """, {"sid": session_id, "content": full_response})
    # Re-enable input
    yield sse_message(
        Script("document.getElementById('chat-input').disabled=false; document.getElementById('chat-input').focus();"),
        event="token",
    )


# ===================== API ENDPOINTS =====================

@rt("/api/trending")
def api_trending():
    return TrendingWidget(_get_trending())

@rt("/api/journalists")
def api_journalists():
    return JournalistPanel(_get_top_journalists())

@rt("/api/sources")
def api_sources():
    """Get all sources for config panel."""
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)

@rt("/api/sources/add", methods=["POST"])
def api_add_source(name: str, domain: str, rss_url: str, language: str = "en"):
    """Add a new source."""
    execute_sql("""
        INSERT INTO sources (name, domain, rss_url, language)
        VALUES (:name, :domain, :rss_url, :language)
        ON CONFLICT (domain) DO UPDATE SET name = EXCLUDED.name, rss_url = EXCLUDED.rss_url
    """, {"name": name, "domain": domain, "rss_url": rss_url, "language": language})
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)

@rt("/api/sources/{source_id}/toggle", methods=["POST"])
def api_toggle_source(source_id: str):
    """Toggle source active/inactive."""
    execute_sql("UPDATE sources SET is_active = NOT is_active WHERE id = :id", {"id": source_id})
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return _sources_list(sources)


# ===================== AUTH ROUTES =====================

@rt("/login")
def login_page():
    return page_shell(
        Div(
            Card(
                DivCentered(
                    UkIcon("newspaper", height=32),
                    H2("NewsGuru", cls="text-2xl font-bold"),
                    P("Sign in to your account", cls=TextPresets.muted_sm),
                    cls="mb-4",
                ),
                Form(
                    Div(
                        Label("Email", fr="email"),
                        Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"),
                        cls="space-y-1",
                    ),
                    Div(
                        Label("Password", fr="password"),
                        Input(name="password", type="password", id="password", placeholder="Password", cls="uk-input"),
                        cls="space-y-1 mt-3",
                    ),
                    Button("Sign In", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                    hx_post="/auth/login",
                    hx_target="body",
                ),
                Div(
                    P("Don't have an account?", cls="text-sm text-center mt-3"),
                    A("Register", href="/register", cls="uk-button uk-button-text"),
                    cls="text-center",
                ),
                cls="max-w-sm mx-auto mt-12",
            ),
            cls="flex justify-center",
        ),
        title="NewsGuru - Login",
    )

@rt("/register")
def register_page():
    return page_shell(
        Div(
            Card(
                DivCentered(
                    UkIcon("newspaper", height=32),
                    H2("NewsGuru", cls="text-2xl font-bold"),
                    P("Create a new account", cls=TextPresets.muted_sm),
                    cls="mb-4",
                ),
                Form(
                    Div(
                        Label("Display Name", fr="display_name"),
                        Input(name="display_name", id="display_name", placeholder="Your name", cls="uk-input"),
                        cls="space-y-1",
                    ),
                    Div(
                        Label("Email", fr="email"),
                        Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"),
                        cls="space-y-1 mt-3",
                    ),
                    Div(
                        Label("Password", fr="password"),
                        Input(name="password", type="password", id="password", placeholder="Password", cls="uk-input"),
                        cls="space-y-1 mt-3",
                    ),
                    Button("Create Account", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                    hx_post="/auth/register",
                    hx_target="body",
                ),
                Div(
                    P("Already have an account?", cls="text-sm text-center mt-3"),
                    A("Sign In", href="/login", cls="uk-button uk-button-text"),
                    cls="text-center",
                ),
                cls="max-w-sm mx-auto mt-12",
            ),
            cls="flex justify-center",
        ),
        title="NewsGuru - Register",
    )

@rt("/auth/login", methods=["POST"])
def auth_login(email: str, password: str, sess):
    user = fetch_one("SELECT id, email, display_name FROM users WHERE email = :email", {"email": email})
    if not user:
        return RedirectResponse("/login", status_code=303)
    sess["user_id"] = str(user["id"])
    sess["user_email"] = user["email"]
    sess["user_name"] = user.get("display_name", email)
    return RedirectResponse("/", status_code=303)

@rt("/auth/register", methods=["POST"])
def auth_register(display_name: str, email: str, password: str, sess):
    existing = fetch_one("SELECT id FROM users WHERE email = :email", {"email": email})
    if existing:
        return RedirectResponse("/login", status_code=303)
    execute_sql("""
        INSERT INTO users (email, display_name) VALUES (:email, :name)
    """, {"email": email, "name": display_name})
    user = fetch_one("SELECT id, email, display_name FROM users WHERE email = :email", {"email": email})
    sess["user_id"] = str(user["id"])
    sess["user_email"] = user["email"]
    sess["user_name"] = user.get("display_name", email)
    return RedirectResponse("/", status_code=303)

@rt("/auth/logout")
def auth_logout(sess):
    sess.clear()
    return RedirectResponse("/", status_code=303)


# ===================== HELPERS =====================

def _group_topics(topics: list[dict]) -> list[dict]:
    """Merge 6 topics into 3 grouped cards."""
    groups = {
        "News & Politics": {"slugs": ["politics", "culture"], "icon": "landmark", "color": "#ef4444"},
        "Business & Tech": {"slugs": ["business", "technology"], "icon": "briefcase", "color": "#3b82f6"},
        "Sports & Science": {"slugs": ["sports", "science"], "icon": "trophy", "color": "#10b981"},
    }
    result = []
    topic_map = {t["slug"]: t for t in topics}
    for name, g in groups.items():
        count = sum(topic_map.get(s, {}).get("article_count", 0) for s in g["slugs"])
        # Pick latest headline from any sub-topic
        headline = None
        for s in g["slugs"]:
            h = topic_map.get(s, {}).get("latest_headline")
            if h:
                headline = h
                break
        # Use first slug as default chat target
        result.append({
            "name": name,
            "slug": g["slugs"][0],
            "icon": g["icon"],
            "color": g["color"],
            "article_count": count,
            "latest_headline": headline,
            "sub_slugs": g["slugs"],
        })
    return result


def _config_panel():
    """Expandable config section at bottom of home page."""
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return Details(
        Summary(
            DivLAligned(UkIcon("settings", height=16), Span("Configure Sources", cls="text-sm font-semibold")),
            cls="cursor-pointer list-none p-2",
        ),
        Div(
            # Add source form
            Form(
                Grid(
                    Input(name="name", placeholder="Source name", cls="uk-input uk-form-small"),
                    Input(name="domain", placeholder="domain.com", cls="uk-input uk-form-small"),
                    Input(name="rss_url", placeholder="RSS URL", cls="uk-input uk-form-small"),
                    Select(
                        Option("English", value="en"),
                        Option("Estonian", value="et"),
                        name="language", cls="uk-select uk-form-small",
                    ),
                    cols=4, cls="gap-2",
                ),
                Button("Add Source", type="submit", cls=ButtonT.primary + " uk-button-small mt-2"),
                hx_post="/api/sources/add",
                hx_target="#sources-list",
                hx_swap="outerHTML",
            ),
            # Sources list
            Div(id="sources-list", cls="mt-3"),
            _sources_list(sources),
            cls="p-3",
        ),
        cls="border rounded mt-4",
    )


def _sources_list(sources: list[dict]):
    """Render the list of sources with subscribe/unsubscribe toggles."""
    rows = []
    for s in sources:
        active_cls = "" if s["is_active"] else "opacity-50"
        btn_text = "Unsubscribe" if s["is_active"] else "Subscribe"
        btn_cls = "uk-button-danger uk-button-small" if s["is_active"] else "uk-button-primary uk-button-small"
        rows.append(
            DivFullySpaced(
                Div(
                    Strong(s["name"], cls="text-sm"),
                    Small(f" ({s['domain']}) [{s['language'].upper()}]", cls="text-muted"),
                    cls=active_cls,
                ),
                Button(
                    btn_text,
                    cls=f"uk-button {btn_cls}",
                    hx_post=f"/api/sources/{s['id']}/toggle",
                    hx_target="#sources-list",
                    hx_swap="outerHTML",
                ),
                cls="py-1 border-b",
            )
        )
    return Div(*rows, id="sources-list")


def _get_topics_with_counts() -> list[dict]:
    rows = fetch_all("""
        SELECT t.name, t.slug, t.icon, t.color, t.display_order,
               COALESCE(cnt.c, 0) AS article_count,
               latest.title AS latest_headline
        FROM topics t
        LEFT JOIN (
            SELECT at2.topic_id, COUNT(*) AS c
            FROM article_topics at2
            JOIN articles a ON a.id = at2.article_id
            WHERE a.created_at > NOW() - INTERVAL '24 hours'
            GROUP BY at2.topic_id
        ) cnt ON cnt.topic_id = t.id
        LEFT JOIN LATERAL (
            SELECT a.title FROM articles a
            JOIN article_topics at3 ON at3.article_id = a.id
            WHERE at3.topic_id = t.id
            ORDER BY a.created_at DESC LIMIT 1
        ) latest ON true
        WHERE t.is_active = true
        ORDER BY t.display_order
    """)
    return rows

def _get_trending() -> list[dict]:
    return fetch_all("""
        SELECT t.name, t.slug, t.color, COUNT(at2.article_id) AS cnt
        FROM topics t
        JOIN article_topics at2 ON at2.topic_id = t.id
        JOIN articles a ON a.id = at2.article_id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY t.id, t.name, t.slug, t.color
        ORDER BY cnt DESC
        LIMIT 6
    """)

def _get_top_journalists() -> list[dict]:
    return fetch_all("""
        SELECT j.name, j.article_count, s.name AS source_name
        FROM journalists j
        LEFT JOIN sources s ON s.id = j.source_id
        ORDER BY j.article_count DESC, j.last_seen_at DESC
        LIMIT 10
    """)

def _get_or_create_session(topic_slug: str) -> dict:
    sess = fetch_one("""
        SELECT id, topic_slug, title, created_at FROM chat_sessions
        WHERE topic_slug = :slug AND created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC LIMIT 1
    """, {"slug": topic_slug})
    if sess:
        return sess
    execute_sql("""
        INSERT INTO chat_sessions (topic_slug, title)
        VALUES (:slug, 'New chat')
    """, {"slug": topic_slug})
    return fetch_one("""
        SELECT id, topic_slug, title, created_at FROM chat_sessions
        WHERE topic_slug = :slug ORDER BY created_at DESC LIMIT 1
    """, {"slug": topic_slug})

def _get_recent_sessions(topic_slug: str) -> list[dict]:
    return fetch_all("""
        SELECT id, title, created_at FROM chat_sessions
        WHERE topic_slug = :slug
        ORDER BY updated_at DESC LIMIT 10
    """, {"slug": topic_slug})


# ===================== STARTUP =====================

@app.on_event("startup")
async def on_startup():
    for t in get_topics():
        topic_queues[t["slug"]] = asyncio.Queue()
    from services.feed_scheduler import run_feed_scheduler
    asyncio.create_task(run_feed_scheduler(
        config, shutdown_event, article_queue, topic_queues
    ))


serve(port=5020)
