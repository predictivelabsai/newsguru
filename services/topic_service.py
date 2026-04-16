import logging
from db.pool import fetch_all, execute_sql
from utils.config import get_topics

logger = logging.getLogger(__name__)


def classify_article(title: str, summary: str, full_text: str = "") -> list[dict]:
    """Classify an article into topics using keyword matching.
    Returns list of {slug, relevance_score} dicts."""
    text_lower = f"{title} {summary} {full_text[:500]}".lower()
    topics = get_topics()
    matches = []

    for topic in topics:
        keywords = topic.get("keywords", [])
        hit_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hit_count > 0:
            relevance = min(1.0, hit_count / max(len(keywords) * 0.3, 1))
            matches.append({
                "slug": topic["slug"],
                "relevance_score": round(relevance, 2),
            })

    # If no keyword match, default to most general topic
    if not matches:
        matches.append({"slug": "culture", "relevance_score": 0.1})

    return matches


def save_article_topics(article_id: str, topic_matches: list[dict]):
    """Link an article to its classified topics in the DB."""
    for match in topic_matches:
        try:
            execute_sql("""
                INSERT INTO article_topics (article_id, topic_id, relevance_score)
                SELECT :aid, t.id, :score
                FROM topics t WHERE t.slug = :slug
                ON CONFLICT (article_id, topic_id) DO NOTHING
            """, {
                "aid": article_id,
                "slug": match["slug"],
                "score": match["relevance_score"],
            })
        except Exception as e:
            logger.error(f"Failed to save topic link: {e}")


def get_trending_topics(hours: int = 24) -> list[dict]:
    """Get topics ranked by article count in the last N hours."""
    return fetch_all("""
        SELECT t.name, t.slug, t.color, t.icon, COUNT(at2.article_id) AS article_count
        FROM topics t
        JOIN article_topics at2 ON at2.topic_id = t.id
        JOIN articles a ON a.id = at2.article_id
        WHERE a.created_at > NOW() - make_interval(hours => :hours)
        GROUP BY t.id, t.name, t.slug, t.color, t.icon
        ORDER BY article_count DESC
    """, {"hours": hours})
