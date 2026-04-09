# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — Harness 引擎."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
from spide.exceptions import SpideError
from spide.harness.engine import Engine, RuntimeBundle


class TestRuntimeBundle:
    """RuntimeBundle 数据类."""

    def test_defaults(self):
        bundle = RuntimeBundle()
        assert bundle.session_id
        assert len(bundle.session_id) == 12
        assert bundle.messages == []
        assert bundle.progress == 0.0


class TestEngineLifecycle:
    """引擎生命周期."""

    @pytest.mark.asyncio
    async def test_start_stop(self, tmp_workspace: Path):
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"), \
             patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock):

            bundle = await engine.start(workspace=str(tmp_workspace))
            assert bundle.session_id
            assert "Spide Agent" in bundle.system_prompt

            await engine.stop()
            assert engine._bundle is None

    @pytest.mark.asyncio
    async def test_not_started_error(self):
        engine = Engine(Settings())
        with pytest.raises(SpideError, match="未启动"):
            _ = engine.bundle

    @pytest.mark.asyncio
    async def test_crawl_no_uapi(self, tmp_workspace: Path):
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(),  # 无 API key
        )
        engine = Engine(settings)

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"):
            await engine.start(workspace=str(tmp_workspace))
            with pytest.raises(SpideError, match="UAPI"):
                await engine.crawl(sources=["weibo"])
            await engine.stop()

    @pytest.mark.asyncio
    async def test_chat_mock(self, tmp_workspace: Path):
        settings = Settings(llm=LLMConfig(common=LLMCommonConfig(api_key="test")))
        engine = Engine(settings)

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"):
            await engine.start(workspace=str(tmp_workspace))

            # Mock LLM chat
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = "你好，我是 Spide"

            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_resp):
                resp = await engine.chat("你好")
                assert resp.choices[0].message.content == "你好，我是 Spide"

            # 验证消息历史
            bundle = engine.bundle
            assert len(bundle.messages) == 2
            assert bundle.messages[0]["role"] == "user"
            assert bundle.messages[1]["role"] == "assistant"

            await engine.stop()
