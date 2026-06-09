# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""搜索适配器层 — 统一封装网页搜索、内容抓取、仓库信息.

用法:
    from spide.mcp.search_provider import WebSearchProvider, WebContentProvider, RepoInfoProvider

    # 网页搜索
    provider = WebSearchProvider()
    results = await provider.search("Python asyncio", limit=10)

    # 网页抓取
    content = await WebContentProvider.fetch_page("https://example.com")

    # 仓库信息
    readme = await RepoInfoProvider.fetch_readme("zhipu/zai-sdk-python")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from spide.logging import get_logger

logger = get_logger(__name__)

# DuckDuckGo HTML 搜索 URL
_DDGS_URL = "https://html.duckduckgo.com/html/"
# GitHub REST API
_GITHUB_API = "https://api.github.com"
# 请求超时
_TIMEOUT = aiohttp.ClientTimeout(total=15)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """搜索结果条目."""

    title: str = ""
    url: str = ""
    description: str = ""
    source: str = ""


@dataclass
class PageContent:
    """网页内容."""

    url: str = ""
    title: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)


@dataclass
class RepoInfo:
    """仓库信息."""

    repo: str = ""
    description: str = ""
    stars: int = 0
    language: str = ""
    readme: str = ""


# ---------------------------------------------------------------------------
# WebSearchProvider — 多引擎网页搜索
# ---------------------------------------------------------------------------


class WebSearchProvider:
    """网页搜索 — DuckDuckGo HTML + 可选智谱 Web Search."""

    async def search(
        self,
        query: str,
        *,
        engine: str = "duckduckgo",
        limit: int = 10,
    ) -> list[SearchResult]:
        """执行网页搜索.

        Args:
            query: 搜索关键词
            engine: 搜索引擎 (duckduckgo)
            limit: 返回数量上限

        Returns:
            SearchResult 列表
        """
        if engine == "duckduckgo":
            return await self._search_ddgs(query, limit)
        return []

    async def _search_ddgs(self, query: str, limit: int) -> list[SearchResult]:
        """DuckDuckGo HTML 搜索."""
        results: list[SearchResult] = []
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session, session.post(
                _DDGS_URL,
                data={"q": query, "b": ""},
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SpideAgent/1.0)",
                },
            ) as resp:
                if resp.status != 200:
                    logger.warning("ddgs_search_failed", status=resp.status)
                    return results

                html = await resp.text()
                results = self._parse_ddgs_html(html, limit)

        except Exception as e:
            logger.warning("ddgs_search_error", error=str(e))

        logger.debug("web_search_done", engine="duckduckgo", query=query[:50], count=len(results))
        return results

    @staticmethod
    def _parse_ddgs_html(html: str, limit: int) -> list[SearchResult]:
        """解析 DuckDuckGo HTML 搜索结果."""
        results: list[SearchResult] = []

        # 提取结果块
        blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
            r'.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )

        for url, title_html, desc_html in blocks[:limit]:
            title = _strip_html(title_html).strip()
            desc = _strip_html(desc_html).strip()
            if title and url:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    description=desc,
                    source="duckduckgo",
                ))

        return results


# ---------------------------------------------------------------------------
# WebContentProvider — 网页内容抓取
# ---------------------------------------------------------------------------


class WebContentProvider:
    """网页内容抓取 — aiohttp + HTML 文本提取."""

    @staticmethod
    async def fetch_page(
        url: str,
        *,
        extract_links: bool = False,
        max_length: int = 10000,
    ) -> PageContent:
        """抓取网页内容.

        Args:
            url: 目标 URL
            extract_links: 是否提取链接
            max_length: 正文最大长度

        Returns:
            PageContent
        """
        page = PageContent(url=url)
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session, session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; SpideAgent/1.0)"},
            ) as resp:
                if resp.status != 200:
                    logger.warning("fetch_page_failed", url=url, status=resp.status)
                    return page

                html = await resp.text()

            # 提取 title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
            if title_match:
                page.title = _strip_html(title_match.group(1)).strip()

            # 提取正文
            body = _extract_body(html)
            page.text = _strip_html(body)[:max_length]

            # 提取链接
            if extract_links:
                links = re.findall(r'href="(https?://[^"]+)"', html)
                page.links = links[:50]

        except Exception as e:
            logger.warning("fetch_page_error", url=url, error=str(e))

        return page

    @staticmethod
    async def fetch_github_readme(repo: str) -> str:
        """获取 GitHub 仓库 README.

        Args:
            repo: 仓库路径 (owner/repo)

        Returns:
            README 文本（Markdown）
        """
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                url = f"{_GITHUB_API}/repos/{repo}/readme"
                async with session.get(
                    url,
                    headers={
                        "Accept": "application/vnd.github.raw+json",
                        "User-Agent": "SpideAgent/1.0",
                    },
                ) as resp:
                    if resp.status != 200:
                        logger.warning("github_readme_failed", repo=repo, status=resp.status)
                        return ""
                    return await resp.text()

        except Exception as e:
            logger.warning("github_readme_error", repo=repo, error=str(e))
            return ""


# ---------------------------------------------------------------------------
# RepoInfoProvider — 开源仓库信息
# ---------------------------------------------------------------------------


class RepoInfoProvider:
    """开源仓库信息 — GitHub API + README."""

    @staticmethod
    async def fetch_repo_info(repo: str) -> RepoInfo:
        """获取仓库元数据 + README.

        Args:
            repo: 仓库路径 (owner/repo)

        Returns:
            RepoInfo
        """
        info = RepoInfo(repo=repo)
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                # 仓库元数据
                async with session.get(
                    f"{_GITHUB_API}/repos/{repo}",
                    headers={"User-Agent": "SpideAgent/1.0"},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        info.description = data.get("description", "") or ""
                        info.stars = data.get("stargazers_count", 0)
                        info.language = data.get("language", "") or ""

                # README
                readme = await WebContentProvider.fetch_github_readme(repo)
                info.readme = readme[:5000]

        except Exception as e:
            logger.warning("repo_info_error", repo=repo, error=str(e))

        return info

    @staticmethod
    async def fetch_repo_summary(repo: str) -> dict[str, Any]:
        """获取仓库摘要（元数据 + README 前 1000 字符）."""
        info = await RepoInfoProvider.fetch_repo_info(repo)
        return {
            "repo": info.repo,
            "description": info.description,
            "stars": info.stars,
            "language": info.language,
            "readme_preview": info.readme[:1000],
        }


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _strip_html(html: str) -> str:
    """去除 HTML 标签，保留文本."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body(html: str) -> str:
    """提取 body 标签内容."""
    match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # 移除 head/style/script
    text = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text
