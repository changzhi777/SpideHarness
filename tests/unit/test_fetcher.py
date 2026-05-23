# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 异步页面抓取器."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.exceptions import SpiderError
from spide.spider.fetcher import AsyncFetcher


def _mock_aiohttp_get(resp):
    """构建 aiohttp ClientSession.get mock."""
    get_cm = MagicMock()
    get_cm.__aenter__ = AsyncMock(return_value=resp)
    get_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get.return_value = get_cm
    return session


class TestFetcherMock:
    """Fetcher mock 测试."""

    async def test_get_html(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="<html><body><h1>标题</h1><p>正文</p></body></html>")

        with patch("aiohttp.ClientSession.get", new=_mock_aiohttp_get(mock_resp).get):
            result = await fetcher.get("https://example.com")
            assert "<h1>标题</h1>" in result

        await fetcher.stop()

    async def test_get_text_strips_tags(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value="<html><body><script>alert('xss')</script><p>内容</p></body></html>")

        with patch("aiohttp.ClientSession.get", new=_mock_aiohttp_get(mock_resp).get):
            text = await fetcher.get_text("https://example.com")
            assert "内容" in text
            assert "alert" not in text

        await fetcher.stop()

    async def test_get_json(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        data = {"key": "value", "count": 42}
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=data)

        with patch("aiohttp.ClientSession.get", new=_mock_aiohttp_get(mock_resp).get):
            result = await fetcher.get_json("https://api.example.com/data")
            assert result["count"] == 42

        await fetcher.stop()

    async def test_http_error(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        mock_resp = MagicMock()
        mock_resp.status = 404

        with patch("aiohttp.ClientSession.get", new=_mock_aiohttp_get(mock_resp).get):
            with pytest.raises(SpiderError, match="404"):
                await fetcher.get("https://example.com/notfound")

        await fetcher.stop()

    async def test_not_started(self):
        fetcher = AsyncFetcher()
        with pytest.raises(SpiderError, match="未初始化"):
            await fetcher.get("https://example.com")
