# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — MCP Server/Client."""


import pytest

from spide.exceptions import MCPError
from spide.mcp.server import create_mcp_server
from spide.mcp.tools import ALL_TOOLS, CRAWL_TOOL, SEARCH_TOOL


class TestMCPServer:
    """MCP Server."""

    def test_create(self):
        server = create_mcp_server()
        assert server.name == "spide-agent"

    def test_tool_count(self):
        assert len(ALL_TOOLS) == 5

    def test_crawl_tool_schema(self):
        props = CRAWL_TOOL["inputSchema"]["properties"]
        assert "source" in props
        assert "save" in props
        assert props["source"]["enum"] == ["weibo", "baidu", "douyin", "zhihu", "bilibili"]

    def test_search_tool_schema(self):
        props = SEARCH_TOOL["inputSchema"]["properties"]
        assert "query" in props
        assert "engine" in props


class TestMCPClient:
    """MCP Client 错误处理."""

    @pytest.mark.asyncio
    async def test_not_connected(self):
        from spide.mcp.client import MCPClient

        client = MCPClient(server_command="python")
        with pytest.raises(MCPError, match="未连接"):
            await client.list_tools()

    @pytest.mark.asyncio
    async def test_not_connected_call_tool(self):
        from spide.mcp.client import MCPClient

        client = MCPClient(server_command="python")
        with pytest.raises(MCPError, match="未连接"):
            await client.call_tool("test", {})
