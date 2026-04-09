# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""评论词云生成 — jieba 分词 + wordcloud 可视化.

用法:
    from spide.analysis.wordcloud_generator import WordCloudGenerator

    gen = WordCloudGenerator(output_dir="data/wordcloud")
    await gen.generate(comments, filename="weibo_comments")
    await gen.generate_from_texts(texts, filename="hot_topic_keywords")
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from pathlib import Path
from typing import Any

from spide.exceptions import AnalysisError
from spide.logging import get_logger

logger = get_logger(__name__)

# 中文停用词（常见虚词/助词/代词）
_STOP_WORDS: frozenset[str] = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
    "它", "们", "那", "这个", "那个", "什么", "吗", "吧", "啊", "呢",
    "哦", "哈", "嗯", "呀", "啦", "唉", "哎", "嘛", "呗", "却",
    "把", "被", "让", "给", "从", "对", "比", "跟", "与", "而",
    "或", "但", "如果", "因为", "所以", "虽然", "而且", "还是", "已经",
    "可以", "能", "想", "知道", "时候", "出来", "起来", "下来", "回来",
    "过来", "过去", "下去", "出去", "那么", "怎么", "为什么",
    "这些", "那些", "它们", "他们", "我们", "你们", "大家",
})


class WordCloudGenerator:
    """评论词云生成器."""

    def __init__(
        self,
        *,
        output_dir: str = "data/wordcloud",
        font_path: str | None = None,
        width: int = 800,
        height: int = 600,
        max_words: int = 200,
        background_color: str = "white",
    ) -> None:
        self._output_dir = Path(output_dir)
        self._font_path = font_path
        self._width = width
        self._height = height
        self._max_words = max_words
        self._bg_color = background_color

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """使用 jieba 分词，过滤停用词和短词."""
        import jieba

        words = jieba.lcut(text)
        return [
            w.strip()
            for w in words
            if len(w.strip()) >= 2 and w.strip() not in _STOP_WORDS
        ]

    @staticmethod
    def _extract_texts(
        items: list[Any],
        text_field: str = "content",
    ) -> list[str]:
        """从数据列表中提取文本字段.

        支持 dict / Pydantic BaseModel / str 直接传入.
        """
        texts: list[str] = []
        for item in items:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                texts.append(str(item.get(text_field, "")))
            elif hasattr(item, text_field):
                texts.append(str(getattr(item, text_field, "")))
        return texts

    def _build_freq(self, texts: list[str]) -> Counter[str]:
        """构建词频统计."""
        counter: Counter[str] = Counter()
        for text in texts:
            words = self._tokenize(text)
            counter.update(words)
        return counter

    async def generate(
        self,
        items: list[Any],
        *,
        filename: str = "wordcloud",
        text_field: str = "content",
        title: str | None = None,
    ) -> Path:
        """从数据项生成词云图.

        Args:
            items: 数据列表（dict / BaseModel / str）
            filename: 输出文件名（不含扩展名）
            text_field: 文本字段名
            title: 词云标题（可选，会叠加在图上）

        Returns:
            词云图片路径
        """
        texts = self._extract_texts(items, text_field)
        if not texts:
            raise AnalysisError("没有可用的文本数据生成词云")

        return await self.generate_from_texts(
            texts, filename=filename, title=title
        )

    async def generate_from_texts(
        self,
        texts: list[str],
        *,
        filename: str = "wordcloud",
        title: str | None = None,
    ) -> Path:
        """从文本列表生成词云图.

        Args:
            texts: 文本列表
            filename: 输出文件名（不含扩展名）
            title: 词云标题

        Returns:
            词云图片路径
        """
        if not texts:
            raise AnalysisError("文本列表为空")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        filepath = self._output_dir / f"{filename}.png"

        freq = self._build_freq(texts)
        if not freq:
            raise AnalysisError("分词后没有有效词语")

        await asyncio.to_thread(
            self._render_wordcloud, filepath, freq, title
        )

        logger.debug(
            "wordcloud_generated",
            path=str(filepath),
            unique_words=len(freq),
            total_texts=len(texts),
        )
        return filepath

    async def get_top_keywords(
        self,
        items: list[Any],
        *,
        text_field: str = "content",
        top_n: int = 20,
    ) -> list[tuple[str, int]]:
        """提取高频关键词（不生成图片）.

        Returns:
            [(word, count), ...] 按频次降序
        """
        texts = self._extract_texts(items, text_field)
        freq = self._build_freq(texts)
        return freq.most_common(top_n)

    def _render_wordcloud(
        self,
        filepath: Path,
        freq: Counter[str],
        title: str | None = None,
    ) -> None:
        """同步渲染词云图片."""
        start = time.monotonic()
        import matplotlib
        matplotlib.use("Agg")  # 非交互后端，避免 tkinter 线程问题

        from wordcloud import WordCloud as WC

        wc = WC(
            font_path=self._font_path,
            width=self._width,
            height=self._height,
            max_words=self._max_words,
            background_color=self._bg_color,
            colormap="viridis",
        )
        wc.generate_from_frequencies(freq)

        if title:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(self._width / 100, self._height / 100), dpi=100)
            ax.imshow(wc, interpolation="bilinear")
            ax.set_title(title, fontsize=16, fontproperties=self._font_path)
            ax.axis("off")
            fig.savefig(filepath, bbox_inches="tight", dpi=100)
            plt.close(fig)
        else:
            wc.to_file(filepath)

        duration_ms = (time.monotonic() - start) * 1000
        logger.debug("render_wordcloud_duration", duration_ms=round(duration_ms, 1), unique_words=len(freq), path=str(filepath))
