"""飞书 WebSocket 长连接客户端 — 接收事件 + 发送回复.

替换 HTTP Webhook 模式，无需公网 URL 或 Cloudflare Tunnel。
服务端主动发起出站 WebSocket 连接到飞书服务器接收事件。

依赖: lark-oapi SDK (lark_oapi.ws.Client + EventDispatcherHandler)
"""

from __future__ import annotations

import json
import logging
from typing import Callable

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
    P2ImMessageReceiveV1,
)

logger = logging.getLogger("spide.feishu.ws")

# ── 全局状态 ──────────────────────────────────────────────────────────

_client: lark.ws.Client | None = None
_api_client: lark.Client | None = None
_on_message: Callable[[P2ImMessageReceiveV1], None] | None = None


# ── 公开 API ──────────────────────────────────────────────────────────


def init_ws_client(
    app_id: str,
    app_secret: str,
    log_level: lark.LogLevel = lark.LogLevel.INFO,
) -> None:
    """初始化 WebSocket 客户端（不启动，由 start_ws_client 启动）。"""
    global _api_client
    _api_client = lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(log_level).build()


def register_message_handler(handler: Callable[[P2ImMessageReceiveV1], None]) -> None:
    """注册消息事件回调。"""
    global _on_message
    _on_message = handler


def start_ws_client(app_id: str, app_secret: str) -> None:
    """启动 WebSocket 长连接（阻塞式，需在独立线程/任务中调用）。"""
    global _client

    if _on_message is None:
        raise RuntimeError("必须先调用 register_message_handler() 注册消息处理器")

    event_handler = (
        lark.EventDispatcherHandler.builder(app_id, app_secret)
        .register_p2_im_message_receive_v1(_on_message)
        .build()
    )

    _client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )

    logger.info("feishu_ws_starting", app_id=app_id[:8] + "***")
    _client.start()


def stop_ws_client() -> None:
    """停止 WebSocket 连接。"""
    global _client
    if _client:
        _client.stop()
        _client = None
        logger.info("feishu_ws_stopped")


def reset_ws_client() -> None:
    """重置全局状态（测试用）。"""
    global _client, _api_client, _on_message
    _client = None
    _api_client = None
    _on_message = None


def send_message(chat_id: str, text: str, msg_type: str = "text") -> dict:
    """通过 SDK 发送消息到飞书。

    Args:
        chat_id: 消息目标 chat_id 或 open_id
        text: 消息文本（当 msg_type=text 时）
        msg_type: 消息类型 (text / interactive)

    Returns:
        {"status": "ok", "message_id": "xxx"} 或 {"status": "error", ...}
    """
    if _api_client is None:
        return {"status": "error", "message": "API 客户端未初始化（请先调用 init_ws_client）"}

    body = (
        CreateMessageRequestBody.builder()
        .receive_id(chat_id)
        .msg_type(msg_type)
        .content(json.dumps({"text": text}))
        .build()
    )

    request = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(body)
        .build()
    )

    try:
        response: CreateMessageResponse = _api_client.request(request)
        if response.success():
            return {
                "status": "ok",
                "message_id": getattr(response.data, "message_id", ""),
            }
        return {
            "status": "error",
            "code": response.code,
            "message": response.msg,
        }
    except Exception as exc:
        logger.error("feishu_send_message_failed: %s", exc)
        return {"status": "error", "message": str(exc)}
