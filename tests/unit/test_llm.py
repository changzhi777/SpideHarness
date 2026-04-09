# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — LLM 客户端."""

from unittest.mock import MagicMock

import pytest

from spide.config import LLMCommonConfig, LLMConfig
from spide.exceptions import LLMError
from spide.llm import LLMClient


class TestLLMParams:
    """参数构建验证."""

    def test_default_params(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        params = client._build_chat_params(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert params["model"] == "glm-5.1"
        assert params["stream"] is False

    def test_custom_params(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        params = client._build_chat_params(
            messages=[{"role": "user", "content": "hi"}],
            model="glm-5v-turbo",
            temperature=0.5,
            max_tokens=1024,
            stream=True,
        )
        assert params["model"] == "glm-5v-turbo"
        assert params["temperature"] == 0.5
        assert params["max_tokens"] == 1024
        assert params["stream"] is True

    def test_thinking_mode(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        params = client._build_chat_params(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert "thinking" in params
        assert params["thinking"]["type"] == "enabled"

    def test_tools_passed(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        tools = [{"type": "function", "function": {"name": "test"}}]
        params = client._build_chat_params(
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        )
        assert params["tools"] == tools


class TestLLMErrors:
    """错误处理."""

    def test_not_initialized(self):
        client = LLMClient(LLMConfig())
        with pytest.raises(LLMError, match="未初始化"):
            client.chat(messages=[])

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        client = LLMClient(LLMConfig())
        with pytest.raises(LLMError, match="未配置"):
            await client.start()

    def test_chat_mock(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        client._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "回复"
        client._client.chat.completions.create.return_value = mock_resp

        resp = client.chat(messages=[{"role": "user", "content": "hi"}])
        assert resp.choices[0].message.content == "回复"

    def test_web_search_mock(self):
        client = LLMClient(LLMConfig(common=LLMCommonConfig(api_key="test")))
        client._client = MagicMock()
        client._client.web_search.web_search.return_value = {"results": []}
        result = client.web_search(query="测试")
        assert result is not None
