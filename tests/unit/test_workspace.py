# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 工作空间管理."""



from spide.workspace import (
    get_memory_dir,
    get_memory_index_path,
    get_sessions_dir,
    get_soul_path,
    get_workspace_root,
    initialize_workspace,
    workspace_health,
)


class TestPathResolution:
    """路径解析优先级."""

    def test_explicit_workspace(self, tmp_path):
        root = get_workspace_root(str(tmp_path))
        assert root == tmp_path.resolve()

    def test_env_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        root = get_workspace_root()
        assert root == tmp_path.resolve()

    def test_default_workspace(self, monkeypatch):
        monkeypatch.delenv("SPIDE_WORKSPACE", raising=False)
        root = get_workspace_root()
        assert root.name == ".spide_agent"


class TestInitialize:
    """工作空间初始化."""

    def test_creates_directories(self, tmp_path):
        root = initialize_workspace(str(tmp_path))
        assert root.is_dir()
        assert get_memory_dir(root).is_dir()
        assert get_sessions_dir(root).is_dir()

    def test_creates_template_files(self, tmp_path):
        root = initialize_workspace(str(tmp_path))
        assert get_soul_path(root).exists()
        assert get_memory_index_path(root).exists()

    def test_idempotent(self, tmp_path):
        root1 = initialize_workspace(str(tmp_path))
        root2 = initialize_workspace(str(tmp_path))
        assert root1 == root2
        # 不应覆盖已有文件
        soul = get_soul_path(root1)
        content = soul.read_text(encoding="utf-8")
        initialize_workspace(str(tmp_path))
        assert soul.read_text(encoding="utf-8") == content


class TestHealthCheck:
    """健康检查."""

    def test_uninitialized(self, tmp_path, monkeypatch):
        # 使用不存在的子路径，而非已存在的 tmp_path
        uninit_path = tmp_path / "not_initialized"
        monkeypatch.setenv("SPIDE_WORKSPACE", str(uninit_path))
        health = workspace_health(str(uninit_path))
        assert health["workspace_root"] is False

    def test_after_init(self, tmp_path):
        initialize_workspace(str(tmp_path))
        health = workspace_health(str(tmp_path))
        assert health["workspace_root"] is True
        assert health["soul"] is True
        assert health["memory_dir"] is True
