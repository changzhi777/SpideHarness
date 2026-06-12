# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — Harness 引擎."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
from spide.exceptions import SpideError
from spide.harness.engine import Engine, RuntimeBundle
from spide.storage.models import HotTopic, TopicSource


class TestRuntimeBundle:
    """RuntimeBundle 数据类."""

    def test_defaults(self):
        bundle = RuntimeBundle()
        assert bundle.session_id
        assert len(bundle.session_id) == 12
        assert bundle.messages == []
        assert bundle.progress == 0.0

    def test_custom_session_id(self):
        bundle = RuntimeBundle(session_id="custom-id")
        assert bundle.session_id == "custom-id"

    def test_default_settings_loaded(self):
        bundle = RuntimeBundle()
        assert bundle.settings is not None


class TestEngineLifecycle:
    """引擎生命周期."""

    async def test_start_stop(self, tmp_workspace: Path):
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
        ):
            bundle = await engine.start(workspace=str(tmp_workspace))
            assert bundle.session_id
            assert "SpideHarness Agent" in bundle.system_prompt

            await engine.stop()
            assert engine._bundle is None

    async def test_not_started_error(self):
        engine = Engine(Settings())
        with pytest.raises(SpideError, match="未启动"):
            _ = engine.bundle

    async def test_double_stop(self, tmp_workspace: Path):
        """连续 stop() 不应报错."""
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
        )
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
        ):
            await engine.start(workspace=str(tmp_workspace))
            await engine.stop()
            await engine.stop()

    async def test_crawl_no_uapi(self, tmp_workspace: Path):
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(),  # 无 API key
        )
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
        ):
            await engine.start(workspace=str(tmp_workspace))
            with pytest.raises(SpideError, match="UAPI"):
                await engine.crawl(sources=["weibo"])
            await engine.stop()

    async def test_crawl_success(self, tmp_workspace: Path):
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        mock_topics = [
            HotTopic(title="热搜1", source=TopicSource.WEIBO, hot_value=99999),
            HotTopic(title="热搜2", source=TopicSource.WEIBO, hot_value=88888),
        ]

        uapi_fetch = patch(
            "spide.spider.uapi_client.UAPIClient.fetch_hotboard",
            new_callable=AsyncMock,
            return_value=mock_topics,
        )
        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
            uapi_fetch,
        ):
            await engine.start(workspace=str(tmp_workspace))
            results = await engine.crawl(sources=["weibo"])
            assert "weibo" in results
            assert len(results["weibo"]) == 2
            assert results["weibo"][0].title == "热搜1"
            await engine.stop()

    async def test_crawl_partial_failure(self, tmp_workspace: Path):
        """部分源采集失败不影响其他源."""
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        mock_topics = [HotTopic(title="百度热搜", source=TopicSource.BAIDU, hot_value=100)]

        async def _mock_fetch(source):
            if source == "weibo":
                raise ConnectionError("网络超时")
            return mock_topics

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.fetch_hotboard", side_effect=_mock_fetch),
        ):
            await engine.start(workspace=str(tmp_workspace))
            results = await engine.crawl(sources=["weibo", "baidu"])
            assert results["weibo"] == []
            assert len(results["baidu"]) == 1
            await engine.stop()

    async def test_chat_mock(self, tmp_workspace: Path):
        settings = Settings(llm=LLMConfig(common=LLMCommonConfig(api_key="test")))
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
        ):
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

    async def test_chat_no_llm(self, tmp_workspace: Path):
        """bundle.llm 为 None 时 chat 应抛异常."""
        settings = Settings(llm=LLMConfig())
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
        ):
            await engine.start(workspace=str(tmp_workspace))
            # 手动置空 LLM 模拟异常场景
            engine.bundle.llm = None
            with pytest.raises(SpideError, match="LLM"):
                await engine.chat("测试")
            await engine.stop()
