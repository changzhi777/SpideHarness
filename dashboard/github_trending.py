"""GitHub AI 热点采集 — 采集 AI/LLM/Agent/MCP/MLX 相关热门仓库，格式化为飞书卡片推送.

用法:
    from dashboard.github_trending import GitHubTrendingService

    svc = GitHubTrendingService(feishu_webhook_url="https://...")
    repos = await svc.collect()
    ok = await svc.push_to_feishu(repos)

    # 或一键执行
    result = await svc.run()  # 采集 + 推送
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import aiohttp

from spide.logging import get_logger

logger = get_logger(__name__)

_GITHUB_API = "https://api.github.com"
_GITHUB_SEARCH = f"{_GITHUB_API}/search/repositories"
_TIMEOUT = aiohttp.ClientTimeout(total=20)
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "SpideAgent/3.1",
}

# 关注的技术方向关键词
TOPIC_QUERIES: list[dict[str, str]] = [
    {"topic": "AI 人工智能", "query": "topic:ai+topic:agent&sort=stars&order=desc&per_page=5"},
    {
        "topic": "大模型 LLM",
        "query": "topic:llm+topic:large-language-model&sort=stars&order=desc&per_page=5",
    },
    {"topic": "Agent 智能体", "query": "topic:ai-agent&sort=stars&order=desc&per_page=5"},
    {
        "topic": "MCP 协议",
        "query": "topic:mcp+topic:model-context-protocol&sort=stars&order=desc&per_page=5",
    },
    {"topic": "MLX 苹果AI", "query": "topic:mlx&sort=stars&order=desc&per_page=5"},
]

# 备用：最近7天高星项目（GitHub trending 效果）
TRENDING_QUERIES: list[dict[str, str]] = [
    {
        "topic": "AI Agent 热门",
        "query": "ai+agent&sort=stars&order=desc&q=created:>2026-05-20&per_page=8",
    },
    {
        "topic": "LLM 新项目",
        "query": "llm+language+model&sort=stars&order=desc&q=created:>2026-05-20&per_page=8",
    },
    {
        "topic": "MCP 新项目",
        "query": "mcp+model+context+protocol&sort=stars&order=desc&q=created:>2026-05-20&per_page=5",
    },
    {
        "topic": "MLX 新项目",
        "query": "mlx+apple&sort=stars&order=desc&q=created:>2026-05-20&per_page=5",
    },
]


@dataclass
class GitHubRepo:
    """GitHub 仓库信息."""

    full_name: str = ""
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    html_url: str = ""
    topics: list[str] = field(default_factory=list)
    updated_at: str = ""
    category: str = ""  # 采集分类

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "html_url": self.html_url,
            "topics": self.topics,
            "updated_at": self.updated_at,
            "category": self.category,
        }


class GitHubTrendingService:
    """GitHub AI 热点采集与飞书推送."""

    def __init__(self, *, feishu_webhook_url: str = "") -> None:
        self._feishu_url = feishu_webhook_url
        self._seen_repos: set[str] = set()

    async def collect(self) -> list[GitHubRepo]:
        """采集各方向的 GitHub 热门仓库（去重）."""
        all_repos: list[GitHubRepo] = []

        async with aiohttp.ClientSession(timeout=_TIMEOUT, headers=_HEADERS) as session:
            for q in TOPIC_QUERIES:
                repos = await self._search(session, q["query"], category=q["topic"])
                all_repos.extend(repos)

            for q in TRENDING_QUERIES:
                repos = await self._search(session, q["query"], category=q["topic"])
                all_repos.extend(repos)

        # 去重（同一仓库可能出现在多个查询中）
        seen: set[str] = set()
        unique: list[GitHubRepo] = []
        for r in all_repos:
            if r.full_name not in seen:
                seen.add(r.full_name)
                unique.append(r)

        # 按星数排序
        unique.sort(key=lambda r: r.stars, reverse=True)

        logger.info("github_trending_collected", total=len(unique))
        return unique

    async def _search(
        self,
        session: aiohttp.ClientSession,
        query: str,
        category: str = "",
    ) -> list[GitHubRepo]:
        """执行 GitHub Search API 查询."""
        repos: list[GitHubRepo] = []
        url = f"{_GITHUB_SEARCH}?q={query}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    for item in items[:10]:
                        repo = GitHubRepo(
                            full_name=item.get("full_name", ""),
                            description=item.get("description", "") or "",
                            stars=item.get("stargazers_count", 0),
                            forks=item.get("forks_count", 0),
                            language=item.get("language", "") or "",
                            html_url=item.get("html_url", ""),
                            topics=item.get("topics", []),
                            updated_at=item.get("updated_at", "")[:10],
                            category=category,
                        )
                        repos.append(repo)
                elif resp.status == 403:
                    logger.warning("github_rate_limit")
                else:
                    logger.warning("github_search_failed", status=resp.status, query=query[:50])
        except Exception as e:
            logger.warning("github_search_error", error=str(e), query=query[:50])

        return repos

    def format_feishu_card(self, repos: list[GitHubRepo]) -> dict[str, Any]:
        """将采集结果格式化为飞书消息卡片."""
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        # 分组
        categories: dict[str, list[GitHubRepo]] = {}
        for r in repos:
            cat = r.category or "其他"
            categories.setdefault(cat, []).append(r)

        elements: list[dict[str, Any]] = []

        # 概览
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"共采集 **{len(repos)}** 个热门仓库，分为 **{len(categories)}** 个方向",
                },
            }
        )
        elements.append({"tag": "hr"})

        # 每个分类一个区块
        for cat, cat_repos in categories.items():
            lines = [f"**{cat}**"]
            for r in cat_repos[:5]:
                desc = (r.description[:60] + "...") if len(r.description) > 60 else r.description
                lines.append(
                    f"- [{r.full_name}]({r.html_url})  ⭐ {r.stars:,}  🍴 {r.forks:,}\n  {desc}"
                )
            elements.append(
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "\n".join(lines)},
                }
            )

        # 底部
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"SpideHarness GitHub Trending | {now}",
                    },
                ],
            }
        )

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"GitHub AI 热点日报 | {datetime.now().strftime('%Y-%m-%d')}",
                    },
                    "template": "blue",
                },
                "elements": elements,
            },
        }
        return card

    async def push_to_feishu(self, repos: list[GitHubRepo]) -> bool:
        """推送采集结果到飞书 Webhook."""
        if not self._feishu_url:
            logger.warning("feishu_webhook_not_configured")
            return False

        card = self.format_feishu_card(repos)

        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
                session.post(self._feishu_url, json=card) as resp,
            ):
                body = await resp.text()
                if resp.status >= 400:
                    logger.warning("feishu_push_failed", status=resp.status, body=body[:200])
                    return False
                logger.info("feishu_push_ok", repos=len(repos))
                return True
        except Exception as e:
            logger.warning("feishu_push_error", error=str(e))
            return False

    async def run(self) -> dict[str, Any]:
        """一键采集 + 推送."""
        repos = await self.collect()
        pushed = False
        if self._feishu_url and repos:
            pushed = await self.push_to_feishu(repos)
        return {
            "total_repos": len(repos),
            "pushed_to_feishu": pushed,
            "repos": [r.to_dict() for r in repos[:20]],
        }
