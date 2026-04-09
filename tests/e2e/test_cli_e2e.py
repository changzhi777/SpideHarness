# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""E2E 测试 — CLI 完整流程.

用法:
    uv run pytest tests/e2e/test_cli_e2e.py -m e2e -v

测试策略:
    - CLI 入口真实调用（Typer CliRunner）
    - 工作空间使用 tmp_path
    - UAPI 使用 mock（避免外部依赖）
    - LLM 使用 mock
    - SQLite 使用真实临时数据库
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from spide.cli import app
from spide.storage.models import HotTopic, TopicSource

runner = CliRunner()


@pytest.fixture
def cli_workspace(tmp_path: Path, monkeypatch):
    """CLI 测试用工作空间."""
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.mark.e2e
class TestCLIE2E:
    """CLI 端到端流程."""

    def test_version_flag(self):
        """--version 显示版本号."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "spide-agent" in result.stdout

    def test_init_creates_workspace(self, cli_workspace: Path):
        """init 命令创建工作空间."""
        result = runner.invoke(app, ["init", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "工作空间已初始化" in result.stdout

        # 验证文件已创建
        from spide.workspace import get_soul_path

        soul = get_soul_path(cli_workspace)
        assert soul.exists()

    def test_doctor_after_init(self, cli_workspace: Path):
        """init → doctor 流程."""
        # 先初始化
        runner.invoke(app, ["init", "-w", str(cli_workspace)])

        # 然后检查
        result = runner.invoke(app, ["doctor", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "SpideHarness Agent 环境检查" in result.stdout

    def test_config_command(self, cli_workspace: Path):
        """config 命令运行."""
        result = runner.invoke(app, ["config", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "SpideHarness Agent 配置" in result.stdout

    def test_memory_list_after_init(self, cli_workspace: Path):
        """memory list 初始化后应显示 MEMORY.md."""
        runner.invoke(app, ["init", "-w", str(cli_workspace)])

        result = runner.invoke(app, ["memory", "list", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        # 初始化会创建 MEMORY.md 索引文件
        assert "MEMORY.md" in result.stdout

    def test_memory_add_and_list(self, cli_workspace: Path):
        """memory add → list 流程."""
        # 初始化
        runner.invoke(app, ["init", "-w", str(cli_workspace)])

        # 添加记忆
        result = runner.invoke(
            app,
            ["memory", "add", "测试记忆", "这是一条测试记忆内容", "-w", str(cli_workspace)],
        )
        assert result.exit_code == 0
        assert "记忆已添加" in result.stdout

        # 查看列表
        result = runner.invoke(app, ["memory", "list", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "测试记忆" in result.stdout

    def test_crawl_command_mock(self, cli_workspace: Path):
        """crawl 命令（mock UAPI）."""

        with patch("spide.cli._crawl_async", new_callable=AsyncMock) as mock_crawl:
            # 直接模拟 _crawl_async 避免完整的 Engine 初始化
            mock_crawl.return_value = None

            runner.invoke(app, ["crawl", "-s", "weibo"])
            # 命令应该正常退出（_crawl_async 被 mock 了）
            assert mock_crawl.called

    def test_default_no_args(self):
        """无参数运行显示欢迎信息."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "SpideHarness Agent" in result.stdout
        assert "常用命令" in result.stdout

    def test_help_flag(self):
        """--help 显示帮助."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "crawl" in result.stdout
        assert "doctor" in result.stdout


@pytest.mark.e2e
class TestCrawlE2E:
    """爬取端到端流程（mock HTTP + 真实 SQLite）."""

    @pytest.mark.asyncio
    async def test_crawl_save_flow(self, cli_workspace: Path, tmp_db):
        """完整流程: init → crawl → save to SQLite → verify."""
        from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
        from spide.harness.engine import Engine
        from spide.storage.sqlite_repo import SqliteRepository

        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        mock_topics = [
            HotTopic(title="E2E热搜1", source=TopicSource.WEIBO, hot_value=10000, rank=1),
            HotTopic(title="E2E热搜2", source=TopicSource.WEIBO, hot_value=8000, rank=2),
            HotTopic(title="E2E热搜3", source=TopicSource.BAIDU, hot_value=6000, rank=1),
        ]

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"), \
             patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.fetch_hotboard", new_callable=AsyncMock, return_value=mock_topics[:2]), \
             patch("spide.spider.uapi_client.UAPIClient.fetch_all", new_callable=AsyncMock, return_value={"weibo": mock_topics[:2], "baidu": [mock_topics[2]]}):

            await engine.start(workspace=str(cli_workspace))

            # 单源采集
            results = await engine.crawl(sources=["weibo"])
            assert len(results["weibo"]) == 2

            # 存入数据库
            repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
            await repo.start()
            ids = await repo.save_many(results["weibo"])
            assert len(ids) == 2

            # 验证数据
            stored = await repo.query(source="weibo")
            assert len(stored) == 2
            titles = {t.title for t in stored}
            assert "E2E热搜1" in titles
            assert "E2E热搜2" in titles

            await repo.stop()
            await engine.stop()

    @pytest.mark.asyncio
    async def test_full_session_flow(self, cli_workspace: Path):
        """完整 Agent 会话: start → chat → crawl → stop."""
        from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
        from spide.harness.engine import Engine

        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"), \
             patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock):

            bundle = await engine.start(workspace=str(cli_workspace))

            # 模拟对话
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = "已了解，开始采集热搜"

            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_resp):
                resp = await engine.chat("帮我采集微博热搜")
                assert "采集热搜" in resp.choices[0].message.content

            # 验证消息历史
            assert len(bundle.messages) == 2

            # 模拟采集
            mock_topics = [HotTopic(title="会话测试热搜", source=TopicSource.WEIBO)]
            with patch.object(bundle.uapi, "fetch_hotboard", new_callable=AsyncMock, return_value=mock_topics):
                results = await engine.crawl(sources=["weibo"])
                assert len(results["weibo"]) == 1

            # 停止引擎
            await engine.stop()

            # 验证引擎已停止
            assert engine._bundle is None
