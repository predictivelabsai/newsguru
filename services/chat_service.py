import os
import json
import logging
import markdown
from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from db.pool import fetch_all
from utils.config import load_config

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        config = load_config()
        _llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["model"],
            temperature=config["llm"]["temperature"],
            max_tokens=config["llm"]["max_tokens"],
            streaming=True,
        )
    return _llm


# ---- Tool definitions ----

@tool
def search_tavily(query: str) -> str:
    """Search the web for recent news using Tavily. Use this for current events, breaking news, or when you need fresh information."""
    import asyncio
    from services.search_service import search_tavily as _search
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(asyncio.run, _search(query, 5)).result()
        else:
            results = asyncio.run(_search(query, 5))
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"- [{r['title']}]({r['url']})\n  {r['summary'][:200]}")
    return "\n".join(lines)


@tool
def search_exa(query: str) -> str:
    """Search the web using Exa neural search. Good for finding specific articles, research, or nuanced queries."""
    import asyncio
    from services.search_service import search_exa as _search
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(asyncio.run, _search(query, 5)).result()
        else:
            results = asyncio.run(_search(query, 5))
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"- [{r['title']}]({r['url']})\n  {r['summary'][:200]}")
    return "\n".join(lines)


@tool
def get_recent_articles(topic: str = "", limit: int = 10) -> str:
    """Get recent articles from the NewsGuru database, optionally filtered by topic slug (technology, politics, business, sports, science, culture)."""
    if topic:
        articles = fetch_all("""
            SELECT a.title, a.url, a.author, s.name AS source_name,
                   asent.label AS sentiment, asent.score AS sentiment_score
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_sentiments asent ON asent.article_id = a.id
            JOIN article_topics at2 ON at2.article_id = a.id
            JOIN topics t ON t.id = at2.topic_id AND t.slug = :slug
            ORDER BY a.created_at DESC LIMIT :limit
        """, {"slug": topic, "limit": limit})
    else:
        articles = fetch_all("""
            SELECT a.title, a.url, a.author, s.name AS source_name,
                   asent.label AS sentiment, asent.score AS sentiment_score
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_sentiments asent ON asent.article_id = a.id
            ORDER BY a.created_at DESC LIMIT :limit
        """, {"limit": limit})
    if not articles:
        return "No articles found."
    lines = []
    for a in articles:
        sent = f" [Sentiment: {a['sentiment']} ({a['sentiment_score']:+.2f})]" if a.get("sentiment") else ""
        src = f" - {a['source_name']}" if a.get("source_name") else ""
        lines.append(f"- {a['title']}{src}{sent}\n  URL: {a['url']}")
    return "\n".join(lines)


TOOLS = [search_tavily, search_exa, get_recent_articles]
TOOL_MAP = {t.name: t for t in TOOLS}
TOOL_LABELS = {
    "search_tavily": "Searching Tavily...",
    "search_exa": "Searching Exa...",
    "get_recent_articles": "Checking articles...",
}


def _get_recent_articles_context(topic_slug: str = None, limit: int = 10) -> str:
    if topic_slug:
        articles = fetch_all("""
            SELECT a.title, a.summary, a.url, s.name AS source_name,
                   asent.label AS sentiment, asent.score AS sentiment_score
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_sentiments asent ON asent.article_id = a.id
            JOIN article_topics at2 ON at2.article_id = a.id
            JOIN topics t ON t.id = at2.topic_id AND t.slug = :slug
            ORDER BY a.created_at DESC LIMIT :limit
        """, {"slug": topic_slug, "limit": limit})
    else:
        articles = fetch_all("""
            SELECT a.title, a.summary, a.url, s.name AS source_name,
                   asent.label AS sentiment, asent.score AS sentiment_score
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_sentiments asent ON asent.article_id = a.id
            ORDER BY a.created_at DESC LIMIT :limit
        """, {"limit": limit})
    if not articles:
        return "No recent articles available."
    lines = []
    for a in articles:
        sent = f" [Sentiment: {a['sentiment']} ({a['sentiment_score']:+.2f})]" if a.get("sentiment") else ""
        src = f" - {a['source_name']}" if a.get("source_name") else ""
        lines.append(f"- {a['title']}{src}{sent}\n  {a.get('summary', '')[:200]}\n  URL: {a['url']}")
    return "\n".join(lines)


def _build_messages(chat_history: list[dict], topic_slug: str = None) -> list:
    context = _get_recent_articles_context(topic_slug)
    system_msg = f"""You are NewsGuru, an AI-powered news assistant. You help users understand current events.

You have access to tools:
- search_tavily: Search web for latest news via Tavily
- search_exa: Neural search via Exa for specific articles
- get_recent_articles: Query the NewsGuru article database by topic

Use tools when the user asks about current events or needs fresh info. Always cite sources with titles and URLs.

Format your responses with clear structure using markdown: headers (##), bold (**text**), bullet lists, and links [title](url).

RECENT ARTICLES IN DATABASE:
{context}"""

    messages = [SystemMessage(content=system_msg)]
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def md_to_html(text: str) -> str:
    """Convert markdown to HTML."""
    return markdown.markdown(
        text,
        extensions=["extra", "nl2br", "sane_lists"],
    )


async def get_chat_response_stream(
    chat_history: list[dict],
    topic_slug: str = None,
) -> AsyncGenerator[dict, None]:
    """Stream chat response with status events for tool calls.
    Yields dicts: {"type": "status", "text": "..."} or {"type": "token", "html": "..."}
    """
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    messages = _build_messages(chat_history, topic_slug)

    yield {"type": "status", "text": "Thinking..."}

    # First call — may produce tool calls or direct content
    full_text = ""
    tool_calls = []

    try:
        async for chunk in llm_with_tools.astream(messages):
            if chunk.content:
                full_text += chunk.content
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
            if hasattr(chunk, "additional_kwargs"):
                tc = chunk.additional_kwargs.get("tool_calls", [])
                for t in tc:
                    if t.get("function", {}).get("name"):
                        tool_calls.append({
                            "id": t.get("id", ""),
                            "name": t["function"]["name"],
                            "args": t["function"].get("arguments", "{}"),
                        })
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        yield {"type": "token", "html": f'<p class="text-red-500">Error: {e}</p>'}
        return

    # If there are tool calls, execute them and do a second LLM call
    if tool_calls:
        # Deduplicate tool calls by name
        seen = set()
        unique_calls = []
        for tc in tool_calls:
            name = tc.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_calls.append(tc)

        # Add the assistant message with tool calls to history
        from langchain_core.messages import AIMessage as AI
        assistant_msg = AI(content=full_text, tool_calls=[
            {"id": tc.get("id", f"call_{i}"), "name": tc["name"], "args": json.loads(tc["args"]) if isinstance(tc.get("args"), str) else tc.get("args", {})}
            for i, tc in enumerate(unique_calls)
        ])
        messages.append(assistant_msg)

        # Execute each tool
        from langchain_core.messages import ToolMessage
        for tc in unique_calls:
            name = tc.get("name", "")
            label = TOOL_LABELS.get(name, f"Using {name}...")
            yield {"type": "status", "text": label}

            tool_fn = TOOL_MAP.get(name)
            if tool_fn:
                try:
                    args = tc.get("args", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    result = tool_fn.invoke(args)
                except Exception as e:
                    result = f"Tool error: {e}"
            else:
                result = f"Unknown tool: {name}"

            call_id = tc.get("id", f"call_{unique_calls.index(tc)}")
            messages.append(ToolMessage(content=str(result), tool_call_id=call_id))

        # Second LLM call with tool results
        yield {"type": "status", "text": "Composing response..."}
        full_text = ""
        try:
            async for chunk in llm.astream(messages):
                if chunk.content:
                    full_text += chunk.content
        except Exception as e:
            logger.error(f"Second LLM call error: {e}")
            yield {"type": "token", "html": f'<p class="text-red-500">Error: {e}</p>'}
            return

    # Convert final markdown to HTML and yield
    if full_text:
        html = md_to_html(full_text)
        yield {"type": "token", "html": html}
    else:
        yield {"type": "token", "html": "<p>I couldn't generate a response. Please try again.</p>"}
