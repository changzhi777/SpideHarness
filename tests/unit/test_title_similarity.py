# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 标题相似度."""

from spide.analysis.title_similarity import (
    edit_similarity,
    is_similar,
    jaccard_similarity,
)


class TestJaccardSimilarity:
    """Jaccard 相似度测试."""

    def test_identical(self):
        assert jaccard_similarity("AI大模型", "AI大模型") == 1.0

    def test_completely_different(self):
        result = jaccard_similarity("天气炎热", "股市暴跌")
        assert result < 0.3

    def test_partial_overlap(self):
        result = jaccard_similarity("OpenAI发布GPT-5", "GPT-5正式发布")
        assert 0.3 < result < 1.0

    def test_empty_strings(self):
        assert jaccard_similarity("", "") == 1.0
        assert jaccard_similarity("abc", "") == 0.0


class TestEditSimilarity:
    """编辑距离相似度测试."""

    def test_identical(self):
        assert edit_similarity("相同文本", "相同文本") == 1.0

    def test_completely_different(self):
        result = edit_similarity("abcd", "wxyz")
        assert result < 0.5

    def test_one_char_diff(self):
        result = edit_similarity("测试文本A", "测试文本B")
        assert result >= 0.8

    def test_empty(self):
        assert edit_similarity("", "") == 1.0
        assert edit_similarity("abc", "") == 0.0


class TestIsSimilar:
    """is_similar 综合判断测试."""

    def test_identical_titles(self):
        assert is_similar("OpenAI发布GPT-5", "OpenAI发布GPT-5") is True

    def test_similar_reorder(self):
        assert is_similar("OpenAI发布GPT-5", "OpenAI发布GPT-5", threshold=0.5) is True

    def test_near_duplicate(self):
        assert is_similar("AI大模型突破性进展", "AI大模型突破性进展!", threshold=0.5) is True

    def test_different_topics(self):
        assert is_similar("天气炎热", "股市暴跌") is False

    def test_empty(self):
        assert is_similar("", "") is False
        assert is_similar("test", "") is False

    def test_custom_threshold(self):
        assert is_similar("测试A", "测试B", threshold=0.3) is True
        assert is_similar("测试A", "测试B", threshold=0.99) is False
