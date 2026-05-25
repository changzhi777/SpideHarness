# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 定时搜索服务."""

from unittest.mock import AsyncMock, MagicMock, patch

from spide.spider.timed_search import TimedSearchService
from spide.storage.models import TimedSearchBatch, TimedSearchRecord, TopicSource


class TestTimedSearchModels:
    """数据模型测试."""

    def test_batch_defaults(self):
        batch = TimedSearchBatch(batch_key="2026-05-25_0900", schedule_time="09:00")
        assert batch.status == "pending"
        assert batch.total_topics == 0
        assert batch.platforms == []

    def test_record_defaults(self):
        record = TimedSearchRecord(
            topic_title="测试热搜",
            topic_source=TopicSource.WEIBO,
        )
        assert record.search_title == ""
        assert record.search_url == ""
        assert record.batch_id is None

    def test_batch_roundtrip(self):
        batch = TimedSearchBatch(
            batch_key="2026-05-25_1800",
            schedule_time="18:00",
            platforms=["weibo", "baidu"],
            total_topics=30,
            search_count=25,
            status="completed",
        )
        data = batch.model_dump(mode="json")
        restored = TimedSearchBatch(**data)
        assert restored.batch_key == "2026-05-25_1800"
        assert restored.platforms == ["weibo", "baidu"]
        assert restored.search_count == 25

    def test_record_roundtrip(self):
        record = TimedSearchRecord(
            batch_id=1,
            topic_title="AI突破",
            topic_source=TopicSource.ZHIHU,
            topic_hot_value=5000,
            topic_rank=1,
            search_title="AI技术进展",
            search_url="https://example.com",
            search_snippet="摘要内容",
            schedule_time="09:00",
        )
        data = record.model_dump(mode="json")
        restored = TimedSearchRecord(**data)
        assert restored.topic_title == "AI突破"
        assert restored.search_url == "https://example.com"


class TestTimedSearchService:
    """TimedSearchService 测试."""

    async def test_run_once_with_mock(self, tmp_path):
        from spide.mcp.search_provider import SearchResult

        db_path = str(tmp_path / "test.db")
        svc = TimedSearchService(db_path=db_path)
        await svc.start()
        try:
            # Mock UAPI 采集
            mock_topic = MagicMock()
            mock_topic.title = "AI大模型突破"
            mock_topic.source = TopicSource.WEIBO
            mock_topic.hot_value = 5000
            mock_topic.rank = 1
            mock_topic.url = "https://weibo.com/1"

            # Mock WebSearchProvider
            mock_search_results = [
                SearchResult(title="AI进展", url="https://a.com", description="描述"),
            ]

            with patch("spide.spider.uapi_client.UAPIClient") as MockClient, \
                 patch("spide.mcp.search_provider.WebSearchProvider") as MockSearch, \
                 patch("spide.config.load_settings") as MockSettings:
                MockSettings.return_value = MagicMock()
                client_inst = MockClient.return_value
                client_inst.start = AsyncMock()
                client_inst.stop = AsyncMock()
                client_inst.fetch_hotboard = AsyncMock(return_value=[mock_topic])

                provider_inst = MockSearch.return_value
                provider_inst.search = AsyncMock(return_value=mock_search_results)

                result = await svc.run_once(
                    schedule_time="09:00",
                    sources=["weibo"],
                    top_n=5,
                    search_limit=3,
                )

            assert result["status"] == "completed"
            assert result["total_topics"] == 1
            assert result["search_count"] == 1
            assert "2026-" in result["batch_key"]
            assert "_0900" in result["batch_key"]
        finally:
            await svc.stop()

    async def test_run_once_fetch_fails(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        svc = TimedSearchService(db_path=db_path)
        await svc.start()
        try:
            with patch("spide.spider.uapi_client.UAPIClient") as MockClient, \
                 patch("spide.mcp.search_provider.WebSearchProvider"):
                client_inst = MockClient.return_value
                client_inst.start = AsyncMock(side_effect=Exception("API不可用"))

                result = await svc.run_once(schedule_time="18:00", sources=["weibo"])

            assert result["status"] == "completed"
            assert result["total_topics"] == 0
            assert result["search_count"] == 0
        finally:
            await svc.stop()

    async def test_query_records(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        svc = TimedSearchService(db_path=db_path)
        await svc.start()
        try:
            # 手动插入一条记录
            record = TimedSearchRecord(
                topic_title="测试",
                topic_source=TopicSource.WEIBO,
                schedule_time="09:00",
            )
            await svc._record_repo.save(record)

            records = await svc.query_records(schedule_time="09:00", limit=10)
            assert len(records) == 1
            assert records[0]["topic_title"] == "测试"
        finally:
            await svc.stop()

    async def test_query_batches_empty(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        svc = TimedSearchService(db_path=db_path)
        await svc.start()
        try:
            batches = await svc.query_batches()
            assert batches == []
        finally:
            await svc.stop()
