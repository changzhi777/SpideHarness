# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP Client — 连接外部 MCP Server 调用工具.

用法:
    from spide.mcp.client import MCPClient

    # stdio 模式
    async with MCPClient(server_command="python", args=["path/to/server.py"]) as client:
        tools = await client.list_tools()
        result = await client.call_tool("crawl_hot_topics", {"source": "weibo"})

    # HTTP 模式
    async with MCPClient(url="http://localhost:8768/mcp") as client:
        tools = await client.list_tools()
        result = await client.call_tool("tool_name", {"arg": "value"})
"""

from __future__ import annotations

import json
from typing import Any

import aiohttp

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from spide.exceptions import MCPError
from spide.logging import get_logger

logger = get_logger(__name__)


class MCPClient:
    """MCP Client — 连接外部 MCP Server."""

    def __init__(
        self,
        *,
        # stdio 模式参数
        server_command: str = "python",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        # HTTP 模式参数
        url: str | None = None,
    ) -> None:
        # stdio 模式
        self._server_params = StdioServerParameters(
            command=server_command,
            args=args or [],
            env=env,
        )
        # HTTP 模式
        self._url = url
        self._session: ClientSession | None = None
        self._http_session: aiohttp.ClientSession | None = None
        self._read_stream = None
        self._write_stream = None
        self._cm_stack: list[Any] = []
        self._is_http = url is not None

    async def __aenter__(self) -> MCPClient:
        """启动 MCP 客户端会话."""
        if self._is_http:
            return await self._connect_http()
        else:
            return await self._connect_stdio()

    async def _connect_stdio(self) -> MCPClient:
        """连接 stdio MCP Server."""
        try:
            # stdio_client 上下文
            stdio_cm = stdio_client(self._server_params)
            read_stream, write_stream = await stdio_cm.__aenter__()
            self._cm_stack.append(stdio_cm)

            # ClientSession 上下文
            session_cm = ClientSession(read_stream, write_stream)
            self._session = await session_cm.__aenter__()
            self._cm_stack.append(session_cm)

            # 初始化
            await self._session.initialize()

            logger.debug("mcp_client_connected", command=self._server_params.command)
            return self
        except Exception as e:
            await self._cleanup()
            raise MCPError(f"MCP 客户端连接失败: {e}") from e

    async def _connect_http(self) -> MCPClient:
        """连接 HTTP MCP Server."""
        try:
            self._http_session = aiohttp.ClientSession()
            # HTTP 模式下不需要 ClientSession，直接使用 HTTP API
            logger.debug("mcp_client_connected", url=self._url)
            return self
        except Exception as e:
            await self._cleanup()
            raise MCPError(f"MCP HTTP 客户端连接失败: {e}") from e

    async def __aexit__(self, *exc: Any) -> None:
        """关闭 MCP 客户端."""
        await self._cleanup()

    async def _cleanup(self) -> None:
        """按逆序关闭所有上下文."""
        import contextlib

        for cm in reversed(self._cm_stack):
            with contextlib.suppress(Exception):
                await cm.__aexit__(None, None, None)
        self._cm_stack.clear()
        self._session = None

    def _ensure_session(self) -> ClientSession:
        if self._session is None:
            raise MCPError("MCP 客户端未连接")
        return self._session

    async def list_tools(self) -> list[types.Tool]:
        """列出服务端可用工具."""
        if self._is_http:
            return await self._list_tools_http()
        session = self._ensure_session()
        result = await session.list_tools()
        return result.tools

    async def _list_tools_http(self) -> list[types.Tool]:
        """通过 HTTP 获取工具列表."""
        if self._http_session is None:
            raise MCPError("MCP HTTP 客户端未连接")

        url = f"{self._url}/tools"
        async with self._http_session.get(url) as resp:
            if resp.status != 200:
                raise MCPError(f"获取工具列表失败: {resp.status}")

            data = await resp.json()
            tools_data = data.get("tools", [])

            # 转换为 types.Tool
            return [
                types.Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in tools_data
            ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """调用服务端工具."""
        if self._is_http:
            return await self._call_tool_http(name, arguments or {})
        else:
            session = self._ensure_session()
            result = await session.call_tool(name, arguments or {})
            return result.content  # type: ignore[return-value]

    async def _call_tool_http(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> list[types.TextContent]:
        """通过 HTTP 调用工具."""
        if self._http_session is None:
            raise MCPError("MCP HTTP 客户端未连接")

        url = f"{self._url}/tools/{name}/call"
        async with self._http_session.post(url, json={"arguments": arguments}) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise MCPError(f"工具调用失败: {resp.status} - {error_text}")

            data = await resp.json()
            if "error" in data:
                raise MCPError(f"工具执行错误: {data['error']}")

            result = data.get("result", [])
            # 转换为 TextContent 列表
            if isinstance(result, list):
                return [
                    types.TextContent(type="text", text=str(r))
                    if not isinstance(r, dict)
                    else types.TextContent(
                        type="text",
                        text=r.get("text", json.dumps(r, ensure_ascii=False)),
                    )
                    for r in result
                ]
            else:
                return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    async def list_tools_http(self) -> list[dict[str, Any]]:
        """通过 HTTP 获取工具列表."""
        if self._http_session is None:
            raise MCPError("MCP HTTP 客户端未连接")

        url = f"{self._url}/tools"
        async with self._http_session.get(url) as resp:
            if resp.status != 200:
                raise MCPError(f"获取工具列表失败: {resp.status}")

            data = await resp.json()
            return data.get("tools", [])
