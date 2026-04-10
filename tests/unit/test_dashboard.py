# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Dashboard 看板模块单元测试."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from spide.storage.models import HotTopic, TopicSource


def _make_topic(
    title: str = "测试话题",
    source: TopicSource = TopicSource.WEIBO,
    hot_value: int = 10000,
    rank: int = 1,
) -> HotTopic:
    return HotTopic(
        title=title,
        source=source,
        hot_value=hot_value,
        rank=rank,
        url="https://example.com/1",
    )


# ---------------------------------------------------------------------------
# collector
# ---------------------------------------------------------------------------


class TestAggregate:
    """数据聚合逻辑."""

    def test_empty_dashboard(self):
        from spide.dashboard.collector import _empty_dashboard

        data = _empty_dashboard()
        assert data["total_count"] == 0
        assert data["platform_stats"] == []
        assert data["top_topics"] == []
        assert data["stats_summary"]["total"] == 0

    def test_aggregate_single_topic(self):
        from spide.dashboard.collector import _aggregate

        topics = [_make_topic()]
        data = _aggregate(topics, 1)

        assert data["total_count"] == 1
        assert len(data["platform_stats"]) == 1
        assert data["platform_stats"][0]["source"] == "weibo"
        assert data["platform_stats"][0]["count"] == 1
        assert len(data["top_topics"]) == 1
        assert data["top_topics"][0]["title"] == "测试话题"

    def test_aggregate_multiple_platforms(self):
        from spide.dashboard.collector import _aggregate

        topics = [
            _make_topic("微博话题", TopicSource.WEIBO, 50000),
            _make_topic("百度话题", TopicSource.BAIDU, 40000),
            _make_topic("抖音话题", TopicSource.DOUYIN, 30000),
        ]
        data = _aggregate(topics, 3)

        assert data["stats_summary"]["platforms"] == 3
        assert len(data["platform_stats"]) == 3
        # 按数量排序
        assert data["platform_stats"][0]["count"] == 1

    def test_aggregate_top_topics_sorted_by_hot(self):
        from spide.dashboard.collector import _aggregate

        topics = [
            _make_topic("低热度", TopicSource.WEIBO, 1000),
            _make_topic("高热度", TopicSource.WEIBO, 99999),
            _make_topic("中热度", TopicSource.WEIBO, 5000),
        ]
        data = _aggregate(topics, 3)

        assert data["top_topics"][0]["title"] == "高热度"
        assert data["top_topics"][0]["hot_value"] == 99999

    def test_aggregate_platform_ranks(self):
        from spide.dashboard.collector import _aggregate

        topics = [
            _make_topic("微博1", TopicSource.WEIBO, 90000),
            _make_topic("微博2", TopicSource.WEIBO, 80000),
            _make_topic("百度1", TopicSource.BAIDU, 70000),
        ]
        data = _aggregate(topics, 3)

        assert "weibo" in data["platform_ranks"]
        assert len(data["platform_ranks"]["weibo"]) == 2
        assert data["platform_ranks"]["weibo"][0]["title"] == "微博1"

    def test_aggregate_avg_hot_value(self):
        from spide.dashboard.collector import _aggregate

        topics = [
            _make_topic(hot_value=1000),
            _make_topic(hot_value=3000),
        ]
        data = _aggregate(topics, 2)

        assert data["stats_summary"]["avg_hot_value"] == 2000


# ---------------------------------------------------------------------------
# renderer
# ---------------------------------------------------------------------------


class TestRenderer:
    """HTML 渲染逻辑."""

    def test_render_contains_html_structure(self):
        from spide.dashboard.renderer import render_dashboard
        from spide.dashboard.collector import _empty_dashboard

        data = _empty_dashboard()
        html = render_dashboard(data)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "SpideHarness Agent" in html

    def test_render_injects_json_data(self):
        from spide.dashboard.renderer import render_dashboard

        data = {"total_count": 42, "top_topics": [{"title": "测试"}]}
        html = render_dashboard(data)

        assert '"total_count": 42' in html
        assert '"测试"' in html

    def test_render_with_unicode(self):
        from spide.dashboard.renderer import render_dashboard

        data = {"total_count": 1, "top_topics": [{"title": "中文话题 🎉"}]}
        html = render_dashboard(data)

        assert "中文话题" in html
        assert "\ud83c\udf89" in html or "🎉" in html

    def test_write_dashboard_creates_file(self, tmp_path):
        from spide.dashboard.renderer import render_dashboard, write_dashboard

        html = render_dashboard({"total_count": 0})
        filepath = write_dashboard(html, tmp_path / "sub" / "dashboard.html")

        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestDashboardCLI:
    """dashboard CLI 命令."""

    def test_dashboard_help(self):
        from typer.testing import CliRunner
        from spide.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "看板" in result.stdout or "dashboard" in result.stdout.lower()

    def test_dashboard_no_database(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        from spide.cli import app

        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(app, ["dashboard", "-w", str(tmp_path), "--no-open"])
        # 数据库不存在应提示
        assert "未找到数据库" in result.stdout or result.exit_code == 0
