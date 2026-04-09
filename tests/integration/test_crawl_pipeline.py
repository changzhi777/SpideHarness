# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""集成测试 — 爬取管道（SQLite 真实数据库 + UAPI mock）."""

import pytest

from spide.storage.models import HotTopic, TopicSource
from spide.storage.sqlite_repo import SqliteRepository


class TestSqliteRealDB:
    """SQLite 真实数据库操作."""

    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, tmp_db):
        """完整的 CRUD 生命周期."""
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        # CREATE
        topic = HotTopic(
            title="测试热搜",
            source=TopicSource.WEIBO,
            hot_value=10000,
            url="https://weibo.com/test",
            rank=1,
        )
        topic_id = await repo.save(topic)
        assert topic_id is not None and topic_id > 0

        # READ
        loaded = await repo.get(topic_id)
        assert loaded is not None
        assert loaded.title == "测试热搜"
        assert loaded.source == TopicSource.WEIBO
        assert loaded.hot_value == 10000

        # UPDATE
        loaded.hot_value = 20000
        updated_id = await repo.save(loaded)
        assert updated_id == topic_id

        refreshed = await repo.get(topic_id)
        assert refreshed.hot_value == 20000

        # DELETE
        deleted = await repo.delete(topic_id)
        assert deleted is True
        assert await repo.get(topic_id) is None

        await repo.stop()

    @pytest.mark.asyncio
    async def test_batch_save_and_query(self, tmp_db):
        """批量保存 + 条件查询."""
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        # 批量插入
        topics = [
            HotTopic(title=f"微博热搜{i}", source=TopicSource.WEIBO, rank=i)
            for i in range(1, 6)
        ] + [
            HotTopic(title=f"百度热搜{i}", source=TopicSource.BAIDU, rank=i)
            for i in range(1, 4)
        ]

        ids = await repo.save_many(topics)
        assert len(ids) == 8
        assert all(id_ > 0 for id_ in ids)

        # 按源过滤
        weibo = await repo.query(source="weibo")
        assert len(weibo) == 5

        baidu = await repo.query(source="baidu")
        assert len(baidu) == 3

        # 统计
        total = await repo.count()
        assert total == 8

        weibo_count = await repo.count(source="weibo")
        assert weibo_count == 5

        await repo.stop()

    @pytest.mark.asyncio
    async def test_concurrent_access(self, tmp_db):
        """并发数据库访问（同一连接）."""
        import asyncio

        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()

        # 并发写入
        async def write_one(i: int) -> int:
            topic = HotTopic(title=f"并发测试{i}", source=TopicSource.WEIBO)
            return await repo.save(topic)

        ids = await asyncio.gather(*[write_one(i) for i in range(10)])
        assert len(ids) == 10
        assert all(id_ > 0 for id_ in ids)

        # 验证总数
        total = await repo.count()
        assert total == 10

        await repo.stop()

    @pytest.mark.asyncio
    async def test_persistence_across_sessions(self, tmp_db):
        """跨会话持久化验证."""
        # 会话 1：写入
        repo1 = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo1.start()
        topic = HotTopic(title="持久化测试", source=TopicSource.ZHIHU)
        topic_id = await repo1.save(topic)
        await repo1.stop()

        # 会话 2：读取
        repo2 = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo2.start()
        loaded = await repo2.get(topic_id)
        assert loaded is not None
        assert loaded.title == "持久化测试"
        assert loaded.source == TopicSource.ZHIHU
        await repo2.stop()


class TestCrawlPipelineIntegration:
    """爬取管道集成测试（mock HTTP + 真实 SQLite）."""

    @pytest.mark.asyncio
    async def test_fetch_parse_store(self, tmp_db):
        """完整流程: 抓取 → 解析 → 去重 → 存储."""

        from spide.spider.pipeline import deduplicate_items, parse_hot_items

        # 模拟 UAPI 响应
        mock_data = {
            "list": [
                {"title": "热点新闻A", "hot_value": 10000, "url": "https://a.com", "index": 1},
                {"title": "热点新闻B", "hot_value": 8000, "url": "https://b.com", "index": 2},
                {"title": "热点新闻A", "hot_value": 12000, "url": "https://a.com/v2", "index": 3},
            ]
        }

        # 解析
        items = parse_hot_items(mock_data["list"], source="weibo")
        assert len(items) == 3

        # 去重
        unique = deduplicate_items(items)
        assert len(unique) == 2
        # 保留更高热度
        a_item = next(i for i in unique if i.title == "热点新闻A")
        assert a_item.hot_value == 12000

        # 存储
        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()
        ids = await repo.save_many(unique)
        assert len(ids) == 2

        # 验证
        stored = await repo.query(source="weibo")
        assert len(stored) == 2

        await repo.stop()
