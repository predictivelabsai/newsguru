import asyncio
import logging
from db.pool import fetch_one, execute_sql, fetch_all
from services.rss_service import fetch_all_rss
from services.scraper_service import scrape_article
from services.topic_service import classify_article, save_article_topics
from services.journalist_service import track_journalist
from services.sentiment_service import score_sentiment
from utils.config import get_all_sources

logger = logging.getLogger(__name__)


async def _process_article(raw: dict, article_queue: asyncio.Queue, topic_queues: dict):
    """Process a single raw article: save, scrape, classify, score, push to SSE."""
    # Look up source_id
    source = fetch_one(
        "SELECT id FROM sources WHERE domain = :domain",
        {"domain": raw["source_domain"]},
    )
    source_id = source["id"] if source else None

    # Save article stub
    result = fetch_one("""
        INSERT INTO articles (source_id, url, title, summary, author, published_at, image_url, language)
        VALUES (:source_id, :url, :title, :summary, :author, :published_at, :image_url, :language)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
    """, {
        "source_id": source_id,
        "url": raw["url"],
        "title": raw["title"],
        "summary": raw.get("summary", ""),
        "author": raw.get("author", ""),
        "published_at": raw.get("published_at"),
        "image_url": raw.get("image_url"),
        "language": raw.get("language", "en"),
    })

    if not result:
        return  # Already exists

    article_id = str(result["id"])

    # Scrape full text (best-effort, don't block on failure)
    scraped = await scrape_article(raw["url"])
    if scraped.get("full_text"):
        execute_sql("""
            UPDATE articles SET full_text = :text, word_count = :wc
            WHERE id = :id
        """, {"text": scraped["full_text"], "wc": scraped["word_count"], "id": article_id})

    # Use scraped author if RSS didn't have one
    author = raw.get("author") or scraped.get("author", "")
    if author and not raw.get("author"):
        execute_sql("UPDATE articles SET author = :author WHERE id = :id",
                     {"author": author, "id": article_id})

    # Classify into topics
    topics = classify_article(raw["title"], raw.get("summary", ""), scraped.get("full_text", ""))
    save_article_topics(article_id, topics)

    # Track journalist
    if author:
        track_journalist(article_id, author, source_id)

    # Score sentiment (async, don't block)
    text_for_sentiment = scraped.get("full_text") or raw.get("summary", "")
    await score_sentiment(article_id, raw["title"], text_for_sentiment)

    # Translate title to the other language
    from services.translate_service import translate_article_title
    await translate_article_title(article_id, raw["title"], raw.get("language", "en"))

    # Build article dict for SSE push
    article_for_push = _build_push_article(article_id)
    if article_for_push:
        # Push to global queue
        try:
            article_queue.put_nowait(article_for_push)
        except asyncio.QueueFull:
            pass
        # Push to topic-specific queues
        for t in topics:
            q = topic_queues.get(t["slug"])
            if q:
                try:
                    q.put_nowait(article_for_push)
                except asyncio.QueueFull:
                    pass


def _build_push_article(article_id: str) -> dict | None:
    return fetch_one("""
        SELECT a.id, a.title, a.title_en, a.title_et, a.language, a.url, a.author, a.published_at,
               s.name AS source_name,
               asent.label AS sentiment_label, asent.score AS sentiment_score
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        WHERE a.id = :id
    """, {"id": article_id})


async def run_feed_scheduler(
    config: dict,
    shutdown_event,
    article_queue: asyncio.Queue,
    topic_queues: dict,
):
    """Background loop: fetch RSS -> scrape -> classify -> score -> push."""
    interval = config["app"].get("fetch_interval_seconds", 300)
    logger.info(f"Feed scheduler started (interval={interval}s)")

    # Initial short delay to let app start
    await asyncio.sleep(5)

    cycle = 0
    while not shutdown_event.is_set():
        cycle += 1
        logger.info(f"Feed scheduler cycle {cycle} starting...")
        try:
            sources = get_all_sources()
            new_articles = await fetch_all_rss(sources)
            logger.info(f"Cycle {cycle}: {len(new_articles)} new articles from RSS")

            for raw in new_articles:
                if shutdown_event.is_set():
                    break
                try:
                    await _process_article(raw, article_queue, topic_queues)
                except Exception as e:
                    logger.error(f"Failed to process article {raw.get('url')}: {e}")

            # Tavily discovery every 3rd cycle
            if cycle % 3 == 0:
                try:
                    from services.search_service import discover_trending
                    from services.topic_service import get_trending_topics
                    trending = get_trending_topics(hours=24)
                    topic_names = [t["name"] for t in trending[:3]]
                    if topic_names:
                        discovered = await discover_trending(topic_names)
                        for d in discovered:
                            raw_article = {
                                "url": d["url"],
                                "title": d["title"],
                                "summary": d.get("summary", ""),
                                "author": "",
                                "published_at": None,
                                "image_url": None,
                                "language": "en",
                                "source_domain": d.get("source", "tavily"),
                            }
                            try:
                                await _process_article(raw_article, article_queue, topic_queues)
                            except Exception as e:
                                logger.error(f"Tavily article process error: {e}")
                except Exception as e:
                    logger.error(f"Tavily discovery error: {e}")

        except Exception as e:
            logger.error(f"Feed scheduler cycle {cycle} error: {e}")

        logger.info(f"Feed scheduler cycle {cycle} complete. Sleeping {interval}s...")
        try:
            await asyncio.wait_for(asyncio.shield(shutdown_event.wait()), timeout=interval)
            break  # Shutdown requested
        except asyncio.TimeoutError:
            pass  # Normal timeout, continue loop
