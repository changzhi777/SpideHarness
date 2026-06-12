# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""告警规则引擎 — 关键词匹配 + 热度阈值 + 状态触发.

用法:
    from spide.monitor.alert_engine import AlertEngine

    engine = AlertEngine(rules=rules)
    alerts = engine.evaluate(topics=current_topics, changes=changes)
"""

from __future__ import annotations

from pathlib import Path

import yaml

from spide.logging import get_logger
from spide.storage.models import (
    AlertRecord,
    AlertRule,
    HotTopic,
    HotTopicChange,
    TopicSource,
    TopicStatus,
)

logger = get_logger(__name__)


class AlertEngine:
    """告警评估引擎 — 匹配话题与规则，生成告警记录."""

    def __init__(self, rules: list[AlertRule] | None = None) -> None:
        self._rules = rules or []

    @property
    def rules(self) -> list[AlertRule]:
        return self._rules

    @staticmethod
    def load_rules(rules_path: Path | str | None) -> list[AlertRule]:
        """从 YAML 文件加载告警规则.

        YAML 格式:
            rules:
              - name: "AI热点"
                keywords: ["AI", "GPT"]
                sources: [weibo, zhihu]
                hot_value_threshold: 10000
                status_trigger: [new, rising]
                enabled: true
        """
        if rules_path is None:
            return []

        path = Path(rules_path)
        if not path.exists():
            logger.warning("alert_rules_not_found", path=str(path))
            return []

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        raw_rules = data.get("rules", [])
        rules: list[AlertRule] = []
        for raw in raw_rules:
            if not raw.get("enabled", True):
                continue

            sources = []
            for s in raw.get("sources", []):
                try:
                    sources.append(TopicSource(s))
                except ValueError:
                    logger.warning("alert_unknown_source", source=s)

            status_trigger = []
            for s in raw.get("status_trigger", ["new"]):
                try:
                    status_trigger.append(TopicStatus(s))
                except ValueError:
                    logger.warning("alert_unknown_status", status=s)

            rules.append(
                AlertRule(
                    name=raw.get("name", "unnamed"),
                    keywords=[k.strip() for k in raw.get("keywords", []) if k.strip()],
                    sources=sources,
                    hot_value_threshold=raw.get("hot_value_threshold", 0),
                    status_trigger=status_trigger or [TopicStatus.NEW],
                )
            )

        logger.info("alert_rules_loaded", count=len(rules), path=str(path))
        return rules

    def evaluate(
        self,
        topics: list[HotTopic],
        changes: list[HotTopicChange] | None = None,
    ) -> list[AlertRecord]:
        """评估话题并生成告警记录.

        三种匹配方式：
        1. keyword_match — 话题标题包含规则关键词
        2. hot_value_exceed — 话题热度超过阈值
        3. status_change — 话题变化状态在触发列表中
        """
        if not self._rules:
            return []

        # 构建变化索引
        change_map: dict[str, HotTopicChange] = {}
        if changes:
            for c in changes:
                change_map[c.title.strip().lower()] = c

        alerts: list[AlertRecord] = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            for topic in topics:
                # 平台过滤
                if rule.sources and topic.source not in rule.sources:
                    continue

                alert_type = self._match_rule(rule, topic, change_map)
                if alert_type is None:
                    continue

                alerts.append(
                    AlertRecord(
                        rule_id=rule.id or 0,
                        rule_name=rule.name,
                        topic_title=topic.title,
                        topic_source=topic.source,
                        topic_hot_value=topic.hot_value,
                        alert_type=alert_type,
                    )
                )

        if alerts:
            logger.info(
                "alert_evaluated",
                total_topics=len(topics),
                total_alerts=len(alerts),
                rules_evaluated=len(self._rules),
            )

        return alerts

    def _match_rule(
        self,
        rule: AlertRule,
        topic: HotTopic,
        change_map: dict[str, HotTopicChange],
    ) -> str | None:
        """检查话题是否匹配规则，返回告警类型或 None."""
        title_lower = topic.title.lower()

        # 关键词匹配
        if rule.keywords and any(kw.lower() in title_lower for kw in rule.keywords):
            return "keyword_match"

        # 热度阈值
        if rule.hot_value_threshold > 0 and (topic.hot_value or 0) >= rule.hot_value_threshold:
            return "hot_value_exceed"

        # 状态触发
        if rule.status_trigger and change_map:
            change = change_map.get(topic.title.strip().lower())
            if change and change.status in rule.status_trigger:
                return "status_change"

        return None
