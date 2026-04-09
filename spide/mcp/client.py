# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP Client — 连接外部 MCP Server 调用工具.

用法:
    from spide.mcp.client import MCPClient

    async with MCPClient(server_command="python", args=["path/to/server.py"]) as client:
        tools = await client.list_tools()
        result = await client.call_tool("crawl_hot_topics", {"source": "weibo"})
"""

from __future__ import annotations

from typing import Any

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
        server_command: str = "python",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._server_params = StdioServerParameters(
            command=server_command,
            args=args or [],
            env=env,
        )
        self._session: ClientSession | None = None
        self._read_stream = None
        self._write_stream = None
        self._cm_stack: list[Any] = []

    async def __aenter__(self) -> MCPClient:
        """启动 MCP 客户端会话."""
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
        session = self._ensure_session()
        result = await session.list_tools()
        return result.tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """调用服务端工具."""
        session = self._ensure_session()
        result = await session.call_tool(name, arguments or {})
        return result.content  # type: ignore[return-value]
