# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv pip install -e .

# Run database migration (creates schema + seeds sources/topics from config.yaml)
python db/migrate.py

# Start the app (port 5020)
python main.py

# Run tests
python -m pytest tests/test_suite.py -v

# Capture demo video (requires app running + playwright)
python tests/capture_video.py

# Docker
docker compose up --build -d
```

## Architecture

NewsGuru is a chat-based news aggregator built on FastHTML + MonsterUI + HTMX SSE. The LLM is xAI Grok accessed via `langchain-openai`'s `ChatOpenAI` with `base_url="https://api.x.ai/v1"`.

### Request Flow

**News ingestion** (background): RSS feeds (feedparser) → deduplicate by URL → scrape full text (newspaper4k) → classify topics (keyword matching from config.yaml) → track journalists → LLM sentiment scoring → push to asyncio.Queue → SSE push to connected clients.

**Chat** (user-initiated): User POST → save message → return thinking indicator + SSE div → LLM first call with `bind_tools([search_tavily, search_exa, get_recent_articles])` → execute tool calls → second LLM call with tool results → markdown → HTML → SSE push → save response.

### Key Files

- `main.py` — All routes, SSE generators, startup hook, helper queries. The app entry point.
- `services/chat_service.py` — LangChain tool-calling with two-call pattern (first call may trigger tools, second call produces final response). Tools are `@tool`-decorated functions. Output is markdown converted to HTML via `markdown.markdown()`.
- `services/feed_scheduler.py` — Background `asyncio` loop started in `@app.on_event("startup")`. Runs every 300s (configurable). Every 3rd cycle also does Tavily discovery.
- `db/pool.py` — SQLAlchemy engine singleton with `search_path=newsguru,public`. Three helpers: `execute_sql()`, `fetch_all()`, `fetch_one()`. All use raw SQL with `:named` params.
- `config.yaml` — Topic definitions (name, slug, icon, color, keywords), RSS source URLs, LLM model/temperature settings, fetch intervals.
- `sql/schema.sql` — 12 tables under PostgreSQL schema `newsguru`. All `CREATE IF NOT EXISTS`.

### SSE Pattern

Two SSE streams: live article feed (`/sse/feed`) and chat response (`/sse/chat/{session_id}`). Both use FastHTML's `EventStream()` wrapping async generators that yield `sse_message()`. Feed generators send keepalives every 20s on timeout. Chat stream yields status updates (modifying `#thinking-text` via Script tags) then the full HTML response.

### Data Layer

No ORM models. All database access is raw SQL through `fetch_all(sql, params)` / `fetch_one(sql, params)` returning `list[dict]` / `dict | None`. The connection uses `search_path=newsguru,public` so table names don't need schema prefix in queries.

## Important Patterns

- **Assistant messages are stored as HTML**, not markdown. Use `NotStr(content)` when rendering to avoid double-escaping.
- **Topic classification is keyword-based** (from config.yaml), not LLM-based. This keeps it fast and free.
- **Tool calls are deduplicated by name** before execution in `chat_service.py`.
- **Scraping is best-effort** — if newspaper4k fails, the article is saved with just RSS metadata.
- **Global asyncio.Queue objects** (`article_queue`, `topic_queues`) are shared between the feed scheduler (producer) and SSE handlers (consumers). Use `put_nowait()` to avoid blocking.
- **FastHTML convention**: `app, rt = fast_app(...)` then `@rt` decorator for routes. `serve(port=5020)` at the bottom. No `if __name__ == "__main__"` needed.
- **MonsterUI components**: `Card`, `Grid`, `DivFullySpaced`, `DivLAligned`, `UkIcon`, `ButtonT.primary`, `TextPresets.muted_sm`. Pico CSS is disabled (`pico=False`).

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DB_URL` | Yes | PostgreSQL connection string |
| `XAI_API_KEY` | Yes | xAI Grok API (used as OpenAI-compatible) |
| `TAVILY_API_KEY` | No | Tavily web search |
| `EXA_API_KEY` | No | Exa neural search |
