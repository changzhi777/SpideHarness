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


def test_llm_client_singleton(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """get_llm_client 返回单例。"""
    # 切到无 feishu.yaml 的目录,避免解析 ${ENV_VAR} 占位符
    monkeypatch.chdir(tmp_path)
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


async def test_health_check_sends_auth_header() -> None:
    """健康检查应携带 Authorization header(鉴权服务)。"""
    client = LLMClient(LLMConfig(api_key="sk-test-123"))
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_resp
        result = await client.health_check()
    # 验证调用时传了 Authorization
    assert result is True
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test-123"


async def test_health_check_no_auth_when_no_key() -> None:
    """无 api_key 时不应发送 Authorization header。"""
    client = LLMClient(LLMConfig(api_key=""))
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_get.return_value = mock_resp
        result = await client.health_check()
    assert result is True
    call_kwargs = mock_get.call_args.kwargs
    assert "Authorization" not in call_kwargs["headers"]


def test_load_llm_config_from_yaml_missing_file() -> None:
    """YAML 文件不存在时返回 None。"""
    from dashboard.llm_client import load_llm_config_from_yaml

    assert load_llm_config_from_yaml("/nonexistent/path.yaml") is None


def test_load_llm_config_from_yaml_no_llm_section(tmp_path) -> None:
    """YAML 缺少 llm 节时返回 None。"""
    import yaml

    from dashboard.llm_client import load_llm_config_from_yaml

    cfg = tmp_path / "feishu.yaml"
    cfg.write_text(yaml.safe_dump({"feishu": {"app_id": "cli_xxx"}}), encoding="utf-8")
    assert load_llm_config_from_yaml(str(cfg)) is None


def test_load_llm_config_from_yaml_with_env_placeholder(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """YAML 含 ${ENV_VAR[:default]} 占位符时,正确解析。"""
    import yaml

    from dashboard.llm_client import load_llm_config_from_yaml

    monkeypatch.setenv("SPIDE_LLM__LOCAL_API_KEY", "ak47")
    cfg = tmp_path / "feishu.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "base_url": "http://10.10.10.138:8001",
                    "model": "gemma-4-e4b-it-4bit",
                    "api_key": "${SPIDE_LLM__LOCAL_API_KEY:EMPTY}",
                    "timeout": 180,
                    "supports_function_calling": False,
                }
            }
        ),
        encoding="utf-8",
    )
    result = load_llm_config_from_yaml(str(cfg))
    assert result is not None
    assert result.base_url == "http://10.10.10.138:8001"
    assert result.model == "gemma-4-e4b-it-4bit"
    assert result.api_key == "ak47"  # 解析自环境变量
    assert result.timeout == 180
    assert result.supports_function_calling is False


def test_get_llm_client_loads_from_yaml(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """get_llm_client() 在没有显式 config 时,从 yaml 加载。"""
    import yaml

    from dashboard.llm_client import get_llm_client, reset_llm_client

    monkeypatch.setenv("SPIDE_LLM__LOCAL_API_KEY", "ak47")
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    cfg = configs_dir / "feishu.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "base_url": "http://10.10.10.138:8001",
                    "model": "gemma-4-e4b-it-4bit",
                    "api_key": "${SPIDE_LLM__LOCAL_API_KEY:EMPTY}",
                }
            }
        ),
        encoding="utf-8",
    )
    # 切到临时目录(让 Path('configs/feishu.yaml') 解析到 tmp_path/configs/feishu.yaml)
    monkeypatch.chdir(tmp_path)
    reset_llm_client()
    client = get_llm_client()
    assert client.config.base_url == "http://10.10.10.138:8001"
    assert client.config.api_key == "ak47"
    reset_llm_client()
