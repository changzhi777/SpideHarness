# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""异步页面抓取器 — aiohttp + BeautifulSoup.

用法:
    from spide.spider.fetcher import AsyncFetcher

    fetcher = AsyncFetcher()
    await fetcher.start()
    html = await fetcher.get("https://example.com")
    text = await fetcher.get_text("https://example.com")
    await fetcher.stop()
"""

from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup

from spide.exceptions import SpiderError
from spide.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class AsyncFetcher:
    """异步 HTTP 抓取器."""

    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> None:
        self._headers = {**_DEFAULT_HEADERS, **(headers or {})}
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """初始化 HTTP 会话."""
        self._session = aiohttp.ClientSession(
            headers=self._headers,
            timeout=self._timeout,
        )
        logger.debug("fetcher_started")

    async def stop(self) -> None:
        """关闭 HTTP 会话."""
        if self._session:
            await self._session.close()
            self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise SpiderError("Fetcher 未初始化，请先调用 start()")
        return self._session

    async def get(self, url: str, **kwargs: object) -> str:
        """获取 URL 的原始 HTML 内容."""
        session = self._ensure_session()
        try:
            async with session.get(url, **kwargs) as resp:
                if resp.status != 200:
                    raise SpiderError(f"HTTP {resp.status}: {url}")
                return await resp.text()
        except aiohttp.ClientError as e:
            raise SpiderError(f"请求失败 {url}: {e}") from e

    async def get_text(self, url: str, **kwargs: object) -> str:
        """获取 URL 的纯文本内容（去除 HTML 标签）."""
        html = await self.get(url, **kwargs)
        soup = BeautifulSoup(html, "html.parser")
        # 移除 script 和 style
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    async def get_json(self, url: str, **kwargs: object) -> dict:
        """获取 URL 的 JSON 响应."""
        session = self._ensure_session()
        try:
            async with session.get(url, **kwargs) as resp:
                if resp.status != 200:
                    raise SpiderError(f"HTTP {resp.status}: {url}")
                return await resp.json()
        except aiohttp.ClientError as e:
            raise SpiderError(f"请求失败 {url}: {e}") from e
