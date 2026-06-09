# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""E2E 测试 — Dashboard Web API (FastAPI TestClient)."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    """创建包含测试数据的 SQLite 数据库."""
    db_path = tmp_path / "spide_data.db"
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
            fetched_at TEXT DEFAULT (datetime('now'))
        )
    """)
    rows = [
        ("微博热搜1", "weibo", 99999, "https://weibo.com/1", 1, "tech"),
        ("微博热搜2", "weibo", 88888, "https://weibo.com/2", 2, "society"),
        ("百度热搜1", "baidu", 77777, "https://baidu.com/1", 1, "tech"),
        ("知乎热榜1", "zhihu", 66666, "https://zhihu.com/1", 1, "science"),
    ]
    conn.executemany(
        "INSERT INTO hot_topics "
        "(title, source, hot_value, url, rank, category) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def api_client(populated_db):
    """创建 FastAPI TestClient，指向测试数据库."""
    from fastapi.testclient import TestClient

    with patch("dashboard.api.DB_PATH", populated_db):
        from dashboard.api import app

        client = TestClient(app)
        yield client


@pytest.mark.e2e
class TestDashboardAPI:
    """Dashboard API 端点测试."""

    def test_index_page(self, api_client):
        """根路径返回 HTML 页面."""
        resp = api_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_get_dashboard(self, api_client):
        """Dashboard API 返回全量数据."""
        resp = api_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 4
        assert len(data["platform_stats"]) >= 2
        assert len(data["top_topics"]) >= 1
        assert "total" in data["stats_summary"]
        assert data["stats_summary"]["total"] == 4

    def test_get_topics_default(self, api_client):
        """话题列表默认分页."""
        resp = api_client.get("/api/topics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4

    def test_get_topics_by_source(self, api_client):
        """按平台筛选话题."""
        resp = api_client.get("/api/topics", params={"source": "weibo"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(item["source"] == "weibo" for item in data["items"])

    def test_get_topics_pagination(self, api_client):
        """分页参数."""
        resp = api_client.get("/api/topics", params={"limit": 1, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 4

    def test_get_sources(self, api_client):
        """获取数据源平台列表."""
        resp = api_client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.json()
        sources = {s["source"] for s in data["sources"]}
        assert "weibo" in sources
        assert "baidu" in sources
        assert "zhihu" in sources

    def test_get_dashboard_top_topics_sorted(self, api_client):
        """Top topics 按热度降序."""
        resp = api_client.get("/api/dashboard")
        data = resp.json()
        topics = data["top_topics"]
        for i in range(len(topics) - 1):
            assert topics[i]["hot_value"] >= topics[i + 1]["hot_value"]


@pytest.mark.e2e
class TestAgentDiscovery:
    """AI Agent 自发现端点测试（/.well-known/agent.json）."""

    def test_agent_json_returns_200(self, api_client):
        """agent.json 端点返回 200."""
        resp = api_client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_agent_json_structure(self, api_client):
        """agent.json 包含必要字段."""
        data = api_client.get("/.well-known/agent.json").json()
        assert "agent" in data
        assert "capabilities" in data
        assert "discovery" in data
        assert data["agent"]["name"] == "SpideHarness Agent"
        assert data["agent"]["version"] == "3.1.1"

    def test_agent_json_mcp_tools(self, api_client):
        """agent.json 包含 8 个 MCP 工具."""
        data = api_client.get("/.well-known/agent.json").json()
        tools = data["capabilities"]["mcp"]["tools"]
        assert len(tools) == 8
        tool_names = {t["name"] for t in tools}
        assert "crawl_hot_topics" in tool_names
        assert "web_search" in tool_names
        assert "deep_crawl_hot_topics" in tool_names
        # 每个工具必须含 inputSchema
        for t in tools:
            assert "inputSchema" in t
            assert "description" in t

    def test_agent_json_http_endpoints(self, api_client):
        """agent.json 包含 HTTP 端点."""
        data = api_client.get("/.well-known/agent.json").json()
        endpoints = data["capabilities"]["http"]["endpoints"]
        assert len(endpoints) >= 5
        paths = {e["path"] for e in endpoints}
        assert "/api/dashboard" in paths
        assert "/api/crawl" in paths
        assert "/.well-known/agent.json" in paths

    def test_agent_json_skills(self, api_client):
        """agent.json 自动扫描 skills 目录."""
        data = api_client.get("/.well-known/agent.json").json()
        skills = data["capabilities"]["skills"]
        assert len(skills) >= 5
        skill_names = {s["name"] for s in skills}
        assert "spide-crawl" in skill_names
        assert "spide-analyze" in skill_names

    def test_agent_json_discovery_links(self, api_client):
        """agent.json 包含文档发现链接."""
        data = api_client.get("/.well-known/agent.json").json()
        discovery = data["discovery"]
        assert "mcp_reference" in discovery
        assert "http_reference" in discovery
        assert "skills_index" in discovery


@pytest.mark.e2e
class TestFeishuHandlerParsing:
    """飞书 handler 指令解析测试."""

    def test_parse_crawl(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("crawl weibo")
        assert result == ("crawl", {"source": "weibo"})

    def test_parse_crawl_all(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("crawl all")
        assert result == ("crawl", {"source": "all"})

    def test_parse_status(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("status")
        assert result == ("status", {})

    def test_parse_help(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("help")
        assert result == ("help", {})

    def test_parse_track(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("track weibo 5")
        assert result == ("track", {"source": "weibo", "top_n": 5})

    def test_parse_track_default_n(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("track zhihu")
        assert result == ("track", {"source": "zhihu", "top_n": 10})

    def test_parse_export(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("export weibo")
        assert result == ("export", {"source": "weibo"})

    def test_parse_batch(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("batch xhs,dy")
        assert result == ("batch", {"platforms": ["xhs", "dy"]})

    def test_parse_analyze(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("analyze baidu")
        assert result == ("analyze", {"source": "baidu"})

    def test_parse_case_insensitive(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("CRAWL WEIBO")
        assert result == ("crawl", {"source": "WEIBO"})

    def test_parse_empty(self):
        from dashboard.feishu_handler import parse_command

        assert parse_command("") is None
        assert parse_command("  ") is None

    def test_parse_unknown(self):
        from dashboard.feishu_handler import parse_command

        assert parse_command("unknown xyz") is None

    def test_parse_leading_whitespace(self):
        from dashboard.feishu_handler import parse_command

        result = parse_command("  crawl weibo  ")
        assert result == ("crawl", {"source": "weibo"})


@pytest.mark.e2e
class TestFeishuCommandEndpoint:
    """飞书通用命令执行端点测试."""

    def test_command_help(self, api_client):
        """help 命令应返回帮助文本."""
        resp = api_client.post("/api/feishu/command", json={"text": "help"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "crawl" in data["message"]

    def test_command_text_format(self, api_client):
        """支持 text 字段自动解析."""
        resp = api_client.post("/api/feishu/command", json={"text": "help"})
        assert resp.status_code == 200

    def test_command_direct_format(self, api_client):
        """支持 command + args 直接指定."""
        resp = api_client.post(
            "/api/feishu/command",
            json={"command": "help", "args": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_command_unparsable(self, api_client):
        """无法解析的指令应报错."""
        resp = api_client.post("/api/feishu/command", json={"text": "xyz123"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_command_missing_fields(self, api_client):
        """缺少 text/command 字段应返回 400."""
        resp = api_client.post("/api/feishu/command", json={})
        assert resp.status_code == 400


@pytest.mark.e2e
class TestGitHubTrendingUnit:
    """GitHub Trending 服务单元级 E2E 测试."""

    def test_github_repo_to_dict(self):
        from dashboard.github_trending import GitHubRepo

        repo = GitHubRepo(
            full_name="test/repo",
            description="Test repo",
            stars=100,
            forks=20,
            language="Python",
            html_url="https://github.com/test/repo",
            topics=["ai", "agent"],
            updated_at="2026-05-27",
            category="AI",
        )
        d = repo.to_dict()
        assert d["full_name"] == "test/repo"
        assert d["stars"] == 100
        assert d["category"] == "AI"

    def test_format_feishu_card(self):
        from dashboard.github_trending import GitHubRepo, GitHubTrendingService

        svc = GitHubTrendingService()
        repos = [
            GitHubRepo(full_name="ai/repo", stars=100, category="AI Agent"),
            GitHubRepo(full_name="llm/tools", stars=200, category="大模型"),
        ]
        card = svc.format_feishu_card(repos)
        assert card["msg_type"] == "interactive"
        assert "header" in card["card"]
        elements = card["card"]["elements"]
        assert len(elements) >= 4  # overview + hr + 2 categories + hr + note
