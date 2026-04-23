# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP HTTP + SSE 传输层.

用法:
    from spide.mcp.transport.http import create_app

    app = create_app()
    # 然后使用 uvicorn run app
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from spide.logging import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """创建 MCP HTTP 应用（供 uvicorn 使用）."""
    app = FastAPI(title="SpideHarness MCP Server", version="1.0.0")

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # SSE 端点
    @app.get("/mcp/events")
    async def events():
        async def event_stream():
            try:
                while True:
                    yield "data: ping\n\n"
                    await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("sse_connection_closed")

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # 工具列表端点
    @app.get("/mcp/tools")
    async def list_tools():
        from spide.mcp.tools import ALL_TOOLS
        return JSONResponse(content={"tools": ALL_TOOLS})

    # 调用工具端点
    @app.post("/mcp/tools/{tool_name}/call")
    async def call_tool(tool_name: str, request: Request):
        from spide.mcp.server import _dispatch_tool

        body = await request.json()
        arguments = body.get("arguments", {})

        try:
            result = await _dispatch_tool(tool_name, arguments, None)
            return JSONResponse(content={"result": result})
        except Exception as e:
            logger.error("mcp_tool_error", tool=tool_name, error=str(e))
            return JSONResponse(status_code=500, content={"error": str(e)})

    # 健康检查端点
    @app.get("/health")
    async def health():
        return JSONResponse(content={"status": "ok"})

    return app


# 保留 HttpTransport 类以保持向后兼容
class HttpTransport:
    """MCP HTTP + SSE 传输层."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8768,
        cors_origins: list[str] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.cors_origins = cors_origins or ["*"]
        self._app: FastAPI | None = None
        self._server = None

    @property
    def app(self) -> FastAPI:
        """获取 FastAPI 应用实例."""
        if self._app is None:
            self._app = create_app()
        return self._app

    def _create_app(self) -> FastAPI:
        """创建 FastAPI 应用（已弃用，请使用 create_app）."""
        return create_app()
        app = FastAPI(title="SpideHarness MCP Server", version="1.0.0")

        # CORS 中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # SSE 端点 - 用于流式响应
        @app.get("/mcp/events")
        async def events(request: Request):
            """SSE 流式事件端点."""
            async def event_stream():
                # 保持连接打开，等待服务端消息
                try:
                    while True:
                        # 发送心跳
                        yield "data: ping\n\n"
                        await asyncio.sleep(30)
                except asyncio.CancelledError:
                    logger.info("sse_connection_closed")

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # 工具列表端点
        @app.get("/mcp/tools")
        async def list_tools():
            """列出所有可用工具."""
            from spide.mcp.tools import ALL_TOOLS

            return JSONResponse(content={"tools": ALL_TOOLS})

        # 调用工具端点
        @app.post("/mcp/tools/{tool_name}/call")
        async def call_tool(tool_name: str, request: Request):
            """调用指定工具."""
            from spide.mcp.server import _dispatch_tool

            body = await request.json()
            arguments = body.get("arguments", {})

            try:
                result = await _dispatch_tool(tool_name, arguments, None)
                return JSONResponse(content={"result": result})
            except Exception as e:
                logger.error("mcp_tool_error", tool=tool_name, error=str(e))
                return JSONResponse(
                    status_code=500,
                    content={"error": str(e)},
                )

        # 健康检查端点
        @app.get("/health")
        async def health():
            """健康检查."""
            return JSONResponse(content={"status": "ok"})

        return app

    async def start(self) -> None:
        """启动 HTTP 服务器."""
        import uvicorn

        logger.info("mcp_http_starting", host=self.host, port=self.port)

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self) -> None:
        """停止 HTTP 服务器."""
        if self._server:
            self._server.should_exit = True
            logger.info("mcp_http_stopped")

    def run(self) -> None:
        """同步运行服务器（阻塞）."""
        import uvicorn

        uvicorn.run(self.app, host=self.host, port=self.port)


# ---------------------------------------------------------------------------
# SSE 事件流工具
# ---------------------------------------------------------------------------


async def sse_stream(
    generator: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[str]:
    """将异步生成器转换为 SSE 格式."""
    async for item in generator:
        yield f"data: {json.dumps(item)}\n\n"


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------


class MCPRequest:
    """MCP 请求模型."""

    def __init__(
        self,
        jsonrpc: str = "2.0",
        method: str | None = None,
        params: dict[str, Any] | None = None,
        id: int | str | None = None,
    ) -> None:
        self.jsonrpc = jsonrpc
        self.method = method
        self.params = params or {}
        self.id = id


class MCPResponse:
    """MCP 响应模型."""

    def __init__(
        self,
        jsonrpc: str = "2.0",
        result: Any = None,
        error: dict[str, Any] | None = None,
        id: int | str | None = None,
    ) -> None:
        self.jsonrpc = jsonrpc
        self.result = result
        self.error = error
        self.id = id

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        if self.error:
            return {
                "jsonrpc": self.jsonrpc,
                "error": self.error,
                "id": self.id,
            }
        return {
            "jsonrpc": self.jsonrpc,
            "result": self.result,
            "id": self.id,
        }
