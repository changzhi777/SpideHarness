# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 定时采集调度器."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.spider.task_scheduler import ScheduledJob, TaskScheduler


class TestScheduledJob:
    """定时任务配置."""

    def test_default_values(self):
        job = ScheduledJob(name="test")
        assert job.interval_seconds == 300
        assert job.max_runs == 0
        assert job.enabled is True
        assert job.run_count == 0
        assert job.last_run is None
        assert not job.is_exhausted

    def test_exhausted(self):
        job = ScheduledJob(name="test", max_runs=2)
        assert not job.is_exhausted
        job._run_count = 2
        assert job.is_exhausted

    def test_not_exhausted_unlimited(self):
        job = ScheduledJob(name="test", max_runs=0)
        job._run_count = 100
        assert not job.is_exhausted


class TestTaskScheduler:
    """定时调度器."""

    def test_add_job(self):
        scheduler = TaskScheduler()
        job = ScheduledJob(name="test_job", sources=["weibo"])
        scheduler.add_job(job)
        assert "test_job" in scheduler.jobs

    def test_add_duplicate_job_raises(self):
        scheduler = TaskScheduler()
        scheduler.add_job(ScheduledJob(name="test"))
        with pytest.raises(Exception, match="已存在"):
            scheduler.add_job(ScheduledJob(name="test"))

    def test_remove_job(self):
        scheduler = TaskScheduler()
        scheduler.add_job(ScheduledJob(name="test"))
        scheduler.remove_job("test")
        assert "test" not in scheduler.jobs

    def test_remove_nonexistent_raises(self):
        scheduler = TaskScheduler()
        with pytest.raises(Exception, match="不存在"):
            scheduler.remove_job("nonexistent")

    async def test_start_stop(self):
        scheduler = TaskScheduler()
        job = ScheduledJob(
            name="quick",
            sources=[],
            platforms=[],
            interval_seconds=1,
            max_runs=1,
        )
        scheduler.add_job(job)
        assert not scheduler.is_running

        await scheduler.start()
        assert scheduler.is_running

        # 等任务执行完
        await asyncio.sleep(0.3)
        await scheduler.stop()
        assert not scheduler.is_running

    async def test_max_runs_respected(self):
        """验证 max_runs 限制."""
        results_log = []

        async def on_result(data):
            results_log.append(data)

        scheduler = TaskScheduler()
        scheduler.on_result(on_result)

        job = ScheduledJob(
            name="limited",
            sources=["weibo"],
            interval_seconds=0,
            max_runs=2,
        )
        scheduler.add_job(job)

        with patch(
            "spide.spider.uapi_client.UAPIClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.start = AsyncMock()
            instance.stop = AsyncMock()
            instance.fetch_hotboard = AsyncMock(return_value=[MagicMock()])

            await scheduler.start()
            await asyncio.sleep(0.5)
            await scheduler.stop()

        assert job.run_count <= 2

    async def test_disabled_job_not_started(self):
        scheduler = TaskScheduler()
        job = ScheduledJob(
            name="disabled",
            sources=[],
            platforms=[],
            interval_seconds=1,
            enabled=False,
        )
        scheduler.add_job(job)
        await scheduler.start()
        assert len(scheduler._tasks) == 0
        await scheduler.stop()

    def test_jobs_property_returns_copy(self):
        scheduler = TaskScheduler()
        scheduler.add_job(ScheduledJob(name="test"))
        jobs = scheduler.jobs
        jobs["another"] = ScheduledJob(name="another")
        assert "another" not in scheduler.jobs


class TestCronTimes:
    """cron 定时测试."""

    def test_cron_times_field(self):
        job = ScheduledJob(name="cron_job", cron_times=["09:00", "18:00"])
        assert job.cron_times == ["09:00", "18:00"]

    def test_interval_mode_no_cron(self):
        job = ScheduledJob(name="interval", interval_seconds=300)
        assert job.next_wait_seconds() == 300.0

    def test_cron_next_wait_future(self):
        """当前时间在 cron 时间之前."""
        from unittest.mock import patch
        from datetime import datetime

        job = ScheduledJob(name="cron", cron_times=["23:59"])
        # mock 当前时间为 08:00
        mock_now = datetime(2026, 5, 25, 8, 0, 0)
        with patch("spide.spider.task_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            wait = job.next_wait_seconds()
            # 08:00 → 23:59 = 15h59m = 57540s
            assert 57500 <= wait <= 57540

    def test_cron_next_wait_past_today(self):
        """当前时间已过所有 cron 时间，应等到明天."""
        from unittest.mock import patch
        from datetime import datetime

        job = ScheduledJob(name="cron", cron_times=["06:00"])
        mock_now = datetime(2026, 5, 25, 20, 0, 0)
        with patch("spide.spider.task_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            wait = job.next_wait_seconds()
            # 20:00 → 明天 06:00 = 10h = 36000s
            assert 35900 <= wait <= 36000

    def test_cron_picks_nearest(self):
        """多个 cron 时间，选最近的."""
        from unittest.mock import patch
        from datetime import datetime

        job = ScheduledJob(name="cron", cron_times=["09:00", "18:00"])
        mock_now = datetime(2026, 5, 25, 8, 30, 0)
        with patch("spide.spider.task_scheduler.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            wait = job.next_wait_seconds()
            # 08:30 → 09:00 = 30m = 1800s
            assert 1700 <= wait <= 1800
