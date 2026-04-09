# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — SQLite 仓库完整覆盖."""

from pathlib import Path

import pytest

from spide.storage.models import CrawlTask, HotTopic, TaskStatus, TopicSource
from spide.storage.sqlite_repo import SqliteRepository


class TestSqliteCRUD:
    """SQLite 增删改查完整测试."""

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
    async def test_save_many_batch(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        items = [HotTopic(title=f"批量{i}", source=TopicSource.WEIBO, rank=i + 1) for i in range(5)]
        ids = await repo.save_many(items)
        assert len(ids) == 5
        assert all(i > 0 for i in ids)
        await repo.stop()

    @pytest.mark.asyncio
    async def test_update(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        topic = HotTopic(title="原标题", source=TopicSource.WEIBO, hot_value=100)
        topic_id = await repo.save(topic)

        topic.id = topic_id
        topic.title = "修改标题"
        topic.hot_value = 99999
        await repo.save(topic)

        loaded = await repo.get(topic_id)
        assert loaded.title == "修改标题"
        assert loaded.hot_value == 99999
        await repo.stop()

    @pytest.mark.asyncio
    async def test_query_with_filter(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        for i in range(3):
            await repo.save(HotTopic(title=f"微博{i}", source=TopicSource.WEIBO, rank=i + 1))
        for i in range(2):
            await repo.save(HotTopic(title=f"百度{i}", source=TopicSource.BAIDU, rank=i + 1))

        weibo = await repo.query(source="weibo")
        assert len(weibo) == 3
        baidu = await repo.query(source="baidu")
        assert len(baidu) == 2
        await repo.stop()

    @pytest.mark.asyncio
    async def test_query_offset(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        for i in range(10):
            await repo.save(HotTopic(title=f"话题{i}", source=TopicSource.WEIBO))

        page1 = await repo.query(limit=3, offset=0)
        page2 = await repo.query(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        # ID 降序，不应重复
        ids1 = {t.id for t in page1}
        ids2 = {t.id for t in page2}
        assert ids1.isdisjoint(ids2)
        await repo.stop()

    @pytest.mark.asyncio
    async def test_count_and_exists(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        await repo.save(HotTopic(title="A", source=TopicSource.WEIBO))
        await repo.save(HotTopic(title="B", source=TopicSource.BAIDU))

        assert await repo.count() == 2
        assert await repo.count(source="weibo") == 1
        assert await repo.exists(source="weibo") is True
        assert await repo.exists(source="zhihu") is False
        await repo.stop()

    @pytest.mark.asyncio
    async def test_delete(self, tmp_db: Path):
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        topic_id = await repo.save(HotTopic(title="待删除", source=TopicSource.ZHIHU))
        assert await repo.delete(topic_id) is True
        assert await repo.get(topic_id) is None
        assert await repo.delete(9999) is False
        await repo.stop()

    @pytest.mark.asyncio
    async def test_ensure_db_error(self):
        from spide.exceptions import StorageError

        repo = SqliteRepository(HotTopic)
        with pytest.raises(StorageError, match="未初始化"):
            await repo.save(HotTopic(title="test", source=TopicSource.WEIBO))

    @pytest.mark.asyncio
    async def test_crawl_task_repo(self, tmp_db: Path):
        repo = SqliteRepository(CrawlTask, db_path=str(tmp_db))
        await repo.start()

        task = CrawlTask(name="weibo_crawl", source=TopicSource.WEIBO, status=TaskStatus.PENDING)
        task_id = await repo.save(task)
        loaded = await repo.get(task_id)
        assert loaded.name == "weibo_crawl"
        assert loaded.status == TaskStatus.PENDING
        await repo.stop()
