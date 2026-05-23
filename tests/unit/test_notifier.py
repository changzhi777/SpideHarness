# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 通知渠道."""

from spide.monitor.notifier import (
    BaseNotifier,
    LogNotifier,
    NotifierDispatcher,
)
from spide.storage.models import AlertRecord, TopicSource


def _make_alert(title: str = "测试话题", rule_name: str = "test") -> AlertRecord:
    return AlertRecord(
        rule_id=1,
        rule_name=rule_name,
        topic_title=title,
        topic_source=TopicSource.WEIBO,
        topic_hot_value=5000,
        alert_type="keyword_match",
    )


class TestLogNotifier:
    """LogNotifier 测试."""

    async def test_send(self):
        notifier = LogNotifier()
        result = await notifier.send(_make_alert())
        assert result is True


class TestNotifierDispatcher:
    """NotifierDispatcher 测试."""

    async def test_dispatch_log(self):
        dispatcher = NotifierDispatcher()
        results = await dispatcher.dispatch(_make_alert(), ["log"])
        assert results["log"] is True

    async def test_dispatch_default_log(self):
        dispatcher = NotifierDispatcher()
        results = await dispatcher.dispatch(_make_alert())
        assert "log" in results
        assert results["log"] is True

    async def test_dispatch_unknown_channel(self):
        dispatcher = NotifierDispatcher()
        results = await dispatcher.dispatch(_make_alert(), ["unknown_channel"])
        assert results["unknown_channel"] is False

    async def test_dispatch_webhook_no_url(self):
        dispatcher = NotifierDispatcher()
        results = await dispatcher.dispatch(_make_alert(), ["webhook"])
        assert results["webhook"] is False
