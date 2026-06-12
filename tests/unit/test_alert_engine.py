# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 告警规则引擎."""

from pathlib import Path

import yaml

from spide.monitor.alert_engine import AlertEngine
from spide.storage.models import (
    AlertRule,
    HotTopic,
    HotTopicChange,
    TopicSource,
    TopicStatus,
)


def _make_topic(title: str, hot_value: int = 1000) -> HotTopic:
    return HotTopic(title=title, source=TopicSource.WEIBO, hot_value=hot_value)


def _make_rule(
    name: str = "test",
    keywords: list[str] | None = None,
    hot_value_threshold: int = 0,
    sources: list[TopicSource] | None = None,
    status_trigger: list[TopicStatus] | None = None,
) -> AlertRule:
    return AlertRule(
        name=name,
        keywords=keywords or [],
        hot_value_threshold=hot_value_threshold,
        sources=sources or [],
        status_trigger=status_trigger or [TopicStatus.NEW],
    )


class TestAlertEngineEvaluate:
    """evaluate 测试."""

    def test_keyword_match(self):
        rule = _make_rule(keywords=["AI", "GPT"])
        engine = AlertEngine(rules=[rule])
        topics = [_make_topic("AI大模型突破"), _make_topic("天气不错")]

        alerts = engine.evaluate(topics)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "keyword_match"
        assert alerts[0].topic_title == "AI大模型突破"

    def test_hot_value_exceed(self):
        rule = _make_rule(hot_value_threshold=5000)
        engine = AlertEngine(rules=[rule])
        topics = [_make_topic("普通话题", 3000), _make_topic("爆热话题", 8000)]

        alerts = engine.evaluate(topics)
        assert len(alerts) == 1
        assert alerts[0].topic_title == "爆热话题"

    def test_status_change_trigger(self):
        rule = _make_rule(status_trigger=[TopicStatus.RISING])
        engine = AlertEngine(rules=[rule])

        topics = [_make_topic("上升话题", 5000)]
        changes = [
            HotTopicChange(title="上升话题", source=TopicSource.WEIBO, status=TopicStatus.RISING),
        ]

        alerts = engine.evaluate(topics, changes=changes)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "status_change"

    def test_source_filter(self):
        rule = _make_rule(sources=[TopicSource.ZHIHU])
        engine = AlertEngine(rules=[rule])
        topics = [_make_topic("话题")]

        alerts = engine.evaluate(topics)
        assert len(alerts) == 0

    def test_disabled_rule(self):
        rule = _make_rule(keywords=["AI"])
        rule.enabled = False
        engine = AlertEngine(rules=[rule])
        topics = [_make_topic("AI突破")]

        alerts = engine.evaluate(topics)
        assert len(alerts) == 0

    def test_no_rules(self):
        engine = AlertEngine(rules=[])
        topics = [_make_topic("任何话题")]
        alerts = engine.evaluate(topics)
        assert alerts == []

    def test_multiple_rules(self):
        rules = [
            _make_rule(name="AI", keywords=["AI"]),
            _make_rule(name="hot", hot_value_threshold=10000),
        ]
        engine = AlertEngine(rules=rules)
        topics = [_make_topic("AI突破", 15000)]

        alerts = engine.evaluate(topics)
        assert len(alerts) == 2


class TestLoadRules:
    """load_rules 测试."""

    def test_load_from_yaml(self, tmp_path: Path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(
            yaml.dump(
                {
                    "rules": [
                        {
                            "name": "测试规则",
                            "keywords": ["AI"],
                            "sources": ["weibo"],
                            "hot_value_threshold": 10000,
                            "status_trigger": ["new"],
                            "enabled": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        rules = AlertEngine.load_rules(rules_file)
        assert len(rules) == 1
        assert rules[0].name == "测试规则"
        assert rules[0].keywords == ["AI"]

    def test_load_nonexistent(self):
        rules = AlertEngine.load_rules(Path("/nonexistent/rules.yaml"))
        assert rules == []

    def test_load_none_path(self):
        rules = AlertEngine.load_rules(None)
        assert rules == []

    def test_skip_disabled_rules(self, tmp_path: Path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(
            yaml.dump(
                {
                    "rules": [
                        {"name": "enabled", "keywords": ["AI"], "enabled": True},
                        {"name": "disabled", "keywords": ["GPT"], "enabled": False},
                    ],
                }
            ),
            encoding="utf-8",
        )

        rules = AlertEngine.load_rules(rules_file)
        assert len(rules) == 1
        assert rules[0].name == "enabled"
