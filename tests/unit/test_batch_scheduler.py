# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 批量采集调度器."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.spider.batch_scheduler import BatchCrawlScheduler, BatchResult, BatchTask
from spide.storage.models import DeepContent, Platform


class TestBatchTask:
    """采集任务配置."""

    def test_default_values(self):
        task = BatchTask(platform="xhs")
        assert task.platform == Platform.XHS
        assert task.keywords == []
        assert task.max_notes == 20
        assert task.enable_comments is True

    def test_string_conversion(self):
        task = BatchTask(platform="dy", mode="detail")
        assert task.platform == Platform.DOUYIN
        assert task.mode.value == "detail"

    def test_custom_values(self):
        task = BatchTask(
            platform="bili",
            mode="creator",
            keywords=["AI", "技术"],
            max_notes=50,
            enable_comments=False,
        )
        assert task.platform == Platform.BILIBILI
        assert len(task.keywords) == 2


class TestBatchResult:
    """批量采集结果."""

    def test_default(self):
        result = BatchResult()
        assert result.total_contents == 0
        assert result.succeeded == []
        assert result.failed == {}

    def test_with_data(self):
        result = BatchResult(
            succeeded=["xhs", "dy"],
            failed={"wb": "timeout"},
            total_contents=10,
        )
        assert len(result.succeeded) == 2
        assert "wb" in result.failed


class TestBatchCrawlScheduler:
    """批量采集调度器."""

    @pytest.mark.asyncio
    async def test_empty_tasks_raises(self):
        scheduler = BatchCrawlScheduler()
        with pytest.raises(Exception, match="任务列表为空"):
            await scheduler.run([])

    @pytest.mark.asyncio
    async def test_run_with_mock_adapter(self):
        """使用 mock 测试批量调度逻辑."""
        mock_result = MagicMock()
        mock_result.contents = [
            DeepContent(platform=Platform.XHS, title="测试1"),
            DeepContent(platform=Platform.XHS, title="测试2"),
        ]
        mock_result.comments = []
        mock_result.creators = []

        progress_log = []

        async def mock_progress(completed, total, platform, status):
            progress_log.append((completed, platform, status))

        with patch(
            "spide.spider.media_crawler_adapter.MediaCrawlerAdapter"
        ) as MockAdapter:
            instance = MockAdapter.return_value
            instance.deep_crawl = AsyncMock(return_value=mock_result)

            scheduler = BatchCrawlScheduler(max_concurrent=2)
            tasks = [
                BatchTask(platform="xhs", keywords=["AI"]),
                BatchTask(platform="dy", keywords=["AI"]),
            ]
            result = await scheduler.run(tasks, on_progress=mock_progress)

        assert result.total_contents == 4  # 2 per platform
        assert "xhs" in result.succeeded
        assert "dy" in result.succeeded
        assert len(result.failed) == 0
        assert len(progress_log) > 0

    @pytest.mark.asyncio
    async def test_run_partial_failure(self):
        """部分平台失败."""
        mock_result = MagicMock()
        mock_result.contents = [DeepContent(platform=Platform.XHS, title="OK")]
        mock_result.comments = []
        mock_result.creators = []

        with patch(
            "spide.spider.media_crawler_adapter.MediaCrawlerAdapter"
        ) as MockAdapter:
            instance = MockAdapter.return_value

            # 第一次调用成功，第二次调用失败
            instance.deep_crawl = AsyncMock(
                side_effect=[mock_result, Exception("平台不可用")]
            )

            scheduler = BatchCrawlScheduler()
            tasks = [
                BatchTask(platform="xhs"),
                BatchTask(platform="ks"),
            ]
            result = await scheduler.run(tasks)

        assert "xhs" in result.succeeded
        assert "ks" in result.failed
        assert result.total_contents == 1

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """验证并发限制通过 Semaphore 控制."""
        call_times = []

        async def mock_deep_crawl(**kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)
            result = MagicMock()
            result.contents = []
            result.comments = []
            result.creators = []
            return result

        with patch(
            "spide.spider.media_crawler_adapter.MediaCrawlerAdapter"
        ) as MockAdapter:
            instance = MockAdapter.return_value
            instance.deep_crawl = mock_deep_crawl

            scheduler = BatchCrawlScheduler(max_concurrent=1)
            tasks = [
                BatchTask(platform="xhs"),
                BatchTask(platform="dy"),
                BatchTask(platform="bili"),
            ]
            await scheduler.run(tasks)

        # max_concurrent=1，应该是串行的
        assert len(call_times) == 3
