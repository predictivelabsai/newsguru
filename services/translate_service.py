"""Translate article titles using LLM."""
import json
import logging
import os
from db.pool import execute_sql, fetch_all
from utils.config import load_config

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        config = load_config()
        _llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["sentiment_model"],
            temperature=0.1,
            max_tokens=1000,
        )
    return _llm


async def translate_article_title(article_id: str, title: str, source_lang: str):
    """Translate title to the other language and store in DB."""
    if not load_config()["llm"].get("enable_translation", True):
        return
    target_lang = "et" if source_lang == "en" else "en"
    target_name = "Estonian" if target_lang == "et" else "English"

    prompt = f"""Translate this news headline to {target_name}. Return ONLY the translated headline, nothing else.

Headline: {title}"""

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        translated = response.content.strip().strip('"').strip("'")
        if translated:
            col = f"title_{target_lang}"
            execute_sql(f"""
                UPDATE articles SET {col} = :translated WHERE id = :id
            """, {"translated": translated, "id": article_id})
            logger.debug(f"Translated [{source_lang}->{target_lang}]: {title[:40]}... -> {translated[:40]}...")
    except Exception as e:
        logger.error(f"Translation failed for {title[:40]}: {e}")


async def batch_translate_untranslated(limit: int = 20):
    """Translate titles that haven't been translated yet."""
    # English articles missing Estonian translation
    en_articles = fetch_all("""
        SELECT id, title FROM articles
        WHERE language = 'en' AND title_et IS NULL
        ORDER BY created_at DESC LIMIT :limit
    """, {"limit": limit})
    for a in en_articles:
        await translate_article_title(str(a["id"]), a["title"], "en")

    # Estonian articles missing English translation
    et_articles = fetch_all("""
        SELECT id, title FROM articles
        WHERE language = 'et' AND title_en IS NULL
        ORDER BY created_at DESC LIMIT :limit
    """, {"limit": limit})
    for a in et_articles:
        await translate_article_title(str(a["id"]), a["title"], "et")
