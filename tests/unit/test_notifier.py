# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 通知渠道."""

from unittest.mock import AsyncMock, MagicMock, patch

from spide.monitor.notifier import (
    FeishuNotifier,
    LogNotifier,
    MQTTNotifier,
    NotifierDispatcher,
    WebhookNotifier,
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


class TestMQTTNotifier:
    """MQTTNotifier 测试."""

    async def test_send_success(self):
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        notifier = MQTTNotifier(mock_client)

        result = await notifier.send(_make_alert())
        assert result is True
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert "alert/test" in call_args[0][0]

    async def test_send_failure(self):
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=ConnectionError("断连"))
        notifier = MQTTNotifier(mock_client)

        result = await notifier.send(_make_alert())
        assert result is False


class TestWebhookNotifier:
    """WebhookNotifier 测试."""

    async def test_send_no_url(self):
        notifier = WebhookNotifier(url="")
        result = await notifier.send(_make_alert())
        assert result is False

    async def test_send_success(self):
        notifier = WebhookNotifier(url="https://hooks.example.com/test")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp):
            result = await notifier.send(_make_alert())
            assert result is True

    async def test_send_http_error(self):
        notifier = WebhookNotifier(url="https://hooks.example.com/test")

        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_resp.text = AsyncMock(return_value="Internal Server Error")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp):
            result = await notifier.send(_make_alert())
            assert result is False

    async def test_send_connection_error(self):
        notifier = WebhookNotifier(url="https://hooks.example.com/test")

        with patch("aiohttp.ClientSession.post", side_effect=Exception("网络错误")):
            result = await notifier.send(_make_alert())
            assert result is False


class TestFeishuNotifier:
    """FeishuNotifier 测试."""

    async def test_send_no_url(self):
        notifier = FeishuNotifier(webhook_url="")
        result = await notifier.send(_make_alert())
        assert result is False

    async def test_send_success(self):
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp) as mock_post:
            result = await notifier.send(_make_alert(title="飞书告警"))
            assert result is True
            call_kwargs = mock_post.call_args
            payload = call_kwargs[1]["json"]
            assert payload["msg_type"] == "interactive"
            assert "飞书告警" in str(payload)

    async def test_send_http_error(self):
        notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx")

        mock_resp = MagicMock()
        mock_resp.status = 403
        mock_resp.text = AsyncMock(return_value="forbidden")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp):
            result = await notifier.send(_make_alert())
            assert result is False


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

    async def test_dispatch_mqtt_channel(self):
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        dispatcher = NotifierDispatcher(mqtt_client=mock_client)
        results = await dispatcher.dispatch(_make_alert(), ["mqtt"])
        assert results["mqtt"] is True

    async def test_dispatch_mqtt_failure(self):
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(side_effect=Exception("fail"))
        dispatcher = NotifierDispatcher(mqtt_client=mock_client)
        results = await dispatcher.dispatch(_make_alert(), ["mqtt"])
        assert results["mqtt"] is False

    async def test_dispatch_multi_channels(self):
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        dispatcher = NotifierDispatcher(
            mqtt_client=mock_client,
            webhook_url="https://hooks.example.com",
        )

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp):
            results = await dispatcher.dispatch(_make_alert(), ["log", "mqtt", "webhook"])
            assert results["log"] is True
            assert results["mqtt"] is True
            assert results["webhook"] is True

    async def test_dispatch_feishu_channel(self):
        dispatcher = NotifierDispatcher(feishu_url="https://open.feishu.cn/hook/x")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession.post", return_value=mock_resp):
            results = await dispatcher.dispatch(_make_alert(), ["feishu"])
            assert results["feishu"] is True
