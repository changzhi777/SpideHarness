# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 数据管道."""


from spide.spider.pipeline import deduplicate_items, parse_hot_items
from spide.storage.models import TopicSource


class TestParseHotItems:
    """数据清洗."""

    def test_normal_items(self):
        raw = [
            {"title": "热搜1", "hot_value": "99999", "index": 1, "url": "https://weibo.com/1"},
            {"title": "热搜2", "hot_value": 88888, "index": 2},
        ]
        topics = parse_hot_items(raw, source="weibo")
        assert len(topics) == 2
        assert topics[0].source == TopicSource.WEIBO

    def test_empty_title_skipped(self):
        raw = [
            {"title": "", "hot_value": 100, "index": 1},
            {"title": "有效", "hot_value": 200, "index": 2},
        ]
        topics = parse_hot_items(raw, source="baidu")
        assert len(topics) == 1
        assert topics[0].title == "有效"

    def test_empty_input(self):
        assert parse_hot_items([], source="weibo") == []

    def test_special_characters(self):
        raw = [{"title": "测试<script>alert('xss')</script>", "hot_value": 100, "index": 1}]
        topics = parse_hot_items(raw, source="zhihu")
        assert len(topics) == 1
        assert "<script>" in topics[0].title  # 保留原始数据，由展示层转义

    def test_unknown_source_falls_back(self):
        raw = [{"title": "未知源", "hot_value": 100, "index": 1}]
        topics = parse_hot_items(raw, source="toutiao")
        assert len(topics) == 1
        assert topics[0].source == TopicSource.CUSTOM


class TestDeduplicate:
    """去重."""

    def test_keeps_highest_hot_value(self):
        from spide.storage.models import HotTopic

        items = [
            HotTopic(title="重复", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="重复", source=TopicSource.BAIDU, hot_value=200),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        assert result[0].hot_value == 200

    def test_case_insensitive(self):
        from spide.storage.models import HotTopic

        items = [
            HotTopic(title="热搜话题", source=TopicSource.WEIBO),
            HotTopic(title="热搜话題", source=TopicSource.BAIDU),  # 不同字符
        ]
        result = deduplicate_items(items)
        assert len(result) == 2  # 不同标题不去重
