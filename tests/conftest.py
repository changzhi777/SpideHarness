# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""测试基础设施."""

import asyncio
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 通用 fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def event_loop():
    """事件循环."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# pytest markers 注册（在 pyproject.toml 中声明）
# ---------------------------------------------------------------------------
