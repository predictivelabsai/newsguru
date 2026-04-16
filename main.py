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
plotly_script = Script(src="https://cdn.plot.ly/plotly-2.35.0.min.js")
plotly_renderer = Script("""
    // Auto-render any Plotly charts injected via HTMX/SSE
    function renderPendingPlotly() {
        document.querySelectorAll('.plotly-pending').forEach(function(el) {
            el.classList.remove('plotly-pending');
            try {
                var d = JSON.parse(el.getAttribute('data-plotly'));
                Plotly.newPlot(el.id, d.data, d.layout, {responsive: true, displayModeBar: false});
            } catch(e) { console.error('Plotly render error:', e); }
        });
    }
    // Run on HTMX settle (covers SSE swaps)
    document.addEventListener('htmx:afterSettle', renderPendingPlotly);
    // Also run on DOM mutation as fallback for SSE innerHTML
    new MutationObserver(renderPendingPlotly).observe(document.body, {childList: true, subtree: true});
""")
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
        plotly_script,
        plotly_renderer,
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

            /* Starter question cards */
            .starter-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
            .starter-card { cursor: pointer; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px;
                            font-size: 0.8rem; transition: background 0.15s, border-color 0.15s; }
            .starter-card:hover { background: #eff6ff; border-color: #3b82f6; }

            /* Mobile */
            .mobile-tabs { display: none; }
            @media (max-width: 768px) {
                .left-pane { display: none; position: fixed; top: 56px; left: 0; bottom: 0; z-index: 50; background: white; width: 85vw; box-shadow: 2px 0 12px rgba(0,0,0,0.15); }
                .left-pane.mobile-open { display: block; }
                .right-pane { display: none; position: fixed; top: 56px; right: 0; bottom: 0; z-index: 50; background: white; width: 85vw; box-shadow: -2px 0 12px rgba(0,0,0,0.15); }
                .right-pane.mobile-open { display: block; }
                .mobile-tabs { display: flex; justify-content: space-around; border-bottom: 1px solid #e5e7eb; padding: 6px 0; }
                .mobile-tabs button { background: none; border: none; font-size: 0.75rem; padding: 4px 12px; cursor: pointer; color: #6b7280; }
                .mobile-tabs button:hover { color: #1e40af; }
                .mobile-overlay { display: none; position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,0.3); }
                .mobile-overlay.active { display: block; }
                .app-layout { height: calc(100vh - 56px); }
                .starter-grid { grid-template-columns: 1fr; }
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
from utils.i18n import t, get_lang, detect_language, LANGUAGES

# ===================== ROUTES =====================

@rt
def index(req, sess):
    """Default view: chat-first layout."""
    lang = get_lang(sess, req)
    user = _get_session_user(sess)
    chat_sess = _get_or_create_session("general")
    return _app_shell(chat_sess, lang=lang, user=user)


@rt("/topic/{topic_slug}")
def topic_view(topic_slug: str, sess):
    """Switch topic — returns the full app shell."""
    lang = get_lang(sess)
    user = _get_session_user(sess)
    chat_sess = _get_or_create_session(topic_slug)
    return _app_shell(chat_sess, active_topic=topic_slug, lang=lang, user=user)


@rt("/session/{session_id}")
def load_session(session_id: str, sess):
    """Load an existing chat session."""
    lang = get_lang(sess)
    user = _get_session_user(sess)
    chat_sess = fetch_one("SELECT id, topic_slug, title, created_at FROM chat_sessions WHERE id = :sid", {"sid": session_id})
    if not chat_sess:
        return RedirectResponse("/", status_code=303)
    return _app_shell(chat_sess, lang=lang, user=user)


@rt("/set-lang/{lang_code}")
def set_language(lang_code: str, sess):
    """Switch UI language — requires login."""
    if not sess.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    if lang_code in LANGUAGES:
        sess["lang"] = lang_code
    return RedirectResponse("/", status_code=303)


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
async def sse_feed(lang: str = "en"):
    return EventStream(_feed_generator(lang=lang))

@rt("/sse/feed/{topic_slug}")
async def sse_feed_topic(topic_slug: str, lang: str = "en"):
    return EventStream(_feed_generator(topic_slug, lang=lang))

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

async def _feed_generator(topic_slug: str = None, lang: str = "en"):
    q = topic_queues.get(topic_slug, article_queue) if topic_slug else article_queue
    while not shutdown_event.is_set():
        try:
            article = await asyncio.wait_for(q.get(), timeout=20.0)
            card = ArticleCard(article, lang=lang)
            yield sse_message(card, event="new-article")
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"


_TREEMAP_TRIGGERS = {"show me the significance heatmap", "näita mulle olulisuse kaarti",
                      "significance heatmap", "significance map", "treemap", "heatmap",
                      "olulisuse kaart", "olulisuse kaardi"}


def _is_treemap_request(messages: list[dict]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    return last.get("role") == "user" and last.get("content", "").strip().lower() in _TREEMAP_TRIGGERS


async def _chat_stream(session_id: str, messages: list[dict], topic_slug: str = None):
    # Check if this is a treemap request
    if _is_treemap_request(messages):
        async for msg in _treemap_stream(session_id):
            yield msg
        return

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


async def _treemap_stream(session_id: str):
    """Generate treemap and stream it into the chat."""
    from services.treemap_service import build_significance_treemap

    yield sse_message(
        Script("document.getElementById('thinking-text').textContent='Generating significance map...';"),
        event="token",
    )
    treemap_html = await asyncio.to_thread(build_significance_treemap)

    full_html = f'<p style="font-size:0.8rem;color:#6b7280;margin-bottom:8px;">Significance map (last 24h). Size = article count, color = significance score.</p>{treemap_html}'
    yield sse_message(
        Div(
            Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
            Div(NotStr(full_html), cls="chat-assistant"),
        ),
        event="token",
    )
    execute_sql("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:sid, 'assistant', :content)
    """, {"sid": session_id, "content": full_html})
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
def login_page(sess):
    lang = get_lang(sess)
    return Title("NewsGuru - " + t("login", lang)), _nav_bar(lang), Div(
        Card(
            DivCentered(UkIcon("newspaper", height=32), H2("NewsGuru", cls="text-2xl font-bold"),
                        P(t("sign_in_desc", lang), cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label(t("email", lang), fr="email"), Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"), cls="space-y-1"),
                Div(Label(t("password", lang), fr="password"), Input(name="password", type="password", id="password", placeholder=t("password", lang), cls="uk-input"), cls="space-y-1 mt-3"),
                Button(t("sign_in", lang), type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/login", hx_target="body",
            ),
            Div(P(t("no_account", lang), cls="text-sm text-center mt-3"), A(t("register", lang), href="/register", cls="uk-button uk-button-text"), cls="text-center"),
            cls="max-w-sm mx-auto mt-12",
        ), cls="flex justify-center p-8",
    )

@rt("/register")
def register_page(sess):
    lang = get_lang(sess)
    return Title("NewsGuru - " + t("register", lang)), _nav_bar(lang), Div(
        Card(
            DivCentered(UkIcon("newspaper", height=32), H2("NewsGuru", cls="text-2xl font-bold"),
                        P(t("create_account_desc", lang), cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label(t("display_name", lang), fr="dn"), Input(name="display_name", id="dn", placeholder=t("display_name", lang), cls="uk-input"), cls="space-y-1"),
                Div(Label(t("email", lang), fr="email"), Input(name="email", type="email", id="email", placeholder="you@example.com", cls="uk-input"), cls="space-y-1 mt-3"),
                Div(Label(t("password", lang), fr="password"), Input(name="password", type="password", id="password", placeholder=t("password", lang), cls="uk-input"), cls="space-y-1 mt-3"),
                Button(t("create_account", lang), type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/register", hx_target="body",
            ),
            Div(P(t("have_account", lang), cls="text-sm text-center mt-3"), A(t("sign_in", lang), href="/login", cls="uk-button uk-button-text"), cls="text-center"),
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

def _nav_bar(lang: str = "en", user: dict = None):
    right_items = []
    if user:
        # Logged in: show language flags + user name + logout
        lang_flags = DivLAligned(
            *[A(
                Span(info["flag"], cls="text-base" + (" opacity-40" if code != lang else "")),
                href=f"/set-lang/{code}",
                cls="no-underline",
                title=info["native"],
            ) for code, info in LANGUAGES.items()],
            cls="gap-1",
        )
        right_items = [
            lang_flags,
            Span(user.get("name", ""), cls="text-sm"),
            A(t("logout", lang), href="/auth/logout", cls="uk-button uk-button-default uk-button-small"),
        ]
    else:
        # Not logged in: just login/register, no language switcher
        right_items = [
            A(t("login", lang), href="/login", cls="uk-button uk-button-default uk-button-small"),
            A(t("register", lang), href="/register", cls="uk-button uk-button-primary uk-button-small"),
        ]
    return Div(
        A(DivLAligned(UkIcon("newspaper", height=22), Span("NewsGuru", cls="text-lg font-bold"), cls="gap-2"), href="/", cls="no-underline"),
        DivLAligned(*right_items, cls="gap-3"),
        cls="app-nav",
    )


def _app_shell(session: dict, active_topic: str = None, lang: str = "en", user: dict = None):
    """Main 3-pane app shell. Chat-first, no login required."""
    session_id = str(session["id"])
    topics = _get_topics_with_counts()
    grouped = _group_topics(topics, lang)

    # Load existing messages
    messages = fetch_all("SELECT role, content FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC", {"sid": session_id})

    # Recent articles — prioritize user's language
    recent_articles = _get_recent_articles(20, lang)

    # Build chat bubbles — always show welcome + starter cards if no messages
    msg_bubbles = [ChatMessageBubble(m["role"], m["content"]) for m in messages]
    if not messages:
        msg_bubbles.append(
            Div(
                Div(
                    P(t("welcome_title", lang), cls="font-semibold text-sm"),
                    P(t("welcome_body", lang), cls="text-sm text-muted mt-1"),
                    _starter_cards(session_id, lang),
                    cls="p-3",
                ),
                cls="chat-assistant",
            )
        )

    return (
        Title("NewsGuru"),
        _nav_bar(lang, user),
        # Mobile tab bar
        Div(
            Button(UkIcon("menu", height=14), " ", t("topics", lang), onclick="togglePane('left')", cls="text-xs"),
            Button(UkIcon("message-circle", height=14), " Chat", cls="text-xs font-semibold"),
            Button(UkIcon("rss", height=14), " ", t("live_feed", lang), onclick="togglePane('right')", cls="text-xs"),
            cls="mobile-tabs",
        ),
        # Mobile overlay
        Div(id="mobile-overlay", cls="mobile-overlay", onclick="closePanes()"),
        Script("""
            function togglePane(side) {
                var left = document.getElementById('left-pane');
                var right = document.getElementById('right-pane');
                var overlay = document.getElementById('mobile-overlay');
                if (side === 'left') {
                    left.classList.toggle('mobile-open');
                    right.classList.remove('mobile-open');
                } else {
                    right.classList.toggle('mobile-open');
                    left.classList.remove('mobile-open');
                }
                overlay.classList.toggle('active', left.classList.contains('mobile-open') || right.classList.contains('mobile-open'));
            }
            function closePanes() {
                document.getElementById('left-pane').classList.remove('mobile-open');
                document.getElementById('right-pane').classList.remove('mobile-open');
                document.getElementById('mobile-overlay').classList.remove('active');
            }
        """),
        Div(
            # ===== LEFT PANE =====
            Div(
                # New Chat + Chat History
                Div(
                    A(
                        DivLAligned(UkIcon("plus", height=16), Span("New Chat", cls="text-sm font-medium"), cls="gap-2"),
                        href="/",
                        cls="sidebar-topic no-underline",
                        style="border: 1px dashed #d1d5db; border-left: none;",
                    ),
                    *_chat_history_items(session_id),
                    cls="sidebar-section",
                ),
                # Topics + Treemap
                Div(
                    Div(t("topics", lang), cls="sidebar-section-title"),
                    *[_sidebar_topic(tpc, active=(tpc["slug"] == active_topic), lang=lang) for tpc in grouped],
                    A(
                        DivLAligned(UkIcon("grid", height=18), Span(t("heatmap", lang), cls="text-sm font-medium"), cls="gap-2"),
                        href="#",
                        cls="sidebar-topic no-underline",
                        onclick=f"document.getElementById('chat-input').value={repr(t('heatmap_prompt', lang))}; document.getElementById('chat-input').form.requestSubmit(); return false;",
                    ),
                    cls="sidebar-section",
                ),
                # Trending
                Div(
                    Div(t("trending", lang), cls="sidebar-section-title"),
                    _trending_widget(_get_trending(), lang),
                    cls="sidebar-section",
                ),
                # Sources
                Div(
                    Div(t("sources", lang), cls="sidebar-section-title"),
                    _sources_widget(_get_active_sources()),
                    cls="sidebar-section",
                ),
                # Journalists
                Div(
                    Div(t("journalists", lang), cls="sidebar-section-title"),
                    _journalist_widget(_get_top_journalists(), lang),
                    cls="sidebar-section",
                ),
                _config_panel(lang) if user else None,
                id="left-pane",
                cls="left-pane",
            ),

            # ===== CENTER PANE (always chat) =====
            Div(
                Div(*msg_bubbles, id="chat-messages", cls="feed-area"),
                Div(
                    Form(
                        DivFullySpaced(
                            Input(name="msg", id="chat-input", placeholder=t("ask_placeholder", lang), autofocus=True, cls="uk-input uk-width-expand"),
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
                H4(DivLAligned(UkIcon("rss", height=16), Span(t("live_feed", lang), cls="text-sm font-semibold"), cls="gap-2"), cls="mb-2"),
                Div(
                    Div(
                        id="live-feed-items",
                        hx_ext="sse",
                        sse_connect=f"/sse/feed?lang={lang}",
                        sse_swap="new-article",
                        hx_swap="afterbegin",
                    ),
                    *[ArticleCard(a, lang=lang) for a in recent_articles],
                    id="feed-scroll",
                    style="overflow-y: auto; max-height: calc(100vh - 120px);",
                ),
                id="right-pane",
                cls="right-pane",
            ),

            cls="app-layout",
        ),
    )


def _chat_history_items(active_session_id: str) -> list:
    """Recent chat sessions for the left pane."""
    sessions = fetch_all("""
        SELECT id, title, created_at FROM chat_sessions
        ORDER BY updated_at DESC LIMIT 8
    """)
    items = []
    for s in sessions:
        is_active = str(s["id"]) == active_session_id
        ts = s["created_at"].strftime("%b %d, %H:%M") if hasattr(s["created_at"], "strftime") else ""
        items.append(
            A(
                DivLAligned(
                    UkIcon("message-circle", height=12),
                    Div(
                        Span(s["title"][:25] + ("..." if len(s["title"]) > 25 else ""), cls="text-xs"),
                        Br(),
                        Span(ts, style="font-size:0.6rem; color:#9ca3af;"),
                    ),
                    cls="gap-1",
                ),
                href=f"/session/{s['id']}",
                cls="sidebar-topic no-underline" + (" active" if is_active else ""),
                style="padding:5px 8px;",
            )
        )
    return items


def _starter_cards(session_id: str, lang: str = "en"):
    """6 clickable starter question cards for new chats."""
    starters = [t(f"starter_{i}", lang) for i in range(1, 7)]
    icons = ["newspaper", "cpu", "landmark", "briefcase", "star", "flag"]
    cards = []
    for question, icon in zip(starters, icons):
        cards.append(
            Div(
                DivLAligned(UkIcon(icon, height=14), Span(question), cls="gap-2"),
                cls="starter-card",
                onclick=f"document.getElementById('chat-input').value={repr(question)}; document.getElementById('chat-input').form.requestSubmit(); this.closest('.starter-grid').remove();",
            )
        )
    return Div(*cards, cls="starter-grid")


def _sidebar_topic(topic: dict, active: bool = False, lang: str = "en"):
    count = topic.get("article_count", 0)
    name = topic.get("name_i18n", topic["name"])
    return A(
        DivLAligned(
            UkIcon(topic["icon"], height=18),
            Div(
                Span(name, cls="text-sm font-medium"),
                Span(f" ({count})", cls="text-xs text-muted"),
            ),
            cls="gap-2",
        ),
        href=f"/topic/{topic['slug']}",
        cls="sidebar-topic no-underline" + (" active" if active else ""),
        style=f"border-left-color: {topic['color']};" if active else "",
    )


def _trending_widget(topics: list[dict], lang: str = "en"):
    if not topics:
        return P(t("no_trending", lang), cls="text-xs text-muted px-2")
    items = []
    for tp in topics:
        items.append(
            DivFullySpaced(
                DivLAligned(
                    Span("", style=f"width:8px;height:8px;border-radius:50%;background:{tp['color']};display:inline-block;"),
                    A(tp["name"], href=f"/topic/{tp['slug']}", cls="text-xs no-underline"),
                    cls="gap-1",
                ),
                Span(f"{tp['cnt']}", cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items, hx_get="/api/trending", hx_trigger="every 60s", hx_swap="outerHTML")


def _sources_widget(sources: list[dict]):
    """Show active news sources in left pane — clickable to ask about source."""
    if not sources:
        return P("No sources yet.", cls="text-xs text-muted px-2")
    items = []
    for s in sources:
        q = f"What are the latest headlines from {s['name']}?"
        items.append(
            DivFullySpaced(
                DivLAligned(
                    Span("", style="width:6px;height:6px;border-radius:50%;background:#10b981;display:inline-block;"),
                    A(s["name"], href="#", cls="text-xs no-underline hover:underline",
                      onclick=f"document.getElementById('chat-input').value={repr(q)}; document.getElementById('chat-input').form.requestSubmit(); return false;"),
                    cls="gap-1",
                ),
                Span(str(s.get("article_count", 0)), cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items)


def _journalist_widget(journalists: list[dict], lang: str = "en"):
    if not journalists:
        return P(t("no_journalists", lang), cls="text-xs text-muted px-2")
    items = []
    for j in journalists[:7]:
        pub = f" ({j['source_name']})" if j.get("source_name") else ""
        name = j["name"]
        q = f"What has {name} been writing about recently?"
        items.append(
            DivFullySpaced(
                A(f"{name}{pub}", href="#", cls="text-xs no-underline hover:underline",
                  onclick=f"document.getElementById('chat-input').value={repr(q)}; document.getElementById('chat-input').form.requestSubmit(); return false;"),
                Span(str(j["article_count"]), cls="text-xs text-muted"),
                cls="px-2 py-0.5",
            )
        )
    return Div(*items, hx_get="/api/journalists", hx_trigger="every 120s", hx_swap="outerHTML")


def _config_panel(lang: str = "en"):
    sources = fetch_all("SELECT id, name, domain, rss_url, language, is_active FROM sources ORDER BY name")
    return Details(
        Summary(
            DivLAligned(UkIcon("settings", height=14), Span(t("configure_sources", lang), cls="text-xs font-semibold"), cls="gap-1"),
            cls="cursor-pointer list-none px-2 py-1",
        ),
        Div(
            # Language selector
            Div(
                Div(t("language", lang), cls="sidebar-section-title"),
                DivLAligned(
                    *[A(
                        DivLAligned(
                            Span(info["flag"]),
                            Span(info["native"], cls="text-xs"),
                            cls="gap-1",
                        ),
                        href=f"/set-lang/{code}",
                        cls="no-underline px-2 py-1 rounded text-xs" + (" bg-primary/10 font-semibold" if code == lang else " hover:bg-muted/50"),
                    ) for code, info in LANGUAGES.items()],
                    cls="gap-2 mb-3",
                ),
                cls="mb-2",
            ),
            Form(
                Input(name="name", placeholder=t("source_name", lang), cls="uk-input uk-form-small mb-1"),
                Input(name="domain", placeholder=t("source_domain", lang), cls="uk-input uk-form-small mb-1"),
                Input(name="rss_url", placeholder=t("rss_url", lang), cls="uk-input uk-form-small mb-1"),
                Select(Option("EN", value="en"), Option("ET", value="et"), name="language", cls="uk-select uk-form-small mb-1"),
                Button(t("add_source", lang), type="submit", cls=ButtonT.primary + " uk-button-small uk-width-1-1"),
                hx_post="/api/sources/add", hx_target="#sources-list", hx_swap="outerHTML",
            ),
            _sources_list(sources, lang),
            cls="px-2 mt-2",
        ),
        cls="sidebar-section mt-2",
    )


def _sources_list(sources: list[dict], lang: str = "en"):
    rows = []
    for s in sources:
        active_cls = "" if s["is_active"] else "opacity-50"
        btn_text = t("unsubscribe", lang) if s["is_active"] else t("subscribe", lang)
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

def _get_session_user(sess) -> dict | None:
    """Get logged-in user info from session, or None."""
    uid = sess.get("user_id") if isinstance(sess, dict) else None
    if not uid:
        return None
    return {"id": uid, "email": sess.get("user_email", ""), "name": sess.get("user_name", "")}


def _get_active_sources() -> list[dict]:
    return fetch_all("""
        SELECT s.name, s.domain, COUNT(a.id) AS article_count
        FROM sources s
        LEFT JOIN articles a ON a.source_id = s.id AND a.created_at > NOW() - INTERVAL '24 hours'
        WHERE s.is_active = true
        GROUP BY s.id, s.name, s.domain
        ORDER BY article_count DESC
    """)

def _get_recent_articles(limit: int = 20, lang: str = "en") -> list[dict]:
    """Get recent articles, prioritizing significance then user's language."""
    return fetch_all("""
        SELECT a.id, a.title, a.title_en, a.title_et, a.language, a.url, a.author, a.published_at,
               s.name AS source_name,
               asent.label AS sentiment_label, asent.score AS sentiment_score,
               asig.significance_score
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        ORDER BY COALESCE(asig.significance_score, 0) DESC,
                 CASE WHEN a.language = :lang THEN 0 ELSE 1 END,
                 a.created_at DESC
        LIMIT :limit
    """, {"limit": limit, "lang": lang})

def _group_topics(topics: list[dict], lang: str = "en") -> list[dict]:
    groups = {
        "topic_news_politics": {"slugs": ["politics", "culture"], "icon": "landmark", "color": "#ef4444"},
        "topic_business_tech": {"slugs": ["business", "technology"], "icon": "briefcase", "color": "#3b82f6"},
        "topic_sports_science": {"slugs": ["sports", "science"], "icon": "trophy", "color": "#10b981"},
    }
    result = []
    topic_map = {tp["slug"]: tp for tp in topics}
    for key, g in groups.items():
        count = sum(topic_map.get(s, {}).get("article_count", 0) for s in g["slugs"])
        result.append({"name": t(key, lang), "name_i18n": t(key, lang), "slug": g["slugs"][0],
                        "icon": g["icon"], "color": g["color"], "article_count": count, "sub_slugs": g["slugs"]})
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
