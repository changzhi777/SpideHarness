# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 0 — 环境预检 E2E 测试.

验证 CLI 基础命令（version/doctor/config/init/help）是否正常工作。
无外部依赖，始终可运行。
"""

import pytest
from typer.testing import CliRunner

from spide.cli import app

runner = CliRunner()


@pytest.fixture
def cli_workspace(tmp_path, monkeypatch):
    """临时工作空间（仅设置环境变量，不调用 initialize_workspace）."""
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# TestCLIVersion
# ---------------------------------------------------------------------------


class TestCLIVersion:
    """版本号显示测试."""

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "spide-agent" in result.stdout

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "spide-agent" in result.stdout


# ---------------------------------------------------------------------------
# TestCLIInit
# ---------------------------------------------------------------------------


class TestCLIInit:
    """init 命令测试."""

    def test_init_creates_workspace(self, cli_workspace):
        result = runner.invoke(app, ["init", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "工作空间已初始化" in result.stdout

    def test_init_creates_template_files(self, cli_workspace):
        runner.invoke(app, ["init", "-w", str(cli_workspace)])
        from spide.workspace import get_soul_path, get_user_path, get_identity_path

        assert get_soul_path(str(cli_workspace)).exists()
        assert get_user_path(str(cli_workspace)).exists()
        assert get_identity_path(str(cli_workspace)).exists()

    def test_init_idempotent(self, cli_workspace):
        result1 = runner.invoke(app, ["init", "-w", str(cli_workspace)])
        result2 = runner.invoke(app, ["init", "-w", str(cli_workspace)])
        assert result1.exit_code == 0
        assert result2.exit_code == 0


# ---------------------------------------------------------------------------
# TestCLIDoctor
# ---------------------------------------------------------------------------


class TestCLIDoctor:
    """doctor 命令测试."""

    def test_doctor_after_init(self, cli_workspace):
        runner.invoke(app, ["init", "-w", str(cli_workspace)])
        result = runner.invoke(app, ["doctor", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "环境检查" in result.stdout or "Spide" in result.stdout

    def test_doctor_shows_python_version(self, cli_workspace):
        runner.invoke(app, ["init", "-w", str(cli_workspace)])
        result = runner.invoke(app, ["doctor", "-w", str(cli_workspace)])
        assert "Python" in result.stdout


# ---------------------------------------------------------------------------
# TestCLIConfig
# ---------------------------------------------------------------------------


class TestCLIConfig:
    """config 命令测试."""

    def test_config_command_output(self, cli_workspace):
        runner.invoke(app, ["init", "-w", str(cli_workspace)])
        result = runner.invoke(app, ["config", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "配置" in result.stdout


# ---------------------------------------------------------------------------
# TestCLIHelp
# ---------------------------------------------------------------------------


class TestCLIHelp:
    """帮助信息测试."""

    def test_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ["init", "crawl", "doctor", "analyze", "export", "wordcloud", "schedule", "memory"]:
            assert cmd in result.stdout

    def test_no_args_shows_welcome(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Spide" in result.stdout
