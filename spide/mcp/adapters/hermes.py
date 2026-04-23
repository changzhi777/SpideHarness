# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Hermes Agent MCP 适配器.

提供对 Hermes Agent 工具的桥接:
- skills: 技能管理（创建、运行、改进）
- memory: 记忆系统（持久化、学习、搜索）
- subagent: 子 Agent 管理
- schedule: 定时任务

用法:
    from spide.mcp.adapters.hermes import HermesAdapter

    adapter = HermesAdapter()
    tools = adapter.get_tools()

    # 或通过 MCP Client 连接
    adapter = HermesAdapter(connection_url="http://localhost:8768/mcp")
    await adapter.connect()
    result = await adapter.create_skill("my_skill", {"description": "...", "actions": [...]})
"""

from __future__ import annotations

from typing import Any

from spide.logging import get_logger

logger = get_logger(__name__)

# Hermes 工具定义
HERMES_TOOLS = [
    {
        "name": "hermes_skill_create",
        "description": "创建新技能（Hermes 内置学习循环会根据使用自动改进）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "技能名称"},
                "description": {"type": "string", "description": "技能描述"},
                "instructions": {"type": "string", "description": "技能指令"},
                "actions": {
                    "type": "array",
                    "description": "技能动作列表",
                    "items": {"type": "string"},
                },
            },
            "required": ["name", "instructions"],
        },
    },
    {
        "name": "hermes_skill_run",
        "description": "运行指定技能",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "技能名称"},
                "input": {"type": "string", "description": "输入内容"},
                "context": {"type": "object", "description": "额外上下文"},
            },
            "required": ["skill_name"],
        },
    },
    {
        "name": "hermes_skill_list",
        "description": "列出所有已创建技能",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "hermes_skill_improve",
        "description": "让 Agent 根据使用情况改进技能",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "技能名称"},
                "feedback": {"type": "string", "description": "改进反馈"},
            },
            "required": ["skill_name"],
        },
    },
    {
        "name": "hermes_memory_persist",
        "description": "将当前会话重要信息持久化到记忆",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "要记忆的内容"},
                "tags": {
                    "type": "array",
                    "description": "标签",
                    "items": {"type": "string"},
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "hermes_memory_search",
        "description": "搜索历史记忆（使用 FTS5 全文搜索 + LLM 摘要）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"},
                "limit": {"type": "number", "description": "返回数量", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "hermes_memory_recall",
        "description": "根据用户画像回忆相关信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "主题"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "hermes_subagent_spawn",
        "description": "创建子 Agent 并行处理任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "子 Agent 名称"},
                "prompt": {"type": "string", "description": "子 Agent 任务提示"},
                "tools": {
                    "type": "array",
                    "description": "授权工具列表",
                    "items": {"type": "string"},
                },
            },
            "required": ["name", "prompt"],
        },
    },
    {
        "name": "hermes_subagent_status",
        "description": "查看子 Agent 状态",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subagent_id": {"type": "string", "description": "子 Agent ID"},
            },
            "required": ["subagent_id"],
        },
    },
    {
        "name": "hermes_subagent_result",
        "description": "获取子 Agent 执行结果",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subagent_id": {"type": "string", "description": "子 Agent ID"},
            },
            "required": ["subagent_id"],
        },
    },
    {
        "name": "hermes_schedule_create",
        "description": "创建定时任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "任务名称"},
                "cron": {"type": "string", "description": "Cron 表达式"},
                "action": {"type": "string", "description": "要执行的操作"},
                "channel": {"type": "string", "description": "结果发送渠道"},
            },
            "required": ["name", "cron", "action"],
        },
    },
    {
        "name": "hermes_schedule_list",
        "description": "列出所有定时任务",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "hermes_schedule_delete",
        "description": "删除定时任务",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "任务名称"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "hermes_model_list",
        "description": "列出支持的模型提供商和模型",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "hermes_model_set",
        "description": "设置当前使用的模型",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "description": "提供商: nous, openrouter, openai, etc."},
                "model": {"type": "string", "description": "模型名称"},
            },
            "required": ["provider", "model"],
        },
    },
]


class HermesAdapter:
    """Hermes Agent 适配器 — 桥接 Hermes 工具到 Spide Agent."""

    def __init__(
        self,
        connection_url: str | None = None,
        hermes_port: int = 8768,
    ) -> None:
        """初始化适配器.

        Args:
            connection_url: Hermes MCP Server URL（HTTP 模式）
            hermes_port: Hermes 端口（默认 8768）
        """
        self._connection_url = connection_url or f"http://localhost:{hermes_port}/mcp"
        self._hermes_port = hermes_port
        self._http_session = None

    async def connect(self) -> None:
        """建立连接."""
        import aiohttp

        self._http_session = aiohttp.ClientSession()
        logger.info("hermes_adapter_connected", url=self._connection_url)

    async def disconnect(self) -> None:
        """断开连接."""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

    def get_tools(self) -> list[dict[str, Any]]:
        """获取 Hermes 工具列表."""
        return HERMES_TOOLS

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """调用 Hermes 工具.

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果或错误信息
        """
        try:
            if self._http_session is None:
                await self.connect()

            url = f"{self._connection_url}/tools/{tool_name}/call"
            async with self._http_session.post(url, json={"arguments": arguments}) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error("hermes_tool_error", tool=tool_name, status=resp.status, error=error)
                    return {"error": f"HTTP {resp.status}: {error}"}

                data = await resp.json()
                return data.get("result", {})
        except Exception as e:
            logger.error("hermes_call_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # 便捷方法 - Skills
    # -------------------------------------------------------------------------

    async def create_skill(
        self,
        name: str,
        instructions: str,
        description: str = "",
        actions: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建技能."""
        return await self.call_tool("hermes_skill_create", {
            "name": name,
            "description": description,
            "instructions": instructions,
            "actions": actions or [],
        })

    async def run_skill(
        self,
        skill_name: str,
        input: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """运行技能."""
        return await self.call_tool("hermes_skill_run", {
            "skill_name": skill_name,
            "input": input,
            "context": context or {},
        })

    async def list_skills(self) -> dict[str, Any]:
        """列出所有技能."""
        return await self.call_tool("hermes_skill_list", {})

    async def improve_skill(self, skill_name: str, feedback: str) -> dict[str, Any]:
        """改进技能."""
        return await self.call_tool("hermes_skill_improve", {
            "skill_name": skill_name,
            "feedback": feedback,
        })

    # -------------------------------------------------------------------------
    # 便捷方法 - Memory
    # -------------------------------------------------------------------------

    async def persist_memory(self, content: str, tags: list[str] | None = None) -> dict[str, Any]:
        """持久化记忆."""
        return await self.call_tool("hermes_memory_persist", {
            "content": content,
            "tags": tags or [],
        })

    async def search_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        """搜索记忆."""
        return await self.call_tool("hermes_memory_search", {
            "query": query,
            "limit": limit,
        })

    async def recall_memory(self, topic: str) -> dict[str, Any]:
        """回忆记忆."""
        return await self.call_tool("hermes_memory_recall", {"topic": topic})

    # -------------------------------------------------------------------------
    # 便捷方法 - Subagent
    # -------------------------------------------------------------------------

    async def spawn_subagent(
        self,
        name: str,
        prompt: str,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """创建子 Agent."""
        return await self.call_tool("hermes_subagent_spawn", {
            "name": name,
            "prompt": prompt,
            "tools": tools or [],
        })

    async def subagent_status(self, subagent_id: str) -> dict[str, Any]:
        """查看子 Agent 状态."""
        return await self.call_tool("hermes_subagent_status", {"subagent_id": subagent_id})

    async def get_subagent_result(self, subagent_id: str) -> dict[str, Any]:
        """获取子 Agent 结果."""
        return await self.call_tool("hermes_subagent_result", {"subagent_id": subagent_id})

    # -------------------------------------------------------------------------
    # 便捷方法 - Schedule
    # -------------------------------------------------------------------------

    async def create_schedule(
        self,
        name: str,
        cron: str,
        action: str,
        channel: str = "",
    ) -> dict[str, Any]:
        """创建定时任务."""
        return await self.call_tool("hermes_schedule_create", {
            "name": name,
            "cron": cron,
            "action": action,
            "channel": channel,
        })

    async def list_schedules(self) -> dict[str, Any]:
        """列出定时任务."""
        return await self.call_tool("hermes_schedule_list", {})

    async def delete_schedule(self, name: str) -> dict[str, Any]:
        """删除定时任务."""
        return await self.call_tool("hermes_schedule_delete", {"name": name})

    # -------------------------------------------------------------------------
    # 便捷方法 - Model
    # -------------------------------------------------------------------------

    async def list_models(self) -> dict[str, Any]:
        """列出可用模型."""
        return await self.call_tool("hermes_model_list", {})

    async def set_model(self, provider: str, model: str) -> dict[str, Any]:
        """设置模型."""
        return await self.call_tool("hermes_model_set", {
            "provider": provider,
            "model": model,
        })

    async def __aenter__(self) -> "HermesAdapter":
        """上下文管理器入口."""
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """上下文管理器出口."""
        await self.disconnect()
