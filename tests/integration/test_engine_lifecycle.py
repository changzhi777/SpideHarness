# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""集成测试 — Engine 生命周期（SQLite 真实 + LLM/UAPI mock）."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
from spide.harness.engine import Engine
from spide.storage.models import HotTopic, TopicSource


class TestEngineIntegration:
    """Engine 真实生命周期."""

    @pytest.mark.asyncio
    async def test_start_creates_session_files(self, tmp_workspace: Path):
        """start() 应创建会话存储目录."""
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
            assert bundle.workspace == str(tmp_workspace)

            # 验证 session_storage 已初始化
            assert bundle.session_storage is not None

            await engine.stop()

    @pytest.mark.asyncio
    async def test_stop_saves_session_snapshot(self, tmp_workspace: Path):
        """stop() 应保存会话快照."""
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

            # 模拟一些消息
            bundle.messages.append({"role": "user", "content": "测试消息"})
            bundle.progress = 0.5

            await engine.stop()

            # 验证会话快照已保存
            from spide.session_storage import SessionStorage

            storage = SessionStorage(workspace=str(tmp_workspace))
            latest = await storage.load_latest()
            assert latest is not None
            assert latest["session_id"] == bundle.session_id

    @pytest.mark.asyncio
    async def test_crawl_and_store(self, tmp_workspace: Path, tmp_db):
        """采集 → 存储完整流程."""
        from spide.storage.sqlite_repo import SqliteRepository

        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
            uapi=UAPIConfig(api_key="test-uapi"),
        )
        engine = Engine(settings)

        mock_topics = [
            HotTopic(title="集成测试热搜", source=TopicSource.WEIBO, hot_value=9999, rank=1),
        ]

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"), \
             patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock), \
             patch("spide.spider.uapi_client.UAPIClient.fetch_hotboard", new_callable=AsyncMock, return_value=mock_topics):

            await engine.start(workspace=str(tmp_workspace))
            results = await engine.crawl(sources=["weibo"])

            assert "weibo" in results
            assert len(results["weibo"]) == 1
            assert results["weibo"][0].title == "集成测试热搜"

            # 存入 SQLite
            repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
            await repo.start()
            ids = await repo.save_many(results["weibo"])
            assert len(ids) == 1

            stored = await repo.query(source="weibo")
            assert len(stored) == 1
            assert stored[0].title == "集成测试热搜"
            await repo.stop()

            await engine.stop()

    @pytest.mark.asyncio
    async def test_chat_maintains_history(self, tmp_workspace: Path):
        """多轮对话消息历史维护."""
        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test")),
        )
        engine = Engine(settings)

        with patch("spide.llm.LLMClient.start", new_callable=AsyncMock), \
             patch("spide.llm.LLMClient.stop"):

            await engine.start(workspace=str(tmp_workspace))

            # 模拟第一轮对话
            mock_resp1 = MagicMock()
            mock_resp1.choices = [MagicMock()]
            mock_resp1.choices[0].message.content = "第一轮回复"

            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_resp1):
                await engine.chat("你好")

            # 模拟第二轮对话
            mock_resp2 = MagicMock()
            mock_resp2.choices = [MagicMock()]
            mock_resp2.choices[0].message.content = "第二轮回复"

            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_resp2):
                await engine.chat("继续")

            # 验证消息历史
            bundle = engine.bundle
            assert len(bundle.messages) == 4  # 2 user + 2 assistant
            assert bundle.messages[0]["role"] == "user"
            assert bundle.messages[1]["role"] == "assistant"
            assert bundle.messages[2]["role"] == "user"
            assert bundle.messages[3]["role"] == "assistant"

            await engine.stop()
