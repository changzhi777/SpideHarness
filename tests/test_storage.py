# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""迭代 2 验证测试 — 存储层 + 会话持久化."""

from pathlib import Path

import pytest

from spide.session_storage import SessionStorage
from spide.storage.models import CrawlTask, HotTopic, TaskStatus, TopicSource
from spide.storage.sqlite_repo import SqliteRepository

# ---------------------------------------------------------------------------
# 模型序列化测试
# ---------------------------------------------------------------------------


class TestModels:
    """Pydantic 模型序列化/反序列化."""

    def test_hot_topic_serialization(self):
        topic = HotTopic(
            title="测试热搜",
            source=TopicSource.WEIBO,
            hot_value=99999,
            rank=1,
        )
        data = topic.model_dump(mode="json")
        assert data["title"] == "测试热搜"
        assert data["source"] == "weibo"
        assert data["hot_value"] == 99999

        # 反序列化
        restored = HotTopic(**data)
        assert restored.title == topic.title
        assert restored.source == topic.source

    def test_crawl_task_serialization(self):
        task = CrawlTask(name="weibo_crawl", source=TopicSource.WEIBO, status=TaskStatus.PENDING)
        data = task.model_dump(mode="json")
        restored = CrawlTask(**data)
        assert restored.status == TaskStatus.PENDING


# ---------------------------------------------------------------------------
# SQLite CRUD 测试
# ---------------------------------------------------------------------------


class TestSqliteRepo:
    """SQLite 异步仓库."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        topic = HotTopic(title="微博热搜1", source=TopicSource.WEIBO, hot_value=50000, rank=1)
        topic_id = await repo.save(topic)
        assert topic_id > 0

        loaded = await repo.get(topic_id)
        assert loaded is not None
        assert loaded.title == "微博热搜1"
        assert loaded.source == TopicSource.WEIBO
        await repo.stop()

    @pytest.mark.asyncio
    async def test_query_with_filter(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        for i in range(5):
            await repo.save(
                HotTopic(title=f"微博{i}", source=TopicSource.WEIBO, rank=i + 1)
            )
        for i in range(3):
            await repo.save(
                HotTopic(title=f"百度{i}", source=TopicSource.BAIDU, rank=i + 1)
            )

        weibo_topics = await repo.query(source="weibo")
        assert len(weibo_topics) == 5

        baidu_topics = await repo.query(source="baidu")
        assert len(baidu_topics) == 3

        all_count = await repo.count()
        assert all_count == 8
        await repo.stop()

    @pytest.mark.asyncio
    async def test_delete(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        topic_id = await repo.save(
            HotTopic(title="待删除", source=TopicSource.ZHIHU)
        )
        assert await repo.delete(topic_id) is True
        assert await repo.get(topic_id) is None
        assert await repo.delete(9999) is False
        await repo.stop()


# ---------------------------------------------------------------------------
# 会话持久化测试
# ---------------------------------------------------------------------------


class TestSessionStorage:
    """会话快照存储."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, tmp_path: Path, monkeypatch):
        # 重定向工作空间到临时目录
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        await storage.save_snapshot(
            session_id="test-001",
            session_key="weibo:daily",
            model="glm-5.1",
            messages=[{"role": "user", "content": "采集微博热搜"}],
            crawled_urls=["https://weibo.com/1", "https://weibo.com/2"],
            progress=0.5,
        )

        # 加载最新
        latest = await storage.load_latest()
        assert latest is not None
        assert latest["session_id"] == "test-001"
        assert len(latest["crawled_urls"]) == 2
        assert latest["progress"] == 0.5

        # 按 session_key 加载
        key_data = await storage.load_latest_for_session_key("weibo:daily")
        assert key_data is not None
        assert key_data["session_id"] == "test-001"

    @pytest.mark.asyncio
    async def test_list_snapshots(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        for i in range(3):
            await storage.save_snapshot(session_id=f"snap-{i}")

        snapshots = await storage.list_snapshots()
        assert len(snapshots) == 3
