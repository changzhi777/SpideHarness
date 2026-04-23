# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""OpenClaw MCP 适配器.

提供对 OpenClaw 工具的桥接:
- browser: 网页抓取和控制
- sessions: 会话管理
- skills: 技能管理
- channels: 渠道配置

用法:
    from spide.mcp.adapters.openclaw import OpenClawAdapter

    adapter = OpenClawAdapter()
    tools = adapter.get_tools()

    # 或通过 MCP Client 连接
    adapter = OpenClawAdapter(connection_url="http://localhost:18789/mcp")
    await adapter.connect()
    result = await adapter.run_browser_command("navigate", {"url": "https://example.com"})
"""

from __future__ import annotations

import asyncio
from typing import Any

from spide.logging import get_logger

logger = get_logger(__name__)

# OpenClaw 支持的渠道
OPENCLAW_CHANNELS = [
    "whatsapp", "telegram", "slack", "discord", "google_chat",
    "signal", "imessage", "bluebubbles", "irc", "microsoft_teams",
    "matrix", "feishu", "line", "mattermost", "nextcloud_talk",
    "nostr", "synology_chat", "tlon", "twitch", "zalo",
    "wechat", "qq", "webchat", "macos", "ios", "android",
]

# OpenClaw 工具定义
OPENCLAW_TOOLS = [
    {
        "name": "openclaw_browser_navigate",
        "description": "导航到指定 URL（通过 OpenClaw browser 工具）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "目标 URL"},
                "wait": {"type": "number", "description": "等待秒数", "default": 3},
            },
            "required": ["url"],
        },
    },
    {
        "name": "openclaw_browser_click",
        "description": "点击页面元素",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS 选择器"},
                "x": {"type": "number", "description": "X 坐标"},
                "y": {"type": "number", "description": "Y 坐标"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "openclaw_browser_type",
        "description": "在输入框中输入文本",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "输入框选择器"},
                "text": {"type": "string", "description": "要输入的文本"},
                "submit": {"type": "boolean", "description": "输入后提交", "default": False},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "openclaw_browser_screenshot",
        "description": "截取当前页面截图",
        "inputSchema": {
            "type": "object",
            "properties": {
                "full_page": {"type": "boolean", "description": "截取完整页面", "default": False},
            },
        },
    },
    {
        "name": "openclaw_browser_content",
        "description": "获取页面内容（文本或 HTML）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "可选：CSS 选择器"},
                "as_html": {"type": "boolean", "description": "返回 HTML 而非文本", "default": False},
            },
        },
    },
    {
        "name": "openclaw_sessions_list",
        "description": "列出所有活动会话",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "openclaw_sessions_history",
        "description": "获取会话历史消息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "会话 ID"},
                "limit": {"type": "number", "description": "消息数量限制", "default": 50},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "openclaw_sessions_send",
        "description": "向会话发送消息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "会话 ID"},
                "message": {"type": "string", "description": "消息内容"},
            },
            "required": ["session_id", "message"],
        },
    },
    {
        "name": "openclaw_sessions_spawn",
        "description": "创建新会话",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "渠道名称"},
                "prompt": {"type": "string", "description": "初始提示"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "openclaw_skills_list",
        "description": "列出所有可用技能",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "openclaw_skills_run",
        "description": "运行指定技能",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_name": {"type": "string", "description": "技能名称"},
                "args": {"type": "object", "description": "技能参数"},
            },
            "required": ["skill_name"],
        },
    },
    {
        "name": "openclaw_skills_install",
        "description": "从 ClawHub 安装技能",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_url": {"type": "string", "description": "技能 GitHub URL 或 ClawHub ID"},
            },
            "required": ["skill_url"],
        },
    },
    {
        "name": "openclaw_channels_list",
        "description": "列出所有已配置渠道",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "openclaw_channels_status",
        "description": "检查渠道连接状态",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "渠道名称"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "openclaw_gateway_status",
        "description": "检查 Gateway 运行状态",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


class OpenClawAdapter:
    """OpenClaw 适配器 — 桥接 OpenClaw 工具到 Spide Agent."""

    def __init__(
        self,
        connection_url: str | None = None,
        gateway_port: int = 18789,
    ) -> None:
        """初始化适配器.

        Args:
            connection_url: OpenClaw MCP Server URL（HTTP 模式）
            gateway_port: OpenClaw Gateway 端口（默认 18789）
        """
        self._connection_url = connection_url or f"http://localhost:{gateway_port}/mcp"
        self._gateway_port = gateway_port
        self._http_session = None

    async def connect(self) -> None:
        """建立连接."""
        import aiohttp

        self._http_session = aiohttp.ClientSession()
        logger.info("openclaw_adapter_connected", url=self._connection_url)

    async def disconnect(self) -> None:
        """断开连接."""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

    def get_tools(self) -> list[dict[str, Any]]:
        """获取 OpenClaw 工具列表."""
        return OPENCLAW_TOOLS

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """调用 OpenClaw 工具.

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
                    logger.error("openclaw_tool_error", tool=tool_name, status=resp.status, error=error)
                    return {"error": f"HTTP {resp.status}: {error}"}

                data = await resp.json()
                return data.get("result", {})
        except Exception as e:
            logger.error("openclaw_call_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # 便捷方法
    # -------------------------------------------------------------------------

    async def navigate(self, url: str, wait: int = 3) -> dict[str, Any]:
        """导航到 URL."""
        return await self.call_tool("openclaw_browser_navigate", {"url": url, "wait": wait})

    async def click(self, selector: str) -> dict[str, Any]:
        """点击元素."""
        return await self.call_tool("openclaw_browser_click", {"selector": selector})

    async def type_text(self, selector: str, text: str, submit: bool = False) -> dict[str, Any]:
        """输入文本."""
        return await self.call_tool("openclaw_browser_type", {
            "selector": selector,
            "text": text,
            "submit": submit,
        })

    async def screenshot(self, full_page: bool = False) -> dict[str, Any]:
        """截取截图."""
        return await self.call_tool("openclaw_browser_screenshot", {"full_page": full_page})

    async def get_content(self, selector: str | None = None, as_html: bool = False) -> dict[str, Any]:
        """获取页面内容."""
        return await self.call_tool("openclaw_browser_content", {
            "selector": selector,
            "as_html": as_html,
        })

    async def list_sessions(self) -> dict[str, Any]:
        """列出所有会话."""
        return await self.call_tool("openclaw_sessions_list", {})

    async def get_session_history(self, session_id: str, limit: int = 50) -> dict[str, Any]:
        """获取会话历史."""
        return await self.call_tool("openclaw_sessions_history", {
            "session_id": session_id,
            "limit": limit,
        })

    async def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        """发送消息."""
        return await self.call_tool("openclaw_sessions_send", {
            "session_id": session_id,
            "message": message,
        })

    async def spawn_session(self, channel: str, prompt: str = "") -> dict[str, Any]:
        """创建新会话."""
        return await self.call_tool("openclaw_sessions_spawn", {
            "channel": channel,
            "prompt": prompt,
        })

    async def list_skills(self) -> dict[str, Any]:
        """列出所有技能."""
        return await self.call_tool("openclaw_skills_list", {})

    async def run_skill(self, skill_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """运行技能."""
        return await self.call_tool("openclaw_skills_run", {
            "skill_name": skill_name,
            "args": args or {},
        })

    async def install_skill(self, skill_url: str) -> dict[str, Any]:
        """安装技能."""
        return await self.call_tool("openclaw_skills_install", {"skill_url": skill_url})

    async def list_channels(self) -> dict[str, Any]:
        """列出所有渠道."""
        return await self.call_tool("openclaw_channels_list", {})

    async def check_channel_status(self, channel: str) -> dict[str, Any]:
        """检查渠道状态."""
        return await self.call_tool("openclaw_channels_status", {"channel": channel})

    async def gateway_status(self) -> dict[str, Any]:
        """检查 Gateway 状态."""
        return await self.call_tool("openclaw_gateway_status", {})

    async def __aenter__(self) -> "OpenClawAdapter":
        """上下文管理器入口."""
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        """上下文管理器出口."""
        await self.disconnect()
