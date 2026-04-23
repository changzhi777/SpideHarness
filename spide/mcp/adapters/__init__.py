# Copyright (C) 2026 IoTchange - All Rights Reserved
"""MCP 外部适配器."""

from spide.mcp.adapters.hermes import HermesAdapter, HERMES_TOOLS
from spide.mcp.adapters.openclaw import OpenClawAdapter, OPENCLAW_TOOLS

__all__ = [
    "OpenClawAdapter",
    "OpenClaw_TOOLS",
    "HermesAdapter",
    "HERMES_TOOLS",
]
