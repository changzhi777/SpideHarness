# Gateway 模块（独立 HTTP/WS 接入层）

> [根目录](../../CLAUDE.md) > [spide](../) > **gateway**

最后更新：2026-06-13（GAP-001 关闭）

## 职责

通用 HTTP/WebSocket 接入层，**无外部 SDK 依赖**（不绑定飞书 SDK）。是 spide 的
对外网关，可独立启动供任何 HTTP 客户端 / WebSocket 客户端使用。

## 与 dashboard/ 的边界

| 维度 | `dashboard/` | `spide/gateway/` |
|------|-------------|------------------|
| 业务耦合 | 强（飞书 ReAct Agent + 卡片 + WS 推送） | 无 |
| 外部依赖 | `lark-oapi` SDK | 无 |
| 数据源 | SQLite + LLM + 飞书事件 | SQLite only |
| 启动方式 | `uvicorn dashboard.api:app` | `uvicorn spide.gateway:app` |
| 鉴权 | 飞书事件订阅 | 无（KISS，预留扩展）|

**两个 app 可独立启动，无 import 依赖。**

## 文件清单（2 个文件，~210 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 28 | 导出 `app`（FastAPI 实例）|
| `server.py` | 232 | FastAPI app + 3 端点 + ConnectionManager + 全局异常处理 |

## 端点（最小可用实现）

| 端点 | 方法 | 功能 | 模型 |
|------|------|------|------|
| `/health` | GET | 健康检查（status/version/uptime）| `HealthResponse` |
| `/api/v1/topics` | GET | 热搜查询（source + limit 参数）| `TopicsResponse` |
| `/ws/events` | WS | 状态广播（30s heartbeat + echo）| — |

## Pydantic 模型

```python
class HealthResponse(BaseModel):
    status: str           # "ok" | "degraded"
    version: str          # "3.1.2"
    uptime_seconds: float

class TopicItem(BaseModel):
    title: str
    source: str
    hot_value: int
    rank: int
    url: str = ""

class TopicsResponse(BaseModel):
    count: int
    items: list[TopicItem]
```

## WebSocket 协议

- **客户端→服务端**: 任意文本消息（回显为 `{"type": "echo", "received": ..., "ts": ...}`）
- **服务端→客户端**（30s 周期）: `{"type": "heartbeat", "ts": ..., "uptime_seconds": ..., "ws_clients": N}`

## 启动

```bash
# 独立启动
uvicorn spide.gateway:app --host 0.0.0.0 --port 8765

# 开发模式（热重载）
uvicorn spide.gateway.server:app --reload --port 8765

# 验证
curl http://localhost:8765/health
# → {"status":"ok","version":"3.1.2","uptime_seconds":1.234}
```

## 设计原则

- **KISS** — 仅 3 个端点，~210 行实现
- **无外部 SDK** — 纯 FastAPI + asyncio，不依赖 lark-oapi / apscheduler
- **类型安全** — Pydantic 模型 + Query 校验（limit 越界自动 422）
- **优雅退出** — lifespan 启动/取消 heartbeat 任务
- **死连接清理** — broadcast 自动移除断开客户端

## 依赖

- `fastapi>=0.136.3`（已声明）
- `uvicorn>=0.44.0`（已声明）
- `pydantic>=2.0`（已声明）
- `spide.storage.sqlite_repo.SqliteRepository`
- `spide.storage.models.HotTopic`

## 测试

`tests/unit/test_gateway.py` — **14 个单元测试**：

- `TestHealthEndpoint` (2) — 端点 + 直接函数调用
- `TestTopicsEndpoint` (3) — 空数据 / 有数据 / limit 422
- `TestConnectionManager` (4) — 连接管理 + broadcast + 死连接清理
- `TestWebSocketEndpoint` (1) — 真实 WS echo
- `TestAppMetadata` (2) — 路由 + 元数据
- `TestGlobalExceptionHandler` (2) — handler 注册 + 500 JSON

## 未来扩展（YAGNI 暂不实现）

- 鉴权（API Key / JWT）
- 限流 / 配额
- 业务事件订阅（替代单纯 heartbeat）
- OpenAPI 标签分组（按业务域）
- Prometheus metrics 端点

## 变更记录

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-06-13 | 实现 | 关闭 GAP-001，新增 server.py + 14 测试 |
| 2026-04-08 | 预留 | 仅 `__init__.py` 占位 |
