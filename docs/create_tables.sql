-- 快速创建 hot_topics 表
-- 在 Supabase Dashboard -> SQL Editor 中执行

CREATE TABLE IF NOT EXISTS hot_topics (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    hot_value BIGINT,
    url TEXT,
    rank INTEGER,
    category TEXT,
    summary TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    extra JSONB DEFAULT '{}'
);

-- 添加唯一约束（自动去重）
DO $$ BEGIN
    ALTER TABLE hot_topics ADD CONSTRAINT uk_hot_topics_title_source UNIQUE (title, source);
EXCEPTION
    WHEN duplicate_table THEN null;
END $$;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hot_topics_source ON hot_topics(source);
CREATE INDEX IF NOT EXISTS idx_hot_topics_hot_value ON hot_topics(hot_value DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_hot_topics_fetched_at ON hot_topics(fetched_at DESC);

-- 启用 RLS
ALTER TABLE hot_topics ENABLE ROW LEVEL SECURITY;

-- 允许匿名读取
CREATE POLICY "allow_public_read_hot_topics" ON hot_topics FOR SELECT USING (true);
