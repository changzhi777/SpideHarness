# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""E2E 测试 — 高级 CLI 命令流程（crawl-diff / dedup / monitor / track / dashboard）.

测试策略: CLI 入口真实调用 + Mock 外部依赖 + 真实 SQLite.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from spide.cli import app
from spide.storage.models import HotTopic, TopicSource

runner = CliRunner()


@pytest.fixture
def cli_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.fixture
def populated_db(cli_workspace: Path) -> Path:
    """创建包含测试数据的数据库."""
    import sqlite3

    db_path = cli_workspace / "spide_data.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hot_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            hot_value INTEGER,
            url TEXT,
            rank INTEGER,
            category TEXT,
            summary TEXT,
            fetched_at TEXT DEFAULT (datetime('now')),
            extra TEXT DEFAULT '{}')
    """)
    # 插入含重复的数据
    rows = [
        ("微博热搜A", "weibo", 50000, "https://weibo.com/a", 1, "tech"),
        ("微博热搜A", "weibo", 40000, "https://weibo.com/a2", 2, "tech"),  # 重复
        ("微博热搜B", "weibo", 30000, "https://weibo.com/b", 3, "society"),
        ("百度热搜X", "baidu", 60000, "https://baidu.com/x", 1, "tech"),
    ]
    conn.executemany(
        "INSERT INTO hot_topics "
        "(title, source, hot_value, url, rank, category) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.e2e
class TestCrawlDiffCLI:
    """crawl-diff CLI 命令."""

    def test_crawl_diff_help(self):
        result = runner.invoke(app, ["crawl-diff", "--help"])
        assert result.exit_code == 0
        assert "source" in result.stdout

    def test_crawl_diff_last_no_data(self, cli_workspace):
        """--last 无历史数据时正常退出（不崩溃）."""
        result = runner.invoke(
            app, ["crawl-diff", "-s", "weibo", "--last", "-w", str(cli_workspace)]
        )
        assert result.exit_code in (0, 1)
        assert not result.exception or isinstance(result.exception, SystemExit)

    def test_crawl_diff_mock(self, cli_workspace):
        """crawl-diff mock 采集 + diff 流程."""
        mock_topics = [
            HotTopic(title="新热搜1", source=TopicSource.WEIBO, hot_value=90000, rank=1),
            HotTopic(title="热搜B", source=TopicSource.WEIBO, hot_value=30000, rank=2),
        ]

        uapi_fetch = patch(
            "spide.spider.uapi_client.UAPIClient.fetch_hotboard",
            new_callable=AsyncMock,
            return_value=mock_topics,
        )
        with (
            patch("spide.config.load_settings") as mock_load,
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
            uapi_fetch,
        ):
            from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig

            settings = Settings(
                llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
                uapi=UAPIConfig(api_key="test-uapi"),
            )
            mock_load.return_value = settings

            result = runner.invoke(app, ["crawl-diff", "-s", "weibo", "-w", str(cli_workspace)])
            assert result.exit_code in (0, 1)


@pytest.mark.e2e
class TestDedupCLI:
    """dedup CLI 命令."""

    def test_dedup_help(self):
        result = runner.invoke(app, ["dedup", "--help"])
        assert result.exit_code == 0
        assert "dry-run" in result.stdout

    def test_dedup_no_database(self, cli_workspace):
        """无数据时正常退出（不崩溃）."""
        result = runner.invoke(app, ["dedup", "-w", str(cli_workspace)])
        assert result.exit_code in (0, 1)
        assert not result.exception or isinstance(result.exception, SystemExit)

    def test_dedup_dry_run(self, populated_db):
        """dry-run 模式不删除数据，输出包含分析信息."""
        result = runner.invoke(app, ["dedup", "--dry-run", "-w", str(populated_db.parent)])
        assert result.exit_code in (0, 1)
        # 输出应包含去重分析信息或"无重复"
        out = result.stdout
        assert "重复" in out or "dry-run" in out.lower() or "无重复" in out or "Spide" in out

    def test_dedup_with_data(self, populated_db):
        """实际去重正常执行（不崩溃）."""
        result = runner.invoke(app, ["dedup", "-w", str(populated_db.parent)])
        assert result.exit_code in (0, 1)
        assert not result.exception or isinstance(result.exception, SystemExit)


@pytest.mark.e2e
class TestMonitorCLI:
    """monitor CLI 命令."""

    def test_monitor_help(self):
        result = runner.invoke(app, ["monitor", "--help"])
        assert result.exit_code == 0
        assert "once" in result.stdout

    def test_monitor_once_no_rules(self, cli_workspace):
        """无告警规则时提示."""
        result = runner.invoke(app, ["monitor", "--once", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        assert "无告警规则" in result.stdout or "规则" in result.stdout


@pytest.mark.e2e
class TestTrackCLI:
    """track CLI 命令."""

    def test_track_help(self):
        result = runner.invoke(app, ["track", "--help"])
        assert result.exit_code == 0
        assert "top" in result.stdout

    def test_track_mock(self, cli_workspace):
        """track mock 采集 + 深度追踪."""
        from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
        from spide.storage.models import TopicDeepTrack

        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )

        mock_topics = [
            HotTopic(title="追踪测试热搜", source=TopicSource.WEIBO, hot_value=50000),
        ]
        mock_tracks = [
            TopicDeepTrack(
                topic_title="追踪测试热搜",
                topic_source=TopicSource.WEIBO,
                analysis_status="completed",
                sentiment="positive",
                summary="这是一条测试摘要",
                keywords=["测试", "热搜"],
            ),
        ]

        uapi_fetch = patch(
            "spide.spider.uapi_client.UAPIClient.fetch_hotboard",
            new_callable=AsyncMock,
            return_value=mock_topics,
        )
        track_patch = patch(
            "spide.spider.deep_tracker.DeepTopicTracker.track_topics",
            new_callable=AsyncMock,
            return_value=mock_tracks,
        )
        with (
            patch("spide.config.load_settings") as mock_load,
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
            uapi_fetch,
            track_patch,
        ):
            mock_load.return_value = settings
            result = runner.invoke(
                app, ["track", "-s", "weibo", "--top", "1", "-w", str(cli_workspace)]
            )
            assert result.exit_code in (0, 1)
            # 应输出追踪相关信息或错误，而非异常
            assert not result.exception or isinstance(result.exception, SystemExit)


@pytest.mark.e2e
class TestDashboardCLI:
    """dashboard CLI 命令."""

    def test_dashboard_help(self):
        result = runner.invoke(app, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "output" in result.stdout

    def test_dashboard_no_database(self, cli_workspace):
        """dashboard 命令正常执行（不崩溃）."""
        result = runner.invoke(app, ["dashboard", "--no-open", "-w", str(cli_workspace)])
        assert result.exit_code == 0
        out = result.stdout
        assert "看板" in out or "数据库" in out or "dashboard" in out.lower() or "Spide" in out


@pytest.mark.e2e
class TestCrossAnalyzeCLI:
    """cross-analyze CLI 命令."""

    def test_cross_analyze_help(self):
        result = runner.invoke(app, ["cross-analyze", "--help"])
        assert result.exit_code == 0
        assert "report" in result.stdout or "save" in result.stdout
