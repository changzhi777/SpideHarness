# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 话题深度追踪."""

from unittest.mock import AsyncMock, MagicMock, patch

from spide.spider.deep_tracker import DeepTopicTracker
from spide.storage.models import HotTopic, TopicSource


def _make_topic(title: str, hot_value: int = 5000) -> HotTopic:
    return HotTopic(title=title, source=TopicSource.WEIBO, hot_value=hot_value)


class TestDeepTopicTracker:
    """DeepTopicTracker 测试."""

    async def test_track_topics_empty(self):
        tracker = DeepTopicTracker(llm=MagicMock())
        result = await tracker.track_topics([])
        assert result == []

    @patch("spide.spider.deep_tracker.DeepTopicTracker._analyze_one")
    async def test_track_topics_success(self, mock_analyze):
        from spide.storage.models import TopicDeepTrack

        mock_analyze.return_value = TopicDeepTrack(
            topic_title="AI突破",
            topic_source=TopicSource.WEIBO,
            topic_hot_value=5000,
            analysis_status="completed",
            summary="AI技术重大突破",
            keywords=["AI"],
        )

        tracker = DeepTopicTracker(llm=MagicMock())
        topics = [_make_topic("AI突破")]
        result = await tracker.track_topics(topics, top_n=1)

        assert len(result) == 1
        assert result[0].analysis_status == "completed"
        assert result[0].summary == "AI技术重大突破"

    @patch("spide.spider.deep_tracker.DeepTopicTracker._analyze_one")
    async def test_track_topics_handles_error(self, mock_analyze):
        mock_analyze.side_effect = Exception("LLM failed")

        tracker = DeepTopicTracker(llm=MagicMock())
        topics = [_make_topic("AI突破")]
        result = await tracker.track_topics(topics, top_n=1)

        assert len(result) == 1
        assert result[0].analysis_status == "failed"

    @patch("spide.spider.deep_tracker.DeepTopicTracker._analyze_one")
    async def test_track_topics_top_n_limit(self, mock_analyze):
        from spide.storage.models import TopicDeepTrack

        mock_analyze.return_value = TopicDeepTrack(
            topic_title="x",
            topic_source=TopicSource.WEIBO,
            analysis_status="completed",
        )

        tracker = DeepTopicTracker(llm=MagicMock())
        topics = [_make_topic(f"topic_{i}") for i in range(10)]
        result = await tracker.track_topics(topics, top_n=3)

        assert len(result) == 3
        assert mock_analyze.call_count == 3


class TestBuildContent:
    """_build_content 测试."""

    def test_basic_content(self):
        topic = _make_topic("AI突破", 5000)
        articles = [
            {"title": "AI进展", "snippet": "技术突破"},
            {"title": "AI应用", "snippet": "广泛落地"},
        ]
        content = DeepTopicTracker._build_content(topic, articles)

        assert "AI突破" in content
        assert "5000" in content
        assert "AI进展" in content
        assert "技术突破" in content

    def test_empty_articles(self):
        topic = _make_topic("测试")
        content = DeepTopicTracker._build_content(topic, [])
        assert "测试" in content

    def test_articles_limited_to_three(self):
        topic = _make_topic("测试")
        articles = [{"title": f"文章{i}"} for i in range(5)]
        content = DeepTopicTracker._build_content(topic, articles)
        assert "文章0" in content
        assert "文章2" in content
        # 第 4、5 篇不应出现（只取前 3 篇）
        assert "文章3" not in content
        assert "文章4" not in content


class TestWebSearch:
    """_web_search 集成测试."""

    @patch("spide.mcp.search_provider.WebSearchProvider")
    async def test_web_search_returns_articles(self, mock_cls):
        from spide.mcp.search_provider import SearchResult

        mock_provider = AsyncMock()
        mock_provider.search.return_value = [
            SearchResult(title="AI进展", url="https://a.com", description="描述"),
        ]
        mock_cls.return_value = mock_provider

        tracker = DeepTopicTracker(llm=MagicMock())
        results = await tracker._web_search("AI")

        assert len(results) == 1
        assert results[0]["title"] == "AI进展"
        assert results[0]["url"] == "https://a.com"

    @patch("spide.mcp.search_provider.WebSearchProvider")
    async def test_web_search_error_returns_empty(self, mock_cls):
        mock_cls.side_effect = Exception("Network error")

        tracker = DeepTopicTracker(llm=MagicMock())
        results = await tracker._web_search("测试")

        assert results == []
