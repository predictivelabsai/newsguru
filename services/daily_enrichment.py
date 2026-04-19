"""Daily batch LLM enrichment.

RSS ingestion runs continuously (every 300s) but only writes raw articles.
Sentiment, significance, translation, and clustering are deferred to a single
batch that runs once per `llm.daily_interval_seconds` (default 86400s).
This cuts xAI spend by ~90% by amortizing fixed prompt overhead.
"""
import asyncio
import logging

from db.pool import fetch_all
from utils.config import load_config

logger = logging.getLogger(__name__)


async def _batch_sentiment(limit: int):
    from services.sentiment_service import score_sentiment
    rows = fetch_all("""
        SELECT a.id, a.title, COALESCE(a.full_text, a.summary, '') AS text
        FROM articles a
        LEFT JOIN article_sentiments s ON s.article_id = a.id
        WHERE s.article_id IS NULL
          AND a.created_at > NOW() - INTERVAL '7 days'
        ORDER BY a.created_at DESC
        LIMIT :lim
    """, {"lim": limit})
    logger.info(f"Daily enrichment: sentiment on {len(rows)} articles")
    for r in rows:
        try:
            await score_sentiment(str(r["id"]), r["title"], r["text"])
        except Exception as e:
            logger.error(f"Batch sentiment error: {e}")


async def _batch_significance(limit: int):
    from services.significance_service import score_significance
    rows = fetch_all("""
        SELECT a.id, a.title, a.summary, s.name AS source_name
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE asig.article_id IS NULL
          AND a.created_at > NOW() - INTERVAL '7 days'
        ORDER BY a.created_at DESC
        LIMIT :lim
    """, {"lim": limit})
    logger.info(f"Daily enrichment: significance on {len(rows)} articles")
    for r in rows:
        try:
            await score_significance(str(r["id"]), r["title"], r.get("summary", "") or "", r.get("source_name", "") or "")
        except Exception as e:
            logger.error(f"Batch significance error: {e}")


async def _batch_translation(limit: int):
    from services.translate_service import batch_translate_untranslated
    logger.info(f"Daily enrichment: translation (limit={limit})")
    try:
        await batch_translate_untranslated(limit=limit)
    except Exception as e:
        logger.error(f"Batch translation error: {e}")


async def _batch_clustering():
    from agents.topic_modeler import run_topic_modeling
    logger.info("Daily enrichment: clustering")
    try:
        await run_topic_modeling()
    except Exception as e:
        logger.error(f"Batch clustering error: {e}")


async def run_daily_enrichment():
    """One pass of all enrichment jobs. Each job self-gates on its enable flag."""
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    limit = int(llm_cfg.get("batch_limit", 100))

    if llm_cfg.get("enable_sentiment", True):
        await _batch_sentiment(limit)
    if llm_cfg.get("enable_significance", True):
        await _batch_significance(limit)
    if llm_cfg.get("enable_translation", True):
        await _batch_translation(limit)
    if llm_cfg.get("enable_clustering", True):
        await _batch_clustering()


async def run_daily_scheduler(shutdown_event):
    """Background loop: run enrichment on startup, then every daily_interval_seconds."""
    cfg = load_config()
    interval = int(cfg.get("llm", {}).get("daily_interval_seconds", 86400))
    logger.info(f"Daily enrichment scheduler started (interval={interval}s)")

    await asyncio.sleep(30)  # let app settle
    while not shutdown_event.is_set():
        try:
            logger.info("Daily enrichment cycle starting...")
            await run_daily_enrichment()
            logger.info("Daily enrichment cycle complete")
        except Exception as e:
            logger.error(f"Daily enrichment cycle error: {e}")
        try:
            await asyncio.wait_for(asyncio.shield(shutdown_event.wait()), timeout=interval)
            break  # shutdown requested
        except asyncio.TimeoutError:
            pass
