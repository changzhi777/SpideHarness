# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — AI 分析模块."""

import json
from unittest.mock import MagicMock

import pytest

from spide.analysis.summarizer import (
    ContentSummarizer,
    SmartCrawlStrategy,
    TrendAnalyzer,
)


def _mock_llm_response(json_str: str) -> MagicMock:
    """构造 mock LLM 响应."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = json_str
    return mock


class TestContentSummarizer:
    """内容智能摘要."""

    @pytest.mark.asyncio
    async def test_summarize(self):
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "summary": "AI 技术取得重大突破",
                    "keywords": ["AI", "大模型", "技术突破"],
                    "category": "tech",
                })
            )
        )

        summarizer = ContentSummarizer(llm)
        result = await summarizer.summarize(
            title="AI 行业突破", content="OpenAI 发布了新的 GPT 模型..."
        )

        assert result["summary"] == "AI 技术取得重大突破"
        assert "AI" in result["keywords"]
        assert result["category"] == "tech"

    @pytest.mark.asyncio
    async def test_extract_keywords(self):
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "summary": "摘要",
                    "keywords": ["新能源", "汽车", "电池"],
                    "category": "tech",
                })
            )
        )

        summarizer = ContentSummarizer(llm)
        keywords = await summarizer.extract_keywords(title="新能源", content="电池技术...")

        assert len(keywords) == 3
        assert "新能源" in keywords

    @pytest.mark.asyncio
    async def test_analyze_sentiment(self):
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "positive_ratio": 0.6,
                    "negative_ratio": 0.2,
                    "neutral_ratio": 0.2,
                    "overall": "positive",
                    "top_opinions": ["支持", "不错"],
                })
            )
        )

        summarizer = ContentSummarizer(llm)
        result = await summarizer.analyze_sentiment(
            comments=["好文章", "写得不错", "一般般"]
        )

        assert result["overall"] == "positive"
        assert result["positive_ratio"] == 0.6

    @pytest.mark.asyncio
    async def test_summarize_json_with_markdown(self):
        """LLM 返回带 markdown 代码块的 JSON."""
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                '```json\n{"summary": "测试", "keywords": ["a"], "category": "other"}\n```'
            )
        )

        summarizer = ContentSummarizer(llm)
        result = await summarizer.summarize(title="测试", content="内容")

        assert result["summary"] == "测试"

    @pytest.mark.asyncio
    async def test_summarize_llm_error(self):
        """LLM 调用失败."""
        llm = MagicMock()
        llm.chat = MagicMock(side_effect=Exception("API Error"))

        summarizer = ContentSummarizer(llm)
        result = await summarizer.summarize(title="测试", content="内容")

        assert "error" in result


class TestSmartCrawlStrategy:
    """智能采集策略."""

    @pytest.mark.asyncio
    async def test_recommend(self):
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "trending_topics": [{"title": "AI", "reason": "热度飙升"}],
                    "recommended_sources": ["weibo", "zhihu"],
                    "search_keywords": ["AI", "大模型"],
                    "analysis": "AI 相关话题持续升温",
                })
            )
        )

        strategist = SmartCrawlStrategy(llm)
        result = await strategist.recommend(
            hot_topics=[
                {"title": "AI 大模型突破", "hot_value": 99999, "source": "weibo"},
            ]
        )

        assert "AI" in result["search_keywords"]
        assert len(result["recommended_sources"]) == 2

    @pytest.mark.asyncio
    async def test_recommend_error(self):
        llm = MagicMock()
        llm.chat = MagicMock(side_effect=Exception("Error"))

        strategist = SmartCrawlStrategy(llm)
        result = await strategist.recommend(hot_topics=[])

        assert "error" in result


class TestTrendAnalyzer:
    """热点趋势分析."""

    @pytest.mark.asyncio
    async def test_single_analysis(self):
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "top_categories": ["科技", "社会"],
                    "hot_domains": ["AI", "新能源"],
                    "analysis": "科技类话题占主导",
                    "recommendations": ["关注 AI 领域"],
                })
            )
        )

        analyzer = TrendAnalyzer(llm)
        result = await analyzer.analyze(
            current_topics=[
                {"title": "AI 突破", "hot_value": 10000, "source": "weibo"},
            ]
        )

        assert "科技" in result["top_categories"]

    @pytest.mark.asyncio
    async def test_compare_analysis(self):
        """对比分析 — 纯本地计算，不需要 LLM."""
        llm = MagicMock()  # 不应该被调用

        analyzer = TrendAnalyzer(llm)
        result = await analyzer.analyze(
            current_topics=[
                {"title": "话题A", "hot_value": 20000},
                {"title": "话题B", "hot_value": 15000},
                {"title": "话题C", "hot_value": 5000},
            ],
            previous_topics=[
                {"title": "话题A", "hot_value": 10000},
                {"title": "话题B", "hot_value": 20000},
                {"title": "话题D", "hot_value": 8000},
            ],
        )

        assert result["new_entries"] == ["话题C"]
        assert "话题D" in result["disappeared"]
        assert result["persisted_count"] == 2
        # 话题A 热度上升
        rising_titles = [r["title"] for r in result["rising"]]
        assert "话题A" in rising_titles
        # 话题B 热度下降
        falling_titles = [f["title"] for f in result["falling"]]
        assert "话题B" in falling_titles

    @pytest.mark.asyncio
    async def test_compare_empty_previous(self):
        """空历史数据回退到单次分析."""
        llm = MagicMock()
        llm.chat = MagicMock(
            return_value=_mock_llm_response(
                json.dumps({
                    "top_categories": ["社会"],
                    "hot_domains": ["民生"],
                    "analysis": "测试",
                    "recommendations": [],
                })
            )
        )

        analyzer = TrendAnalyzer(llm)
        result = await analyzer.analyze(
            current_topics=[{"title": "测试", "hot_value": 100}]
        )

        assert "top_categories" in result
