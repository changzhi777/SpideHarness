"""能力注册表 — AI Agent 自发现协议 (/.well-known/agent.json).

设计:
- 单例模式（模块级 _registry 实例）
- 三个核心方法: register_mcp_tool / register_http_endpoint / register_skill
- 一个出口: to_agent_json() 生成符合 OpenAPI Discovery 风格的描述

AI Agent 只需 GET /.well-known/agent.json 即可发现所有能力。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPTool:
    """MCP 工具描述."""

    name: str
    description: str
    input_schema: dict[str, Any]
    auth: str = "none"  # none | uapi_key | llm_key
    category: str = "general"


@dataclass
class HTTPEndpoint:
    """HTTP 端点描述."""

    path: str
    method: str
    summary: str
    request_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    auth: str = "none"
    category: str = "general"


@dataclass
class Skill:
    """AI Skill 描述."""

    name: str
    description: str
    path: str
    category: str = "general"


class CapabilityRegistry:
    """能力注册表（单例）."""

    _instance: CapabilityRegistry | None = None
    _initialized: bool = False

    def __new__(cls) -> CapabilityRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._mcp_tools: list[MCPTool] = []
        self._http_endpoints: list[HTTPEndpoint] = []
        self._skills: list[Skill] = []
        self._agent_meta: dict[str, str] = {
            "name": "SpideHarness Agent",
            "version": "3.1.1",
            "description": "热点新闻信息抓取与智能整理 Agent",
        }
        self._initialized = True

    def set_agent_meta(self, *, name: str = "", version: str = "", description: str = "") -> None:
        if name:
            self._agent_meta["name"] = name
        if version:
            self._agent_meta["version"] = version
        if description:
            self._agent_meta["description"] = description

    def register_mcp_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        *,
        auth: str = "none",
        category: str = "general",
    ) -> None:
        self._mcp_tools.append(
            MCPTool(
                name=name,
                description=description,
                input_schema=input_schema,
                auth=auth,
                category=category,
            )
        )

    def register_http_endpoint(
        self,
        path: str,
        method: str,
        summary: str,
        *,
        request_schema: dict[str, Any] | None = None,
        response_schema: dict[str, Any] | None = None,
        auth: str = "none",
        category: str = "general",
    ) -> None:
        self._http_endpoints.append(
            HTTPEndpoint(
                path=path,
                method=method.upper(),
                summary=summary,
                request_schema=request_schema or {},
                response_schema=response_schema or {},
                auth=auth,
                category=category,
            )
        )

    def register_skill(
        self,
        name: str,
        description: str,
        path: str,
        *,
        category: str = "general",
    ) -> None:
        self._skills.append(
            Skill(
                name=name,
                description=description,
                path=path,
                category=category,
            )
        )

    def to_agent_json(self, *, base_url: str = "") -> dict[str, Any]:
        """生成符合 OpenAPI Discovery 风格的 agent.json."""
        return {
            "$schema": "https://spide-agent.example/schemas/agent-discovery-v1.json",
            "agent": {
                "name": self._agent_meta["name"],
                "version": self._agent_meta["version"],
                "description": self._agent_meta["description"],
            },
            "capabilities": {
                "mcp": {
                    "transport": ["stdio", "sse"],
                    "command": "spide mcp-serve",
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.input_schema,
                            "auth": t.auth,
                            "category": t.category,
                        }
                        for t in self._mcp_tools
                    ],
                },
                "http": {
                    "base_url": base_url,
                    "endpoints": [
                        {
                            "path": e.path,
                            "method": e.method,
                            "summary": e.summary,
                            "requestSchema": e.request_schema,
                            "responseSchema": e.response_schema,
                            "auth": e.auth,
                            "category": e.category,
                        }
                        for e in self._http_endpoints
                    ],
                },
                "skills": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "path": s.path,
                        "category": s.category,
                    }
                    for s in self._skills
                ],
            },
            "discovery": {
                "docs": "docs/integration/INTEGRATION.md",
                "mcp_reference": "docs/mcp-api-reference.md",
                "http_reference": "docs/http-api-reference.md",
                "skills_index": "skills/README.md",
            },
        }


# 模块级单例
registry = CapabilityRegistry()
