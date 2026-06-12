# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""限流、熔断与断点恢复 — 采集稳定性保障.

用法:
    from spide.spider.rate_limiter import RateLimiter, CircuitBreaker, CheckpointManager

    # 令牌桶限流
    limiter = RateLimiter(max_rpm=30, max_concurrent=5)
    async with limiter:
        await fetch(url)

    # 熔断保护
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
    result = await breaker.call(api_fetch, source="weibo")

    # 断点恢复
    ckpt = CheckpointManager(db_path="spide_data.db")
    await ckpt.start()
    state = await ckpt.load_checkpoint("batch_20260521_1200")
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import aiosqlite

from spide.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# RateLimiter — 令牌桶 + 并发控制
# ---------------------------------------------------------------------------


class RateLimiter:
    """令牌桶限流器 + 并发信号量.

    双重控制：
    - 信号量控制并发连接数
    - 令牌桶控制每分钟请求数
    """

    def __init__(
        self,
        *,
        max_rpm: int = 30,
        max_concurrent: int = 5,
    ) -> None:
        self._max_rpm = max_rpm
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tokens: float = max_rpm
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取一个令牌（等待直到可用）."""
        await self._semaphore.acquire()
        await self._wait_for_token()

    def release(self) -> None:
        """释放并发信号量."""
        self._semaphore.release()

    async def _wait_for_token(self) -> None:
        """等待令牌可用."""
        async with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

        # 无令牌可用，计算等待时间
        wait_seconds = (1.0 - self._tokens) * (60.0 / self._max_rpm)
        logger.debug("rate_limiter_wait", wait_seconds=round(wait_seconds, 2))
        await asyncio.sleep(wait_seconds)

        async with self._lock:
            self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        """按时间补充令牌."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        refill = elapsed * (self._max_rpm / 60.0)
        self._tokens = min(self._max_rpm, self._tokens + refill)
        self._last_refill = now

    async def __aenter__(self) -> RateLimiter:
        await self.acquire()
        return self

    async def __aexit__(self, *_: Any) -> None:
        self.release()


# ---------------------------------------------------------------------------
# CircuitBreaker — 熔断器
# ---------------------------------------------------------------------------


class _BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """熔断器 — 连续失败达到阈值后熔断，超时后半开试探.

    状态机: CLOSED → OPEN → HALF_OPEN → CLOSED
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._name = name
        self._state = _BreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def is_open(self) -> bool:
        if self._state == _BreakerState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = _BreakerState.HALF_OPEN
                logger.debug("circuit_breaker_half_open", name=self._name)
                return False
            return True
        return False

    async def call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """通过熔断器执行异步函数.

        Args:
            fn: 异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器打开时
        """
        if self.is_open:
            raise CircuitBreakerOpenError(
                f"熔断器 [{self._name}] 已打开，请等待 {self._recovery_timeout}s 后重试"
            )

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self._failure_count = 0
        if self._state == _BreakerState.HALF_OPEN:
            self._state = _BreakerState.CLOSED
            logger.info(
                "circuit_breaker_closed", name=self._name, success_count=self._success_count
            )
        self._success_count += 1

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == _BreakerState.HALF_OPEN:
            self._state = _BreakerState.OPEN
            logger.warning("circuit_breaker_reopened", name=self._name)
            return

        if self._failure_count >= self._failure_threshold:
            self._state = _BreakerState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                name=self._name,
                failures=self._failure_count,
                threshold=self._failure_threshold,
            )

    def reset(self) -> None:
        """手动重置熔断器."""
        self._state = _BreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        logger.debug("circuit_breaker_reset", name=self._name)


class CircuitBreakerOpenError(Exception):
    """熔断器打开异常."""


# ---------------------------------------------------------------------------
# CheckpointManager — 断点恢复
# ---------------------------------------------------------------------------


@dataclass
class Checkpoint:
    """断点记录."""

    task_id: str
    state: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class CheckpointManager:
    """断点管理器 — 基于 SQLite 的采集进度持久化.

    用于长时间批量采集中断后恢复进度。
    """

    def __init__(self, *, db_path: str = "spide_data.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def start(self) -> None:
        """初始化数据库连接和表."""
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            "task_id TEXT PRIMARY KEY, "
            "state TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        await self._db.commit()

    async def stop(self) -> None:
        """关闭数据库连接."""
        if self._db:
            await self._db.close()
            self._db = None

    async def save_checkpoint(self, task_id: str, state: dict[str, Any]) -> None:
        """保存或更新断点."""
        if self._db is None:
            return

        now = datetime.now().isoformat()
        state_json = json.dumps(state, ensure_ascii=False)

        await self._db.execute(
            "INSERT INTO checkpoints (task_id, state, created_at, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(task_id) DO UPDATE SET state=?, updated_at=?",
            (task_id, state_json, now, now, state_json, now),
        )
        await self._db.commit()
        logger.debug("checkpoint_saved", task_id=task_id)

    async def load_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """加载断点."""
        if self._db is None:
            return None

        cursor = await self._db.execute(
            "SELECT state FROM checkpoints WHERE task_id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    async def list_checkpoints(self) -> list[dict[str, Any]]:
        """列出所有断点."""
        if self._db is None:
            return []

        cursor = await self._db.execute(
            "SELECT task_id, state, created_at, updated_at FROM checkpoints ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "task_id": row[0],
                    "created_at": row[2],
                    "updated_at": row[3],
                    **json.loads(row[1]),
                }
            )
        return results

    async def delete_checkpoint(self, task_id: str) -> bool:
        """删除断点."""
        if self._db is None:
            return False

        cursor = await self._db.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
        await self._db.commit()
        return cursor.rowcount > 0
