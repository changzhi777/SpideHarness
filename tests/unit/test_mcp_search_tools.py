# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — MCP 新搜索工具分发."""

from unittest.mock import AsyncMock, patch

from spide.mcp.server import _dispatch_tool


class TestWebSearchEnhancedTool:
    """web_search_enhanced 工具测试."""

    @patch("spide.mcp.search_provider.WebSearchProvider")
    async def test_duckduckgo_search(self, mock_cls):
        from spide.mcp.search_provider import SearchResult

        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            SearchResult(title="Result 1", url="https://a.com", description="Desc 1"),
        ]
        mock_cls.return_value = mock_provider

        result = await _dispatch_tool("web_search_enhanced", {
            "query": "test",
            "engine": "duckduckgo",
            "limit": 5,
        }, None)

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Result 1"
        mock_provider.search.assert_called_once_with("test", engine="duckduckgo", limit=5)


class TestFetchWebPageTool:
    """fetch_web_page 工具测试."""

    @patch("spide.mcp.search_provider.WebContentProvider")
    async def test_fetch_page(self, mock_cls):
        from spide.mcp.search_provider import PageContent

        mock_cls.fetch_page = AsyncMock(return_value=PageContent(
            url="https://example.com",
            title="Example",
            text="Content here",
        ))

        result = await _dispatch_tool("fetch_web_page", {
            "url": "https://example.com",
        }, None)

        assert result["title"] == "Example"
        assert "Content here" in result["content"]


class TestFetchRepoInfoTool:
    """fetch_repo_info 工具测试."""

    @patch("spide.mcp.search_provider.RepoInfoProvider")
    async def test_summary(self, mock_cls):
        mock_cls.fetch_repo_summary = AsyncMock(return_value={
            "repo": "test/repo",
            "description": "Test",
            "stars": 100,
            "language": "Python",
            "readme_preview": "# Hello",
        })

        result = await _dispatch_tool("fetch_repo_info", {
            "repo": "test/repo",
            "info_type": "summary",
        }, None)

        assert result["repo"] == "test/repo"
        assert result["stars"] == 100

    @patch("spide.mcp.search_provider.WebContentProvider")
    async def test_readme(self, mock_cls):
        mock_cls.fetch_github_readme = AsyncMock(return_value="# README content")

        result = await _dispatch_tool("fetch_repo_info", {
            "repo": "test/repo",
            "info_type": "readme",
        }, None)

        assert "# README content" in result["readme"]
