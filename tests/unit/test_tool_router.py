"""工具路由器测试（8 个 MCP 工具的本地调用路由）."""

from __future__ import annotations

from unittest.mock import patch

from dashboard.tool_router import (
    _fallback_cli,
    call_tool,
    format_tool_result,
    get_tool_schemas,
    list_tools,
)


def test_list_tools_count() -> None:
    """列出 8 个工具。"""
    tools = list_tools()
    assert len(tools) == 8
    assert "crawl_hot_topics" in tools
    assert "health_check" in tools
    assert "deep_crawl_hot_topics" in tools


def test_get_tool_schemas_for_llm() -> None:
    """get_tool_schemas 返回 OpenAI Function Calling 格式。"""
    schemas = get_tool_schemas()
    assert len(schemas) == 8
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]


def test_format_tool_result_truncates() -> None:
    """format_tool_result 截断超长结果。"""
    long_text = "x" * 2000
    result = {"status": "ok", "data": long_text}
    formatted = format_tool_result("test", result, max_length=100)
    assert len(formatted) <= 200  # 100 + "[已截断]"
    assert "已截断" in formatted


def test_format_tool_result_short() -> None:
    """format_tool_result 短结果完整保留。"""
    result = {"status": "ok", "count": 5}
    formatted = format_tool_result("test", result)
    assert '"count": 5' in formatted
    assert "已截断" not in formatted


async def test_call_tool_unknown() -> None:
    """call_tool 未知工具名返回错误。"""
    result = await call_tool("nonexistent_tool", {})
    assert result["status"] == "error"
    assert "未知工具" in result["message"]


async def test_call_tool_timeout() -> None:
    """call_tool 工具超时返回错误。"""
    import asyncio

    async def slow_handler(args):
        await asyncio.sleep(2)
        return {"status": "ok"}

    with patch("dashboard.tool_router._TOOL_ROUTES", {"slow_tool": slow_handler}):
        result = await call_tool("slow_tool", {}, timeout=0.1)
    assert result["status"] == "error"
    assert "超时" in result["message"]


async def test_health_check_tool() -> None:
    """健康检查工具直接返回状态。"""
    result = await call_tool("health_check", {})
    assert result["status"] == "ok"
    assert "spide-agent" in result["service"]
    assert "python" in result


async def test_fallback_cli_no_subprocess_on_import() -> None:
    """_fallback_cli 接受参数（不实际执行以避免慢测试）。"""
    import inspect

    sig = inspect.signature(_fallback_cli)
    assert "args" in sig.parameters
    assert "timeout" in sig.parameters
