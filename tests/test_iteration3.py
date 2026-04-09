# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""迭代 3 验证测试 — Prompt + Memory + Spider + Pipeline."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.storage.models import HotTopic, TopicSource

# ---------------------------------------------------------------------------
# Prompt 层叠系统测试
# ---------------------------------------------------------------------------


class TestPrompts:
    """Prompt 组装测试."""

    def test_build_system_prompt_with_workspace(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(workspace=str(tmp_path))

        # 必须包含基础指令
        assert "SpideHarness Agent" in prompt
        assert "热点新闻" in prompt
        # 包含工作空间信息
        assert str(tmp_path) in prompt

    def test_build_system_prompt_with_extra(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(
            workspace=str(tmp_path),
            extra_prompt="自定义指令：只采集科技新闻",
        )
        assert "自定义指令" in prompt

    def test_build_system_prompt_includes_soul(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import get_soul_path, initialize_workspace

        initialize_workspace(str(tmp_path))

        # 修改灵魂文件
        soul_path = get_soul_path(tmp_path)
        soul_path.write_text("测试灵魂内容：抓取最新资讯", encoding="utf-8")

        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(workspace=str(tmp_path))
        assert "测试灵魂内容" in prompt


# ---------------------------------------------------------------------------
# Memory 管理测试
# ---------------------------------------------------------------------------


class TestMemory:
    """Memory CRUD 测试."""

    def test_add_and_list(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.memory import add_memory, list_memory_files

        add_memory(str(tmp_path), title="微博采集规则", content="每5分钟采集一次")
        add_memory(str(tmp_path), title="百度采集规则", content="注意反爬")

        files = list_memory_files(str(tmp_path))
        assert len(files) == 2

    def test_remove(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.memory import add_memory, list_memory_files, remove_memory

        add_memory(str(tmp_path), title="测试记忆", content="内容")
        assert len(list_memory_files(str(tmp_path))) == 1

        assert remove_memory(str(tmp_path), name="测试记忆") is True
        assert len(list_memory_files(str(tmp_path))) == 0

    def test_get_content(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.memory import add_memory, get_memory_content

        add_memory(str(tmp_path), title="规则A", content="采集间隔300秒")
        content = get_memory_content(str(tmp_path), name="规则A")
        assert content is not None
        assert "300秒" in content

    def test_memory_index_updated(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import get_memory_index_path, initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.memory import add_memory

        add_memory(str(tmp_path), title="测试条目", content="内容")

        index_path = get_memory_index_path(tmp_path)
        index_content = index_path.read_text(encoding="utf-8")
        assert "测试条目" in index_content


# ---------------------------------------------------------------------------
# Spider Pipeline 测试
# ---------------------------------------------------------------------------


class TestPipeline:
    """数据管道测试."""

    def test_parse_hot_items(self):
        from spide.spider.pipeline import parse_hot_items

        raw = [
            {"title": "测试热搜1", "hot_value": "10000", "index": 1, "url": "https://example.com/1"},
            {"title": "测试热搜2", "hot_value": 5000, "index": 2},
            {"title": "", "hot_value": 100, "index": 3},  # 空标题应跳过
        ]

        topics = parse_hot_items(raw, source="weibo")
        assert len(topics) == 2
        assert topics[0].title == "测试热搜1"
        assert topics[0].hot_value == 10000
        assert topics[0].rank == 1
        assert topics[0].url == "https://example.com/1"

    def test_deduplicate_items(self):
        from spide.spider.pipeline import deduplicate_items

        items = [
            HotTopic(title="重复话题", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="重复话题", source=TopicSource.BAIDU, hot_value=200),
            HotTopic(title="唯一话题", source=TopicSource.ZHIHU, hot_value=50),
        ]

        result = deduplicate_items(items)
        assert len(result) == 2

        # 保留热度更高的
        dup = next(t for t in result if t.title == "重复话题")
        assert dup.hot_value == 200


# ---------------------------------------------------------------------------
# Fetcher 测试
# ---------------------------------------------------------------------------


class TestFetcher:
    """AsyncFetcher 测试."""

    @pytest.mark.asyncio
    async def test_get_text(self):
        from spide.spider.fetcher import AsyncFetcher

        fetcher = AsyncFetcher()
        await fetcher.start()

        html = "<html><body><h1>标题</h1><script>忽略</script><p>正文内容</p></body></html>"
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=html)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            text = await fetcher.get_text("https://example.com")
            assert "标题" in text
            assert "正文内容" in text
            assert "忽略" not in text

        await fetcher.stop()

    @pytest.mark.asyncio
    async def test_fetcher_not_started(self):
        from spide.exceptions import SpiderError
        from spide.spider.fetcher import AsyncFetcher

        fetcher = AsyncFetcher()
        with pytest.raises(SpiderError, match="未初始化"):
            await fetcher.get("https://example.com")


# ---------------------------------------------------------------------------
# UAPI Client 测试（mock）
# ---------------------------------------------------------------------------


class TestUAPIClient:
    """UAPI 热搜客户端测试."""

    @pytest.mark.asyncio
    async def test_fetch_hotboard_mock(self):
        from spide.config import UAPIConfig
        from spide.spider.uapi_client import UAPIClient

        config = UAPIConfig(api_key="test-key")
        client = UAPIClient(config)
        await client.start()

        mock_response = {
            "type": "weibo",
            "update_time": "2026-04-08 12:00:00",
            "list": [
                {"title": "热搜1", "hot_value": "99999", "index": 1, "url": "https://weibo.com/1"},
                {"title": "热搜2", "hot_value": "88888", "index": 2, "url": "https://weibo.com/2"},
            ],
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_get.return_value = mock_resp

            topics = await client.fetch_hotboard("weibo")
            assert len(topics) == 2
            assert topics[0].title == "热搜1"
            assert topics[0].source == TopicSource.WEIBO
            assert topics[0].hot_value == 99999

        await client.stop()

    @pytest.mark.asyncio
    async def test_uapi_not_started(self):
        from spide.config import UAPIConfig
        from spide.exceptions import SpiderError
        from spide.spider.uapi_client import UAPIClient

        config = UAPIConfig()
        client = UAPIClient(config)
        with pytest.raises(SpiderError, match="未初始化"):
            await client.fetch_hotboard("weibo")


# ---------------------------------------------------------------------------
# LLM Client 测试（mock）
# ---------------------------------------------------------------------------


class TestLLMClient:
    """LLM 客户端测试."""

    def test_chat_mock(self):
        from spide.config import LLMCommonConfig, LLMConfig, LLMTextConfig
        from spide.llm import LLMClient

        config = LLMConfig(
            common=LLMCommonConfig(api_key="test-key"),
            text=LLMTextConfig(model="glm-5.1"),
        )
        client = LLMClient(config)
        client._client = MagicMock()

        # Mock ZaiClient.chat.completions.create 返回值
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "你好，我是 SpideHarness Agent"
        client._client.chat.completions.create.return_value = mock_response

        response = client.chat(messages=[{"role": "user", "content": "你好"}])
        assert response.choices[0].message.content == "你好，我是 SpideHarness Agent"

    def test_not_started(self):
        from spide.config import LLMConfig
        from spide.exceptions import LLMError
        from spide.llm import LLMClient

        client = LLMClient(LLMConfig())
        with pytest.raises(LLMError, match="未初始化"):
            client.chat(messages=[{"role": "user", "content": "test"}])

    def test_web_search_mock(self):
        from spide.config import LLMCommonConfig, LLMConfig
        from spide.llm import LLMClient

        config = LLMConfig(common=LLMCommonConfig(api_key="test-key"))
        client = LLMClient(config)
        client._client = MagicMock()

        mock_result = MagicMock()
        mock_result.search_result = [{"title": "测试", "url": "https://example.com"}]
        client._client.web_search.web_search.return_value = mock_result

        result = client.web_search(query="测试搜索")
        assert result is not None


# ---------------------------------------------------------------------------
# Engine 测试（mock）
# ---------------------------------------------------------------------------


class TestEngine:
    """Harness 调度引擎测试."""

    @pytest.mark.asyncio
    async def test_engine_start_stop(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        from spide.workspace import initialize_workspace
        initialize_workspace(str(tmp_path))

        from spide.config import LLMCommonConfig, LLMConfig, Settings, UAPIConfig
        from spide.harness.engine import Engine

        settings = Settings(
            llm=LLMConfig(common=LLMCommonConfig(api_key="test-key")),
            uapi=UAPIConfig(api_key="test-uapi-key"),
        )
        engine = Engine(settings)

        with (
            patch("spide.llm.LLMClient.start", new_callable=AsyncMock),
            patch("spide.llm.LLMClient.stop"),
            patch("spide.spider.uapi_client.UAPIClient.start", new_callable=AsyncMock),
            patch("spide.spider.uapi_client.UAPIClient.stop", new_callable=AsyncMock),
        ):
            bundle = await engine.start(workspace=str(tmp_path))
            assert bundle.session_id
            assert bundle.system_prompt
            assert "SpideHarness Agent" in bundle.system_prompt

            await engine.stop()
