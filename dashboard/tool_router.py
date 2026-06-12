"""工具路由器 — 将 MCP 工具映射为本地可异步调用的函数。

8 个 MCP 工具：
- crawl_hot_topics / web_search / web_search_enhanced / fetch_web_page
- fetch_repo_info / manage_memory / health_check / deep_crawl_hot_topics

路由策略：直接复用 spide 内部模块（无 subprocess 开销），失败回退到 spide CLI subprocess。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── 工具实现 ──────────────────────────────────────────────────────


async def _tool_crawl_hot_topics(args: dict[str, Any]) -> dict[str, Any]:
    """采集热搜（直接调用 UAPIClient）。"""
    source = args.get("source", "weibo")
    save = bool(args.get("save", False))

    try:
        from spide.config import load_settings
        from spide.spider.uapi_client import UAPIClient

        settings = load_settings()
        client = UAPIClient(settings=settings)
        items = await client.fetch_hotboard(source=source)
        items = items[:20]

        if save:
            from spide.storage.sqlite_repo import SQLiteRepo

            repo = SQLiteRepo(settings.storage.sqlite_path)
            await repo.init()
            await repo.save_topics(items)

        return {
            "status": "ok",
            "source": source,
            "count": len(items),
            "items": [
                {
                    "rank": getattr(t, "rank", i + 1),
                    "title": t.title,
                    "hot_value": getattr(t, "hot_value", 0),
                }
                for i, t in enumerate(items)
            ],
        }
    except Exception as exc:
        logger.warning("crawl_tool_failed", error=str(exc))
        return await _fallback_cli(["crawl", "-s", source] + (["--save"] if save else []))


async def _tool_web_search(args: dict[str, Any]) -> dict[str, Any]:
    """智谱联网搜索。"""
    query = args.get("query", "")
    if not query:
        return {"status": "error", "message": "query 不能为空"}
    engine = args.get("engine", "search_pro")
    count = int(args.get("count", 10))

    try:
        from spide.config import load_settings
        from spide.llm import LLMClient

        settings = load_settings()
        client = LLMClient(settings=settings)
        results = await client.web_search(query=query, engine=engine, count=count)
        return {"status": "ok", "query": query, "results": results}
    except Exception as exc:
        logger.warning("web_search_failed", error=str(exc))
        return {"status": "error", "message": str(exc)}


async def _tool_web_search_enhanced(args: dict[str, Any]) -> dict[str, Any]:
    """增强联网搜索（DuckDuckGo / Zhipu）。"""
    query = args.get("query", "")
    if not query:
        return {"status": "error", "message": "query 不能为空"}
    engine = args.get("engine", "duckduckgo")
    limit = int(args.get("limit", 10))

    try:
        from spide.mcp.search_provider import WebSearchProvider

        provider = WebSearchProvider()
        if engine == "duckduckgo":
            results = await provider.search(query, limit=limit)
            return {
                "status": "ok",
                "query": query,
                "engine": engine,
                "results": [
                    {"title": r.title, "url": r.url, "description": r.description} for r in results
                ],
            }
        return await _tool_web_search({"query": query, "count": limit})
    except Exception as exc:
        logger.warning("web_search_enhanced_failed", error=str(exc))
        return {"status": "error", "message": str(exc)}


async def _tool_fetch_web_page(args: dict[str, Any]) -> dict[str, Any]:
    """抓取网页内容。"""
    url = args.get("url", "")
    if not url:
        return {"status": "error", "message": "url 不能为空"}
    extract_links = bool(args.get("extract_links", False))

    try:
        from spide.mcp.search_provider import WebContentProvider

        provider = WebContentProvider()
        page = await provider.fetch_page(url, max_length=5000)
        result = {
            "status": "ok",
            "url": page.url,
            "title": page.title,
            "content": page.text[:5000],
        }
        if extract_links:
            result["links"] = page.links[:50]
        return result
    except Exception as exc:
        logger.warning("fetch_web_page_failed", error=str(exc))
        return {"status": "error", "message": str(exc)}


async def _tool_fetch_repo_info(args: dict[str, Any]) -> dict[str, Any]:
    """GitHub 仓库信息。"""
    repo = args.get("repo", "")
    if not repo or "/" not in repo:
        return {"status": "error", "message": "repo 格式应为 owner/repo"}
    info_type = args.get("info_type", "summary")

    try:
        from spide.mcp.search_provider import RepoInfoProvider, WebContentProvider

        if info_type == "readme":
            provider = WebContentProvider()
            readme = await provider.fetch_github_readme(repo)
            return {"status": "ok", "repo": repo, "readme": readme[:5000]}

        provider2 = RepoInfoProvider()
        info = await provider2.fetch_repo_info(repo)
        return {"status": "ok", "repo": repo, "info": info}
    except Exception as exc:
        logger.warning("fetch_repo_info_failed", error=str(exc))
        return {"status": "error", "message": str(exc)}


async def _tool_manage_memory(args: dict[str, Any]) -> dict[str, Any]:
    """记忆管理。"""
    action = args.get("action", "list")
    title = args.get("title", "")
    content = args.get("content", "")

    try:
        from spide import memory

        if action == "list":
            items = memory.list_memories()
            return {"status": "ok", "memories": items}
        if action == "get":
            data = memory.get_memory(title)
            return {"status": "ok", "memory": data}
        if action == "add":
            memory.add_memory(title=title, content=content)
            return {"status": "ok", "message": f"已添加: {title}"}
        if action == "remove":
            memory.remove_memory(title)
            return {"status": "ok", "message": f"已删除: {title}"}
        return {"status": "error", "message": f"未知 action: {action}"}
    except Exception as exc:
        logger.warning("manage_memory_failed", error=str(exc))
        return {"status": "error", "message": str(exc)}


async def _tool_health_check(args: dict[str, Any]) -> dict[str, Any]:
    """健康检查。"""
    import platform

    return {
        "status": "ok",
        "service": "spide-agent",
        "version": "1.1.1",
        "python": platform.python_version(),
    }


async def _tool_deep_crawl(args: dict[str, Any]) -> dict[str, Any]:
    """深度采集（subprocess 调用，避免 Playwright 阻塞事件循环）。"""
    platform_ = args.get("platform", "xhs")
    mode = args.get("mode", "search")
    keywords = args.get("keywords", "")
    max_notes = int(args.get("max_notes", 20))

    cli_args = ["deep-crawl", "-p", platform_, "--mode", mode, "--max-notes", str(max_notes)]
    if keywords:
        cli_args.extend(["--keywords", keywords])
    return await _fallback_cli(cli_args, timeout=300)


# ── CLI 兜底 ──────────────────────────────────────────────────────


async def _fallback_cli(args: list[str], timeout: int = 120) -> dict[str, Any]:
    """通过 subprocess 调用 spide CLI（兜底）。"""

    def _run() -> dict[str, Any]:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "spide", *args],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                timeout=timeout,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")[-2000:]
            stderr = result.stderr.decode("utf-8", errors="replace")[-500:]
            if result.returncode != 0:
                return {"status": "error", "message": stderr or stdout}
            return {"status": "ok", "output": stdout}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"超时 (>{timeout}s)"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ── 路由表 ──────────────────────────────────────────────────────


_TOOL_ROUTES: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "crawl_hot_topics": _tool_crawl_hot_topics,
    "web_search": _tool_web_search,
    "web_search_enhanced": _tool_web_search_enhanced,
    "fetch_web_page": _tool_fetch_web_page,
    "fetch_repo_info": _tool_fetch_repo_info,
    "manage_memory": _tool_manage_memory,
    "health_check": _tool_health_check,
    "deep_crawl_hot_topics": _tool_deep_crawl,
}


async def call_tool(name: str, arguments: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    """统一工具调用入口（含超时保护）。"""
    handler = _TOOL_ROUTES.get(name)
    if handler is None:
        return {"status": "error", "message": f"未知工具: {name}"}

    logger.info("tool_call", name=name, args=arguments)
    try:
        return await asyncio.wait_for(handler(arguments), timeout=timeout)
    except TimeoutError:
        logger.warning("tool_timeout", name=name, timeout=timeout)
        return {"status": "error", "message": f"工具调用超时 (>{timeout}s)"}
    except Exception as exc:
        logger.error("tool_exception", name=name, error=str(exc))
        return {"status": "error", "message": str(exc)}


def list_tools() -> list[str]:
    """列出所有已注册工具名。"""
    return list(_TOOL_ROUTES.keys())


def get_tool_schemas() -> list[dict[str, Any]]:
    """获取 OpenAI Function Calling schema（用于 LLM tools 参数）。"""
    from spide.mcp.tools import ALL_TOOLS

    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"],
            },
        }
        for t in ALL_TOOLS
    ]


def format_tool_result(name: str, result: dict[str, Any], max_length: int = 1500) -> str:
    """格式化工具结果为短文本（注入 LLM 上下文）。"""
    try:
        text = json.dumps(result, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = str(result)
    if len(text) > max_length:
        text = text[:max_length] + "...[已截断]"
    return text
