# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""定时采集调度器 — Cron-like 定时任务管理.

用法:
    from spide.spider.task_scheduler import TaskScheduler, ScheduledJob

    scheduler = TaskScheduler()
    scheduler.add_job(
        ScheduledJob(
            name="微博热搜",
            platforms=["weibo"],
            interval_seconds=300,  # 每 5 分钟
        ),
    )
    await scheduler.start()
    # ... 运行一段时间后
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from spide.exceptions import SpiderError
from spide.logging import get_logger

logger = get_logger(__name__)

# 任务执行回调
JobCallback = Callable[[dict[str, list]], Coroutine[Any, Any, None]]


@dataclass
class ScheduledJob:
    """定时采集任务配置."""

    name: str
    platforms: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # UAPI 热搜源
    interval_seconds: int = 300  # 默认 5 分钟
    save_to_db: bool = False
    export_format: str = ""  # 空=不导出, json/csv/excel
    max_runs: int = 0  # 0=无限
    enabled: bool = True

    # 运行时状态
    _run_count: int = field(default=0, init=False, repr=False)
    _last_run: datetime | None = field(default=None, init=False, repr=False)

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def last_run(self) -> datetime | None:
        return self._last_run

    @property
    def is_exhausted(self) -> bool:
        return self.max_runs > 0 and self._run_count >= self.max_runs


class TaskScheduler:
    """定时采集调度器.

    基于 asyncio 循环实现的轻量级任务调度，
    支持多任务并行、最大运行次数、启停控制。
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._on_result: JobCallback | None = None

    def add_job(self, job: ScheduledJob) -> None:
        """添加定时任务."""
        if job.name in self._jobs:
            raise SpiderError(f"任务名称已存在: {job.name}")
        self._jobs[job.name] = job
        logger.debug("job_added", name=job.name, interval=job.interval_seconds)

    def remove_job(self, name: str) -> None:
        """移除定时任务."""
        if name not in self._jobs:
            raise SpiderError(f"任务不存在: {name}")
        # 停止运行中的任务
        if name in self._tasks:
            self._tasks[name].cancel()
            del self._tasks[name]
        del self._jobs[name]
        logger.debug("job_removed", name=name)

    def on_result(self, callback: JobCallback) -> None:
        """注册结果回调."""
        self._on_result = callback

    @property
    def jobs(self) -> dict[str, ScheduledJob]:
        """获取所有任务状态."""
        return dict(self._jobs)

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """启动调度器."""
        if self._running:
            return

        self._running = True
        logger.info("scheduler_started", jobs=len(self._jobs))

        for name, job in self._jobs.items():
            if job.enabled:
                task = asyncio.create_task(self._run_loop(job))
                self._tasks[name] = task

    async def stop(self) -> None:
        """停止调度器."""
        self._running = False

        for _name, task in self._tasks.items():
            task.cancel()
            import contextlib

            with contextlib.suppress(asyncio.CancelledError):
                await task

        self._tasks.clear()
        logger.info("scheduler_stopped")

    async def _run_loop(self, job: ScheduledJob) -> None:
        """单个任务的运行循环."""
        while self._running and not job.is_exhausted:
            try:
                result = await self._execute_job(job)
                job._run_count += 1
                job._last_run = datetime.now()

                if self._on_result:
                    await self._on_result(result)

                logger.debug(
                    "job_executed",
                    name=job.name,
                    run_count=job._run_count,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("job_error", name=job.name, error=str(e))

            # 等待下次执行
            try:
                await asyncio.sleep(job.interval_seconds)
            except asyncio.CancelledError:
                break

    async def _execute_job(self, job: ScheduledJob) -> dict[str, list]:
        """执行单个任务 — 采集热搜或深度采集."""
        start = time.monotonic()
        all_results: dict[str, list] = {}

        # UAPI 热搜采集
        if job.sources:
            from spide.config import load_settings
            from spide.spider.uapi_client import UAPIClient

            settings = load_settings()
            client = UAPIClient(settings.uapi)
            await client.start()
            try:
                for source in job.sources:
                    try:
                        topics = await client.fetch_hotboard(source)
                        all_results[f"hot_{source}"] = topics
                    except Exception as e:
                        logger.warning("job_source_failed", source=source, error=str(e))
            finally:
                await client.stop()

        # 深度采集
        if job.platforms:
            from spide.spider.batch_scheduler import BatchCrawlScheduler, BatchTask

            batch_tasks = [
                BatchTask(platform=p, mode="search", max_notes=10)
                for p in job.platforms
            ]
            scheduler = BatchCrawlScheduler()
            batch_result = await scheduler.run(batch_tasks)

            all_results["deep_contents"] = batch_result.contents
            all_results["deep_comments"] = batch_result.comments

        duration_ms = (time.monotonic() - start) * 1000
        logger.debug("job_execute_duration", duration_ms=round(duration_ms, 1), job_name=job.name)

        return all_results
