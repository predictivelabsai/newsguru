import logging
import re
from db.pool import execute_sql, fetch_one

logger = logging.getLogger(__name__)

# Patterns that indicate non-journalist author fields (RSS metadata, not real names)
_SKIP_PATTERNS = [
    r"^https?://",            # URLs
    r"^www\.",                 # Websites
    r"\.com$", r"\.ee$", r"\.org$", r"\.net$",  # Domain endings
    r"\|",                     # Pipe-separated metadata like "uudised | ERR"
    r"@",                      # Email addresses
    r"^\d+$",                  # Pure numbers
    r"^.{0,2}$",              # Too short
    r"toimetus$",              # Estonian: "editorial" (kultuuritoimetus, etc.)
    r"^(ERR|BBC|CNN|Reuters|AFP|AP|Bloomberg|CNBC|Postimees|Delfi)$",  # News org names used as "author"
]

_SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SKIP_PATTERNS]

# Words that suggest this is a role/section, not a person
_NON_PERSON_WORDS = {
    "toimetus", "toimetaja", "uudised", "sport", "kultuur", "eeter", "novaator",
    "teadus", "arvamus", "majandus", "fotograaf", "ajakirjanik",
    "editor", "editorial", "newsroom", "staff", "reporter", "correspondent",
    "news", "sports", "culture", "science", "business",
}


def _is_likely_person(name: str) -> bool:
    """Check if a string looks like an actual person's name."""
    # Skip if matches any skip pattern
    for pattern in _SKIP_COMPILED:
        if pattern.search(name):
            return False

    # Skip if it's a single word that's a known non-person term
    words = name.lower().split()
    if len(words) == 1 and words[0] in _NON_PERSON_WORDS:
        return False

    # A real name should have at least 2 words (first + last)
    # Exception: some cultures use single names, but most RSS garbage is also single-word
    if len(words) < 2:
        return False

    # Skip if all words are non-person terms
    if all(w in _NON_PERSON_WORDS for w in words):
        return False

    # Skip if too long (likely a sentence or metadata blob)
    if len(name) > 60:
        return False

    return True


def _clean_name(name: str) -> str:
    """Strip role suffixes and clean up a single name."""
    # Strip common Estonian/English role suffixes
    suffixes = [
        r"\s*[-,]\s*toimetaja$", r"\s*ajakirjanik$", r"\s*fotograaf$",
        r"\s*fotoreporter$", r"\s*politoloog$", r"\s*kolumnist$",
        r"\s*reporter$", r"\s*correspondent$", r"\s*editor$",
    ]
    for suf in suffixes:
        name = re.sub(suf, "", name, flags=re.IGNORECASE)
    return name.strip()


def _normalize_author(author: str) -> list[str]:
    """Split and clean author names, filtering out non-person entries."""
    if not author:
        return []
    # Remove common prefixes
    author = re.sub(r"^(by|author[:]?)\s+", "", author, flags=re.IGNORECASE)
    # Split on comma, "and", "&"
    names = re.split(r"[,&]|\band\b", author)
    cleaned = []
    seen = set()
    for name in names:
        name = _clean_name(name.strip())
        if _is_likely_person(name) and name.lower() not in seen:
            seen.add(name.lower())
            cleaned.append(name)
    return cleaned


def track_journalist(article_id: str, author_str: str, source_id: str | None):
    """Extract real journalist names and upsert into journalists table."""
    names = _normalize_author(author_str)
    for name in names:
        try:
            journalist = fetch_one("""
                INSERT INTO journalists (name, source_id, article_count, last_seen_at)
                VALUES (:name, :source_id, 1, NOW())
                ON CONFLICT (name, source_id) DO UPDATE SET
                    article_count = journalists.article_count + 1,
                    last_seen_at = NOW()
                RETURNING id
            """, {"name": name, "source_id": source_id})

            if journalist:
                execute_sql("""
                    INSERT INTO journalist_articles (journalist_id, article_id)
                    VALUES (:jid, :aid)
                    ON CONFLICT DO NOTHING
                """, {"jid": journalist["id"], "aid": article_id})
        except Exception as e:
            logger.error(f"Failed to track journalist '{name}': {e}")
