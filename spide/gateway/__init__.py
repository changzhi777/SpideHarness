# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""HTTP/WebSocket Gateway — spide 独立网关层.

与 `dashboard/` 的区别：
- `dashboard/` — 飞书智能体集成（ReAct + WS SDK + 卡片），强业务耦合
- `spide/gateway/` — 通用 HTTP/WS 接入层（无外部 SDK 依赖），KISS 设计

端点（最小可用实现）：
- `GET  /health`                  健康检查（公开）
- `GET  /api/v1/topics`           热搜查询（鉴权 + 限流）
- `WS   /ws/events`               简单状态广播（heartbeat）

鉴权（V3.1.3+）：
- 通过 `X-API-Key` 请求头验证
- 环境变量 `SPIDE_GATEWAY_API_KEYS` 配置多个 Key（逗号分隔）
- 未配置 = 禁用鉴权（开发模式）

限流（V3.1.3+）：
- 纯 asyncio 滑动窗口（默认 60 req/min/客户端）
- 客户端标识：X-API-Key 优先，降级 IP
- 触发后 429 + Retry-After 头

启动：`uvicorn spide.gateway.server:app --host 0.0.0.0 --port 8765`
"""

from spide.gateway.server import app

__all__ = ["app"]
