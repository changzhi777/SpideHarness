# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""数据清洗与结构化管道.

用法:
    from spide.spider.pipeline import parse_hot_items, deduplicate_items

    # 清洗热搜数据
    cleaned = parse_hot_items(raw_items, source="weibo")

    # 去重
    unique = deduplicate_items(all_topics)
"""

from __future__ import annotations

from typing import Any

from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicSource

logger = get_logger(__name__)


def parse_hot_items(
    items: list[dict[str, Any]],
    *,
    source: str = "custom",
) -> list[HotTopic]:
    """清洗原始热搜数据为 HotTopic 模型列表.

    Args:
        items: 原始数据列表（来自 UAPI 或爬虫）
        source: 数据来源标识（自动映射到 TopicSource 枚举，未知值回退为 custom）

    Returns:
        清洗后的 HotTopic 列表
    """
    from spide.spider.uapi_client import _PLATFORM_MAP

    # 将字符串 source 转换为 TopicSource 枚举
    source_enum = _PLATFORM_MAP.get(source, TopicSource.CUSTOM)

    topics: list[HotTopic] = []
    for item in items:
        try:
            topic = HotTopic(
                title=_safe_str(item, "title"),
                source=source_enum,
                hot_value=_safe_int(item, "hot_value"),
                url=_safe_str(item, "url"),
                rank=_safe_int(item, "index") or _safe_int(item, "rank"),
                category=_safe_str(item, "category"),  # type: ignore[arg-type]
                summary=_safe_str(item, "summary"),
                extra=item.get("extra", {}),
            )
            if topic.title:  # 跳过无标题的条目
                topics.append(topic)
        except Exception as e:
            logger.warning("parse_item_error", item=str(item)[:100], error=str(e))
            continue

    return topics


def deduplicate_items(items: list[HotTopic]) -> list[HotTopic]:
    """按标题去重（保留热度最高的）."""
    seen: dict[str, HotTopic] = {}
    for item in items:
        key = item.title.strip().lower()
        if not key:
            continue
        existing = seen.get(key)
        if existing is None or (item.hot_value or 0) > (existing.hot_value or 0):
            seen[key] = item

    return list(seen.values())


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _safe_str(data: dict[str, Any], key: str) -> str | None:
    val = data.get(key)
    if val is None:
        return None
    return str(val).strip() or None


def _safe_int(data: dict[str, Any], key: str) -> int | None:
    val = data.get(key)
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
