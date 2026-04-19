"""
Significance scoring for news articles.

Uses a 7-factor methodology (Scale, Impact, Novelty, Potential, Legacy, Positivity, Credibility)
to produce a single 0-10 significance score per article. Scoring rules are defined in
prompts/scoring_rules.md.
"""
import json
import logging
import os
from pathlib import Path
from db.pool import execute_sql, fetch_one
from utils.config import load_config

logger = logging.getLogger(__name__)

_llm = None
_scoring_prompt = None

WEIGHTS = {
    "scale": 4,
    "impact": 4,
    "novelty": 3,
    "potential": 3,
    "legacy": 3,
    "positivity": 1,
    "credibility": 2,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())  # 20


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        config = load_config()
        _llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["model"],
            temperature=0.1,
            max_tokens=500,
        )
    return _llm


def _get_scoring_prompt() -> str:
    global _scoring_prompt
    if _scoring_prompt is None:
        rules_path = Path(__file__).parent.parent / "prompts" / "scoring_rules.md"
        _scoring_prompt = rules_path.read_text()
    return _scoring_prompt


def _compute_significance(factors: dict) -> float:
    """Compute weighted significance score from 7 factors."""
    score = sum(factors.get(k, 0) * w for k, w in WEIGHTS.items()) / TOTAL_WEIGHT
    return round(max(0.0, min(10.0, score)), 1)


async def score_significance(article_id: str, title: str, summary: str, source_name: str = ""):
    """Score an article's significance using the 7-factor methodology."""
    if not load_config()["llm"].get("enable_significance", True):
        return
    if not title:
        return

    rules = _get_scoring_prompt()

    prompt = f"""You are a news significance analyst. Score this article using the 7-factor methodology.

{rules}

---

ARTICLE TO SCORE:
Title: {title}
Source: {source_name}
Summary: {summary[:800]}

Respond with ONLY valid JSON, no other text:
{{
  "scale": <int 0-10>,
  "impact": <int 0-10>,
  "novelty": <int 0-10>,
  "potential": <int 0-10>,
  "legacy": <int 0-10>,
  "positivity": <int 0-10>,
  "credibility": <int 0-10>,
  "reasoning": "<one sentence explaining the score>"
}}"""

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Extract JSON
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)

        factors = {}
        for key in WEIGHTS:
            val = int(data.get(key, 0))
            factors[key] = max(0, min(10, val))

        significance = _compute_significance(factors)
        reasoning = data.get("reasoning", "")

        # Save to DB
        execute_sql("""
            INSERT INTO article_significance (article_id, significance_score,
                scale, impact, novelty, potential, legacy, positivity, credibility,
                reasoning, model_used)
            VALUES (:aid, :sig, :scale, :impact, :novelty, :potential, :legacy,
                    :positivity, :credibility, :reasoning, :model)
            ON CONFLICT (article_id) DO UPDATE SET
                significance_score = EXCLUDED.significance_score,
                scale = EXCLUDED.scale, impact = EXCLUDED.impact,
                novelty = EXCLUDED.novelty, potential = EXCLUDED.potential,
                legacy = EXCLUDED.legacy, positivity = EXCLUDED.positivity,
                credibility = EXCLUDED.credibility,
                reasoning = EXCLUDED.reasoning, scored_at = NOW()
        """, {
            "aid": article_id,
            "sig": significance,
            "scale": factors["scale"],
            "impact": factors["impact"],
            "novelty": factors["novelty"],
            "potential": factors["potential"],
            "legacy": factors["legacy"],
            "positivity": factors["positivity"],
            "credibility": factors["credibility"],
            "reasoning": reasoning[:500],
            "model": load_config()["llm"]["model"],
        })

        logger.info(f"Significance {significance:.1f}/10: {title[:50]}...")
        return significance

    except Exception as e:
        logger.error(f"Significance scoring failed for {title[:50]}: {e}")
        return None
