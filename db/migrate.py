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


def add_translation_columns():
    """Add title_en and title_et columns if they don't exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE newsguru.articles ADD COLUMN IF NOT EXISTS title_en TEXT;
            ALTER TABLE newsguru.articles ADD COLUMN IF NOT EXISTS title_et TEXT;
        """))
        conn.commit()
    print("Translation columns added.")


def add_significance_table():
    """Create article_significance table if it doesn't exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS newsguru.article_significance (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                article_id      UUID NOT NULL UNIQUE REFERENCES newsguru.articles(id) ON DELETE CASCADE,
                significance_score REAL NOT NULL,
                scale           SMALLINT NOT NULL DEFAULT 0,
                impact          SMALLINT NOT NULL DEFAULT 0,
                novelty         SMALLINT NOT NULL DEFAULT 0,
                potential       SMALLINT NOT NULL DEFAULT 0,
                legacy          SMALLINT NOT NULL DEFAULT 0,
                positivity      SMALLINT NOT NULL DEFAULT 0,
                credibility     SMALLINT NOT NULL DEFAULT 0,
                reasoning       TEXT,
                model_used      VARCHAR(128),
                scored_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_article_significance_score
                ON newsguru.article_significance(significance_score DESC);
        """))
        conn.commit()
    print("Significance table created.")


def add_news_feed_table():
    """Create news_feed history table."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS newsguru.news_feed (
                id              BIGSERIAL PRIMARY KEY,
                article_id      UUID REFERENCES newsguru.articles(id) ON DELETE SET NULL,
                title           TEXT NOT NULL,
                url             TEXT NOT NULL,
                source_name     VARCHAR(255),
                source_domain   VARCHAR(255),
                author          VARCHAR(512),
                language        VARCHAR(10) DEFAULT 'en',
                published_at    TIMESTAMPTZ,
                sentiment_label VARCHAR(20),
                sentiment_score REAL,
                significance_score REAL,
                topics          TEXT[],
                inserted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_news_feed_inserted ON newsguru.news_feed(inserted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_news_feed_significance ON newsguru.news_feed(significance_score DESC NULLS LAST);
        """))
        conn.commit()
    print("News feed table created.")


if __name__ == "__main__":
    run_schema()
    add_translation_columns()
    add_significance_table()
    add_news_feed_table()
    seed_sources()
    seed_topics()
    print("Migration complete.")
