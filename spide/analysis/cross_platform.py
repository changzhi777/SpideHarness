# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""跨平台关联分析 — LLM 语义聚类 + 相似度去重.

用法:
    from spide.analysis.cross_platform import CrossPlatformAnalyzer

    analyzer = CrossPlatformAnalyzer(llm_client)
    clusters = await analyzer.analyze({"weibo": topics1, "zhihu": topics2})
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from spide.analysis.title_similarity import is_similar
from spide.llm import LLMClient
from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicCluster

logger = get_logger(__name__)

# 聚类系统提示
_CLUSTER_SYSTEM_PROMPT = """你是一个热点新闻分析专家。请分析以下来自不同平台的热搜话题，进行语义聚类。

要求：
1. 将语义相近的话题归为一组
2. 为每组生成一个名称和关键词
3. 标记是否为跨平台热点
4. 提供简要分析

请以 JSON 数组格式返回，每项格式：
{
  "name": "聚类名称",
  "keywords": ["关键词1", "关键词2"],
  "topic_titles": ["话题1", "话题2"],
  "platforms": ["weibo", "zhihu"],
  "cross_platform": true,
  "analysis": "简要分析（50字以内）"
}

只返回 JSON 数组，不要其他文字。"""


class CrossPlatformAnalyzer:
    """跨平台关联分析器."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(
        self,
        topics_by_source: dict[str, list[HotTopic]],
    ) -> list[TopicCluster]:
        """分析多平台热搜，生成语义聚类.

        Args:
            topics_by_source: 平台 → 热搜列表

        Returns:
            TopicCluster 列表
        """
        # 步骤 1: 本地相似度去重
        deduped = self._dedup_cross_platform(topics_by_source)

        # 步骤 2: LLM 语义聚类
        clusters = await self._cluster_by_llm(deduped)

        logger.info(
            "cross_platform_analyzed",
            sources=len(topics_by_source),
            clusters=len(clusters),
            cross_platform_count=sum(1 for c in clusters if c.cross_platform),
        )

        return clusters

    def _dedup_cross_platform(
        self,
        topics_by_source: dict[str, list[HotTopic]],
    ) -> list[dict[str, Any]]:
        """跨平台相似度去重 — 合并相似话题."""
        all_topics: list[dict[str, Any]] = []
        seen_titles: list[str] = []

        for source, topics in topics_by_source.items():
            for topic in topics[:20]:
                title_lower = topic.title.strip().lower()

                # 检查是否与已有话题相似
                merged = False
                for existing in all_topics:
                    if is_similar(title_lower, existing["title"].lower(), threshold=0.6):
                        # 合并到已有条目
                        if source not in existing["platforms"]:
                            existing["platforms"].append(source)
                        existing["hot_value"] += topic.hot_value or 0
                        merged = True
                        break

                if not merged:
                    all_topics.append({
                        "title": topic.title,
                        "source": source,
                        "platforms": [source],
                        "hot_value": topic.hot_value or 0,
                    })
                    seen_titles.append(title_lower)

        return all_topics

    async def _cluster_by_llm(
        self,
        topics: list[dict[str, Any]],
    ) -> list[TopicCluster]:
        """调用 LLM 对话题进行语义聚类."""
        if not topics:
            return []

        # 构建输入
        topics_text = "\n".join(
            f"- [{','.join(t['platforms'])}] {t['title']} (热度: {t['hot_value']})"
            for t in topics[:50]
        )

        messages = [
            {"role": "system", "content": _CLUSTER_SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下热搜话题并聚类：\n{topics_text}"},
        ]

        try:
            response = await asyncio.to_thread(
                self._llm.chat,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            raw_text = response.choices[0].message.content.strip()

            # 清理 markdown 代码块
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]

            raw_clusters = json.loads(raw_text)
            return self._parse_clusters(raw_clusters)

        except json.JSONDecodeError as e:
            logger.warning("cluster_parse_error", error=str(e))
            return self._fallback_clusters(topics)
        except Exception as e:
            logger.error("cluster_failed", error=str(e))
            return self._fallback_clusters(topics)

    @staticmethod
    def _parse_clusters(raw: list[dict[str, Any]]) -> list[TopicCluster]:
        """解析 LLM 返回的聚类 JSON."""
        clusters: list[TopicCluster] = []
        for item in raw:
            clusters.append(TopicCluster(
                cluster_name=item.get("name", "未命名"),
                cluster_keywords=item.get("keywords", []),
                platform_sources=item.get("platforms", []),
                topic_titles=item.get("topic_titles", []),
                cross_platform=item.get("cross_platform", False),
                analysis=item.get("analysis", ""),
            ))
        return clusters

    @staticmethod
    def _fallback_clusters(topics: list[dict[str, Any]]) -> list[TopicCluster]:
        """LLM 失败时的本地降级聚类 — 按平台分组."""
        by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for t in topics:
            for p in t["platforms"]:
                by_platform[p].append(t)

        clusters: list[TopicCluster] = []
        for platform, platform_topics in by_platform.items():
            clusters.append(TopicCluster(
                cluster_name=f"{platform} 热点",
                cluster_keywords=[],
                platform_sources=[platform],
                topic_titles=[t["title"] for t in platform_topics[:10]],
                total_hot_value=sum(t["hot_value"] for t in platform_topics),
                cross_platform=False,
                analysis="LLM 不可用，仅按平台分组",
            ))
        return clusters
