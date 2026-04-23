# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP Server — 工具注册 + stdio transport.

用法:
    from spide.mcp import create_mcp_server

    server = create_mcp_server()
    await server.run()
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from spide.config import load_settings
from spide.logging import get_logger
from spide.mcp.tools import ALL_TOOLS

logger = get_logger(__name__)

# MCP Server 实例名称
_SERVER_NAME = "spide-agent"
_SERVER_VERSION = "0.1.0"


def create_mcp_server(
    *,
    project_root: Path | None = None,
) -> Server:
    """创建配置好的 MCP Server 实例.

    Args:
        project_root: 项目根目录（用于定位配置文件）

    Returns:
        配置好工具和 handler 的 Server 实例
    """
    server = Server(_SERVER_NAME)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """列出所有可用工具."""
        return [
            types.Tool(
                name=tool["name"],  # type: ignore[arg-type]
                description=tool["description"],  # type: ignore[arg-type]
                inputSchema=tool["inputSchema"],  # type: ignore[arg-type]
            )
            for tool in ALL_TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        """处理工具调用."""
        try:
            result = await _dispatch_tool(name, arguments, project_root)
            return [
                types.TextContent(
                    type="text", text=json.dumps(result, ensure_ascii=False, indent=2)
                )
            ]
        except Exception as e:
            logger.error("mcp_tool_error", tool=name, error=str(e))
            return [
                types.TextContent(
                    type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False)
                )
            ]

    return server


async def _dispatch_tool(
    name: str,
    arguments: dict[str, Any],
    project_root: Path | None,
) -> Any:
    """分发工具调用到具体实现."""
    if name == "crawl_hot_topics":
        return await _tool_crawl(arguments, project_root)
    elif name == "web_search":
        return await _tool_search(arguments, project_root)
    elif name == "manage_memory":
        return _tool_memory(arguments, project_root)
    elif name == "health_check":
        return _tool_health(project_root)
    elif name == "deep_crawl_hot_topics":
        return await _tool_deep_crawl(arguments, project_root)
    else:
        return {"error": f"未知工具: {name}"}


async def _tool_crawl(arguments: dict[str, Any], project_root: Path | None) -> Any:
    """热搜采集工具."""
    from spide.spider.uapi_client import UAPIClient

    settings = load_settings(project_root=project_root)
    client = UAPIClient(settings.uapi)
    await client.start()
    try:
        source = arguments.get("source", "weibo")
        topics = await client.fetch_hotboard(source)
        return {
            "source": source,
            "count": len(topics),
            "items": [
                {
                    "rank": t.rank,
                    "title": t.title,
                    "hot_value": t.hot_value,
                    "url": t.url,
                }
                for t in topics[:20]
            ],
        }
    finally:
        await client.stop()


async def _tool_search(arguments: dict[str, Any], project_root: Path | None) -> Any:
    """联网搜索工具."""
    from spide.llm import LLMClient

    settings = load_settings(project_root=project_root)
    client = LLMClient(settings.llm)
    client._client = _create_zai_client(settings)
    result = client.web_search(
        query=arguments["query"],
        search_engine=arguments.get("engine"),
        count=arguments.get("count"),
    )
    return {"query": arguments["query"], "result": str(result)[:2000]}


def _tool_memory(arguments: dict[str, Any], project_root: Path | None) -> Any:
    """记忆管理工具."""
    from spide.memory import add_memory, get_memory_content, list_memory_files, remove_memory

    workspace = None  # 使用默认 workspace
    action = arguments["action"]

    if action == "add":
        path = add_memory(workspace, title=arguments["title"], content=arguments["content"])
        return {"status": "added", "file": str(path)}
    elif action == "remove":
        ok = remove_memory(workspace, name=arguments["title"])
        return {"status": "removed" if ok else "not_found"}
    elif action == "list":
        files = list_memory_files(workspace)
        return {"files": [f.name for f in files]}
    elif action == "get":
        content = get_memory_content(workspace, name=arguments["title"])
        return {"content": content}
    else:
        return {"error": f"未知操作: {action}"}


async def _tool_deep_crawl(arguments: dict[str, Any], project_root: Path | None) -> Any:
    """深度采集工具（通过 MediaCrawler 适配器）."""
    from spide.harness.engine import Engine
    from spide.storage.models import CrawlMode, Platform

    settings = load_settings(project_root=project_root)
    engine = Engine(settings)

    try:
        await engine.start()

        # 解析参数
        platform = Platform(arguments["platform"])
        mode = CrawlMode(arguments.get("mode", "search"))
        keywords_str = arguments.get("keywords", "")
        content_ids_str = arguments.get("content_ids", "")
        creator_ids_str = arguments.get("creator_ids", "")

        kw_list = [k.strip() for k in keywords_str.split(",") if k.strip()] or None
        id_list = [u.strip() for u in content_ids_str.split(",") if u.strip()] or None
        cr_list = [c.strip() for c in creator_ids_str.split(",") if c.strip()] or None

        results = await engine.deep_crawl(
            platform=platform,
            mode=mode,
            keywords=kw_list,
            content_ids=id_list,
            creator_ids=cr_list,
            max_notes=arguments.get("max_notes", 20),
            enable_comments=arguments.get("enable_comments", True),
        )

        return {
            "platform": platform.value,
            "mode": mode.value,
            "contents_count": len(results.get("contents", [])),
            "comments_count": len(results.get("comments", [])),
            "creators_count": len(results.get("creators", [])),
            "contents": [
                {
                    "title": c.title,
                    "author": c.author_name,
                    "like_count": c.like_count,
                    "comment_count": c.comment_count,
                    "url": c.url,
                }
                for c in results.get("contents", [])[:10]
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await engine.stop()


def _tool_health(project_root: Path | None) -> Any:
    """健康检查工具."""
    import sys

    return {
        "status": "ok",
        "version": _SERVER_VERSION,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def _create_zai_client(settings: Any) -> Any:
    """创建 ZaiClient 实例."""
    from zai import ZaiClient

    return ZaiClient(
        api_key=settings.llm.common.api_key,
        base_url=settings.llm.common.base_url,
    )


async def serve_mcp(
    project_root: Path | None = None,
    transport: str = "stdio",
    host: str = "0.0.0.0",
    port: int = 8768,
) -> None:
    """启动 MCP Server.

    Args:
        project_root: 项目根目录
        transport: 传输方式 ("stdio" 或 "http")
        host: HTTP 绑定地址
        port: HTTP 端口
    """
    if transport == "http":
        await serve_mcp_http(host=host, port=port, project_root=project_root)
    else:
        await serve_mcp_stdio(project_root=project_root)


async def serve_mcp_stdio(project_root: Path | None = None) -> None:
    """启动 MCP Server（stdio 模式）."""
    server = create_mcp_server(project_root=project_root)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            types.InitializationOptions(  # type: ignore[attr-defined]
                server_name=_SERVER_NAME,
                server_version=_SERVER_VERSION,
            ),
        )


async def serve_mcp_http(
    host: str = "0.0.0.0",
    port: int = 8768,
    project_root: Path | None = None,
) -> None:
    """启动 MCP Server（HTTP 模式）."""
    from spide.mcp.transport.http import HttpTransport

    transport = HttpTransport(host=host, port=port)
    await transport.start()
