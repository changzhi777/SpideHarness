# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""URL 元数据抓取 — Open Graph / HTML meta 解析.

用于视频 pipeline：从用户分享的 URL 抓取标题/描述/缩略图。

Usage:
    from spide.integrations.url_metadata import fetch

    meta = await fetch("https://www.bilibili.com/video/BV1xx")
    # → {"title": "...", "description": "...", "image": "...", "site_name": "..."}
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from spide.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=15)
_MAX_HTML_BYTES = 2 * 1024 * 1024  # 2MB 限制（防巨大页面）


async def fetch(url: str, *, session: aiohttp.ClientSession | None = None) -> dict[str, Any]:
    """抓取 URL 的 Open Graph / meta 元数据.

    Args:
        url: 目标 URL（需含 http(s)://）
        session: 可选复用 session（None 时创建临时 session）

    Returns:
        {title, description, image, site_name, url} — 缺失字段为空字符串
        失败时返回 {"url": url, "error": "..."}
    """
    if not url.startswith(("http://", "https://")):
        return {"url": url, "error": "URL 必须以 http:// 或 https:// 开头"}

    own_session = session is None
    sess = session or aiohttp.ClientSession(timeout=_TIMEOUT)
    try:
        try:
            async with sess.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return {"url": url, "error": f"HTTP {resp.status}"}
                # 限制下载大小
                content = await resp.content.read(_MAX_HTML_BYTES)
                content_type = resp.headers.get("Content-Type", "")
        except aiohttp.ClientError as e:
            return {"url": url, "error": f"网络错误: {e}"}
        except TimeoutError:
            return {"url": url, "error": "请求超时"}

        if "html" not in content_type.lower():
            return {"url": url, "error": f"非 HTML 内容: {content_type}"}

        return _parse_html(content, url)
    finally:
        if own_session:
            await sess.close()


def _parse_html(html_bytes: bytes, url: str) -> dict[str, Any]:
    """从 HTML 字节提取 Open Graph / meta 元数据."""
    try:
        soup = BeautifulSoup(html_bytes, "html.parser")
    except Exception as e:
        return {"url": url, "error": f"HTML 解析失败: {e}"}

    def _meta(prop: str, attr: str = "content") -> str:
        """查 og:prop / twitter:prop / name=prop 三种 meta 形式."""
        for m in soup.find_all("meta"):
            if m.get("property") == prop or m.get("name") == prop:
                value: Any = m.get(attr)
                return str(value or "").strip()
        return ""

    title = (
        _meta("og:title")
        or _meta("twitter:title")
        or ""
    )
    # 兜底：<title> 标签（bs4 stubs 推断 string 为 str | AttributeValueList）
    if not title and soup.title and soup.title.string:
        title_raw: Any = soup.title.string
        title = str(title_raw).strip()[:500]
    description = (
        _meta("og:description")
        or _meta("twitter:description")
        or _meta("description")
    )
    image = _meta("og:image") or _meta("twitter:image")
    site_name = _meta("og:site_name") or _meta("application-name")

    # 相对 URL 转绝对
    if image and not image.startswith(("http://", "https://")):
        try:
            base = urlparse(url)
            image = f"{base.scheme}://{base.netloc}{image if image.startswith('/') else '/' + image}"
        except Exception:
            image = ""

    return {
        "url": url,
        "title": title[:500],  # 防超长
        "description": description[:2000],
        "image": image[:1000],
        "site_name": site_name[:200],
    }
