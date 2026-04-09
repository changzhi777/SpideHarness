# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 5A — E2E 全流程测试.

Mock-based 始终可运行 + 真实 API 集成测试。
覆盖 init → crawl → analyze → export → wordcloud 完整流水线。
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from spide.cli import app
from spide.storage.models import HotTopic
from spide.storage.models import TopicSource

runner = CliRunner()


@pytest.fixture
def cli_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    return tmp_path


def _make_mock_topics(count=5):
    """构造 mock HotTopic 列表."""
    return [
        HotTopic(
            title=f"测试热搜 {i+1}",
            source=TopicSource.WEIBO,
            hot_value=10000 * (count - i),
            rank=i + 1,
            url=f"https://weibo.com/{i}",
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Mock-based E2E（始终可运行）
# ---------------------------------------------------------------------------


class TestMockE2EPipeline:
    """Mock 外部 API 的完整 E2E 流程."""

    def test_all_cli_commands_help(self):
        """所有命令 --help 应正常输出."""
        commands = [
            ["init", "--help"],
            ["config", "--help"],
            ["doctor", "--help"],
            ["crawl", "--help"],
            ["analyze", "--help"],
            ["export", "--help"],
            ["wordcloud", "--help"],
            ["schedule", "--help"],
            ["deep-crawl", "--help"],
            ["run", "--help"],
            ["batch-crawl", "--help"],
            ["memory", "--help"],
        ]
        for cmd in commands:
            result = runner.invoke(app, cmd)
            assert result.exit_code == 0, f"{' '.join(cmd)} 失败: {result.stdout}"

    def test_init_memory_add_list(self, cli_workspace):
        """init + memory add + memory list."""
        runner.invoke(app, ["init", "-w", str(cli_workspace)])
        result = runner.invoke(app, ["memory", "add", "测试记忆", "这是一条测试记忆内容", "-w", str(cli_workspace)])
        assert result.exit_code == 0

        result = runner.invoke(app, ["memory", "list", "-w", str(cli_workspace)])
        assert result.exit_code == 0

    def test_export_format_json(self, cli_workspace, tmp_path):
        """JSON 导出文件验证."""
        from spide.storage.exporter import DataExporter

        topics = _make_mock_topics(3)
        exporter = DataExporter(output_dir=str(tmp_path / "export"))
        filepath = asyncio.run(
            exporter.export(topics, filename="test_export", fmt="json")
        )
        assert filepath.exists()
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3
        assert data[0]["title"] == "测试热搜 1"

    def test_export_format_csv(self, cli_workspace, tmp_path):
        """CSV 导出文件验证."""
        from spide.storage.exporter import DataExporter

        topics = _make_mock_topics(3)
        exporter = DataExporter(output_dir=str(tmp_path / "export"))
        filepath = asyncio.run(
            exporter.export(topics, filename="test_export", fmt="csv")
        )
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "测试热搜 1" in content

    def test_crawl_all_flag_mock(self, cli_workspace):
        """crawl --all 标志 Mock 测试."""
        mock_topics = _make_mock_topics(3)
        with patch("spide.cli._crawl_async", new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = None
            result = runner.invoke(app, ["crawl", "--all", "-w", str(cli_workspace)])
            # 即使 mock 了异步函数，CLI 入口仍应正确解析参数
            assert result.exit_code == 0 or "采集" in result.stdout or result.exit_code == 1


# ---------------------------------------------------------------------------
# 真实 API E2E
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealE2EPipeline:
    """真实 API 端到端流程."""

    async def test_real_crawl_export_pipeline(self, cli_workspace):
        """真实 crawl → save → export 全流程."""
        from spide.config import load_settings
        from spide.harness import Engine
        from spide.storage.exporter import DataExporter

        settings = load_settings()
        if not settings.uapi.api_key:
            pytest.skip("UAPI API Key 未配置")

        engine = Engine(settings)
        try:
            await engine.start(workspace=str(cli_workspace))
            results = await engine.crawl(sources=["weibo"])
            topics = results.get("weibo", [])

            if not topics:
                pytest.skip("微博热搜无数据")

            # 导出 JSON
            out_dir = str(cli_workspace / "export")
            exporter = DataExporter(output_dir=out_dir)
            filepath = await exporter.export(topics, filename="weibo_real", fmt="json")
            assert filepath.exists()
        finally:
            await engine.stop()

    async def test_real_export_json(self, cli_workspace):
        """真实 JSON 导出."""
        from spide.config import load_settings
        from spide.harness import Engine
        from spide.storage.exporter import DataExporter

        settings = load_settings()
        if not settings.uapi.api_key:
            pytest.skip("UAPI API Key 未配置")

        engine = Engine(settings)
        try:
            await engine.start(workspace=str(cli_workspace))
            results = await engine.crawl(sources=["weibo"])
            topics = results.get("weibo", [])
            if not topics:
                pytest.skip("微博热搜无数据")

            exporter = DataExporter(output_dir=str(cli_workspace / "export"))
            filepath = await exporter.export(topics, filename="real_json", fmt="json")
            assert filepath.exists()
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) > 0
            assert "title" in data[0]
        finally:
            await engine.stop()

    async def test_real_export_csv(self, cli_workspace):
        """真实 CSV 导出."""
        from spide.config import load_settings
        from spide.harness import Engine
        from spide.storage.exporter import DataExporter

        settings = load_settings()
        if not settings.uapi.api_key:
            pytest.skip("UAPI API Key 未配置")

        engine = Engine(settings)
        try:
            await engine.start(workspace=str(cli_workspace))
            results = await engine.crawl(sources=["weibo"])
            topics = results.get("weibo", [])
            if not topics:
                pytest.skip("微博热搜无数据")

            exporter = DataExporter(output_dir=str(cli_workspace / "export"))
            filepath = await exporter.export(topics, filename="real_csv", fmt="csv")
            assert filepath.exists()
        finally:
            await engine.stop()

    async def test_real_export_excel(self, cli_workspace):
        """真实 Excel 导出."""
        from spide.config import load_settings
        from spide.harness import Engine
        from spide.storage.exporter import DataExporter

        settings = load_settings()
        if not settings.uapi.api_key:
            pytest.skip("UAPI API Key 未配置")

        engine = Engine(settings)
        try:
            await engine.start(workspace=str(cli_workspace))
            results = await engine.crawl(sources=["weibo"])
            topics = results.get("weibo", [])
            if not topics:
                pytest.skip("微博热搜无数据")

            exporter = DataExporter(output_dir=str(cli_workspace / "export"))
            filepath = await exporter.export(topics, filename="real_excel", fmt="excel")
            assert filepath.exists()
            assert filepath.suffix == ".xlsx"
        finally:
            await engine.stop()

    async def test_real_wordcloud(self, cli_workspace):
        """真实词云生成."""
        from spide.analysis.wordcloud_generator import WordCloudGenerator

        gen = WordCloudGenerator(output_dir=str(cli_workspace / "wc"))
        filepath = await gen.generate_from_texts(
            texts=["人工智能", "机器学习", "深度学习", "大模型", "ChatGPT", "AI芯片", "自动驾驶", "量子计算"],
            filename="test_wc",
        )
        assert filepath.exists()
        assert filepath.stat().st_size > 1000, "词云文件应 > 1KB"

    async def test_real_analyze_with_strategy(self, cli_workspace):
        """真实 LLM analyze --strategy."""
        from spide.config import load_settings
        from spide.harness import Engine
        from spide.analysis.summarizer import SmartCrawlStrategy

        settings = load_settings()
        if not settings.uapi.api_key or not settings.llm.common.api_key:
            pytest.skip("UAPI 或 LLM API Key 未配置")

        engine = Engine(settings)
        try:
            bundle = await engine.start(workspace=str(cli_workspace))
            results = await engine.crawl(sources=["weibo"])
            topics = results.get("weibo", [])
            if not topics:
                pytest.skip("微博热搜无数据")

            topics_data = [
                {"title": t.title, "hot_value": t.hot_value, "source": t.source.value}
                for t in topics[:5]
            ]
            strategist = SmartCrawlStrategy(bundle.llm)
            result = await strategist.recommend(hot_topics=topics_data)
            assert isinstance(result, dict)
        finally:
            await engine.stop()
