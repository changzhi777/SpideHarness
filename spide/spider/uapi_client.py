# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""UAPI 热搜客户端 — 基于 aiohttp 直接调用 REST API.

用法:
    from spide.spider.uapi_client import UAPIClient
    from spide.config import load_settings

    settings = load_settings()
    client = UAPIClient(settings.uapi)
    await client.start()

    # 获取微博热搜
    items = await client.fetch_hotboard("weibo")

    # 获取支持的平台列表
    sources = await client.fetch_sources()

    await client.stop()
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from spide.config import UAPIConfig
from spide.exceptions import SpiderError
from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicSource

logger = get_logger(__name__)

# UAPI 热搜平台 → TopicSource 映射
_PLATFORM_MAP: dict[str, TopicSource] = {
    "weibo": TopicSource.WEIBO,
    "baidu": TopicSource.BAIDU,
    "douyin": TopicSource.DOUYIN,
    "zhihu": TopicSource.ZHIHU,
    "bilibili": TopicSource.BILIBILI,
    "kuaishou": TopicSource.KUAISHOU,
    "tieba": TopicSource.TIEBA,
}

# UAPI 热搜 API 路径
_HOTBOARD_PATH = "/api/v1/misc/hotboard"


class UAPIClient:
    """UAPI 热搜数据采集客户端."""

    def __init__(self, config: UAPIConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(config.rate_limit.max_concurrent)

    async def start(self) -> None:
        """初始化 HTTP 会话."""
        base_url = self._config.base_url
        if not base_url.endswith("/"):
            base_url += "/"
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            timeout=aiohttp.ClientTimeout(total=self._config.timeout),
        )
        logger.debug("uapi_client_started", base_url=self._config.base_url)

    async def stop(self) -> None:
        """关闭 HTTP 会话."""
        if self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        """检查会话状态."""
        if self._session is None:
            raise SpiderError("UAPI 客户端未初始化，请先调用 start()")
        return self._session

    async def fetch_hotboard(
        self,
        platform: str,
        *,
        keyword: str | None = None,
        time_start: str | None = None,
        time_end: str | None = None,
        limit: int | None = None,
    ) -> list[HotTopic]:
        """采集热搜榜单.

        Args:
            platform: 平台标识 (weibo/baidu/douyin/zhihu/bilibili)
            keyword: 搜索关键词（搜索模式）
            time_start: 搜索起始时间
            time_end: 搜索结束时间
            limit: 返回数量限制

        Returns:
            热搜话题列表
        """
        session = self._ensure_session()
        source = _PLATFORM_MAP.get(platform, TopicSource.CUSTOM)

        params: dict[str, Any] = {"type": platform}
        if keyword:
            params["keyword"] = keyword
        if time_start:
            params["time_start"] = time_start
        if time_end:
            params["time_end"] = time_end
        if limit:
            params["limit"] = limit

        async with self._semaphore:
            try:
                async with session.get(_HOTBOARD_PATH, params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise SpiderError(
                            f"UAPI 热搜请求失败 [{resp.status}]: {text[:200]}"
                        )
                    data = await resp.json()
            except aiohttp.ClientError as e:
                raise SpiderError(f"UAPI 网络错误: {e}") from e

        # 解析响应
        items = data.get("list", [])
        topics: list[HotTopic] = []
        for item in items:
            topic = HotTopic(
                title=item.get("title", ""),
                source=source,
                hot_value=_parse_int(item.get("hot_value")),
                url=item.get("url"),
                rank=item.get("index"),
                extra=item.get("extra") or {},
            )
            topics.append(topic)

        logger.debug(
            "hotboard_fetched",
            platform=platform,
            count=len(topics),
            update_time=data.get("update_time"),
        )
        return topics

    async def fetch_sources(self) -> list[dict[str, Any]]:
        """获取支持的历史热搜平台列表."""
        session = self._ensure_session()

        async with self._semaphore:
            try:
                async with session.get(
                    _HOTBOARD_PATH, params={"sources": "true"}
                ) as resp:
                    if resp.status != 200:
                        raise SpiderError(f"获取平台列表失败 [{resp.status}]")
                    data = await resp.json()
            except aiohttp.ClientError as e:
                raise SpiderError(f"UAPI 网络错误: {e}") from e

        return data if isinstance(data, list) else data.get("sources", [])

    async def fetch_all(self) -> dict[str, list[HotTopic]]:
        """并发采集所有已配置的热搜源.

        Returns:
            平台标识 → 热搜话题列表
        """
        results: dict[str, list[HotTopic]] = {}

        # 预提取平台标识
        source_platforms = [
            (cfg, _extract_platform(cfg.endpoint))
            for cfg in self._config.hot_sources
        ]

        tasks = [
            self._fetch_with_retry(platform, cfg.name)
            for cfg, platform in source_platforms
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for (_, platform), result in zip(source_platforms, responses, strict=False):
            if isinstance(result, Exception):
                logger.error("fetch_all_error", platform=platform, error=str(result))
                results[platform] = []
            else:
                results[platform] = result  # type: ignore[assignment]

        return results

    async def _fetch_with_retry(
        self, platform: str, name: str, max_retries: int | None = None
    ) -> list[HotTopic]:
        """带重试的单平台采集."""
        retries = max_retries or self._config.retry.max_retries
        base_delay = self._config.retry.backoff_base

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                return await self.fetch_hotboard(platform)
            except SpiderError as e:
                last_error = e
                if attempt < retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "fetch_retry",
                        platform=platform,
                        attempt=attempt + 1,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

        raise SpiderError(f"采集 {name}({platform}) 失败: {last_error}")


def _parse_int(value: Any) -> int | None:
    """安全地将 hot_value 转为整数."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _extract_platform(endpoint: str) -> str:
    """从 endpoint 路径提取平台标识.
    例: /social/weibo/hot → weibo
    """
    parts = endpoint.strip("/").split("/")
    return parts[-2] if len(parts) >= 2 else parts[-1]
