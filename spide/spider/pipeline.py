# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""数据清洗与结构化管道.

用法:
    from spide.spider.pipeline import clean_topics, deduplicate_items

    # 清洗 + 去重
    cleaned = clean_topics(raw_topics)

    # 仅去重
    unique = deduplicate_items(all_topics)
"""

from __future__ import annotations

import re
from typing import Any

from spide.logging import get_logger
from spide.storage.models import HotTopic, TopicSource

logger = get_logger(__name__)

# 微博话题标签匹配: #话题# 或 #话题
_TOPIC_TAG_RE = re.compile(r"^#(.+)#?$|^#?(.+)#$")
# 连续空白/换行
_WHITESPACE_RE = re.compile(r"\s+")
# URL 合法前缀
_URL_PREFIX_RE = re.compile(r"^https?://", re.IGNORECASE)
# 标题中需要清除的控制字符（保留正常中文/英文/数字/标点）
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_topics(topics: list[HotTopic]) -> list[HotTopic]:
    """清洗 HotTopic 列表：规范化标题 + 过滤无效数据 + 去重.

    处理流程:
        1. 标题规范化（去标签符号、去空白、去控制字符）
        2. 过滤无效记录（空标题、无效URL、热度异常）
        3. 按 (title, source) 去重（保留热度最高的）
    """
    # Step 1+2: 清洗 + 过滤
    cleaned: list[HotTopic] = []
    skipped_empty = 0
    skipped_url = 0
    skipped_dup_in_batch = 0

    for topic in topics:
        # 标题规范化
        title = _normalize_title(topic.title)
        if not title:
            skipped_empty += 1
            continue

        # URL 清洗
        url = _clean_url(topic.url)

        # 热度值清洗
        hot_value = topic.hot_value
        if hot_value is not None and hot_value < 0:
            hot_value = None

        # 重建 topic
        topic = HotTopic(
            title=title,
            source=topic.source,
            hot_value=hot_value,
            url=url,
            rank=topic.rank,
            category=topic.category,
            summary=topic.summary,
            fetched_at=topic.fetched_at,
            extra=topic.extra,
            id=topic.id,
        )
        cleaned.append(topic)

    # Step 3: 按 (title, source) 去重
    deduped = deduplicate_items(cleaned)
    skipped_dup_in_batch = len(cleaned) - len(deduped)

    if skipped_empty or skipped_dup_in_batch:
        logger.debug(
            "clean_topics",
            input_count=len(topics),
            output_count=len(deduped),
            skipped_empty=skipped_empty,
            skipped_dup_in_batch=skipped_dup_in_batch,
        )

    return deduped


def _normalize_title(raw: str | None) -> str:
    """标题规范化处理.

    - 去除微博 #话题# 标签符号
    - 去除控制字符
    - 合并连续空白为单个空格
    - 去除前后空白
    - 长度限制 (1-200 字符)
    """
    if not raw:
        return ""

    title = str(raw)

    # 去除控制字符
    title = _CONTROL_CHARS_RE.sub("", title)

    # 微博话题标签: #xxx# → xxx
    m = _TOPIC_TAG_RE.match(title.strip())
    if m:
        title = m.group(1) or m.group(2) or title

    # 合并空白
    title = _WHITESPACE_RE.sub(" ", title).strip()

    # 长度校验
    if len(title) < 1 or len(title) > 200:
        return ""

    return title


def _clean_url(url: str | None) -> str | None:
    """URL 清洗.

    - 去除前后空白
    - 校验 http(s) 前缀
    - 无效 URL 返回 None
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not _URL_PREFIX_RE.match(url):
        return None
    return url


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
                extra=item.get("extra") or {},
            )
            if topic.title:
                topics.append(topic)
        except Exception as e:
            logger.warning("parse_item_error", item=str(item)[:100], error=str(e))
            continue

    return topics


def deduplicate_items(items: list[HotTopic]) -> list[HotTopic]:
    """按 (title, source) 去重（保留热度最高的）."""
    seen: dict[tuple[str, str], HotTopic] = {}
    for item in items:
        key = (item.title.strip().lower(), item.source.value)
        if not key[0]:
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
