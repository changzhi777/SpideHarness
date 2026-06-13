# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.gateway 独立 HTTP/WS 网关."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from spide.gateway import server
from spide.gateway.server import (
    ConnectionManager,
    app,
    health,
)


class TestHealthEndpoint:
    """GET /health 健康检查."""

    def test_health_returns_ok(self):
        """健康端点应返回 status=ok + uptime > 0."""
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["version"] == "3.1.2"
            assert data["uptime_seconds"] > 0

    async def test_health_function_directly(self):
        """直接调用 health() 函数."""
        result = await health()
        assert result.status == "ok"
        assert result.uptime_seconds >= 0


class TestTopicsEndpoint:
    """GET /api/v1/topics 热搜查询."""

    def test_topics_empty_db(self, tmp_path, monkeypatch):
        """空数据库应返回 count=0."""
        monkeypatch.setattr(server, "SqliteRepository", None)  # 占位
        # 真实路径：让 server 用临时 db
        with patch("spide.gateway.server.SqliteRepository") as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.start = AsyncMock()
            mock_repo.stop = AsyncMock()
            mock_repo.query = AsyncMock(return_value=[])
            MockRepo.return_value = mock_repo
            with TestClient(app) as client:
                resp = client.get("/api/v1/topics?limit=10")
                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 0
                assert data["items"] == []

    def test_topics_with_data(self):
        """带数据时应正确序列化."""
        mock_topic = MagicMock()
        mock_topic.title = "AI 大模型突破"
        mock_topic.source = MagicMock(value="weibo")
        mock_topic.hot_value = 50000
        mock_topic.rank = 1
        mock_topic.url = "https://example.com/1"

        with patch("spide.gateway.server.SqliteRepository") as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.start = AsyncMock()
            mock_repo.stop = AsyncMock()
            mock_repo.query = AsyncMock(return_value=[mock_topic])
            MockRepo.return_value = mock_repo
            with TestClient(app) as client:
                resp = client.get("/api/v1/topics?source=weibo&limit=5")
                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 1
                assert data["items"][0]["title"] == "AI 大模型突破"
                assert data["items"][0]["source"] == "weibo"
                assert data["items"][0]["hot_value"] == 50000
                # 验证 source 参数被传入
                mock_repo.query.assert_called_once_with(source="weibo", limit=5)

    def test_topics_invalid_limit(self):
        """limit 超出范围应返回 422."""
        with TestClient(app) as client:
            resp = client.get("/api/v1/topics?limit=200")  # > 100
            assert resp.status_code == 422


class TestConnectionManager:
    """WebSocket 连接管理器."""

    async def test_connect_disconnect(self):
        """连接/断开应正确维护计数."""
        mgr = ConnectionManager()
        assert mgr.count == 0

        ws = AsyncMock()
        await mgr.connect(ws)
        assert mgr.count == 1

        await mgr.disconnect(ws)
        assert mgr.count == 0

    async def test_broadcast_empty(self):
        """无连接时 broadcast 应直接返回."""
        mgr = ConnectionManager()
        # 不应抛异常
        await mgr.broadcast({"type": "test"})

    async def test_broadcast_sends_to_all(self):
        """broadcast 应向所有连接发送."""
        mgr = ConnectionManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        await mgr.connect(ws1)
        await mgr.connect(ws2)

        payload = {"type": "heartbeat", "ts": 123.45}
        await mgr.broadcast(payload)
        ws1.send_json.assert_awaited_once_with(payload)
        ws2.send_json.assert_awaited_once_with(payload)

    async def test_broadcast_cleans_dead_connections(self):
        """广播失败时死连接应自动清理."""
        mgr = ConnectionManager()
        alive = AsyncMock()
        dead = AsyncMock()
        dead.send_json.side_effect = RuntimeError("connection closed")
        await mgr.connect(alive)
        await mgr.connect(dead)

        await mgr.broadcast({"type": "x"})

        assert mgr.count == 1
        assert dead not in mgr._connections


class TestWebSocketEndpoint:
    """WS /ws/events 端到端."""

    def test_ws_echo(self):
        """WS 接收消息应回显 + heartbeat 行为."""
        with TestClient(app) as client, client.websocket_connect("/ws/events") as ws:
            ws.send_text("hello")
            data = ws.receive_json()
            assert data["type"] == "echo"
            assert data["received"] == "hello"
            assert "ts" in data


class TestAppMetadata:
    """App 元数据."""

    def test_app_metadata(self):
        """App 应有正确的 title/version."""
        assert app.title == "SpideHarness Gateway"
        assert app.version == "3.1.2"

    def test_app_routes(self):
        """App 应注册 3 个核心端点."""
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        # 移除 FastAPI 默认 docs 端点
        core_paths = {"/health", "/api/v1/topics", "/ws/events"}
        assert core_paths.issubset(paths), f"缺失端点: {core_paths - paths}"


class TestGlobalExceptionHandler:
    """全局异常处理."""

    def test_exception_handler_is_registered(self):
        """全局 Exception 处理器应已注册到 app."""
        from spide.gateway.server import global_exception_handler

        # 验证 handler 已注册
        assert Exception in app.exception_handlers
        assert app.exception_handlers[Exception] is global_exception_handler

    async def test_exception_handler_returns_500_json(self):
        """调用 handler 应返回结构化 500 JSON."""
        from spide.gateway.server import global_exception_handler

        resp = await global_exception_handler(None, ValueError("intentional test"))
        assert resp.status_code == 500
        import json as _json

        body = _json.loads(resp.body)
        assert body["status"] == "error"
        assert "intentional test" in body["error"]
