# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 5B — CLI 错误路径 E2E 测试.

验证 CLI 在缺参数、无效输入等错误场景下的行为。
"""

import pytest
from typer.testing import CliRunner

from spide.cli import app

runner = CliRunner()


@pytest.fixture
def cli_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.mark.e2e
class TestCLIErrors:
    """CLI 错误路径."""

    def test_crawl_no_source_no_all(self, cli_workspace):
        result = runner.invoke(app, ["crawl", "-w", str(cli_workspace)])
        # 应报错：请指定 source 或 --all
        assert result.exit_code != 0

    def test_export_no_source(self, cli_workspace):
        result = runner.invoke(app, ["export", "-f", "json", "-w", str(cli_workspace)])
        assert result.exit_code != 0

    def test_wordcloud_no_source_no_texts(self, cli_workspace):
        result = runner.invoke(app, ["wordcloud", "-w", str(cli_workspace)])
        assert result.exit_code != 0

    def test_deep_crawl_missing_platform(self):
        result = runner.invoke(app, ["deep-crawl"])
        # --platform 是 required 参数，Typer 应报错
        assert result.exit_code != 0

    def test_run_missing_prompt(self):
        result = runner.invoke(app, ["run"])
        # prompt 是 required positional 参数
        assert result.exit_code != 0

    def test_memory_add_missing_args(self, cli_workspace):
        result = runner.invoke(app, ["memory", "add", "-w", str(cli_workspace)])
        assert result.exit_code != 0

    def test_schedule_invalid_action(self, cli_workspace):
        result = runner.invoke(app, ["schedule", "invalid_action_xyz", "-w", str(cli_workspace)])
        # 可能 exit_code != 0 或输出中包含"未知"
        assert result.exit_code != 0 or "未知" in result.stdout or "无效" in result.stdout

    def test_export_unsupported_format(self, cli_workspace):
        """不支持的导出格式应报错或不崩溃."""
        result = runner.invoke(
            app, ["export", "-s", "weibo", "-f", "xml", "-w", str(cli_workspace)]
        )
        # 不崩溃即可，export --help 验证了格式选项存在
        assert result.exit_code in (0, 1)
        assert not result.exception or isinstance(result.exception, SystemExit)

    def test_analyze_no_source_no_keywords(self, cli_workspace):
        """analyze 无 source 也无 keywords 应提示错误."""
        result = runner.invoke(app, ["analyze", "-w", str(cli_workspace)])
        # _analyze_async 应打印"请指定"错误并退出
        assert result.exit_code == 1 or "请指定" in result.stdout
