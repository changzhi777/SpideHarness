# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 异步页面抓取器."""

from unittest.mock import AsyncMock, patch

import pytest

from spide.exceptions import SpiderError
from spide.spider.fetcher import AsyncFetcher


class TestFetcherMock:
    """Fetcher mock 测试."""

    @pytest.mark.asyncio
    async def test_get_html(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        html = "<html><body><h1>标题</h1><p>正文</p></body></html>"
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=html)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            result = await fetcher.get("https://example.com")
            assert "<h1>标题</h1>" in result

        await fetcher.stop()

    @pytest.mark.asyncio
    async def test_get_text_strips_tags(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        html = "<html><body><script>alert('xss')</script><p>内容</p></body></html>"
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=html)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            text = await fetcher.get_text("https://example.com")
            assert "内容" in text
            assert "alert" not in text

        await fetcher.stop()

    @pytest.mark.asyncio
    async def test_get_json(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        data = {"key": "value", "count": 42}
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=data)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            result = await fetcher.get_json("https://api.example.com/data")
            assert result["count"] == 42

        await fetcher.stop()

    @pytest.mark.asyncio
    async def test_http_error(self):
        fetcher = AsyncFetcher()
        await fetcher.start()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 404
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            with pytest.raises(SpiderError, match="404"):
                await fetcher.get("https://example.com/notfound")

        await fetcher.stop()

    @pytest.mark.asyncio
    async def test_not_started(self):
        fetcher = AsyncFetcher()
        with pytest.raises(SpiderError, match="未初始化"):
            await fetcher.get("https://example.com")
