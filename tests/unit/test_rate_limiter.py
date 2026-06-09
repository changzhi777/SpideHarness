# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 限流器 + 熔断器 + 断点恢复."""

import asyncio

import pytest

from spide.spider.rate_limiter import (
    CheckpointManager,
    CircuitBreaker,
    CircuitBreakerOpenError,
    RateLimiter,
)


class TestRateLimiter:
    """RateLimiter 令牌桶测试."""

    async def test_acquire_release(self):
        limiter = RateLimiter(max_rpm=60, max_concurrent=2)
        await limiter.acquire()
        limiter.release()

    async def test_concurrent_limit(self):
        limiter = RateLimiter(max_rpm=100, max_concurrent=1)
        order: list[int] = []

        async def worker(n: int) -> None:
            await limiter.acquire()
            order.append(n)
            await asyncio.sleep(0.05)
            limiter.release()

        await asyncio.gather(*[worker(i) for i in range(3)])
        assert len(order) == 3

    async def test_context_manager(self):
        limiter = RateLimiter(max_rpm=60, max_concurrent=2)
        async with limiter:
            pass


class TestCircuitBreaker:
    """CircuitBreaker 熔断器测试."""

    async def test_closed_state(self):
        breaker = CircuitBreaker(failure_threshold=3, name="test")
        assert breaker.state == "closed"

    async def test_success_stays_closed(self):
        breaker = CircuitBreaker(failure_threshold=3, name="test")

        async def ok_fn():
            return "ok"

        result = await breaker.call(ok_fn)
        assert result == "ok"
        assert breaker.state == "closed"

    async def test_opens_after_failures(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1, name="test")

        async def fail_fn():
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(fail_fn)

        assert breaker.state == "open"

    async def test_open_rejects_calls(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=300, name="test")

        async def fail_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await breaker.call(fail_fn)

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(fail_fn)

    async def test_half_open_after_timeout(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05, name="test")

        async def fail_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await breaker.call(fail_fn)

        await asyncio.sleep(0.1)

        async def ok_fn():
            return "recovered"

        result = await breaker.call(ok_fn)
        assert result == "recovered"
        assert breaker.state == "closed"

    async def test_reset(self):
        breaker = CircuitBreaker(failure_threshold=1, name="test")

        async def fail_fn():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await breaker.call(fail_fn)

        assert breaker.state == "open"
        breaker.reset()
        assert breaker.state == "closed"


class TestCheckpointManager:
    """CheckpointManager 断点恢复测试."""

    async def test_save_and_load(self, tmp_path):
        db_path = str(tmp_path / "ckpt.db")
        mgr = CheckpointManager(db_path=db_path)
        await mgr.start()
        try:
            state = {"completed_platforms": ["weibo"], "pending_platforms": ["zhihu"]}
            await mgr.save_checkpoint("test_task", state)

            loaded = await mgr.load_checkpoint("test_task")
            assert loaded is not None
            assert loaded["completed_platforms"] == ["weibo"]
        finally:
            await mgr.stop()

    async def test_load_nonexistent(self, tmp_path):
        db_path = str(tmp_path / "ckpt.db")
        mgr = CheckpointManager(db_path=db_path)
        await mgr.start()
        try:
            result = await mgr.load_checkpoint("no_such_task")
            assert result is None
        finally:
            await mgr.stop()

    async def test_list_checkpoints(self, tmp_path):
        db_path = str(tmp_path / "ckpt.db")
        mgr = CheckpointManager(db_path=db_path)
        await mgr.start()
        try:
            await mgr.save_checkpoint("task_1", {"a": 1})
            await mgr.save_checkpoint("task_2", {"b": 2})

            checkpoints = await mgr.list_checkpoints()
            assert len(checkpoints) == 2
        finally:
            await mgr.stop()

    async def test_delete_checkpoint(self, tmp_path):
        db_path = str(tmp_path / "ckpt.db")
        mgr = CheckpointManager(db_path=db_path)
        await mgr.start()
        try:
            await mgr.save_checkpoint("task_del", {"x": 1})
            assert await mgr.delete_checkpoint("task_del") is True
            assert await mgr.load_checkpoint("task_del") is None
        finally:
            await mgr.stop()

    async def test_overwrite_checkpoint(self, tmp_path):
        db_path = str(tmp_path / "ckpt.db")
        mgr = CheckpointManager(db_path=db_path)
        await mgr.start()
        try:
            await mgr.save_checkpoint("task_ov", {"v": 1})
            await mgr.save_checkpoint("task_ov", {"v": 2})

            loaded = await mgr.load_checkpoint("task_ov")
            assert loaded["v"] == 2
        finally:
            await mgr.stop()
