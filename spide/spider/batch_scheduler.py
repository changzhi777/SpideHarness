# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""批量多平台采集调度器 — 并行深度采集 + 进度回调 + 结果聚合.

用法:
    from spide.spider.batch_scheduler import BatchCrawlScheduler

    scheduler = BatchCrawlScheduler()
    result = await scheduler.run(
        tasks=[
            BatchTask(platform="xhs", mode="search", keywords=["AI"]),
            BatchTask(platform="dy", mode="search", keywords=["AI"]),
        ],
        on_progress=print,
    )
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from spide.exceptions import SpiderError
from spide.logging import get_logger
from spide.storage.models import (
    CrawlMode,
    DeepComment,
    DeepContent,
    DeepCreator,
    Platform,
)

logger = get_logger(__name__)

# 进度回调类型: (已完成数, 总数, 当前平台, 状态)
ProgressCallback = Callable[[int, int, str, str], Coroutine[Any, Any, None]]


@dataclass
class BatchTask:
    """单个采集任务配置."""

    platform: Platform | str
    mode: CrawlMode | str = CrawlMode.SEARCH
    keywords: list[str] = field(default_factory=list)
    content_ids: list[str] = field(default_factory=list)
    creator_ids: list[str] = field(default_factory=list)
    max_notes: int = 20
    enable_comments: bool = True
    headless: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.platform, str):
            self.platform = Platform(self.platform)
        if isinstance(self.mode, str):
            self.mode = CrawlMode(self.mode)


@dataclass
class BatchResult:
    """批量采集聚合结果."""

    total_contents: int = 0
    total_comments: int = 0
    total_creators: int = 0
    succeeded: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    contents: list[DeepContent] = field(default_factory=list)
    comments: list[DeepComment] = field(default_factory=list)
    creators: list[DeepCreator] = field(default_factory=list)


class BatchCrawlScheduler:
    """批量多平台并行采集调度器.

    使用 asyncio.Semaphore 控制并发数，
    每个平台独立执行，结果最终聚合。
    """

    def __init__(self, *, max_concurrent: int = 3) -> None:
        self._max_concurrent = max_concurrent

    async def run(
        self,
        tasks: list[BatchTask],
        *,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult:
        """执行批量采集任务.

        Args:
            tasks: 采集任务列表
            on_progress: 进度回调 (completed, total, platform, status)

        Returns:
            BatchResult 聚合结果
        """
        if not tasks:
            raise SpiderError("批量采集任务列表为空")

        start = time.monotonic()
        result = BatchResult()
        total = len(tasks)
        semaphore = asyncio.Semaphore(self._max_concurrent)
        completed = 0

        async def _run_one(task: BatchTask) -> None:
            nonlocal completed
            platform_name = task.platform.value if isinstance(task.platform, Platform) else str(task.platform)

            async with semaphore:
                try:
                    if on_progress:
                        await on_progress(completed, total, platform_name, "running")

                    single = await self._crawl_single(task)

                    result.contents.extend(single.get("contents", []))
                    result.comments.extend(single.get("comments", []))
                    result.creators.extend(single.get("creators", []))
                    result.succeeded.append(platform_name)

                    completed += 1
                    if on_progress:
                        await on_progress(completed, total, platform_name, "done")

                    logger.debug(
                        "batch_task_done",
                        platform=platform_name,
                        contents=len(single.get("contents", [])),
                    )

                except Exception as e:
                    completed += 1
                    platform_name_str = task.platform.value if isinstance(task.platform, Platform) else str(task.platform)
                    result.failed[platform_name_str] = str(e)

                    if on_progress:
                        await on_progress(completed, total, platform_name_str, "failed")

                    logger.warning(
                        "batch_task_failed",
                        platform=platform_name_str,
                        error=str(e),
                    )

        # 并行执行所有任务
        await asyncio.gather(*[_run_one(t) for t in tasks])

        result.total_contents = len(result.contents)
        result.total_comments = len(result.comments)
        result.total_creators = len(result.creators)

        duration_ms = (time.monotonic() - start) * 1000
        logger.debug("batch_run_duration", duration_ms=round(duration_ms, 1), total_tasks=total, total_contents=result.total_contents)

        logger.debug(
            "batch_completed",
            succeeded=len(result.succeeded),
            failed=len(result.failed),
            contents=result.total_contents,
        )

        return result

    @staticmethod
    async def _crawl_single(task: BatchTask) -> dict[str, list]:
        """执行单个采集任务."""
        from spide.spider.media_crawler_adapter import MediaCrawlerAdapter

        adapter = MediaCrawlerAdapter()
        crawl_result = await adapter.deep_crawl(
            platform=task.platform,  # type: ignore[arg-type]
            mode=task.mode,  # type: ignore[arg-type]
            keywords=task.keywords or None,
            content_ids=task.content_ids or None,
            creator_ids=task.creator_ids or None,
            max_notes=task.max_notes,
            enable_comments=task.enable_comments,
            headless=task.headless,
        )
        return {
            "contents": crawl_result.contents,
            "comments": crawl_result.comments,
            "creators": crawl_result.creators,
        }
