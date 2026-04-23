# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""GitHub Trending 爬虫客户端.

用法:
    from spide.spider.github_client import GitHubClient

    client = GitHubClient()
    await client.start()

    # 获取 GitHub Trending
    trending = await client.fetch_trending(language="")

    # 获取 AI 相关热门项目
    ai_projects = await client.fetch_ai_projects()

    await client.stop()
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicSource

logger = get_logger(__name__)

# GitHub Trending URL
TRENDING_URL = "https://github.com/trending"
SEARCH_URL = "https://api.github.com/search/repositories"


class GitHubClient:
    """GitHub Trending 数据采集客户端."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """初始化 HTTP 会话."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SpideHarness/1.0",
        }
        self._session = aiohttp.ClientSession(headers=headers)

    async def stop(self) -> None:
        """关闭 HTTP 会话."""
        if self._session:
            await self._session.close()

    async def fetch_trending(
        self,
        language: str = "",
        since: str = "daily",
    ) -> list[dict[str, Any]]:
        """获取 GitHub Trending 榜单.

        Args:
            language: 编程语言筛选 (e.g., "python", "typescript", "")
            since: 时间范围 (daily, weekly, monthly)

        Returns:
            Trending 项目列表
        """
        url = f"{TRENDING_URL}?since={since}"
        if language:
            url += f"&spoken_language_code="

        logger.info("fetching_github_trending", url=url)

        async with self._session.get(url) as resp:
            resp.raise_for_status()
            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article.box-border")

        results = []
        for i, article in enumerate(articles[:25], 1):
            # 项目名和作者
            title_elem = article.select_one("h2 a")
            if not title_elem:
                continue

            full_name = title_elem.get("href", "").strip("/")
            repo_name = full_name.split("/")[-1] if "/" in full_name else full_name

            # 描述
            desc_elem = article.select_one("p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # 星级
            star_elem = article.select_one("a.Link--secondary")
            stars_text = star_elem.get_text(strip=True) if star_elem else "0"
            stars = self._parse_number(stars_text)

            # Fork 数
            fork_elem = article.select_one("span[data-view-component=true].d-inline-block")
            fork_text = fork_elem.get_text(strip=True) if fork_elem else "0"
            forks = self._parse_number(fork_text)

            # 语言
            lang_elem = article.select_one("span[itemprop=programmingLanguage]")
            lang = lang_elem.get_text(strip=True) if lang_elem else ""

            results.append({
                "title": f"{full_name}",
                "repo_name": repo_name,
                "description": description,
                "stars": stars,
                "forks": forks,
                "language": lang,
                "url": f"https://github.com/{full_name}",
                "rank": i,
                "hot_value": stars,
            })

        logger.info("github_trending_fetched", count=len(results))
        return results

    async def fetch_ai_projects(
        self,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """获取 AI 相关热门项目 (通过 GitHub API 搜索).

        Args:
            limit: 返回数量

        Returns:
            AI 相关项目列表
        """
        # 使用 GitHub API 搜索 AI 相关项目
        query = "AI OR artificial-intelligence OR machine-learning OR LLM OR GPT"
        url = f"{SEARCH_URL}?q={query}&sort=stars&order=desc&per_page={limit}"

        logger.info("fetching_ai_projects", url=url)

        async with self._session.get(url) as resp:
            if resp.status == 403:
                logger.warning("github_api_rate_limit")
                # 回退到爬取页面
                return await self._fetch_ai_from_page(limit)
            resp.raise_for_status()
            data = await resp.json()

        items = data.get("items", [])[:limit]
        results = []

        for i, item in enumerate(items, 1):
            results.append({
                "title": item.get("full_name", ""),
                "repo_name": item.get("name", ""),
                "description": item.get("description", ""),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "language": item.get("language", ""),
                "url": item.get("html_url", ""),
                "rank": i,
                "hot_value": item.get("stargazers_count", 0),
            })

        logger.info("ai_projects_fetched", count=len(results))
        return results

    async def _fetch_ai_from_page(
        self,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """从搜索页面获取 AI 项目 (API 限流时的备选方案)."""
        # 爬取 GitHub 搜索结果页面
        search_page_url = "https://github.com/search?q=AI+machine-learning+LLM&type=repositories"

        async with self._session.get(search_page_url) as resp:
            resp.raise_for_status()
            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        repos = soup.select("div[data-testid=results-list] > div")

        results = []
        for i, repo in enumerate(repos[:limit], 1):
            title_elem = repo.select_one("a[data-testid=results-list-item-title]")
            if not title_elem:
                continue

            full_name = title_elem.get("href", "").strip("/")

            # 描述
            desc_elem = repo.select_one("p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # 星级
            star_elem = repo.select_one("a[href$=/stargazers]")
            stars_text = star_elem.get_text(strip=True) if star_elem else "0"
            stars = self._parse_number(stars_text)

            results.append({
                "title": full_name,
                "repo_name": full_name.split("/")[-1] if "/" in full_name else full_name,
                "description": description,
                "stars": stars,
                "forks": 0,
                "language": "",
                "url": f"https://github.com/{full_name}",
                "rank": i,
                "hot_value": stars,
            })

        return results

    def _parse_number(self, text: str) -> int:
        """解析数字字符串 (如 "1.2k", "3.4M")."""
        text = text.strip().upper().replace(",", "")
        if not text:
            return 0

        multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    return int(float(text.replace(suffix, "")) * mult)
                except ValueError:
                    return 0

        try:
            return int(text)
        except ValueError:
            return 0

    def to_hot_topics(
        self,
        projects: list[dict[str, Any]],
        source: str = "github",
    ) -> list[HotTopic]:
        """转换为 HotTopic 数据模型."""
        now = datetime.utcnow()
        topics = []

        for p in projects:
            topic = HotTopic(
                title=p.get("title", ""),
                source=source,
                hot_value=p.get("hot_value", 0) or p.get("stars", 0),
                url=p.get("url", ""),
                rank=p.get("rank"),
                category="tech",
                summary=p.get("description", ""),
                fetched_at=now,
            )
            topics.append(topic)

        return topics
