"""Apply SQL schema and seed data to the database."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.pool import get_engine, get_db
from sqlalchemy import text
from utils.config import get_all_sources, get_topics


def run_schema():
    schema_path = Path(__file__).parent.parent / "sql" / "schema.sql"
    sql = schema_path.read_text()
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("Schema applied successfully.")


def seed_sources():
    sources = get_all_sources()
    with get_db() as db:
        for src in sources:
            db.execute(text("""
                INSERT INTO newsguru.sources (name, domain, rss_url, language)
                VALUES (:name, :domain, :rss_url, :language)
                ON CONFLICT (domain) DO UPDATE SET
                    name = EXCLUDED.name,
                    rss_url = EXCLUDED.rss_url,
                    language = EXCLUDED.language
            """), src)
    print(f"Seeded {len(sources)} sources.")


def seed_topics():
    topics = get_topics()
    with get_db() as db:
        for t in topics:
            db.execute(text("""
                INSERT INTO newsguru.topics (name, slug, icon, color, display_order)
                VALUES (:name, :slug, :icon, :color, :display_order)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    icon = EXCLUDED.icon,
                    color = EXCLUDED.color,
                    display_order = EXCLUDED.display_order
            """), t)
    print(f"Seeded {len(topics)} topics.")


if __name__ == "__main__":
    run_schema()
    seed_sources()
    seed_topics()
    print("Migration complete.")
