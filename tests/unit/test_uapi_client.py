# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — UAPI 热搜客户端."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.config import UAPIConfig
from spide.exceptions import SpiderError
from spide.spider.uapi_client import _PLATFORM_MAP, UAPIClient, _extract_platform


class TestPlatformMapping:
    """平台映射."""

    def test_known_platforms(self):
        assert _PLATFORM_MAP["weibo"].value == "weibo"
        assert _PLATFORM_MAP["baidu"].value == "baidu"
        assert _PLATFORM_MAP["douyin"].value == "douyin"
        assert _PLATFORM_MAP["zhihu"].value == "zhihu"
        assert _PLATFORM_MAP["bilibili"].value == "bilibili"

    def test_extract_platform(self):
        assert _extract_platform("/social/weibo/hot") == "weibo"
        assert _extract_platform("/social/baidu/hot") == "baidu"
        assert _extract_platform("weibo") == "weibo"

    def test_extract_unknown(self):
        assert _extract_platform("/social/unknown/hot") == "unknown"


class TestUAPIClientMock:
    """UAPI 客户端 mock 测试."""

    async def test_fetch_hotboard(self, mock_aiohttp_response):
        config = UAPIConfig(api_key="test")
        client = UAPIClient(config)
        await client.start()

        mock_resp_data = {
            "type": "weibo",
            "list": [
                {"title": "热搜1", "hot_value": "999", "index": 1},
                {"title": "热搜2", "hot_value": "888", "index": 2},
            ],
        }

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_resp_data)

        mock_get = mock_aiohttp_response(mock_resp)
        with patch("aiohttp.ClientSession.get", new=mock_get):
            topics = await client.fetch_hotboard("weibo")
            assert len(topics) == 2
            assert topics[0].title == "热搜1"

        await client.stop()

    async def test_http_error(self, mock_aiohttp_response):
        config = UAPIConfig(api_key="test")
        client = UAPIClient(config)
        await client.start()

        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="Server Error")

        mock_get = mock_aiohttp_response(mock_resp)
        with patch("aiohttp.ClientSession.get", new=mock_get), \
             pytest.raises(SpiderError, match="500"):
            await client.fetch_hotboard("weibo")

        await client.stop()

    async def test_not_started(self):
        client = UAPIClient(UAPIConfig())
        with pytest.raises(SpiderError, match="未初始化"):
            await client.fetch_hotboard("weibo")

    async def test_concurrency_limit(self):
        config = UAPIConfig(api_key="test", rate_limit={"max_concurrent": 2})
        client = UAPIClient(config)
        assert client._rate_limiter._semaphore._value == 2
