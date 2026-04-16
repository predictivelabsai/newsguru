import asyncio
import logging
import os
from utils.config import load_config

logger = logging.getLogger(__name__)

_tavily_client = None
_exa_client = None


def _get_tavily():
    global _tavily_client
    if _tavily_client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return None
        from tavily import TavilyClient
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def _get_exa():
    global _exa_client
    if _exa_client is None:
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            return None
        from exa_py import Exa
        _exa_client = Exa(api_key=api_key)
    return _exa_client


async def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    """Search for news articles via Tavily."""
    client = _get_tavily()
    if client is None:
        return []
    config = load_config()
    tavily_cfg = config.get("search", {}).get("tavily", {})
    try:
        result = await asyncio.to_thread(
            client.search,
            query=query,
            search_depth=tavily_cfg.get("search_depth", "advanced"),
            topic=tavily_cfg.get("topic", "news"),
            max_results=max_results,
        )
        articles = []
        for r in result.get("results", []):
            articles.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "summary": r.get("content", "")[:500],
                "source": r.get("url", "").split("/")[2] if "/" in r.get("url", "") else "",
            })
        return articles
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


async def search_exa(query: str, max_results: int = 5) -> list[dict]:
    """Search for news articles via Exa."""
    client = _get_exa()
    if client is None:
        return []
    try:
        result = await asyncio.to_thread(
            client.search_and_contents,
            query=query,
            num_results=max_results,
            type="neural",
            use_autoprompt=True,
            text={"max_characters": 500},
        )
        articles = []
        for r in result.results:
            articles.append({
                "url": r.url or "",
                "title": r.title or "",
                "summary": (r.text or "")[:500],
                "source": (r.url or "").split("/")[2] if "/" in (r.url or "") else "",
            })
        return articles
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return []


async def search_news(query: str, max_results: int = 10) -> list[dict]:
    """Search using both Tavily and Exa, deduplicating by URL."""
    tavily_results, exa_results = await asyncio.gather(
        search_tavily(query, max_results=max_results // 2 + 1),
        search_exa(query, max_results=max_results // 2 + 1),
        return_exceptions=True,
    )
    if isinstance(tavily_results, Exception):
        tavily_results = []
    if isinstance(exa_results, Exception):
        exa_results = []

    seen_urls = set()
    combined = []
    for a in list(tavily_results) + list(exa_results):
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            combined.append(a)
    return combined[:max_results]


async def discover_trending(topics: list[str], max_per_topic: int = 3) -> list[dict]:
    """Use Tavily to discover articles for trending topics."""
    all_results = []
    for topic_name in topics[:3]:
        results = await search_tavily(f"latest {topic_name} news today", max_per_topic)
        all_results.extend(results)
    return all_results
