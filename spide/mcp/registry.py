# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP 工具注册表 — 动态注册和管理工具.

用法:
    from spide.mcp.registry import ToolRegistry

    registry = ToolRegistry()
    registry.register({"name": "my_tool", "description": "...", "inputSchema": {...}})
    tools = registry.list_tools()
    registry.unregister("my_tool")
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from spide.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """MCP 工具注册表."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register(
        self,
        tool: dict[str, Any],
        handler: Callable[..., Coroutine[Any, Any, Any]] | None = None,
    ) -> None:
        """注册工具.

        Args:
            tool: 工具定义（遵循 MCP Tool schema）
            handler: 可选的自定义处理函数
        """
        name = tool.get("name")
        if not name:
            raise ValueError("工具必须包含 name 字段")

        self._tools[name] = tool
        if handler:
            self._handlers[name] = handler

        logger.info("tool_registered", name=name)

    def unregister(self, name: str) -> bool:
        """注销工具."""
        if name in self._tools:
            del self._tools[name]
            self._handlers.pop(name, None)
            logger.info("tool_unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> dict[str, Any] | None:
        """获取工具定义."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """列出所有已注册工具."""
        return list(self._tools.values())

    def has_handler(self, name: str) -> bool:
        """检查是否有自定义处理函数."""
        return name in self._handlers

    async def call_handler(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """调用工具处理函数."""
        if name not in self._handlers:
            raise KeyError(f"未找到工具处理器: {name}")

        handler = self._handlers[name]
        return await handler(arguments)

    def clear(self) -> None:
        """清空所有工具."""
        self._tools.clear()
        self._handlers.clear()
        logger.info("tool_registry_cleared")


# 全局注册表实例
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局工具注册表."""
    return _global_registry


def register_tool(
    tool: dict[str, Any],
    handler: Callable[..., Coroutine[Any, Any, Any]] | None = None,
) -> None:
    """注册工具到全局注册表."""
    _global_registry.register(tool, handler)


def unregister_tool(name: str) -> bool:
    """从全局注册表注销工具."""
    return _global_registry.unregister(name)


def list_registered_tools() -> list[dict[str, Any]]:
    """列出全局注册表中所有工具."""
    return _global_registry.list_tools()
