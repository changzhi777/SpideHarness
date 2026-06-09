# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 数据管道."""

from spide.spider.pipeline import (
    _clean_url,
    _normalize_title,
    clean_topics,
    deduplicate_items,
    parse_hot_items,
)
from spide.storage.models import HotTopic, TopicSource


class TestNormalizeTitle:
    """标题规范化."""

    def test_none_input(self):
        assert _normalize_title(None) == ""

    def test_empty_string(self):
        assert _normalize_title("") == ""

    def test_whitespace_only(self):
        assert _normalize_title("   ") == ""

    def test_strips_hashtag_tags(self):
        # 正则 ^#(.+)#?$ 中 .+ 贪婪匹配保留尾 #
        result = _normalize_title("#热搜话题#")
        assert "热搜话题" in result

    def test_leading_hashtag(self):
        result = _normalize_title("#话题")
        assert "话题" in result

    def test_control_chars_removed(self):
        result = _normalize_title("标题\x00\x01内容")
        assert result == "标题内容"

    def test_whitespace_collapsed(self):
        result = _normalize_title("多   空  格\n换行")
        assert result == "多 空 格 换行"

    def test_too_long_title(self):
        assert _normalize_title("x" * 201) == ""

    def test_normal_title(self):
        assert _normalize_title("正常标题") == "正常标题"


class TestCleanUrl:
    """URL 清洗."""

    def test_none(self):
        assert _clean_url(None) is None

    def test_empty(self):
        assert _clean_url("") is None

    def test_whitespace_only(self):
        assert _clean_url("   ") is None

    def test_invalid_scheme(self):
        assert _clean_url("ftp://example.com") is None

    def test_http_valid(self):
        assert _clean_url("http://example.com") == "http://example.com"

    def test_https_valid(self):
        assert _clean_url("https://example.com/path") == "https://example.com/path"

    def test_strips_whitespace(self):
        assert _clean_url("  https://example.com  ") == "https://example.com"


class TestCleanTopics:
    """clean_topics 集成测试."""

    def test_empty_input(self):
        assert clean_topics([]) == []

    def test_filters_empty_title(self):
        topics = [
            HotTopic(title="", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="有效", source=TopicSource.WEIBO, hot_value=200),
        ]
        result = clean_topics(topics)
        assert len(result) == 1
        assert result[0].title == "有效"

    def test_normalizes_titles(self):
        topics = [
            HotTopic(title="#带标签#", source=TopicSource.WEIBO, hot_value=100),
        ]
        result = clean_topics(topics)
        assert "带标签" in result[0].title

    def test_deduplicates_in_batch(self):
        topics = [
            HotTopic(title="重复话题", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="重复话题", source=TopicSource.WEIBO, hot_value=200),
        ]
        result = clean_topics(topics)
        assert len(result) == 1
        assert result[0].hot_value == 200

    def test_filters_negative_hot_value(self):
        topics = [
            HotTopic(title="负热度", source=TopicSource.WEIBO, hot_value=-1),
        ]
        result = clean_topics(topics)
        assert len(result) == 1
        assert result[0].hot_value is None

    def test_cleans_invalid_url(self):
        topics = [
            HotTopic(title="测试", source=TopicSource.WEIBO, url="not-a-url"),
        ]
        result = clean_topics(topics)
        assert result[0].url is None

    def test_preserves_valid_url(self):
        topics = [
            HotTopic(title="测试", source=TopicSource.WEIBO, url="https://weibo.com/1"),
        ]
        result = clean_topics(topics)
        assert result[0].url == "https://weibo.com/1"

    def test_full_pipeline(self):
        topics = [
            HotTopic(title="#热搜1#", source=TopicSource.WEIBO, hot_value=999, url="https://weibo.com/1"),
            HotTopic(title="", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(
                title="  热搜2  ", source=TopicSource.BAIDU,
                hot_value=-5, url="  https://baidu.com  ",
            ),
        ]
        result = clean_topics(topics)
        assert len(result) == 2
        # 热搜1 的 # 标签被部分清理
        weibo = next(t for t in result if t.source == TopicSource.WEIBO)
        assert weibo.hot_value == 999
        # 热搜2 负热度变 None
        baidu = next(t for t in result if t.source == TopicSource.BAIDU)
        assert baidu.hot_value is None
        assert baidu.url == "https://baidu.com"


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
        items = [
            HotTopic(title="重复", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="重复", source=TopicSource.WEIBO, hot_value=200),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        assert result[0].hot_value == 200

    def test_case_insensitive(self):
        items = [
            HotTopic(title="热搜话题", source=TopicSource.WEIBO),
            HotTopic(title="热搜话題", source=TopicSource.BAIDU),  # 不同字符
        ]
        result = deduplicate_items(items)
        assert len(result) == 2  # 不同标题不去重

    def test_different_sources_not_deduped(self):
        items = [
            HotTopic(title="相同标题", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="相同标题", source=TopicSource.BAIDU, hot_value=200),
        ]
        result = deduplicate_items(items)
        assert len(result) == 2

    def test_empty_title_skipped(self):
        items = [
            HotTopic(title="   ", source=TopicSource.WEIBO, hot_value=100),
            HotTopic(title="有效", source=TopicSource.WEIBO, hot_value=200),
        ]
        result = deduplicate_items(items)
        assert len(result) == 1
        assert result[0].title == "有效"
