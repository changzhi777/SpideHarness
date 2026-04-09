# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 词云生成器."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spide.analysis.wordcloud_generator import _STOP_WORDS, WordCloudGenerator


class TestWordCloudGenerator:
    """词云生成器."""

    def test_tokenize(self):
        words = WordCloudGenerator._tokenize("人工智能技术取得了重大突破")
        assert len(words) > 0
        # 过滤掉停用词和短词
        for w in words:
            assert len(w) >= 2
            assert w not in _STOP_WORDS

    def test_tokenize_filters_stopwords(self):
        words = WordCloudGenerator._tokenize("这是一个非常好的技术")
        # "这是" "一个" "非常" "好的" 应该被过滤部分
        for w in words:
            assert w not in {"的", "了", "是", "在", "我", "一", "一个"}

    def test_tokenize_filters_short_words(self):
        words = WordCloudGenerator._tokenize("AI 技术")
        for w in words:
            assert len(w) >= 2

    def test_extract_texts_from_strings(self):
        items = ["第一条评论", "第二条评论", "第三条"]
        texts = WordCloudGenerator._extract_texts(items)
        assert texts == items

    def test_extract_texts_from_dicts(self):
        items = [
            {"content": "评论A", "user": "x"},
            {"content": "评论B", "user": "y"},
        ]
        texts = WordCloudGenerator._extract_texts(items, text_field="content")
        assert texts == ["评论A", "评论B"]

    def test_extract_texts_from_models(self):
        mock = MagicMock()
        mock.content = "模拟内容"
        texts = WordCloudGenerator._extract_texts([mock], text_field="content")
        assert texts == ["模拟内容"]

    def test_extract_texts_custom_field(self):
        items = [{"title": "标题A"}, {"title": "标题B"}]
        texts = WordCloudGenerator._extract_texts(items, text_field="title")
        assert texts == ["标题A", "标题B"]

    def test_build_freq(self):
        gen = WordCloudGenerator()
        freq = gen._build_freq(["人工智能技术突破", "AI技术发展迅速"])
        assert isinstance(freq, dict)
        assert len(freq) > 0

    @pytest.mark.asyncio
    async def test_generate_from_texts(self, tmp_path: Path):
        gen = WordCloudGenerator(output_dir=str(tmp_path / "wc"))
        texts = [
            "人工智能技术取得重大突破，大模型发展迅速",
            "AI技术正在改变世界，深度学习应用广泛",
            "机器学习算法不断进步，自然语言处理技术突破",
        ]

        filepath = await gen.generate_from_texts(texts, filename="test")
        assert filepath.exists()
        assert filepath.suffix == ".png"
        assert filepath.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_generate_from_texts_with_title(self, tmp_path: Path):
        gen = WordCloudGenerator(output_dir=str(tmp_path / "wc"))
        texts = ["人工智能技术突破", "深度学习应用广泛", "AI发展迅速"]

        filepath = await gen.generate_from_texts(texts, filename="titled", title="测试词云")
        assert filepath.exists()

    @pytest.mark.asyncio
    async def test_generate_from_texts_empty(self, tmp_path: Path):
        gen = WordCloudGenerator(output_dir=str(tmp_path / "wc"))
        with pytest.raises(Exception, match="文本列表为空"):
            await gen.generate_from_texts([], filename="test")

    @pytest.mark.asyncio
    async def test_generate_from_dicts(self, tmp_path: Path):
        gen = WordCloudGenerator(output_dir=str(tmp_path / "wc"))
        items = [
            {"content": "人工智能技术突破，大模型应用广泛"},
            {"content": "深度学习算法进步，自然语言处理发展"},
        ]
        filepath = await gen.generate(items, filename="dict_test")
        assert filepath.exists()

    @pytest.mark.asyncio
    async def test_generate_empty_items(self, tmp_path: Path):
        gen = WordCloudGenerator(output_dir=str(tmp_path / "wc"))
        with pytest.raises(Exception, match="没有可用的文本数据"):
            await gen.generate([], filename="test")

    @pytest.mark.asyncio
    async def test_get_top_keywords(self):
        gen = WordCloudGenerator()
        items = [
            {"content": "人工智能技术突破，大模型发展"},
            {"content": "AI技术革新，人工智能应用"},
        ]
        keywords = await gen.get_top_keywords(items, top_n=5)
        assert len(keywords) > 0
        assert len(keywords) <= 5
        # 每个元素是 (word, count) 元组
        for word, count in keywords:
            assert isinstance(word, str)
            assert isinstance(count, int)
            assert count > 0

    @pytest.mark.asyncio
    async def test_get_top_keywords_empty(self):
        gen = WordCloudGenerator()
        keywords = await gen.get_top_keywords([], top_n=10)
        assert keywords == []

    def test_stop_words_not_empty(self):
        assert len(_STOP_WORDS) > 0
        assert "的" in _STOP_WORDS
        assert "了" in _STOP_WORDS
