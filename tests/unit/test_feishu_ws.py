"""飞书 WebSocket 客户端测试."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from dashboard.feishu_handler import (
    _extract_text,
    _process_and_reply,
    parse_command,
)
from dashboard.feishu_ws_client import (
    init_ws_client,
    register_message_handler,
    reset_ws_client,
    send_message,
    stop_ws_client,
)

# ── _extract_text ─────────────────────────────────────────────────────


def test_extract_text_text_message():
    content = json.dumps({"text": "crawl weibo"})
    result = _extract_text(content, "text")
    assert result == "crawl weibo"


def test_extract_text_empty():
    result = _extract_text("{}", "text")
    assert result == ""


def test_extract_text_post_message():
    content = json.dumps(
        {
            "title": "标题",
            "content": [[{"tag": "text", "text": "段落1"}]],
        }
    )
    result = _extract_text(content, "post")
    assert "标题" in result
    assert "段落1" in result


def test_extract_text_invalid_json():
    result = _extract_text("not json", "text")
    assert result == "not json"


# ── parse_command ─────────────────────────────────────────────────────


def test_parse_command_crawl():
    assert parse_command("crawl weibo") == ("crawl", {"source": "weibo"})


def test_parse_command_status():
    assert parse_command("status") == ("status", {})


def test_parse_command_help():
    assert parse_command("help") == ("help", {})


def test_parse_command_track():
    assert parse_command("track weibo 20") == ("track", {"source": "weibo", "top_n": 20})


def test_parse_command_unknown():
    assert parse_command("随便说点什么") is None


def test_parse_command_empty():
    assert parse_command("") is None


# ── WebSocket 客户端 ──────────────────────────────────────────────────


def test_init_and_send_message():
    """send_message 在未初始化时返回错误，不会崩溃。"""
    from lark_oapi import LogLevel

    reset_ws_client()
    # 未初始化 → 错误
    result = send_message("chat_123", "hello")
    assert result["status"] == "error"
    assert "未初始化" in result["message"]

    # 初始化后 → 仍会因假 app_id 失败但不会崩溃
    init_ws_client("test_app_id", "test_secret", log_level=LogLevel.INFO)


def test_register_message_handler():
    reset_ws_client()
    called = []

    def handler(event):
        called.append(event)

    register_message_handler(handler)
    from dashboard.feishu_ws_client import _on_message

    assert _on_message is handler


def test_stop_ws_client_noop():
    stop_ws_client()


# ── _process_and_reply ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_command_reply():
    with (
        patch("dashboard.feishu_handler.execute_command", new_callable=AsyncMock) as mock_exec,
        patch("dashboard.feishu_ws_client.send_message") as mock_send,
    ):
        mock_exec.return_value = {"status": "ok", "message": "帮助文本"}
        mock_send.return_value = {"status": "ok"}

        await _process_and_reply("help", "user_123", "chat_456")

        mock_exec.assert_called_once_with("help", {})
        mock_send.assert_called_once_with("chat_456", "帮助文本")


@pytest.mark.asyncio
async def test_process_agent_path_handles_failure():
    """非指令消息进入 Agent 路径，即使 Agent 失败也会发送错误提示。"""
    with (
        patch("dashboard.feishu_handler.parse_command", return_value=None),
        patch("dashboard.feishu_agent.get_feishu_agent") as mock_get_agent,
        patch("dashboard.feishu_ws_client.send_message") as mock_send,
    ):
        mock_send.return_value = {"status": "ok"}
        # 模拟 Agent 初始化失败
        mock_agent = AsyncMock()
        mock_agent.init.side_effect = Exception("LLM 不可用")
        mock_get_agent.return_value = mock_agent

        await _process_and_reply("今天有什么热搜？", "user_123", "chat_456")
        # send_message 被调用发送错误提示
        assert mock_send.call_count >= 1
