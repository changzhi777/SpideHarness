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

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from spide.logging import get_logger
from spide.storage.models import HotTopic
from spide.storage.sqlite_repo import SqliteRepository

logger = get_logger(__name__)


# ── Pydantic Models ──────────────────────────────────────────────


class HealthResponse(BaseModel):
    """健康检查响应."""

    status: str = Field(..., description="服务状态: ok | degraded")
    version: str = Field(default="3.1.2", description="服务版本")
    uptime_seconds: float = Field(..., description="启动至今秒数")


class TopicItem(BaseModel):
    """热搜条目."""

    title: str
    source: str
    hot_value: int
    rank: int
    url: str = ""


class TopicsResponse(BaseModel):
    """热搜查询响应."""

    count: int = Field(..., description="返回的话题数")
    items: list[TopicItem] = Field(default_factory=list)


# ── WebSocket 连接管理 ──────────────────────────────────────────


class ConnectionManager:
    """简单 WS 连接管理器（无外部依赖）.

    与 `dashboard/feishu_ws_client.py` 的区别：
    - 这里只管理**通用 WS 客户端**（不绑定飞书 SDK）
    - 仅做 heartbeat 广播（不处理业务事件）
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info("ws_connected", total=len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        logger.info("ws_disconnected", total=len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """向所有连接广播消息，断连自动清理."""
        if not self._connections:
            return
        # 快照避免迭代时修改
        async with self._lock:
            clients = list(self._connections)
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead.append(client)
        if dead:
            async with self._lock:
                for d in dead:
                    self._connections.discard(d)

    @property
    def count(self) -> int:
        return len(self._connections)


# ── App 生命周期 ────────────────────────────────────────────────


_START_TIME = time.time()
_manager = ConnectionManager()
_broadcast_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动/停止 heartbeat 广播任务."""
    global _broadcast_task
    _broadcast_task = asyncio.create_task(_heartbeat_loop())
    logger.info("gateway_started", port=app.state.port if hasattr(app.state, "port") else 0)
    try:
        yield
    finally:
        if _broadcast_task:
            _broadcast_task.cancel()
            with suppress(asyncio.CancelledError):
                await _broadcast_task
        logger.info("gateway_stopped")


async def _heartbeat_loop() -> None:
    """每 30 秒向所有 WS 客户端广播状态."""
    while True:
        await asyncio.sleep(30)
        await _manager.broadcast({
            "type": "heartbeat",
            "ts": time.time(),
            "uptime_seconds": time.time() - _START_TIME,
            "ws_clients": _manager.count,
        })


# ── FastAPI App ─────────────────────────────────────────────────


app = FastAPI(
    title="SpideHarness Gateway",
    version="3.1.2",
    description="独立 HTTP/WebSocket 接入层（无外部 SDK 依赖）",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康检查端点."""
    return HealthResponse(
        status="ok",
        version="3.1.2",
        uptime_seconds=time.time() - _START_TIME,
    )


@app.get("/api/v1/topics", response_model=TopicsResponse)
async def list_topics(
    source: str | None = Query(default=None, description="数据源过滤（weibo/baidu/...）"),
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
) -> TopicsResponse:
    """查询热搜话题（直接读 SQLite）."""
    db_path = "spide_data.db"
    repo = SqliteRepository(HotTopic, db_path=db_path)
    await repo.start()
    try:
        topics: list[HotTopic] = await repo.query(
            source=source, limit=limit  # type: ignore[arg-type]
        )
    finally:
        await repo.stop()

    items = [
        TopicItem(
            title=t.title,
            source=t.source.value if hasattr(t.source, "value") else str(t.source),
            hot_value=t.hot_value or 0,
            rank=t.rank or 0,
            url=t.url or "",
        )
        for t in topics
    ]
    return TopicsResponse(count=len(items), items=items)


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    """简单状态广播（30s heartbeat）.

    客户端可发送任意消息（将被回显，便于测试）。
    """
    await _manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（保持连接活跃 + 回显）
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "echo",
                "received": data,
                "ts": time.time(),
            })
    except WebSocketDisconnect:
        await _manager.disconnect(websocket)
    except Exception as e:
        logger.warning("ws_error", error=str(e))
        await _manager.disconnect(websocket)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Any, exc: Exception) -> JSONResponse:
    """全局异常处理 — 返回结构化错误."""
    logger.error("gateway_error", error=str(exc), type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": str(exc)},
    )
