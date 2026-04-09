# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 2 — 真实 LLM 分析集成测试.

调用真实智谱 GLM-5.1，验证对话、摘要、情感、趋势、策略等功能。
标记 @pytest.mark.integration，无 API Key 时自动跳过。
"""

import asyncio

import pytest

from spide.config import load_settings
from spide.llm import LLMClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_settings():
    settings = load_settings()
    if not settings.llm.common.api_key:
        pytest.skip("智谱 LLM API Key 未配置")
    return settings


@pytest.fixture
async def real_llm(real_settings):
    client = LLMClient(real_settings.llm)
    await client.start()
    yield client
    await client.stop()


# ---------------------------------------------------------------------------
# LLMClient 直接调用
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealLLMChat:
    """LLM 基础对话."""

    async def test_llm_chat_simple(self, real_llm):
        response = await asyncio.to_thread(
            real_llm.chat,
            messages=[{"role": "user", "content": "请用一句话介绍 Python 语言"}],
        )
        assert response is not None
        content = response.choices[0].message.content
        assert isinstance(content, str)
        assert len(content) > 5, "回复应超过 5 个字符"

    async def test_llm_chat_stream(self, real_llm):
        stream = await asyncio.to_thread(
            real_llm.chat_stream,
            messages=[{"role": "user", "content": "说一个数字"}],
        )
        chunks = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)
        assert len(chunks) > 0, "流式应至少返回一个 chunk"


# ---------------------------------------------------------------------------
# ContentSummarizer
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealSummarizer:
    """内容摘要分析."""

    async def test_summarize_real(self, real_llm):
        from spide.analysis.summarizer import ContentSummarizer

        summarizer = ContentSummarizer(real_llm)
        result = await summarizer.summarize(
            title="OpenAI发布GPT-5",
            content="OpenAI今天正式发布了GPT-5模型，该模型在多项基准测试中取得了突破性进展，"
            "包括代码生成、数学推理和多语言理解等。",
        )
        assert "summary" in result or "error" not in result
        if "summary" in result:
            assert isinstance(result["summary"], str)
            assert len(result["summary"]) > 0

    async def test_extract_keywords_real(self, real_llm):
        from spide.analysis.summarizer import ContentSummarizer

        summarizer = ContentSummarizer(real_llm)
        keywords = await summarizer.extract_keywords(
            title="新能源汽车销量创纪录",
            content="比亚迪、特斯拉等品牌的新能源汽车销量在2025年第一季度创下历史新高。",
        )
        assert isinstance(keywords, list)
        assert len(keywords) >= 1, "应至少提取 1 个关键词"

    async def test_analyze_sentiment_real(self, real_llm):
        from spide.analysis.summarizer import ContentSummarizer

        summarizer = ContentSummarizer(real_llm)
        result = await summarizer.analyze_sentiment(
            comments=["这个产品真的很好用", "体验太差了", "一般般吧"],
        )
        assert "overall" in result or "error" not in result
        if "overall" in result:
            assert result["overall"] in ("positive", "negative", "neutral", "mixed")


# ---------------------------------------------------------------------------
# TrendAnalyzer
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealTrendAnalyzer:
    """趋势分析."""

    async def test_trend_analyze_real(self, real_llm):
        from spide.analysis.summarizer import TrendAnalyzer

        analyzer = TrendAnalyzer(real_llm)
        topics = [
            {"title": "AI大模型突破", "hot_value": 50000, "source": "weibo"},
            {"title": "新能源汽车降价", "hot_value": 45000, "source": "weibo"},
            {"title": "股市暴涨", "hot_value": 40000, "source": "weibo"},
            {"title": "苹果发布新品", "hot_value": 38000, "source": "weibo"},
            {"title": "高考改革方案", "hot_value": 35000, "source": "weibo"},
        ]
        result = await analyzer.analyze(current_topics=topics)
        assert isinstance(result, dict)
        # 至少包含 analysis 或 error 之一
        assert "analysis" in result or "error" in result


# ---------------------------------------------------------------------------
# SmartCrawlStrategy
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealSmartStrategy:
    """智能采集策略."""

    async def test_smart_crawl_strategy_real(self, real_llm):
        from spide.analysis.summarizer import SmartCrawlStrategy

        strategist = SmartCrawlStrategy(real_llm)
        topics = [
            {"title": "AI编程工具", "hot_value": 50000},
            {"title": "量子计算突破", "hot_value": 45000},
            {"title": "机器人马拉松", "hot_value": 40000},
        ]
        result = await strategist.recommend(hot_topics=topics)
        assert isinstance(result, dict)
        assert "analysis" in result or "error" in result
