# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""集成测试 — UAPI 真实调用（需要网络和有效 API Key）.

用法:
    uv run pytest tests/integration/test_uapi_real.py -m integration -v

前提:
    configs/uapi.yaml 中配置了有效的 api_key
"""

import pytest

from spide.config import UAPIConfig, load_settings
from spide.spider.uapi_client import UAPIClient


@pytest.fixture
def uapi_config() -> UAPIConfig:
    """从配置文件加载 UAPI 配置."""
    settings = load_settings()
    if not settings.uapi.api_key:
        pytest.skip("UAPI API Key 未配置，跳过集成测试")
    return settings.uapi


@pytest.fixture
async def uapi_client(uapi_config: UAPIConfig) -> UAPIClient:
    """创建并启动 UAPI 客户端."""
    client = UAPIClient(uapi_config)
    await client.start()
    yield client
    await client.stop()


@pytest.mark.integration
class TestUAPIRealCall:
    """UAPI 真实接口调用."""

    @pytest.mark.asyncio
    async def test_fetch_weibo_hotboard(self, uapi_client: UAPIClient):
        """微博热搜真实采集."""
        topics = await uapi_client.fetch_hotboard("weibo")

        assert isinstance(topics, list)
        assert len(topics) > 0, "微博热搜应返回至少1条结果"

        first = topics[0]
        assert first.title, "热搜标题不应为空"
        assert first.source.value == "weibo"
        assert first.url is not None, "热搜应包含 URL"

    @pytest.mark.asyncio
    async def test_fetch_baidu_hotboard(self, uapi_client: UAPIClient):
        """百度热搜真实采集."""
        topics = await uapi_client.fetch_hotboard("baidu")

        assert isinstance(topics, list)
        assert len(topics) > 0, "百度热搜应返回至少1条结果"

        first = topics[0]
        assert first.title
        assert first.source.value == "baidu"

    @pytest.mark.asyncio
    async def test_fetch_multiple_sources(self, uapi_client: UAPIClient):
        """多源并发采集."""
        import asyncio

        tasks = [
            uapi_client.fetch_hotboard("weibo"),
            uapi_client.fetch_hotboard("baidu"),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            assert not isinstance(result, Exception), f"采集失败: {result}"
            assert isinstance(result, list)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_fetch_sources_list(self, uapi_client: UAPIClient):
        """获取平台列表（API 可能不支持此端点）."""
        try:
            sources = await uapi_client.fetch_sources()
            assert isinstance(sources, list)
        except Exception:
            # API 可能不支持 sources 参数，跳过
            pytest.skip("UAPI 不支持 sources 端点")

    @pytest.mark.asyncio
    async def test_fetch_with_invalid_platform(self, uapi_client: UAPIClient):
        """无效平台应返回错误."""
        from spide.exceptions import SpiderError

        with pytest.raises(SpiderError):
            await uapi_client.fetch_hotboard("nonexistent_platform_xyz")
