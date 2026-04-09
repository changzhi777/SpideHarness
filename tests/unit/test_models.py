# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 数据模型序列化."""



from spide.storage.models import (
    ArticleCategory,
    CrawlSession,
    CrawlTask,
    HotTopic,
    NewsArticle,
    TaskStatus,
    TopicSource,
)


class TestHotTopic:
    """HotTopic 模型."""

    def test_full_serialization(self):
        topic = HotTopic(
            title="测试",
            source=TopicSource.WEIBO,
            hot_value=99999,
            url="https://example.com",
            rank=1,
            category=ArticleCategory.TECH,
            summary="摘要",
        )
        data = topic.model_dump(mode="json")
        restored = HotTopic(**data)
        assert restored.title == topic.title
        assert restored.source == TopicSource.WEIBO
        assert restored.hot_value == 99999
        assert restored.category == ArticleCategory.TECH

    def test_enum_values(self):
        assert TopicSource.WEIBO.value == "weibo"
        assert TaskStatus.PENDING.value == "pending"

    def test_default_values(self):
        topic = HotTopic(title="默认", source=TopicSource.BAIDU)
        assert topic.id is None
        assert topic.hot_value is None
        assert topic.extra == {}
        assert topic.fetched_at is not None


class TestCrawlTask:
    """CrawlTask 模型."""

    def test_status_roundtrip(self):
        task = CrawlTask(name="test", source=TopicSource.WEIBO, status=TaskStatus.RUNNING)
        data = task.model_dump(mode="json")
        restored = CrawlTask(**data)
        assert restored.status == TaskStatus.RUNNING

    def test_params_dict(self):
        task = CrawlTask(name="test", source=TopicSource.ZHIHU, params={"limit": 10})
        data = task.model_dump(mode="json")
        assert data["params"]["limit"] == 10


class TestNewsArticle:
    """NewsArticle 模型."""

    def test_keywords_list(self):
        article = NewsArticle(
            title="新闻",
            url="https://example.com",
            source=TopicSource.WEIBO,
            keywords=["科技", "AI"],
        )
        data = article.model_dump(mode="json")
        restored = NewsArticle(**data)
        assert restored.keywords == ["科技", "AI"]


class TestCrawlSession:
    """CrawlSession 模型."""

    def test_full_session(self):
        session = CrawlSession(
            session_id="test-001",
            session_key="weibo:daily",
            messages=[{"role": "user", "content": "采集"}],
            crawled_urls=["https://weibo.com"],
            task_ids=[1, 2],
            progress=0.5,
        )
        data = session.model_dump(mode="json")
        assert data["session_id"] == "test-001"
        assert data["progress"] == 0.5
        restored = CrawlSession(**data)
        assert restored.crawled_urls == ["https://weibo.com"]
