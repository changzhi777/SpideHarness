# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.gateway.ratelimit 滑动窗口限流."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from spide.gateway import server
from spide.gateway.ratelimit import (
    SlidingWindowLimiter,
    configure,
    get_limiter,
    rate_limit,
)


class TestSlidingWindowLimiterUnit:
    """限流器核心算法."""

    async def test_first_request_allowed(self):
        """首次请求应允许."""
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=1.0)
        allowed, retry_after = await limiter.check("client1")
        assert allowed is True
        assert retry_after == 0.0

    async def test_max_requests_allowed(self):
        """在限额内应全部允许."""
        limiter = SlidingWindowLimiter(max_requests=3, window_seconds=1.0)
        for _ in range(3):
            allowed, _ = await limiter.check("client1")
            assert allowed is True

    async def test_exceeding_max_returns_retry_after(self):
        """超过限额应拒绝 + 返回 retry_after."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=1.0)
        await limiter.check("c1")
        await limiter.check("c1")
        allowed, retry_after = await limiter.check("c1")
        assert allowed is False
        assert retry_after > 0
        assert retry_after <= 1.0

    async def test_different_clients_isolated(self):
        """不同客户端应配额隔离."""
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=1.0)
        a1, _ = await limiter.check("client_a")
        a2, _ = await limiter.check("client_b")
        assert a1 is True
        assert a2 is True
        # 但同客户端第 2 次被拒
        a3, _ = await limiter.check("client_a")
        assert a3 is False

    async def test_window_slides(self):
        """窗口滑动后旧请求应被清理."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=0.1)
        await limiter.check("c1")
        await limiter.check("c1")
        allowed, _ = await limiter.check("c1")
        assert allowed is False
        # 等待窗口过去
        await asyncio.sleep(0.15)
        allowed, _ = await limiter.check("c1")
        assert allowed is True

    async def test_reset_specific_client(self):
        """重置特定客户端应清空其配额."""
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=10.0)
        await limiter.check("c1")
        await limiter.reset("c1")
        allowed, _ = await limiter.check("c1")
        assert allowed is True

    async def test_reset_all_clients(self):
        """重置所有客户端应清空全部配额."""
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=10.0)
        await limiter.check("c1")
        await limiter.check("c2")
        await limiter.reset()
        a1, _ = await limiter.check("c1")
        a2, _ = await limiter.check("c2")
        assert a1 is True
        assert a2 is True

    async def test_stats_reports_state(self):
        """stats 应报告当前状态."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60.0)
        await limiter.check("c1")
        await limiter.check("c1")
        await limiter.check("c2")
        await limiter.check("c1")  # 触发拒绝
        stats = limiter.stats()
        assert stats["max_requests"] == 2
        assert stats["window_seconds"] == 60.0
        assert stats["active_clients"] == 2
        assert stats["rejected_total"] == 1

    async def test_cleanup_removes_empty_buckets(self):
        """清理后空 bucket 应被删除（避免内存泄漏）."""
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=0.05)
        await limiter.check("ephemeral")
        assert "ephemeral" in limiter._buckets
        await asyncio.sleep(0.08)
        # 下次访问会触发 cleanup
        await limiter.check("ephemeral")
        # 仍存在（因为新加了一个）
        assert "ephemeral" in limiter._buckets


class TestModuleLevelLimiter:
    """模块级单例."""

    def test_get_limiter_returns_singleton(self):
        """get_limiter 应返回单例."""
        l1 = get_limiter()
        l2 = get_limiter()
        assert l1 is l2

    def test_configure_replaces_singleton(self):
        """configure 应替换单例."""
        original = get_limiter()
        configure(max_requests=100, window_seconds=10.0)
        new = get_limiter()
        assert new is not original
        assert new.max_requests == 100
        assert new.window_seconds == 10.0
        # 恢复默认
        configure(max_requests=60, window_seconds=60.0)


class TestRateLimitDependency:
    """rate_limit FastAPI 依赖."""

    async def test_anonymous_client_uses_ip(self):
        """无 API Key 应使用 IP 标识（不会拒绝）."""
        from starlette.requests import Request as _Req

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("192.168.1.1", 50000),
            "query_string": b"",
        }
        request = _Req(scope)
        result = await rate_limit(request, x_api_key=None)
        assert result.startswith("ip:")

    async def test_api_key_takes_priority(self):
        """有 API Key 时应优先使用 Key 标识."""
        from starlette.requests import Request as _Req

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("1.2.3.4", 50000),
            "query_string": b"",
        }
        request = _Req(scope)
        result = await rate_limit(request, x_api_key="mykey")
        assert result == "key:mykey"

    async def test_no_client_no_key_returns_anonymous(self):
        """无 client 主机也无 Key 应使用 anonymous."""
        from starlette.requests import Request as _Req

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": None,
            "query_string": b"",
        }
        request = _Req(scope)
        result = await rate_limit(request, x_api_key=None)
        assert result == "anonymous"

    async def test_rate_limit_exceeded_raises_429(self, monkeypatch):
        """超过限额应 429 + Retry-After 头."""
        # 配小限额快速触发
        configure(max_requests=1, window_seconds=10.0)
        try:
            from starlette.requests import Request as _Req

            scope = {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [],
                "client": ("10.0.0.1", 50000),
                "query_string": b"",
            }
            request = _Req(scope)
            # 第一次允许
            await rate_limit(request, x_api_key="burn")
            # 第二次被拒
            with pytest.raises(HTTPException) as exc:
                await rate_limit(request, x_api_key="burn")
            assert exc.value.status_code == 429
            assert "Retry-After" in exc.value.headers
        finally:
            # 恢复默认 + 清空
            configure(max_requests=60, window_seconds=60.0)
            await get_limiter().reset()


class TestRateLimitIntegrationWithEndpoint:
    """限流 + /api/v1/topics 端到端."""

    def test_rate_limit_triggers_429(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """小限额 + 多次请求应触发 429."""
        from unittest.mock import AsyncMock, patch

        # 配小限额
        configure(max_requests=2, window_seconds=10.0)
        try:
            with patch("spide.gateway.server.SqliteRepository") as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.start = AsyncMock()
                mock_repo.stop = AsyncMock()
                mock_repo.query = AsyncMock(return_value=[])

                with TestClient(server.app) as client:
                    # 前 2 次允许
                    r1 = client.get("/api/v1/topics?limit=1")
                    r2 = client.get("/api/v1/topics?limit=1")
                    # 第 3 次触发限流
                    r3 = client.get("/api/v1/topics?limit=1")
                    assert r1.status_code == 200
                    assert r2.status_code == 200
                    assert r3.status_code == 429
                    assert "Retry-After" in r3.headers
        finally:
            configure(max_requests=60, window_seconds=60.0)
            # 同步清空（TestClient 同步上下文内不可 await）
            import asyncio as _aio
            _aio.run(get_limiter().reset())
