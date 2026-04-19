-- NewsGuru Database Schema
-- PostgreSQL schema: newsguru

CREATE SCHEMA IF NOT EXISTS newsguru;

-- Users
CREATE TABLE IF NOT EXISTS newsguru.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(64) UNIQUE,
    password_hash   VARCHAR(255),
    email           VARCHAR(255) UNIQUE,
    display_name    VARCHAR(128),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User profiles
CREATE TABLE IF NOT EXISTS newsguru.profiles (
    user_id         UUID PRIMARY KEY REFERENCES newsguru.users(id) ON DELETE CASCADE,
    preferred_topics TEXT[],
    preferred_lang  VARCHAR(10) DEFAULT 'en',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- News sources
CREATE TABLE IF NOT EXISTS newsguru.sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255) NOT NULL UNIQUE,
    rss_url         TEXT,
    language        VARCHAR(10) NOT NULL DEFAULT 'en',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Articles
CREATE TABLE IF NOT EXISTS newsguru.articles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID REFERENCES newsguru.sources(id) ON DELETE SET NULL,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    title_en        TEXT,
    title_et        TEXT,
    summary         TEXT,
    full_text       TEXT,
    author          VARCHAR(512),
    published_at    TIMESTAMPTZ,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    image_url       TEXT,
    language        VARCHAR(10) DEFAULT 'en',
    word_count      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_published_at ON newsguru.articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source_id ON newsguru.articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON newsguru.articles(created_at DESC);

-- Article sentiments
CREATE TABLE IF NOT EXISTS newsguru.article_sentiments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id      UUID NOT NULL UNIQUE REFERENCES newsguru.articles(id) ON DELETE CASCADE,
    score           REAL NOT NULL,
    label           VARCHAR(20) NOT NULL,
    confidence      REAL,
    model_used      VARCHAR(128),
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Article significance (7-factor scoring)
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

CREATE INDEX IF NOT EXISTS idx_article_significance_score ON newsguru.article_significance(significance_score DESC);

-- Topics
CREATE TABLE IF NOT EXISTS newsguru.topics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL UNIQUE,
    slug            VARCHAR(128) NOT NULL UNIQUE,
    icon            VARCHAR(64),
    color           VARCHAR(32),
    display_order   INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Article <-> Topic junction
CREATE TABLE IF NOT EXISTS newsguru.article_topics (
    article_id      UUID NOT NULL REFERENCES newsguru.articles(id) ON DELETE CASCADE,
    topic_id        UUID NOT NULL REFERENCES newsguru.topics(id) ON DELETE CASCADE,
    relevance_score REAL DEFAULT 1.0,
    PRIMARY KEY (article_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_article_topics_topic ON newsguru.article_topics(topic_id);

-- Journalists
CREATE TABLE IF NOT EXISTS newsguru.journalists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    source_id       UUID REFERENCES newsguru.sources(id) ON DELETE SET NULL,
    article_count   INTEGER NOT NULL DEFAULT 0,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, source_id)
);

-- Journalist <-> Article junction
CREATE TABLE IF NOT EXISTS newsguru.journalist_articles (
    journalist_id   UUID NOT NULL REFERENCES newsguru.journalists(id) ON DELETE CASCADE,
    article_id      UUID NOT NULL REFERENCES newsguru.articles(id) ON DELETE CASCADE,
    PRIMARY KEY (journalist_id, article_id)
);

-- Chat sessions
CREATE TABLE IF NOT EXISTS newsguru.chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES newsguru.users(id) ON DELETE SET NULL,
    topic_slug      VARCHAR(128),
    title           VARCHAR(255) DEFAULT 'New chat',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON newsguru.chat_sessions(user_id, updated_at DESC);

-- Chat messages
CREATE TABLE IF NOT EXISTS newsguru.chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES newsguru.chat_sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON newsguru.chat_messages(session_id, created_at ASC);

-- Trending snapshots
CREATE TABLE IF NOT EXISTS newsguru.trending_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id        UUID NOT NULL REFERENCES newsguru.topics(id) ON DELETE CASCADE,
    article_count   INTEGER NOT NULL DEFAULT 0,
    window_hours    INTEGER NOT NULL DEFAULT 24,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Story clusters (topic modeling — groups related articles across sources)
CREATE TABLE IF NOT EXISTS newsguru.story_clusters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_label   TEXT NOT NULL,
    summary         TEXT,
    article_count   INTEGER NOT NULL DEFAULT 0,
    avg_significance REAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS newsguru.article_clusters (
    article_id      UUID NOT NULL REFERENCES newsguru.articles(id) ON DELETE CASCADE,
    cluster_id      UUID NOT NULL REFERENCES newsguru.story_clusters(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_story_clusters_created ON newsguru.story_clusters(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_article_clusters_cluster ON newsguru.article_clusters(cluster_id);

-- News feed history (autoincrement, for long-term tracking)
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
