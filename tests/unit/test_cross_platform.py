# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 跨平台关联分析."""

from unittest.mock import MagicMock

from spide.analysis.cross_platform import CrossPlatformAnalyzer
from spide.storage.models import HotTopic, TopicSource


def _make_topic(title: str, source: TopicSource, hot_value: int = 1000) -> HotTopic:
    return HotTopic(title=title, source=source, hot_value=hot_value)


class TestCrossPlatformDedup:
    """跨平台去重测试."""

    def test_dedup_similar_titles(self):
        analyzer = CrossPlatformAnalyzer(llm=MagicMock())
        topics_by_source = {
            "weibo": [_make_topic("AI大模型突破", TopicSource.WEIBO, 5000)],
            "zhihu": [_make_topic("AI大模型突破", TopicSource.ZHIHU, 3000)],
        }

        deduped = analyzer._dedup_cross_platform(topics_by_source)
        assert len(deduped) == 1
        assert len(deduped[0]["platforms"]) == 2

    def test_no_dedup_different_titles(self):
        analyzer = CrossPlatformAnalyzer(llm=MagicMock())
        topics_by_source = {
            "weibo": [_make_topic("天气炎热", TopicSource.WEIBO)],
            "zhihu": [_make_topic("股市暴跌", TopicSource.ZHIHU)],
        }

        deduped = analyzer._dedup_cross_platform(topics_by_source)
        assert len(deduped) == 2

    def test_empty_input(self):
        analyzer = CrossPlatformAnalyzer(llm=MagicMock())
        deduped = analyzer._dedup_cross_platform({})
        assert deduped == []


class TestFallbackClusters:
    """降级聚类测试."""

    def test_fallback_by_platform(self):
        topics = [
            {"title": "a", "source": "weibo", "platforms": ["weibo"], "hot_value": 1000},
            {"title": "b", "source": "zhihu", "platforms": ["zhihu"], "hot_value": 2000},
        ]
        clusters = CrossPlatformAnalyzer._fallback_clusters(topics)
        assert len(clusters) == 2
        assert clusters[0].platform_sources == ["weibo"]
        assert clusters[1].platform_sources == ["zhihu"]


class TestParseClusters:
    """聚类解析测试."""

    def test_parse_valid_json(self):
        raw = [
            {
                "name": "AI",
                "keywords": ["AI"],
                "platforms": ["weibo"],
                "topic_titles": ["AI突破"],
                "cross_platform": True,
                "analysis": "test",
            },
        ]
        clusters = CrossPlatformAnalyzer._parse_clusters(raw)
        assert len(clusters) == 1
        assert clusters[0].cluster_name == "AI"
        assert clusters[0].cross_platform is True


class TestAnalyzeWithMock:
    """analyze 异步方法 mock 测试."""

    async def test_analyze_with_llm_clusters(self):
        from unittest.mock import MagicMock

        llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = """```json
[{"name": "科技", "keywords": ["AI"], "platforms": ["weibo"],
  "topic_titles": ["AI突破"], "cross_platform": true,
  "analysis": "AI话题热度高"}]
```"""
        llm.chat.return_value = mock_resp

        analyzer = CrossPlatformAnalyzer(llm=llm)
        topics_by_source = {
            "weibo": [_make_topic("AI突破", TopicSource.WEIBO, 5000)],
        }

        result = await analyzer.analyze(topics_by_source)
        assert len(result) >= 1
        assert result[0].cluster_name == "科技"
