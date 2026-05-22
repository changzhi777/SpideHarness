# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 搜索适配器层."""

from unittest.mock import AsyncMock, MagicMock, patch

from spide.mcp.search_provider import (
    _extract_body,
    _strip_html,
    PageContent,
    RepoInfo,
    RepoInfoProvider,
    SearchResult,
    WebContentProvider,
    WebSearchProvider,
)


class TestStripHtml:
    """HTML 清理测试."""

    def test_basic_tags(self):
        assert _strip_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_entities(self):
        assert _strip_html("a &amp; b &lt; c") == "a & b < c"

    def test_empty(self):
        assert _strip_html("") == ""

    def test_no_tags(self):
        assert _strip_html("plain text") == "plain text"

    def test_nested_tags(self):
        assert _strip_html("<div><span><a>Link</a></span></div>") == "Link"


class TestExtractBody:
    """_extract_body 测试."""

    def test_extracts_body(self):
        html = "<html><head>bad</head><body>good</body></html>"
        assert "good" in _extract_body(html)

    def test_no_body_tag(self):
        html = "<html>content<script>bad</script>good</html>"
        result = _extract_body(html)
        assert "bad" not in result
        assert "good" in result


class TestWebSearchProvider:
    """WebSearchProvider 测试."""

    def test_parse_ddgs_html_two_results(self):
        html = '''
        <a class="result__a" href="https://example.com/1">Result 1</a>
        <a class="result__snippet">Desc 1</a>
        <a class="result__a" href="https://example.com/2">Result 2</a>
        <a class="result__snippet">Desc 2</a>
        '''
        results = WebSearchProvider._parse_ddgs_html(html, limit=10)
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[0].description == "Desc 1"

    def test_parse_respects_limit(self):
        html = ""
        for i in range(20):
            html += f'<a class="result__a" href="https://x.com/{i}">R{i}</a>'
            html += f'<a class="result__snippet">D{i}</a>'
        results = WebSearchProvider._parse_ddgs_html(html, limit=5)
        assert len(results) == 5

    def test_parse_empty_html(self):
        results = WebSearchProvider._parse_ddgs_html("", limit=10)
        assert results == []

    async def test_search_unknown_engine(self):
        provider = WebSearchProvider()
        results = await provider.search("test", engine="unknown")
        assert results == []


class TestWebContentProvider:
    """WebContentProvider 测试."""

    @staticmethod
    def _mock_aiohttp_session(resp):
        """构建 aiohttp ClientSession mock（双层 async context manager）."""
        get_cm = MagicMock()
        get_cm.__aenter__ = AsyncMock(return_value=resp)
        get_cm.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get.return_value = get_cm

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        return session_cm

    async def test_fetch_page_mock_response(self):
        html = "<html><head><title>Test Page</title></head><body><p>Hello World</p></body></html>"

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value=html)

        with patch("spide.mcp.search_provider.aiohttp.ClientSession",
                    return_value=self._mock_aiohttp_session(mock_resp)):
            page = await WebContentProvider.fetch_page("https://example.com")

        assert page.title == "Test Page"
        assert "Hello World" in page.text

    async def test_fetch_page_404(self):
        mock_resp = MagicMock()
        mock_resp.status = 404

        with patch("spide.mcp.search_provider.aiohttp.ClientSession",
                    return_value=self._mock_aiohttp_session(mock_resp)):
            page = await WebContentProvider.fetch_page("https://example.com/404")

        assert page.text == ""

    async def test_fetch_page_with_links(self):
        html = '<html><head><title>T</title></head><body><a href="https://a.com">A</a><a href="https://b.com">B</a></body></html>'

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value=html)

        with patch("spide.mcp.search_provider.aiohttp.ClientSession",
                    return_value=self._mock_aiohttp_session(mock_resp)):
            page = await WebContentProvider.fetch_page("https://example.com", extract_links=True)

        assert "https://a.com" in page.links
        assert "https://b.com" in page.links


class TestRepoInfoProvider:
    """RepoInfoProvider 测试."""

    async def test_fetch_repo_summary(self):
        with patch.object(RepoInfoProvider, "fetch_repo_info") as mock_fetch:
            mock_fetch.return_value = RepoInfo(
                repo="test/repo",
                description="A test",
                stars=50,
                language="Go",
                readme="# Hello\nWorld",
            )

            result = await RepoInfoProvider.fetch_repo_summary("test/repo")
            assert result["repo"] == "test/repo"
            assert result["stars"] == 50
            assert "# Hello" in result["readme_preview"]
