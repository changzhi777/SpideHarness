"""LLM 客户端测试（OpenAI 兼容 + 健康检查 + 响应解析 + JSON Action 兜底）."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dashboard.llm_client import (
    LLMClient,
    LLMConfig,
    get_llm_client,
    reset_llm_client,
)


@pytest.fixture
def llm_config() -> LLMConfig:
    return LLMConfig(
        base_url="http://localhost:8001",
        model="gemma-3-4b-it",
        api_key="EMPTY",
        timeout=10,
    )


def test_llm_config_defaults() -> None:
    """默认配置可实例化。"""
    cfg = LLMConfig()
    assert cfg.base_url == "http://localhost:8001"
    assert cfg.supports_function_calling is False
    assert cfg.max_tokens == 2048


def test_llm_client_singleton() -> None:
    """get_llm_client 返回单例。"""
    reset_llm_client()
    c1 = get_llm_client()
    c2 = get_llm_client()
    assert c1 is c2
    reset_llm_client()


def test_extract_json_action_simple() -> None:
    """JSON Action 提取 — 简单 action/arguments 结构。"""
    content = '思考: 调用爬虫\n```json\n{"action": "crawl_hot_topics", "arguments": {"source": "weibo"}}\n```\n完成'
    tool_calls = LLMClient._extract_json_action(content)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "crawl_hot_topics"
    assert tool_calls[0].arguments == {"source": "weibo"}


def test_extract_json_action_alternative_keys() -> None:
    """JSON Action 提取 — 兼容 tool/params 备选键名。"""
    content = '```json\n{"tool": "web_search", "params": {"query": "AI"}}\n```'
    tool_calls = LLMClient._extract_json_action(content)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "web_search"
    assert tool_calls[0].arguments == {"query": "AI"}


def test_extract_json_action_no_match() -> None:
    """无 JSON Action 时返回空列表。"""
    content = "普通文本响应，无工具调用"
    assert LLMClient._extract_json_action(content) == []


def test_extract_json_action_invalid_json() -> None:
    """JSON 解析失败时跳过该块。"""
    content = '```json\n{invalid json}\n```\n```json\n{"action": "x", "arguments": {}}\n```'
    tool_calls = LLMClient._extract_json_action(content)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "x"


def test_parse_response_with_tool_calls() -> None:
    """解析带 tool_calls 的响应。"""
    client = LLMClient(LLMConfig())
    data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "crawl_hot_topics",
                                "arguments": '{"source": "weibo"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    resp = client._parse_response(data)
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "crawl_hot_topics"
    assert resp.tool_calls[0].arguments == {"source": "weibo"}
    assert resp.finish_reason == "tool_calls"


def test_parse_response_empty_choices() -> None:
    """空 choices 返回 finish_reason=empty。"""
    client = LLMClient(LLMConfig())
    resp = client._parse_response({"choices": []})
    assert resp.finish_reason == "empty"
    assert resp.content == ""


async def test_health_check_success() -> None:
    """健康检查成功：/v1/models 返回 200。"""
    client = LLMClient(LLMConfig())
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_resp
        result = await client.health_check()
    assert result is True
    assert client._healthy is True


async def test_health_check_failure() -> None:
    """健康检查失败：连接异常。"""
    client = LLMClient(LLMConfig())
    with patch("aiohttp.ClientSession.get", side_effect=Exception("connect refused")):
        result = await client.health_check()
    assert result is False
    assert client._healthy is False
