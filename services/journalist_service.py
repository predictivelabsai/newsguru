import logging
import re
from db.pool import execute_sql, fetch_one

logger = logging.getLogger(__name__)


def _normalize_author(author: str) -> list[str]:
    """Split and clean author names."""
    if not author:
        return []
    # Remove common prefixes
    author = re.sub(r"^(by|author[:]?)\s+", "", author, flags=re.IGNORECASE)
    # Split on comma, "and", "&"
    names = re.split(r"[,&]|\band\b", author)
    cleaned = []
    for name in names:
        name = name.strip()
        if name and len(name) > 2 and len(name) < 100:
            cleaned.append(name)
    return cleaned


def track_journalist(article_id: str, author_str: str, source_id: str | None):
    """Extract author names and upsert into journalists table."""
    names = _normalize_author(author_str)
    for name in names:
        try:
            # Upsert journalist
            journalist = fetch_one("""
                INSERT INTO journalists (name, source_id, article_count, last_seen_at)
                VALUES (:name, :source_id, 1, NOW())
                ON CONFLICT (name, source_id) DO UPDATE SET
                    article_count = journalists.article_count + 1,
                    last_seen_at = NOW()
                RETURNING id
            """, {"name": name, "source_id": source_id})

            if journalist:
                # Link to article
                execute_sql("""
                    INSERT INTO journalist_articles (journalist_id, article_id)
                    VALUES (:jid, :aid)
                    ON CONFLICT DO NOTHING
                """, {"jid": journalist["id"], "aid": article_id})
        except Exception as e:
            logger.error(f"Failed to track journalist '{name}': {e}")
