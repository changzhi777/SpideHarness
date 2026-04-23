-- ============================================================
-- Supabase PostgreSQL DDL — SpideHarness Agent
-- 在 Supabase Dashboard → SQL Editor 中执行
-- ============================================================

-- 1. hot_topics — 热搜话题
CREATE TABLE IF NOT EXISTS hot_topics (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    hot_value   BIGINT,
    url         TEXT,
    rank        INTEGER,
    category    TEXT,
    summary     TEXT,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra       JSONB DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_hot_topics_title_source
    ON hot_topics (title, source);
CREATE INDEX IF NOT EXISTS idx_hot_topics_source ON hot_topics (source);
CREATE INDEX IF NOT EXISTS idx_hot_topics_hot_value ON hot_topics (hot_value DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_hot_topics_fetched_at ON hot_topics (fetched_at DESC);

-- 2. news_articles — 新闻文章
CREATE TABLE IF NOT EXISTS news_articles (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL,
    source       TEXT NOT NULL,
    author       TEXT,
    published_at TIMESTAMPTZ,
    content      TEXT,
    summary      TEXT,
    category     TEXT,
    keywords     JSONB DEFAULT '[]',
    image_urls   JSONB DEFAULT '[]',
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra        JSONB DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_news_articles_url_source
    ON news_articles (url, source);

-- 3. deep_contents — 深度采集内容
CREATE TABLE IF NOT EXISTS deep_contents (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform       TEXT NOT NULL,
    content_id     TEXT NOT NULL DEFAULT '',
    content_type   TEXT DEFAULT '',
    title          TEXT DEFAULT '',
    content        TEXT DEFAULT '',
    url            TEXT DEFAULT '',
    author_id      TEXT DEFAULT '',
    author_name    TEXT DEFAULT '',
    author_avatar  TEXT DEFAULT '',
    like_count     BIGINT,
    comment_count  BIGINT,
    share_count    BIGINT,
    collect_count  BIGINT,
    view_count     BIGINT,
    ip_location    TEXT DEFAULT '',
    media_urls     JSONB DEFAULT '[]',
    tags           JSONB DEFAULT '[]',
    publish_time   BIGINT,
    source_keyword TEXT DEFAULT '',
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra          JSONB DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_deep_contents_platform_cid
    ON deep_contents (platform, content_id);
CREATE INDEX IF NOT EXISTS idx_deep_contents_platform ON deep_contents (platform);
CREATE INDEX IF NOT EXISTS idx_deep_contents_keyword ON deep_contents (source_keyword);

-- 4. deep_comments — 深度采集评论
CREATE TABLE IF NOT EXISTS deep_comments (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform           TEXT NOT NULL,
    comment_id         TEXT NOT NULL DEFAULT '',
    content_id         TEXT NOT NULL DEFAULT '',
    parent_comment_id  TEXT DEFAULT '',
    content            TEXT DEFAULT '',
    user_id            TEXT DEFAULT '',
    nickname           TEXT DEFAULT '',
    avatar             TEXT DEFAULT '',
    like_count         BIGINT,
    sub_comment_count  BIGINT,
    ip_location        TEXT DEFAULT '',
    publish_time       BIGINT,
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra              JSONB DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_deep_comments_platform_cid
    ON deep_comments (platform, comment_id);
CREATE INDEX IF NOT EXISTS idx_deep_comments_content ON deep_comments (platform, content_id);

-- 5. deep_creators — 深度采集创作者
CREATE TABLE IF NOT EXISTS deep_creators (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform     TEXT NOT NULL,
    user_id      TEXT NOT NULL DEFAULT '',
    nickname     TEXT DEFAULT '',
    avatar       TEXT DEFAULT '',
    description  TEXT DEFAULT '',
    gender       TEXT DEFAULT '',
    ip_location  TEXT DEFAULT '',
    follows      BIGINT,
    fans         BIGINT,
    interaction  BIGINT,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra        JSONB DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_deep_creators_platform_uid
    ON deep_creators (platform, user_id);

-- 6. crawl_tasks — 爬取任务
CREATE TABLE IF NOT EXISTS crawl_tasks (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT NOT NULL,
    source        TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    params        JSONB DEFAULT '{}',
    result_count  INTEGER DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ
);

-- 7. crawl_sessions — 爬取会话
CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id    TEXT PRIMARY KEY,
    session_key   TEXT,
    cwd           TEXT DEFAULT '',
    model         TEXT DEFAULT 'glm-5.1',
    system_prompt TEXT,
    messages      JSONB DEFAULT '[]',
    usage         JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary       TEXT,
    crawled_urls  JSONB DEFAULT '[]',
    task_ids      JSONB DEFAULT '[]',
    progress      REAL DEFAULT 0.0
);

-- ============================================================
-- RLS 策略 — service_role 可写入，anon 只读
-- ============================================================
ALTER TABLE hot_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_contents ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_creators ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_hot_topics" ON hot_topics FOR SELECT USING (true);
CREATE POLICY "anon_read_news_articles" ON news_articles FOR SELECT USING (true);
CREATE POLICY "anon_read_deep_contents" ON deep_contents FOR SELECT USING (true);
CREATE POLICY "anon_read_deep_comments" ON deep_comments FOR SELECT USING (true);
CREATE POLICY "anon_read_deep_creators" ON deep_creators FOR SELECT USING (true);
CREATE POLICY "anon_read_crawl_tasks" ON crawl_tasks FOR SELECT USING (true);
