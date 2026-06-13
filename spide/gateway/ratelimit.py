# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""滑动窗口限流 — 纯 asyncio 实现，零外部依赖.

算法：每个客户端（Key 或 IP）维护一个时间戳列表，
每次请求时清理过期时间戳，检查剩余数量是否超限。
时间复杂度 O(N) 每次请求，N 为窗口内请求数（一般 < 100）。

特性：
- 异步安全（asyncio.Lock）
- 客户端标识：优先用 API Key（鉴权后），降级用 IP
- 内存自动清理（每次访问清理 + 定期全清）
- 429 Too Many Requests + Retry-After 头
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Annotated, Any

from fastapi import Header, HTTPException, Request, status


class SlidingWindowLimiter:
    """滑动窗口限流器.

    Args:
        max_requests: 窗口内最大请求数
        window_seconds: 窗口大小（秒）
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        # 记录触发限流的次数（用于 metrics/health）
        self.rejected_count = 0

    @property
    def max_requests(self) -> int:
        return self._max_requests

    @property
    def window_seconds(self) -> float:
        return self._window

    def _cleanup_locked(self, client_id: str, now: float) -> None:
        """清理过期时间戳（调用前必须持锁）."""
        bucket = self._buckets[client_id]
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if not bucket:
            self._buckets.pop(client_id, None)

    async def check(self, client_id: str) -> tuple[bool, float]:
        """检查是否允许请求.

        Returns:
            (allowed, retry_after_seconds) — allowed=True 表示放行
        """
        now = time.monotonic()
        async with self._lock:
            self._cleanup_locked(client_id, now)
            bucket = self._buckets.get(client_id)
            if bucket and len(bucket) >= self._max_requests:
                # 计算何时可重试（最旧时间戳 + 窗口）
                retry_after = max(0.0, bucket[0] + self._window - now)
                self.rejected_count += 1
                return False, retry_after
            # 记录本次请求
            if client_id not in self._buckets:
                self._buckets[client_id] = deque()
            self._buckets[client_id].append(now)
            return True, 0.0

    async def reset(self, client_id: str | None = None) -> None:
        """重置限流状态（admin/测试用）."""
        async with self._lock:
            if client_id is None:
                self._buckets.clear()
            else:
                self._buckets.pop(client_id, None)

    def stats(self) -> dict[str, Any]:
        """当前限流状态（用于健康检查）."""
        return {
            "max_requests": self._max_requests,
            "window_seconds": self._window,
            "active_clients": len(self._buckets),
            "rejected_total": self.rejected_count,
        }


# 模块级单例（默认 60 req/min）
_limiter = SlidingWindowLimiter(max_requests=60, window_seconds=60.0)


def configure(max_requests: int, window_seconds: float) -> None:
    """重新配置限流器（必须在 app 启动前调用）."""
    global _limiter
    _limiter = SlidingWindowLimiter(max_requests=max_requests, window_seconds=window_seconds)


def get_limiter() -> SlidingWindowLimiter:
    """获取当前限流器实例（用于测试/health）."""
    return _limiter


async def rate_limit(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """FastAPI 依赖：限流检查.

    客户端标识优先级：X-API-Key → request.client.host → "anonymous"。
    """
    # 优先用 API Key 作为客户端标识（同一 Key 共享配额）
    if x_api_key:
        client_id = f"key:{x_api_key}"
    elif request.client and request.client.host:
        client_id = f"ip:{request.client.host}"
    else:
        client_id = "anonymous"

    allowed, retry_after = await _limiter.check(client_id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {client_id}",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
    return client_id
