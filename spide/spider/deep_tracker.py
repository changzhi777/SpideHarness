# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""话题深度追踪 — 自动搜索 + LLM 摘要 + 情感分析.

用法:
    from spide.spider.deep_tracker import DeepTopicTracker
    from spide.llm import LLMClient

    tracker = DeepTopicTracker(llm=llm_client)
    results = await tracker.track_topics(topics, top_n=10)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from spide.analysis.summarizer import ContentSummarizer
from spide.llm import LLMClient
from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicDeepTrack, TopicSource

logger = get_logger(__name__)

# 默认并发控制
_MAX_CONCURRENT_ANALYSIS = 3


class DeepTopicTracker:
    """话题深度追踪器 — 对 Top N 热搜自动搜索分析."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        max_concurrent: int = _MAX_CONCURRENT_ANALYSIS,
    ) -> None:
        self._llm = llm
        self._summarizer = ContentSummarizer(llm)
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def track_topics(
        self,
        topics: list[HotTopic],
        top_n: int = 10,
    ) -> list[TopicDeepTrack]:
        """追踪 Top N 热搜话题.

        Args:
            topics: 热搜话题列表（按热度排序）
            top_n: 追踪数量

        Returns:
            TopicDeepTrack 列表
        """
        target = topics[:top_n]
        if not target:
            return []

        logger.info("deep_tracking_start", total=len(target))

        tasks = [self._analyze_one(topic) for topic in target]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        tracks: list[TopicDeepTrack] = []
        for topic, result in zip(target, results, strict=False):
            if isinstance(result, Exception):
                logger.warning(
                    "deep_track_failed",
                    title=topic.title[:50],
                    error=str(result),
                )
                tracks.append(TopicDeepTrack(
                    topic_title=topic.title,
                    topic_source=topic.source,
                    topic_hot_value=topic.hot_value,
                    analysis_status="failed",
                ))
            else:
                tracks.append(result)

        logger.info(
            "deep_tracking_done",
            total=len(tracks),
            completed=sum(1 for t in tracks if t.analysis_status == "completed"),
            failed=sum(1 for t in tracks if t.analysis_status == "failed"),
        )

        return tracks

    async def _analyze_one(self, topic: HotTopic) -> TopicDeepTrack:
        """分析单个话题 — 搜索 + 摘要 + 情感."""
        async with self._semaphore:
            track = TopicDeepTrack(
                topic_title=topic.title,
                topic_source=topic.source,
                topic_hot_value=topic.hot_value,
                analysis_status="analyzing",
            )

            try:
                # 步骤 1: 联网搜索获取相关文章
                articles = await self._web_search(topic.title)
                track.related_articles = articles[:5]

                # 步骤 2: 生成摘要
                content = self._build_content(topic, articles)
                summary_result = await self._summarizer.summarize(
                    title=topic.title,
                    content=content,
                    source=topic.source.value,
                )

                if "error" not in summary_result:
                    track.summary = summary_result.get("summary", "")
                    track.keywords = summary_result.get("keywords", [])

                # 步骤 3: 情感分析（基于搜索结果标题）
                article_texts = [a.get("title", "") for a in articles if a.get("title")]
                if article_texts:
                    sentiment_result = await self._summarizer.analyze_sentiment(
                        comments=article_texts,
                    )
                    if "error" not in sentiment_result:
                        track.sentiment = sentiment_result.get("overall", "unknown")

                track.analysis_status = "completed"
                track.analyzed_at = datetime.now()

            except Exception as e:
                logger.warning(
                    "deep_track_analyze_error",
                    title=topic.title[:50],
                    error=str(e),
                )
                track.analysis_status = "failed"

            return track

    async def _web_search(self, query: str) -> list[dict[str, Any]]:
        """调用 LLM 联网搜索获取相关文章."""
        try:
            from spide.config import load_settings

            settings = load_settings()
            web_search_config = settings.llm.web_search

            response = await asyncio.to_thread(
                self._llm.chat,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个搜索助手。请用 JSON 数组格式返回搜索结果，"
                        "每项包含 title、url、snippet 字段。只返回 JSON。",
                    },
                    {
                        "role": "user",
                        "content": f"搜索关于「{query}」的最新新闻和报道，返回 5 条相关结果。",
                    },
                ],
                temperature=0.3,
                max_tokens=1024,
                tools=[{
                    "type": "web_search",
                    "web_search": {
                        "enable": True,
                        "search_engine": web_search_config.engine,
                        "search_result_count": web_search_config.default_count,
                    },
                }],
            )

            import json

            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]

            return json.loads(raw)

        except Exception as e:
            logger.debug("web_search_fallback", query=query[:30], error=str(e))
            return []

    @staticmethod
    def _build_content(topic: HotTopic, articles: list[dict[str, Any]]) -> str:
        """拼接话题信息和搜索结果作为 LLM 输入."""
        parts = [f"热搜标题: {topic.title}"]
        if topic.hot_value:
            parts.append(f"热度值: {topic.hot_value}")

        for i, article in enumerate(articles[:3], 1):
            title = article.get("title", "")
            snippet = article.get("snippet", "")
            if title:
                parts.append(f"相关{i}: {title}")
            if snippet:
                parts.append(f"  摘要: {snippet}")

        return "\n".join(parts)
