import json
import logging
import os
from db.pool import execute_sql
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
            temperature=config["llm"]["sentiment_temperature"],
            max_tokens=200,
        )
    return _llm


async def score_sentiment(article_id: str, title: str, text: str):
    """Score article sentiment using LLM. Saves to DB."""
    if not load_config()["llm"].get("enable_sentiment", True):
        return
    if not text and not title:
        return

    prompt = f"""Analyze the sentiment of this news article. Respond with ONLY valid JSON, no other text.

Title: {title}
Text (excerpt): {text[:600]}

JSON format: {{"score": <float from -1.0 to 1.0>, "label": "<positive|negative|neutral>", "confidence": <float from 0.0 to 1.0>}}"""

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        # Extract JSON from response
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)
        score = max(-1.0, min(1.0, float(data["score"])))
        label = data.get("label", "neutral")
        if label not in ("positive", "negative", "neutral"):
            label = "neutral"
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))

        config = load_config()
        execute_sql("""
            INSERT INTO article_sentiments (article_id, score, label, confidence, model_used)
            VALUES (:aid, :score, :label, :conf, :model)
            ON CONFLICT (article_id) DO UPDATE SET
                score = EXCLUDED.score,
                label = EXCLUDED.label,
                confidence = EXCLUDED.confidence,
                scored_at = NOW()
        """, {
            "aid": article_id,
            "score": score,
            "label": label,
            "conf": confidence,
            "model": config["llm"]["sentiment_model"],
        })
        logger.info(f"Sentiment scored: {title[:50]}... -> {label} ({score:+.2f})")
    except Exception as e:
        logger.error(f"Sentiment scoring failed for {title[:50]}: {e}")
