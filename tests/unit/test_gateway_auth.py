# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.gateway.auth API Key 鉴权."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from spide.gateway import server
from spide.gateway.auth import is_auth_enabled, load_valid_keys, require_api_key


class TestLoadValidKeys:
    """环境变量加载."""

    def test_no_env_returns_empty(self, monkeypatch: pytest.MonkeyPatch):
        """未设置环境变量应返回空集合（禁用鉴权）."""
        monkeypatch.delenv("SPIDE_GATEWAY_API_KEYS", raising=False)
        assert load_valid_keys() == set()

    def test_single_key(self, monkeypatch: pytest.MonkeyPatch):
        """单个 Key 应正确加载."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "key1")
        assert load_valid_keys() == {"key1"}

    def test_multiple_keys(self, monkeypatch: pytest.MonkeyPatch):
        """多个 Key（逗号分隔）应全部加载."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "key1, key2 ,key3")
        assert load_valid_keys() == {"key1", "key2", "key3"}

    def test_empty_string_returns_empty(self, monkeypatch: pytest.MonkeyPatch):
        """空字符串应视为未配置."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "")
        assert load_valid_keys() == set()

    def test_whitespace_only(self, monkeypatch: pytest.MonkeyPatch):
        """纯空白应忽略（无有效 Key）."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "  ,  ,  ")
        assert load_valid_keys() == set()


class TestRequireApiKey:
    """require_api_key 依赖函数."""

    async def test_no_keys_configured_passes_through(self, monkeypatch: pytest.MonkeyPatch):
        """未配置 Key 时应直接放行（开发模式）."""
        monkeypatch.delenv("SPIDE_GATEWAY_API_KEYS", raising=False)
        result = await require_api_key(x_api_key=None)
        assert result == "anonymous"

    async def test_valid_key_passes(self, monkeypatch: pytest.MonkeyPatch):
        """有效 Key 应通过."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret123")
        result = await require_api_key(x_api_key="secret123")
        assert result == "secret123"

    async def test_missing_key_raises_401(self, monkeypatch: pytest.MonkeyPatch):
        """配置了 Key 但请求头缺失应 401."""
        from fastapi import HTTPException

        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret123")
        with pytest.raises(HTTPException) as exc:
            await require_api_key(x_api_key=None)
        assert exc.value.status_code == 401
        assert exc.value.headers.get("WWW-Authenticate") == "ApiKey"

    async def test_invalid_key_raises_401(self, monkeypatch: pytest.MonkeyPatch):
        """错误 Key 应 401."""
        from fastapi import HTTPException

        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret123")
        with pytest.raises(HTTPException) as exc:
            await require_api_key(x_api_key="wrong_key")
        assert exc.value.status_code == 401


class TestIsAuthEnabled:
    """is_auth_enabled 辅助函数."""

    def test_disabled_when_no_env(self, monkeypatch: pytest.MonkeyPatch):
        """未配置环境变量应禁用."""
        monkeypatch.delenv("SPIDE_GATEWAY_API_KEYS", raising=False)
        assert is_auth_enabled() is False

    def test_enabled_when_keys_set(self, monkeypatch: pytest.MonkeyPatch):
        """配置 Key 应启用."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "any_key")
        assert is_auth_enabled() is True


class TestAuthIntegrationWithTopicsEndpoint:
    """鉴权 + /api/v1/topics 端到端."""

    def test_topics_anonymous_when_auth_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """禁用鉴权时，/api/v1/topics 不需要 Key."""
        monkeypatch.delenv("SPIDE_GATEWAY_API_KEYS", raising=False)
        with patch("spide.gateway.server.SqliteRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.start = AsyncMock_()
            mock_repo.stop = AsyncMock_()
            mock_repo.query = AsyncMock_(return_value=[])

            with TestClient(server.app) as client:
                resp = client.get("/api/v1/topics?limit=1")
                assert resp.status_code == 200

    def test_topics_requires_key_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """启用鉴权时，无 Key 应 401."""

        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret")
        with TestClient(server.app) as client:
            resp = client.get("/api/v1/topics?limit=1")
            assert resp.status_code == 401
            assert resp.headers.get("www-authenticate") == "ApiKey"

    def test_topics_with_valid_key_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """启用鉴权时，携带有效 Key 应 200."""
        from unittest.mock import AsyncMock

        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret")
        with patch("spide.gateway.server.SqliteRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.start = AsyncMock()
            mock_repo.stop = AsyncMock()
            mock_repo.query = AsyncMock(return_value=[])

            with TestClient(server.app) as client:
                resp = client.get(
                    "/api/v1/topics?limit=1",
                    headers={"X-API-Key": "secret"},
                )
                assert resp.status_code == 200

    def test_topics_with_invalid_key_returns_401(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """启用鉴权时，错误 Key 应 401."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret")
        with TestClient(server.app) as client:
            resp = client.get(
                "/api/v1/topics?limit=1",
                headers={"X-API-Key": "wrong"},
            )
            assert resp.status_code == 401

    def test_health_endpoint_never_requires_auth(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """/health 应始终公开（鉴权启用也无需 Key）."""
        monkeypatch.setenv("SPIDE_GATEWAY_API_KEYS", "secret")
        with TestClient(server.app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["auth_enabled"] is True


def _async_mock(return_value=None):
    """Helper to create AsyncMock with return_value."""
    from unittest.mock import AsyncMock

    return AsyncMock(return_value=return_value)


AsyncMock_ = _async_mock  # backward compat alias
