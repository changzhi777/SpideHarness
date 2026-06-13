# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.__main__ 入口点（python -m spide）."""

from __future__ import annotations

import subprocess
import sys


class TestMainEntrypoint:
    """验证 python -m spide 可作为入口点运行."""

    def test_module_invocation_runs_app(self):
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

    def test_module_help_works(self):
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

    def test_main_module_importable(self):
        """__main__ 模块本身应可被导入（不实际运行 app）."""
        import importlib.util

        spec = importlib.util.find_spec("spide.__main__")
        assert spec is not None
        assert spec.origin is not None
        # 验证模块文件存在
        assert spec.origin.endswith("__main__.py")

    def test_main_module_has_expected_source(self):
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

    def test_version_string(self):
        """__version__ 应该是符合 SemVer 的字符串."""
        import spide

        assert hasattr(spide, "__version__")
        parts = spide.__version__.split(".")
        assert len(parts) == 3, f"版本应符合 X.Y.Z 格式: {spide.__version__}"
        for p in parts:
            assert p.isdigit(), f"版本号应全为数字: {spide.__version__}"
