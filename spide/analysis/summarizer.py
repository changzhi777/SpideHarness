# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""内容智能摘要 — 基于采集数据自动生成 AI 摘要.

用法:
    from spide.analysis.summarizer import ContentSummarizer

    summarizer = ContentSummarizer(llm_client)
    summary = await summarizer.summarize(title="AI行业突破", content="...")
    keywords = await summarizer.extract_keywords(title="...", content="...")
    analysis = await summarizer.analyze_sentiment(comments=["好文", "垃圾"])
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from spide.llm import LLMClient
from spide.logging import get_logger

logger = get_logger(__name__)

# 摘要生成的系统提示
_SUMMARY_SYSTEM = """你是一个专业的新闻内容摘要助手。请根据用户提供的内容生成：
1. 一段 100-200 字的精炼摘要
2. 3-5 个核心关键词
3. 内容分类（科技/财经/社会/娱乐/体育/国际/健康/其他）

请以 JSON 格式返回：
{"summary": "...", "keywords": ["...", "..."], "category": "..."}

只返回 JSON，不要其他文字。"""

# 情感分析系统提示
_SENTIMENT_SYSTEM = """你是一个评论情感分析助手。请分析提供的评论文本列表，返回：
1. 正面/负面/中性比例
2. 总体情感倾向（positive/negative/neutral）
3. 高频观点摘要（3条以内）

请以 JSON 格式返回：
{"positive_ratio": 0.6, "negative_ratio": 0.2, "neutral_ratio": 0.2, "overall": "positive", "top_opinions": ["...", "..."]}

只返回 JSON，不要其他文字。"""

# 智能采集策略提示
_SMART_CRAWL_SYSTEM = """你是一个热点新闻采集策略专家。根据当前的热搜数据，分析趋势并推荐采集策略。

请返回 JSON 格式：
{
  "trending_topics": [{"title": "...", "reason": "..."}],
  "recommended_sources": ["weibo", "zhihu"],
  "search_keywords": ["关键词1", "关键词2"],
  "analysis": "简要趋势分析（100字以内）"
}

只返回 JSON，不要其他文字。"""


class ContentSummarizer:
    """内容智能摘要."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def summarize(
        self,
        *,
        title: str,
        content: str,
        source: str = "",
    ) -> dict[str, Any]:
        """生成内容摘要.

        Returns:
            {"summary": str, "keywords": list[str], "category": str}
        """
        user_msg = f"标题：{title}\n\n内容：{content[:3000]}"
        if source:
            user_msg = f"来源：{source}\n" + user_msg

        return await self._call_llm(_SUMMARY_SYSTEM, user_msg, "summarize")

    async def extract_keywords(
        self,
        *,
        title: str,
        content: str,
        max_keywords: int = 5,
    ) -> list[str]:
        """提取关键词."""
        result = await self.summarize(title=title, content=content)
        keywords = result.get("keywords", [])
        return keywords[:max_keywords]

    async def analyze_sentiment(
        self,
        comments: list[str],
    ) -> dict[str, Any]:
        """评论情感分析.

        Args:
            comments: 评论文本列表

        Returns:
            {"positive_ratio", "negative_ratio", "neutral_ratio", "overall", "top_opinions"}
        """
        # 限制评论数量和长度，避免超长输入
        truncated = [c[:200] for c in comments[:100]]
        comments_text = "\n".join(f"- {c}" for c in truncated)

        return await self._call_llm(_SENTIMENT_SYSTEM, comments_text, "sentiment")

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        task_name: str,
    ) -> dict[str, Any]:
        """调用 LLM 并解析 JSON 响应."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            response = await asyncio.to_thread(
                self._llm.chat, messages=messages, temperature=0.3, max_tokens=1024
            )
            raw_text = response.choices[0].message.content.strip()

            # 清理可能的 markdown 代码块标记
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]

            result = json.loads(raw_text)
            logger.debug(
                f"{task_name}_completed",
                keys=list(result.keys()),
            )
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"{task_name}_parse_error", error=str(e), raw=raw_text[:200])
            return {"error": f"JSON 解析失败: {e}", "raw": raw_text[:500]}
        except Exception as e:
            logger.error(f"{task_name}_failed", error=str(e))
            return {"error": str(e)}


class SmartCrawlStrategy:
    """智能采集策略 — 根据热搜数据推荐采集方案."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def recommend(
        self,
        hot_topics: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """基于当前热搜数据推荐采集策略.

        Args:
            hot_topics: 热搜数据列表 [{"title": "...", "hot_value": 9999, "source": "weibo"}, ...]

        Returns:
            {"trending_topics", "recommended_sources", "search_keywords", "analysis"}
        """
        # 构建热搜摘要
        topics_text = "\n".join(
            f"- [{t.get('source', '?')}] {t.get('title', '')} (热度: {t.get('hot_value', 'N/A')})"
            for t in hot_topics[:30]
        )

        user_msg = f"当前热搜数据：\n{topics_text}\n\n请分析趋势并推荐采集策略。"

        return await self._call_llm(_SMART_CRAWL_SYSTEM, user_msg)

    async def _call_llm(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """调用 LLM 并解析 JSON 响应."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            response = await asyncio.to_thread(
                self._llm.chat, messages=messages, temperature=0.3, max_tokens=1024
            )
            raw_text = response.choices[0].message.content.strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]

            result = json.loads(raw_text)
            logger.debug("smart_strategy_completed", keys=list(result.keys()))
            return result

        except json.JSONDecodeError as e:
            logger.warning("smart_strategy_parse_error", error=str(e))
            return {"error": f"JSON 解析失败: {e}"}
        except Exception as e:
            logger.error("smart_strategy_failed", error=str(e))
            return {"error": str(e)}


class TrendAnalyzer:
    """热点趋势分析 — 对比历史数据识别趋势变化."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def analyze(
        self,
        current_topics: list[dict[str, Any]],
        previous_topics: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """分析热点趋势.

        Args:
            current_topics: 当前热搜数据
            previous_topics: 上一轮热搜数据（可选，用于对比）

        Returns:
            {"rising", "falling", "new_entries", "analysis"}
        """
        if previous_topics:
            return await self._compare(current_topics, previous_topics)
        else:
            return await self._single_analysis(current_topics)

    async def _single_analysis(self, topics: list[dict[str, Any]]) -> dict[str, Any]:
        """单次热搜分析（无历史对比）."""
        topics_text = "\n".join(
            f"- {t.get('title', '')} (热度: {t.get('hot_value', 'N/A')}, 来源: {t.get('source', '?')})"
            for t in topics[:30]
        )

        system = """你是热点趋势分析专家。分析当前热搜数据，返回 JSON：
{
  "top_categories": ["分类1", "分类2"],
  "hot_domains": ["领域1", "领域2"],
  "analysis": "100字以内的趋势总结",
  "recommendations": ["建议1", "建议2"]
}
只返回 JSON。"""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"当前热搜：\n{topics_text}"},
        ]

        try:
            response = await asyncio.to_thread(
                self._llm.chat, messages=messages, temperature=0.3, max_tokens=1024
            )
            raw_text = response.choices[0].message.content.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[-1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            return json.loads(raw_text)
        except Exception as e:
            return {"error": str(e)}

    async def _compare(
        self,
        current: list[dict[str, Any]],
        previous: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """对比两轮热搜数据."""
        # 本地计算基本变化
        current_titles = {t.get("title", "") for t in current}
        previous_titles = {t.get("title", "") for t in previous}

        new_entries = current_titles - previous_titles
        disappeared = previous_titles - current_titles
        persisted = current_titles & previous_titles

        # 热度变化
        prev_hot = {t.get("title", ""): t.get("hot_value", 0) for t in previous}
        rising = []
        falling = []
        for t in current:
            title = t.get("title", "")
            if title in prev_hot:
                diff = (t.get("hot_value", 0) or 0) - (prev_hot[title] or 0)
                if diff > 0:
                    rising.append({"title": title, "change": diff})
                elif diff < 0:
                    falling.append({"title": title, "change": diff})

        rising.sort(key=lambda x: x["change"], reverse=True)
        falling.sort(key=lambda x: x["change"])

        return {
            "total_current": len(current),
            "total_previous": len(previous),
            "new_entries": list(new_entries)[:10],
            "disappeared": list(disappeared)[:10],
            "persisted_count": len(persisted),
            "rising": rising[:5],
            "falling": falling[:5],
        }
