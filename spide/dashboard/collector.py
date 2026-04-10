# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""数据聚合器 — 从 SQLite 读取数据并计算看板统计指标.

用法:
    from spide.dashboard.collector import collect_dashboard_data

    data = await collect_dashboard_data(db_path="spide_data.db")
    # data 为 JSON-serializable dict，可直接传递给渲染器
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from spide.logging import get_logger
from spide.storage.models import HotTopic
from spide.storage.sqlite_repo import SqliteRepository

logger = get_logger(__name__)

# 平台中文映射
PLATFORM_LABELS: dict[str, str] = {
    "weibo": "微博",
    "baidu": "百度",
    "douyin": "抖音",
    "zhihu": "知乎",
    "bilibili": "B站",
    "kuaishou": "快手",
    "tieba": "贴吧",
    "web_search": "联网搜索",
    "custom": "自定义",
}

# 平台主题色（与前端 PLATFORM_MAP 保持一致）
PLATFORM_COLORS: dict[str, str] = {
    "weibo": "#E6162D",
    "baidu": "#4E6EF2",
    "douyin": "#FE2C55",
    "zhihu": "#0066FF",
    "bilibili": "#00A1D6",
    "kuaishou": "#FF8C00",
    "tieba": "#4879BD",
    "web_search": "#34D399",
    "custom": "#FBBF24",
}


async def collect_dashboard_data(
    *,
    db_path: str = "spide_data.db",
    workspace: str | None = None,
) -> dict[str, Any]:
    """从 SQLite 读取数据并聚合看板统计指标.

    Returns:
        看板数据字典，包含 total_count / platform_stats / top_topics / 等
    """
    # 解析 db_path
    actual_db_path = db_path
    if workspace:
        actual_db_path = str(Path(workspace) / "spide_data.db")

    repo = SqliteRepository(HotTopic, db_path=actual_db_path)

    try:
        await repo.start()

        # 读取全量数据（看板需要聚合）
        total_count = await repo.count()
        if total_count == 0:
            return _empty_dashboard()

        all_topics = await repo.query(limit=total_count)

        return _aggregate(all_topics, total_count)

    finally:
        await repo.stop()


def _empty_dashboard() -> dict[str, Any]:
    """空看板数据（无数据时返回）."""
    return {
        "total_count": 0,
        "platform_stats": [],
        "top_topics": [],
        "category_stats": [],
        "platform_ranks": {},
        "latest_fetch": None,
        "stats_summary": {
            "total": 0,
            "platforms": 0,
            "today_count": 0,
            "avg_hot_value": 0,
        },
    }


def _aggregate(topics: list[HotTopic], total_count: int) -> dict[str, Any]:
    """聚合计算看板统计指标."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # --- 平台分布 ---
    source_counter = Counter(t.source.value for t in topics)
    platform_stats = [
        {
            "source": source,
            "label": PLATFORM_LABELS.get(source, source),
            "count": count,
            "color": PLATFORM_COLORS.get(source, "#40BE7A"),
        }
        for source, count in source_counter.most_common()
    ]

    # --- 热度 Top 20 ---
    sorted_by_hot = sorted(topics, key=lambda t: t.hot_value or 0, reverse=True)
    top_topics = [
        {
            "rank": i + 1,
            "title": t.title,
            "source": t.source.value,
            "source_label": PLATFORM_LABELS.get(t.source.value, t.source.value),
            "hot_value": t.hot_value or 0,
            "url": t.url or "",
            "fetched_at": t.fetched_at.isoformat() if t.fetched_at else None,
        }
        for i, t in enumerate(sorted_by_hot[:20])
    ]

    # --- 分类占比 ---
    cat_counter = Counter(t.category.value for t in topics if t.category)
    category_stats = [
        {"category": cat, "count": count}
        for cat, count in cat_counter.most_common()
    ]

    # --- 各平台 Top 5 ---
    platform_ranks: dict[str, list[dict[str, Any]]] = {}
    for source in source_counter:
        source_topics = [
            t for t in topics if t.source.value == source
        ]
        source_sorted = sorted(source_topics, key=lambda t: t.hot_value or 0, reverse=True)
        platform_ranks[source] = [
            {
                "rank": i + 1,
                "title": t.title,
                "url": t.url or "",
                "hot_value": t.hot_value or 0,
            }
            for i, t in enumerate(source_sorted[:5])
        ]

    # --- 最新采集时间 ---
    fetch_times = [t.fetched_at for t in topics if t.fetched_at]
    latest_fetch = max(fetch_times).isoformat() if fetch_times else None

    # --- 今日新增 ---
    today_count = sum(
        1 for t in topics
        if t.fetched_at and t.fetched_at.strftime("%Y-%m-%d") == today_str
    )

    # --- 平均热度 ---
    hot_values = [t.hot_value for t in topics if t.hot_value]
    avg_hot_value = int(sum(hot_values) / len(hot_values)) if hot_values else 0

    return {
        "total_count": total_count,
        "platform_stats": platform_stats,
        "top_topics": top_topics,
        "category_stats": category_stats,
        "platform_ranks": platform_ranks,
        "latest_fetch": latest_fetch,
        "stats_summary": {
            "total": total_count,
            "platforms": len(source_counter),
            "today_count": today_count,
            "avg_hot_value": avg_hot_value,
        },
    }
