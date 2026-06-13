# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""HTTP/WebSocket Gateway — spide 独立网关层.

与 `dashboard/` 的区别：
- `dashboard/` — 飞书智能体集成（ReAct + WS SDK + 卡片），强业务耦合
- `spide/gateway/` — 通用 HTTP/WS 接入层（无外部 SDK 依赖），KISS 设计

端点（最小可用实现）：
- `GET  /health`                  健康检查
- `GET  /api/v1/topics`           热搜查询（直接读 SQLite）
- `WS   /ws/events`               简单状态广播（heartbeat）

启动：`uvicorn spide.gateway.server:app --host 0.0.0.0 --port 8765`
"""

from spide.gateway.server import app

__all__ = ["app"]
