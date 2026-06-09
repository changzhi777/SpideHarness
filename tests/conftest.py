# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""测试基础设施."""

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 通用 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_aiohttp_response():
    """构建 aiohttp ClientSession.get mock（共享 helper）.

    用法:
        def test_xxx(self, mock_aiohttp_response):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"data": 1})
            with patch("aiohttp.ClientSession.get", new=mock_aiohttp_response(mock_resp)):
                ...
    """
    from unittest.mock import AsyncMock, MagicMock

    def _factory(resp):
        get_cm = MagicMock()
        get_cm.__aenter__ = AsyncMock(return_value=resp)
        get_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get.return_value = get_cm
        return session.get

    return _factory


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """临时 SQLite 数据库路径."""
    return tmp_path / "test.db"


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch) -> Path:
    """临时工作空间（已初始化）."""
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    from spide.workspace import initialize_workspace

    initialize_workspace(str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# pytest markers 注册（在 pyproject.toml 中声明）
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 真实 API 测试 fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_settings():
    """加载真实配置（从 configs/ 目录）."""
    from spide.config import load_settings

    return load_settings()


@pytest.fixture
def skip_if_no_uapi(real_settings):
    """无 UAPI API Key 时跳过测试."""
    if not real_settings.uapi.api_key:
        pytest.skip("UAPI API Key 未配置")


@pytest.fixture
def skip_if_no_llm(real_settings):
    """无智谱 LLM API Key 时跳过测试."""
    if not real_settings.llm.common.api_key:
        pytest.skip("智谱 LLM API Key 未配置")


@pytest.fixture
def skip_if_no_mqtt(real_settings):
    """无 MQTT 配置时跳过测试."""
    if not real_settings.mqtt.host:
        pytest.skip("EMQX Cloud MQTT 未配置")
