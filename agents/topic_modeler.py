"""
Topic Modeling Agent

Groups recent articles into story clusters — the same real-world event
or topic covered by multiple sources. Uses LLM to identify clusters
from article titles, then stores the mapping in story_clusters /
article_clusters tables.

Run periodically (every scheduler cycle) to keep clusters fresh.
"""
import json
import logging
import os
from db.pool import fetch_all, fetch_one, execute_sql
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
            model=config["llm"]["model"],
            temperature=0.1,
            max_tokens=2000,
        )
    return _llm


async def run_topic_modeling():
    """Cluster recent articles into story groups."""
    # Get unclustered articles from last 24h
    articles = fetch_all("""
        SELECT a.id, a.title, s.name AS source_name,
               asent.score AS sentiment_score
        FROM articles a
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        LEFT JOIN article_clusters ac ON ac.article_id = a.id
        WHERE a.created_at > NOW() - INTERVAL '24 hours'
          AND ac.article_id IS NULL
        ORDER BY a.created_at DESC
        LIMIT 80
    """)

    if len(articles) < 3:
        logger.info("Topic modeling: not enough unclustered articles")
        return

    # Build prompt with article list
    article_list = []
    for i, a in enumerate(articles):
        src = a.get("source_name", "")
        article_list.append(f'{i}: "{a["title"]}" [{src}]')

    prompt = f"""You are a news topic clustering agent. Group these articles by the real-world story or event they cover.

ARTICLES:
{chr(10).join(article_list)}

Rules:
- A cluster must have 2+ articles from DIFFERENT sources covering the SAME story/event
- Single-source stories should NOT be clustered (set them as cluster "unclustered")
- Cluster label should be a short, factual description of the event (not a headline)
- Maximum 15 clusters

Return ONLY valid JSON array:
[
  {{"label": "short event description", "article_ids": [0, 3, 7], "summary": "one sentence"}},
  ...
]

Only include clusters with 2+ articles from different sources. Omit single-article clusters."""

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Parse JSON
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        clusters = json.loads(content)

        saved = 0
        for cluster in clusters:
            ids = cluster.get("article_ids", [])
            label = cluster.get("label", "")
            summary = cluster.get("summary", "")

            if len(ids) < 2 or not label:
                continue

            # Verify these are from different sources
            cluster_articles = [articles[i] for i in ids if i < len(articles)]
            sources_in_cluster = set(a.get("source_name", "") for a in cluster_articles)
            if len(sources_in_cluster) < 2:
                continue

            # Create cluster
            result = fetch_one("""
                INSERT INTO story_clusters (cluster_label, summary, article_count)
                VALUES (:label, :summary, :count)
                RETURNING id
            """, {"label": label, "summary": summary, "count": len(cluster_articles)})

            if result:
                cluster_id = str(result["id"])
                for a in cluster_articles:
                    execute_sql("""
                        INSERT INTO article_clusters (article_id, cluster_id)
                        VALUES (:aid, :cid)
                        ON CONFLICT DO NOTHING
                    """, {"aid": str(a["id"]), "cid": cluster_id})
                saved += 1

        logger.info(f"Topic modeling: created {saved} clusters from {len(articles)} articles")

    except Exception as e:
        logger.error(f"Topic modeling failed: {e}")


def get_related_coverage(article_id: str) -> list[dict]:
    """Get other articles covering the same story (different sources)."""
    return fetch_all("""
        SELECT a.id, a.title, a.url, s.name AS source_name,
               asent.score AS sentiment_score, asent.label AS sentiment_label,
               asig.significance_score
        FROM article_clusters ac1
        JOIN article_clusters ac2 ON ac2.cluster_id = ac1.cluster_id AND ac2.article_id != ac1.article_id
        JOIN articles a ON a.id = ac2.article_id
        LEFT JOIN sources s ON s.id = a.source_id
        LEFT JOIN article_sentiments asent ON asent.article_id = a.id
        LEFT JOIN article_significance asig ON asig.article_id = a.id
        WHERE ac1.article_id = :aid
        ORDER BY a.created_at DESC
    """, {"aid": article_id})


def get_cluster_for_article(article_id: str) -> dict | None:
    """Get the story cluster this article belongs to."""
    return fetch_one("""
        SELECT sc.id, sc.cluster_label, sc.summary, sc.article_count
        FROM article_clusters ac
        JOIN story_clusters sc ON sc.id = ac.cluster_id
        WHERE ac.article_id = :aid
        LIMIT 1
    """, {"aid": article_id})


def get_daily_clusters(limit: int = 10) -> list[dict]:
    """Get today's story clusters with multi-source coverage details."""
    clusters = fetch_all("""
        SELECT sc.id, sc.cluster_label, sc.summary, sc.article_count
        FROM story_clusters sc
        WHERE sc.created_at > NOW() - INTERVAL '24 hours'
        ORDER BY sc.article_count DESC
        LIMIT :limit
    """, {"limit": limit})

    for c in clusters:
        c["articles"] = fetch_all("""
            SELECT a.title, a.url, s.name AS source_name,
                   asent.score AS sentiment_score, asent.label AS sentiment_label
            FROM article_clusters ac
            JOIN articles a ON a.id = ac.article_id
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_sentiments asent ON asent.article_id = a.id
            WHERE ac.cluster_id = :cid
            ORDER BY s.name
        """, {"cid": str(c["id"])})
    return clusters
