# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""增量采集检测器 — 对比两轮采集结果，识别话题状态变化.

用法:
    from spide.spider.incremental import IncrementalDetector
    from spide.storage.models import HotTopic, TopicSource

    detector = IncrementalDetector()
    changes = detector.detect_changes(current_topics, previous_topics, TopicSource.WEIBO)
    report = detector.generate_diff_report(changes)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from spide.logging import get_logger
from spide.storage.models import (
    CrawlSnapshot,
    HotTopic,
    HotTopicChange,
    TopicSource,
    TopicStatus,
)

logger = get_logger(__name__)

# 热度变化阈值（百分比）
_HOT_VALUE_CHANGE_THRESHOLD = 0.10


class IncrementalDetector:
    """增量检测器 — 对比两轮热搜数据的变化."""

    def detect_changes(
        self,
        current: list[HotTopic],
        previous: list[HotTopic],
        source: TopicSource,
    ) -> list[HotTopicChange]:
        """检测两轮热搜之间的变化.

        Args:
            current: 本轮热搜列表
            previous: 上轮热搜列表
            source: 数据源平台

        Returns:
            变化记录列表
        """
        # 构建索引
        prev_map: dict[str, HotTopic] = {t.title.strip().lower(): t for t in previous}
        curr_titles: set[str] = set()

        changes: list[HotTopicChange] = []

        # 本轮话题：与上轮对比
        for topic in current:
            key = topic.title.strip().lower()
            curr_titles.add(key)

            prev_topic = prev_map.get(key)
            if prev_topic is None:
                # 新上榜
                changes.append(HotTopicChange(
                    title=topic.title,
                    source=source,
                    status=TopicStatus.NEW,
                    current_rank=topic.rank,
                    current_hot_value=topic.hot_value,
                    hot_value_change=topic.hot_value,
                ))
            else:
                # 已存在 → 判断变化
                status = self._classify_change(topic, prev_topic)
                hot_change = self._calc_hot_change(topic, prev_topic)
                changes.append(HotTopicChange(
                    title=topic.title,
                    source=source,
                    status=status,
                    previous_rank=prev_topic.rank,
                    current_rank=topic.rank,
                    previous_hot_value=prev_topic.hot_value,
                    current_hot_value=topic.hot_value,
                    hot_value_change=hot_change,
                ))

        # 上轮存在但本轮不存在 → 掉榜
        for prev_topic in previous:
            key = prev_topic.title.strip().lower()
            if key not in curr_titles:
                changes.append(HotTopicChange(
                    title=prev_topic.title,
                    source=source,
                    status=TopicStatus.DROPPED,
                    previous_rank=prev_topic.rank,
                    previous_hot_value=prev_topic.hot_value,
                    hot_value_change=-(prev_topic.hot_value or 0),
                ))

        logger.debug(
            "incremental_detected",
            source=source.value,
            new=sum(1 for c in changes if c.status == TopicStatus.NEW),
            rising=sum(1 for c in changes if c.status == TopicStatus.RISING),
            falling=sum(1 for c in changes if c.status == TopicStatus.FALLING),
            stable=sum(1 for c in changes if c.status == TopicStatus.STABLE),
            dropped=sum(1 for c in changes if c.status == TopicStatus.DROPPED),
        )

        return changes

    def build_snapshot(
        self,
        topics: list[HotTopic],
        source: TopicSource,
        changes: list[HotTopicChange] | None = None,
    ) -> CrawlSnapshot:
        """构建采集快照.

        Args:
            topics: 本轮热搜列表
            source: 数据源平台
            changes: 变化记录（可选，不提供时快照不包含变化统计）

        Returns:
            CrawlSnapshot 快照
        """
        now = datetime.now()
        snapshot_key = f"{source.value}_{now.strftime('%Y%m%d_%H%M')}"

        snapshot = CrawlSnapshot(
            snapshot_key=snapshot_key,
            source=source,
            total_topics=len(topics),
            created_at=now,
        )

        if changes:
            snapshot.changes = changes
            snapshot.new_count = sum(1 for c in changes if c.status == TopicStatus.NEW)
            snapshot.rising_count = sum(1 for c in changes if c.status == TopicStatus.RISING)
            snapshot.falling_count = sum(1 for c in changes if c.status == TopicStatus.FALLING)
            snapshot.dropped_count = sum(1 for c in changes if c.status == TopicStatus.DROPPED)

        return snapshot

    def generate_diff_report(self, changes: list[HotTopicChange]) -> dict[str, Any]:
        """生成差异报告摘要.

        Returns:
            {"summary": {...}, "new": [...], "rising": [...], "falling": [...], "dropped": [...]}
        """
        new = [c for c in changes if c.status == TopicStatus.NEW]
        rising = [c for c in changes if c.status == TopicStatus.RISING]
        falling = [c for c in changes if c.status == TopicStatus.FALLING]
        stable = [c for c in changes if c.status == TopicStatus.STABLE]
        dropped = [c for c in changes if c.status == TopicStatus.DROPPED]

        return {
            "summary": {
                "total": len(changes),
                "new": len(new),
                "rising": len(rising),
                "falling": len(falling),
                "stable": len(stable),
                "dropped": len(dropped),
            },
            "new": [{"title": c.title, "hot_value": c.current_hot_value} for c in new[:10]],
            "rising": [{"title": c.title, "change": c.hot_value_change} for c in rising[:10]],
            "falling": [{"title": c.title, "change": c.hot_value_change} for c in falling[:10]],
            "dropped": [{"title": c.title, "last_hot_value": c.previous_hot_value} for c in dropped[:10]],
        }

    def _classify_change(self, current: HotTopic, previous: HotTopic) -> TopicStatus:
        """判断话题状态变化."""
        change_pct = self._calc_change_percent(current, previous)

        if change_pct > _HOT_VALUE_CHANGE_THRESHOLD:
            return TopicStatus.RISING
        if change_pct < -_HOT_VALUE_CHANGE_THRESHOLD:
            return TopicStatus.FALLING
        return TopicStatus.STABLE

    @staticmethod
    def _calc_change_percent(current: HotTopic, previous: HotTopic) -> float:
        """计算热度变化百分比."""
        prev_val = previous.hot_value or 0
        curr_val = current.hot_value or 0
        if prev_val == 0:
            return 1.0 if curr_val > 0 else 0.0
        return (curr_val - prev_val) / prev_val

    @staticmethod
    def _calc_hot_change(current: HotTopic, previous: HotTopic) -> int | None:
        """计算热度绝对变化量."""
        if current.hot_value is None or previous.hot_value is None:
            return None
        return current.hot_value - previous.hot_value
