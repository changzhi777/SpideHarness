# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.integrations.thoth_client Thoth 知识库客户端."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from spide.config import ThothConfig
from spide.exceptions import (
    ThothAuthError,
    ThothError,
    ThothNotFoundError,
    ThothServerError,
)
from spide.integrations.thoth_client import ThothClient


def _make_response(
    status: int, json_data: dict | None = None, reason: str = "OK"
) -> MagicMock:
    """构造 aiohttp 响应 mock（已经是 async context manager 形式）.

    用法: `async with session.get(...) as resp` — resp 本身就是 CM。
    这是 aiohttp Response 对象的正确 mock 方式。
    """
    resp = MagicMock()
    resp.status = status
    resp.reason = reason
    resp.content_length = len(str(json_data)) if json_data else 0

    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)
    else:
        resp.json = AsyncMock(side_effect=Exception("no body"))

    # 让 resp 同时是 async context manager（__aenter__/__aexit__ 已在 MagicMock 中）
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)

    return resp


class TestThothClientInit:
    """ThothClient 初始化."""

    def test_default_config(self) -> None:
        """默认配置应指向 10.10.10.15:8765."""
        client = ThothClient(ThothConfig())
        assert client._config.base_url == "http://10.10.10.15:8765"
        assert client._config.token == ""
        assert client._config.default_room_id == "room_video_2026"
        assert client._config.timeout == 30.0

    def test_custom_config(self) -> None:
        """自定义配置应正确传递."""
        cfg = ThothConfig(
            base_url="http://custom:9000",
            token="my-token",
            default_room_id="custom_room",
            timeout=60.0,
        )
        client = ThothClient(cfg)
        assert client._config.token == "my-token"
        assert client._config.default_room_id == "custom_room"

    def test_session_lazy_init(self) -> None:
        """session 应延迟初始化（构造时为 None）."""
        client = ThothClient(ThothConfig())
        assert client._session is None

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self) -> None:
        """start() 重复调用应幂等（不抛异常）."""
        client = ThothClient(ThothConfig())
        await client.start()
        first_session = client._session
        await client.start()  # 再次调用
        assert client._session is first_session  # 同一实例
        await client.stop()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self) -> None:
        """stop() 重复调用应幂等（不抛异常）."""
        client = ThothClient(ThothConfig())
        await client.start()
        await client.stop()
        await client.stop()  # 重复调用应安全
        assert client._session is None


class TestThothClientHeaders:
    """请求头构造."""

    def test_headers_with_token(self) -> None:
        """配置 token 时应包含 Authorization Bearer."""
        client = ThothClient(ThothConfig(token="abc123"))
        h = client._headers()
        assert h["Authorization"] == "Bearer abc123"
        assert h["Content-Type"] == "application/json"

    def test_headers_without_token(self) -> None:
        """无 token 时不应包含 Authorization 头."""
        client = ThothClient(ThothConfig(token=""))
        h = client._headers()
        assert "Authorization" not in h


class TestHealthCheck:
    """/api/status 健康检查."""

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """服务返回 200 → health_check=True."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_ensure_session") as mock_ensure:
            mock_session = MagicMock()
            mock_resp = _make_response(200, {"status": "ok"})
            # session.get(url) 返回 CM（已经是 CM 形式）
            mock_session.get.return_value = mock_resp
            mock_ensure.return_value = mock_session
            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure_returns_false(self) -> None:
        """服务不可达 → health_check=False（不抛异常）."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_ensure_session") as mock_ensure:
            mock_ensure.side_effect = aiohttp.ClientError("connection refused")
            assert await client.health_check() is False


class TestCreateNote:
    """POST /api/notes."""

    @pytest.mark.asyncio
    async def test_create_note_success(self) -> None:
        """成功创建 note 返回完整 dict."""
        client = ThothClient(ThothConfig(token="t"))
        mock_resp = _make_response(
            201,
            {
                "id": "note_123",
                "title": "GPT-5",
                "content": "正文",
                "tags": "AI",
                "room_id": "room_video_2026",
                "created_at": "2026-06-14T10:00:00",
                "updated_at": "2026-06-14T10:00:00",
            },
        )
        with patch.object(client, "_request", return_value=mock_resp.json.return_value):
            result = await client.create_note(
                title="GPT-5",
                content="正文",
                tags="AI",
                room_id="room_video_2026",
            )
        assert result["id"] == "note_123"
        assert result["title"] == "GPT-5"

    @pytest.mark.asyncio
    async def test_create_note_uses_default_room(self) -> None:
        """未指定 room_id 时使用配置默认值."""
        client = ThothClient(ThothConfig(token="t", default_room_id="my_room"))
        with patch.object(client, "_request") as mock_req:
            mock_req.return_value = {"id": "n1"}
            await client.create_note(title="T", content="C")
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["json"]["room_id"] == "my_room"

    @pytest.mark.asyncio
    async def test_create_note_auth_error(self) -> None:
        """401 → ThothAuthError."""
        client = ThothClient(ThothConfig(token="bad"))
        with patch.object(
            client, "_request", side_effect=ThothAuthError("无效", status_code=401)
        ), pytest.raises(ThothAuthError):
            await client.create_note(title="T", content="C")


class TestGetNote:
    """GET /api/notes/{id}."""

    @pytest.mark.asyncio
    async def test_get_note_success(self) -> None:
        """成功获取 note."""
        client = ThothClient(ThothConfig())
        with patch.object(
            client, "_request", return_value={"id": "n1", "title": "T"}
        ) as mock_req:
            result = await client.get_note("n1")
        assert result["id"] == "n1"
        mock_req.assert_called_once_with("GET", "/api/notes/n1")

    @pytest.mark.asyncio
    async def test_get_note_not_found(self) -> None:
        """404 → ThothNotFoundError."""
        client = ThothClient(ThothConfig())
        with patch.object(
            client, "_request", side_effect=ThothNotFoundError("not found", status_code=404)
        ), pytest.raises(ThothNotFoundError):
            await client.get_note("missing")


class TestSearchNotes:
    """POST /api/notes/search."""

    @pytest.mark.asyncio
    async def test_search_returns_list(self) -> None:
        """搜索返回 list."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_request", return_value=[{"id": "n1"}]):
            result = await client.search_notes("GPT-5")
        assert result == [{"id": "n1"}]

    @pytest.mark.asyncio
    async def test_search_with_items_envelope(self) -> None:
        """容错：返回 dict 含 items 字段时提取 items."""
        client = ThothClient(ThothConfig())
        with patch.object(
            client, "_request", return_value={"items": [{"id": "n1"}]}
        ):
            result = await client.search_notes("GPT")
        assert result == [{"id": "n1"}]

    @pytest.mark.asyncio
    async def test_search_with_room_id(self) -> None:
        """传 room_id 应包含在请求体."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_request", return_value=[]) as mock_req:
            await client.search_notes("GPT", room_id="r1")
            assert mock_req.call_args.kwargs["json"]["room_id"] == "r1"


class TestUpdateNote:
    """PUT /api/notes/{id}."""

    @pytest.mark.asyncio
    async def test_update_note_passes_fields(self) -> None:
        """update 应透传 fields."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_request", return_value={"id": "n1"}) as mock_req:
            await client.update_note("n1", title="New", content="C", is_pinned=True)
            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["json"]["title"] == "New"
            assert call_kwargs["json"]["is_pinned"] is True


class TestDeleteNote:
    """DELETE /api/notes/{id}."""

    @pytest.mark.asyncio
    async def test_delete_note_success(self) -> None:
        """成功删除无返回."""
        client = ThothClient(ThothConfig())
        with patch.object(client, "_request", return_value={}):
            await client.delete_note("n1")  # 不抛


class TestRequestRetry:
    """_request 重试逻辑."""

    @pytest.mark.asyncio
    async def test_network_error_retries_3_times(self) -> None:
        """网络错误应重试 3 次."""
        client = ThothClient(ThothConfig())
        with (
            patch.object(client, "_ensure_session") as mock_ensure,
            # 跳过真实 sleep（避免 0.5+1+2=3.5s 等待）
            patch("spide.integrations.thoth_client.asyncio.sleep", new=AsyncMock()),
        ):
            mock_session = MagicMock()
            mock_session.request.side_effect = aiohttp.ClientError("net error")
            mock_ensure.return_value = mock_session
            with pytest.raises(ThothError):
                await client._request("GET", "/api/test")
            assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_5xx_retries_then_raises(self) -> None:
        """5xx 错误应重试 + 最终抛 ThothServerError."""
        client = ThothClient(ThothConfig())
        with (
            patch.object(client, "_ensure_session") as mock_ensure,
            # 跳过真实 sleep（避免 0.5+1+2=3.5s 等待）
            patch("spide.integrations.thoth_client.asyncio.sleep", new=AsyncMock()),
        ):
            mock_resp = _make_response(500, reason="Internal Server Error")
            mock_session = MagicMock()
            mock_session.request.return_value = mock_resp
            mock_ensure.return_value = mock_session
            with pytest.raises(ThothServerError) as exc_info:
                await client._request("GET", "/api/test")
            assert exc_info.value.status_code == 500
            assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        """4xx 业务错误不应重试."""
        client = ThothClient(ThothConfig())
        with patch.object(
            client, "_ensure_session"
        ) as mock_ensure:
            mock_resp = _make_response(401, {"detail": "token 失效"}, "Unauthorized")
            mock_session = MagicMock()
            mock_session.request.return_value = mock_resp
            mock_ensure.return_value = mock_session
            with pytest.raises(ThothAuthError):
                await client._request("GET", "/api/notes")
            # 仅 1 次调用（不重试）
            assert mock_session.request.call_count == 1


class TestExceptions:
    """异常体系."""

    def test_thoth_error_inherits_spide(self) -> None:
        """ThothError 应继承 SpideError."""
        assert issubclass(ThothError, Exception)
        e = ThothError("msg", status_code=500)
        assert e.status_code == 500
        assert e.detail == ""

    def test_thoth_auth_error_inherits(self) -> None:
        """ThothAuthError 应继承 ThothError."""
        assert issubclass(ThothAuthError, ThothError)

    def test_thoth_not_found_inherits(self) -> None:
        """ThothNotFoundError 应继承 ThothError."""
        assert issubclass(ThothNotFoundError, ThothError)

    def test_thoth_server_error_inherits(self) -> None:
        """ThothServerError 应继承 ThothError."""
        assert issubclass(ThothServerError, ThothError)

    def test_thoth_error_with_detail(self) -> None:
        """detail 参数应被 SpideError 接受."""
        e = ThothError("msg", status_code=400, detail="extra info")
        assert e.detail == "extra info"
        assert e.status_code == 400
