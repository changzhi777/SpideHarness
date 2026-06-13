# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.__main__ 入口点（python -m spide）."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestMainEntrypoint:
    """验证 python -m spide 可作为入口点运行."""

    def test_module_invocation_runs_app(self) -> None:
        """通过 `python -m spide --version` 应成功执行并打印版本."""
        result = subprocess.run(
            [sys.executable, "-m", "spide", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # Typer 默认 --version 输出
        assert "1.1.1" in result.stdout
        assert "spide-agent" in result.stdout

    def test_module_help_works(self) -> None:
        """通过 `python -m spide --help` 应显示帮助文本."""
        result = subprocess.run(
            [sys.executable, "-m", "spide", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # Typer --help 输出包含命令列表
        assert "crawl" in result.stdout
        assert "analyze" in result.stdout

    def test_main_module_importable(self) -> None:
        """__main__ 模块本身应可被导入（不实际运行 app）."""
        import importlib.util

        spec = importlib.util.find_spec("spide.__main__")
        assert spec is not None
        assert spec.origin is not None
        # 验证模块文件存在
        assert spec.origin.endswith("__main__.py")

    def test_main_module_has_expected_source(self) -> None:
        """__main__.py 应正确导入并调用 spide.cli.app."""
        import importlib.util

        spec = importlib.util.find_spec("spide.__main__")
        assert spec is not None
        # 读源码验证关键行
        with open(spec.origin, encoding="utf-8") as f:
            source = f.read()
        assert "from spide.cli import app" in source
        assert "app()" in source


class TestSpideVersionConstant:
    """spide 包 __version__ 暴露."""

    def test_version_string(self) -> None:
        """__version__ 应该是符合 SemVer 的字符串."""
        import spide

        assert hasattr(spide, "__version__")
        parts = spide.__version__.split(".")
        assert len(parts) == 3, f"版本应符合 X.Y.Z 格式: {spide.__version__}"
        for p in parts:
            assert p.isdigit(), f"版本号应全为数字: {spide.__version__}"


class TestMainExecutionInProcess:
    """在主进程内直接执行 __main__（覆盖 0% 报告的根因）.

    pytest-cov 报告 0% 是因为 subprocess 启动的子进程不算主进程覆盖。
    本测试通过 `runpy.run_module` 在主进程内执行 __main__，让覆盖率统计生效。
    """

    def test_runpy_executes_main_in_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """runpy.run_module('spide.__main__') 应在主进程内执行 app()（被 mock 拦截）."""
        import runpy
        from unittest.mock import MagicMock

        # Mock 掉 spide.cli.app 防止真实 CLI 启动阻塞
        fake_app = MagicMock()
        monkeypatch.setattr("spide.cli.app", fake_app)

        # 在主进程内运行 __main__，mock 会拦截 app() 调用
        runpy.run_module(
            "spide.__main__",
            run_name="__main__",
            alter_sys=True,
        )

        # 验证 __main__ 真的调用了 app()
        fake_app.assert_called_once_with()

