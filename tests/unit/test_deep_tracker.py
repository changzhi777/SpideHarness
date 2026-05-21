# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 话题深度追踪."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
