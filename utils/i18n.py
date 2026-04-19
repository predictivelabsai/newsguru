"""
Internationalization framework for NewsGuru.

Usage:
    from utils.i18n import t, detect_language, LANGUAGES

    lang = detect_language(request)  # 'et' or 'en'
    label = t('welcome', lang)       # translated string
"""

import logging

logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": {"name": "English", "flag": "\U0001f1ec\U0001f1e7", "native": "English"},
    "et": {"name": "Estonian", "flag": "\U0001f1ea\U0001f1ea", "native": "Eesti"},
}

DEFAULT_LANG = "en"

# Estonian IP ranges (RIPE NCC allocations for Estonia)
# Major Estonian ISPs: Telia, Elisa, Tele2, Starman
_ESTONIAN_IP_PREFIXES = (
    "85.253.", "90.190.", "90.191.", "80.235.", "213.168.", "195.50.",
    "62.65.", "83.137.", "86.42.", "193.40.", "194.126.", "213.184.",
    "195.222.", "217.146.", "109.235.", "185.31.", "185.51.", "188.166.",
    "46.20.", "77.233.", "88.196.", "212.47.",
)

TRANSLATIONS = {
    # Navigation
    "app_name": {"en": "NewsGuru", "et": "NewsGuru"},
    "home": {"en": "Home", "et": "Avaleht"},
    "login": {"en": "Login", "et": "Logi sisse"},
    "register": {"en": "Register", "et": "Registreeru"},
    "logout": {"en": "Logout", "et": "Logi välja"},
    "back": {"en": "Back", "et": "Tagasi"},

    # Left pane sections
    "topics": {"en": "Topics", "et": "Teemad"},
    "trending": {"en": "Trending", "et": "Populaarsed"},
    "sources": {"en": "Sources", "et": "Allikad"},
    "journalists": {"en": "Journalists", "et": "Ajakirjanikud"},
    "configure_sources": {"en": "Sources", "et": "Allikad"},

    # Topic names
    "topic_news_politics": {"en": "News & Politics", "et": "Uudised ja poliitika"},
    "topic_business_tech": {"en": "Business & Tech", "et": "Äri ja tehnoloogia"},
    "topic_sports_science": {"en": "Sports & Science", "et": "Sport ja teadus"},

    # Live feed
    "live_feed": {"en": "Live Feed", "et": "Otse"},
    "waiting_articles": {"en": "Waiting for new articles...", "et": "Ootan uusi artikleid..."},

    # Chat
    "ask_placeholder": {"en": "Ask about the news...", "et": "Küsi uudiste kohta..."},
    "welcome_title": {"en": "Welcome to NewsGuru!", "et": "Tere tulemast NewsGuru!"},
    "welcome_body": {
        "en": "I'm your AI news assistant. Ask me about the latest headlines, search for specific topics, or get analysis on trending stories. I can search the web using Tavily and Exa, and pull from our article database.",
        "et": "Olen sinu AI uudiste assistent. Küsi minult viimaste pealkirjade, konkreetsete teemade või trendivate lugude analüüsi kohta. Saan otsida veebist Tavily ja Exa abil ning kasutada meie artiklite andmebaasi.",
    },
    "welcome_examples": {
        "en": 'Try: "What\'s happening in Ukraine?", "Latest tech news", or "Summarize today\'s business headlines"',
        "et": 'Proovi: "Mis toimub Ukrainas?", "Viimased tehnikauudised" või "Kokkuvõte tänastest äriteemadest"',
    },
    "thinking": {"en": "Thinking...", "et": "Mõtlen..."},
    "searching_tavily": {"en": "Searching Tavily...", "et": "Otsin Tavilyst..."},
    "searching_exa": {"en": "Searching Exa...", "et": "Otsin Exast..."},
    "checking_articles": {"en": "Checking articles...", "et": "Kontrollin artikleid..."},
    "composing": {"en": "Composing response...", "et": "Koostan vastust..."},

    # Auth
    "sign_in": {"en": "Sign In", "et": "Logi sisse"},
    "sign_in_desc": {"en": "Sign in to your account", "et": "Logi oma kontole sisse"},
    "create_account": {"en": "Create Account", "et": "Loo konto"},
    "create_account_desc": {"en": "Create a new account", "et": "Loo uus konto"},
    "email": {"en": "Email", "et": "E-post"},
    "username": {"en": "Username", "et": "Kasutajanimi"},
    "password": {"en": "Password", "et": "Parool"},
    "display_name": {"en": "Display Name", "et": "Kuvatav nimi"},
    "no_account": {"en": "Don't have an account?", "et": "Pole kontot?"},
    "have_account": {"en": "Already have an account?", "et": "On juba konto?"},
    "invalid_credentials": {"en": "Invalid username or password.", "et": "Vale kasutajanimi või parool."},
    "missing_fields": {"en": "Username and password are required.", "et": "Kasutajanimi ja parool on kohustuslikud."},
    "password_too_short": {"en": "Password must be at least 8 characters.", "et": "Parool peab olema vähemalt 8 märki pikk."},
    "username_taken": {"en": "Username is already taken.", "et": "Kasutajanimi on juba võetud."},
    "register_to_continue_title": {"en": "Free preview limit reached", "et": "Tasuta eelvaate limiit on täis"},
    "register_to_continue_body": {
        "en": "You've used your 3 free messages. Create a free account to keep chatting.",
        "et": "Oled kasutanud oma 3 tasuta sõnumit. Loo tasuta konto, et jätkata vestlust.",
    },
    "too_many_requests": {"en": "Too many requests — please wait a moment.", "et": "Liiga palju päringuid — palun oota hetk."},

    # Config
    "add_source": {"en": "Add", "et": "Lisa"},
    "source_name": {"en": "Name", "et": "Nimi"},
    "source_domain": {"en": "domain.com", "et": "domeen.ee"},
    "rss_url": {"en": "RSS URL", "et": "RSS URL"},
    "unsubscribe": {"en": "Off", "et": "Väljas"},
    "subscribe": {"en": "On", "et": "Sees"},

    # Language
    "language": {"en": "Language", "et": "Keel"},
    "language_en": {"en": "English", "et": "Inglise"},
    "language_et": {"en": "Estonian", "et": "Eesti"},

    # Articles
    "articles_today": {"en": "articles today", "et": "artiklit täna"},
    "no_sources": {"en": "No sources yet.", "et": "Allikaid pole veel."},
    "no_journalists": {"en": "No journalists tracked yet.", "et": "Ajakirjanikke pole veel jälgitud."},
    "no_trending": {"en": "No trending topics yet.", "et": "Populaarseid teemasid pole veel."},

    # Heatmap / Treemap
    "heatmap": {"en": "Significance Map", "et": "Olulisuse kaart"},
    "heatmap_prompt": {"en": "Show me the significance heatmap", "et": "Näita mulle olulisuse kaarti"},
    "generating_treemap": {"en": "Generating treemap...", "et": "Genereerin kaarti..."},
    "analyzing_data": {"en": "Analyzing article data...", "et": "Analüüsin artiklite andmeid..."},

    # Starter question cards
    "starter_1": {"en": "What are the main news today?", "et": "Millised on tänased peamised uudised?"},
    "starter_2": {"en": "Latest developments in AI and technology", "et": "Viimased arengud tehisintellektis ja tehnoloogias"},
    "starter_3": {"en": "What's happening in global politics?", "et": "Mis toimub maailmapoliitikas?"},
    "starter_4": {"en": "Top business and market headlines", "et": "Peamised äri- ja turguuudised"},
    "starter_5": {"en": "Most significant events this week", "et": "Selle nädala olulisimad sündmused"},
    "starter_6": {"en": "What are Estonian media reporting?", "et": "Millest kirjutab Eesti meedia?"},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Get translated string. Falls back to English, then to key."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("en", key))


def detect_language(request) -> str:
    """Detect language from IP address. Returns 'et' for Estonian IPs, 'en' otherwise."""
    try:
        client_ip = _get_client_ip(request)
        if client_ip and any(client_ip.startswith(prefix) for prefix in _ESTONIAN_IP_PREFIXES):
            return "et"
    except Exception:
        pass
    return DEFAULT_LANG


def _get_client_ip(request) -> str | None:
    """Extract client IP from request, checking X-Forwarded-For for proxied requests."""
    # Check X-Forwarded-For (Coolify/reverse proxy)
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Check X-Real-IP
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    # Direct connection
    if hasattr(request, "client") and request.client:
        return request.client.host
    return None


def get_lang(sess, request=None) -> str:
    """Get language from session, or detect from IP if not set."""
    if isinstance(sess, dict) and sess.get("lang"):
        return sess["lang"]
    if request:
        detected = detect_language(request)
        if isinstance(sess, dict):
            sess["lang"] = detected
        return detected
    return DEFAULT_LANG
