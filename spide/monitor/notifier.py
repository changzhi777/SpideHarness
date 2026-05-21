# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""多渠道告警通知器 — Log/MQTT/Webhook/飞书.

用法:
    from spide.monitor.notifier import LogNotifier, MQTTNotifier, WebhookNotifier

    # 日志通知
    notifier = LogNotifier()
    await notifier.notify(alert, channels=["log"])

    # MQTT 通知
    mqtt = MQTTNotifier(mqtt_client)
    await mqtt.notify(alert, channels=["mqtt"])
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import aiohttp

from spide.logging import get_logger
from spide.storage.models import AlertRecord

logger = get_logger(__name__)


class BaseNotifier(ABC):
    """通知器基类."""

    @abstractmethod
    async def send(self, alert: AlertRecord) -> bool:
        """发送通知，返回是否成功."""


class LogNotifier(BaseNotifier):
    """日志通知 — 记录到 structlog."""

    async def send(self, alert: AlertRecord) -> bool:
        logger.info(
            "alert_notification",
            rule=alert.rule_name,
            topic=alert.topic_title,
            source=alert.topic_source.value,
            hot_value=alert.topic_hot_value,
            alert_type=alert.alert_type,
            channel="log",
        )
        return True


class MQTTNotifier(BaseNotifier):
    """MQTT 通知 — 发布到 spide_agent/alert/{rule_name}."""

    def __init__(self, mqtt_client: Any) -> None:
        self._client = mqtt_client

    async def send(self, alert: AlertRecord) -> bool:
        try:
            payload = {
                "rule_name": alert.rule_name,
                "topic_title": alert.topic_title,
                "source": alert.topic_source.value,
                "hot_value": alert.topic_hot_value,
                "alert_type": alert.alert_type,
            }
            await self._client.publish(
                f"alert/{alert.rule_name}",
                payload=payload,
            )
            return True
        except Exception as e:
            logger.warning("mqtt_notify_failed", error=str(e))
            return False


class WebhookNotifier(BaseNotifier):
    """Webhook 通知 — HTTP POST JSON."""

    def __init__(self, url: str = "") -> None:
        self._url = url

    async def send(self, alert: AlertRecord) -> bool:
        if not self._url:
            return False

        payload = {
            "rule_name": alert.rule_name,
            "topic_title": alert.topic_title,
            "source": alert.topic_source.value,
            "hot_value": alert.topic_hot_value,
            "alert_type": alert.alert_type,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            "webhook_notify_failed",
                            status=resp.status,
                            url=self._url,
                        )
                        return False
                    return True
        except Exception as e:
            logger.warning("webhook_notify_error", error=str(e))
            return False


class FeishuNotifier(BaseNotifier):
    """飞书机器人 Webhook 通知."""

    def __init__(self, webhook_url: str = "") -> None:
        self._url = webhook_url

    async def send(self, alert: AlertRecord) -> bool:
        if not self._url:
            return False

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"[SpideAlert] {alert.rule_name}",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**话题**: {alert.topic_title}\n"
                                f"**来源**: {alert.topic_source.value}\n"
                                f"**热度**: {alert.topic_hot_value or 'N/A'}\n"
                                f"**类型**: {alert.alert_type}"
                            ),
                        },
                    },
                ],
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        logger.warning("feishu_notify_failed", status=resp.status, body=text[:200])
                        return False
                    return True
        except Exception as e:
            logger.warning("feishu_notify_error", error=str(e))
            return False


class NotifierDispatcher:
    """通知分发器 — 根据渠道名称分发到对应 Notifier."""

    def __init__(self, *, mqtt_client: Any = None, webhook_url: str = "", feishu_url: str = "") -> None:
        self._notifiers: dict[str, BaseNotifier] = {
            "log": LogNotifier(),
        }
        if mqtt_client:
            self._notifiers["mqtt"] = MQTTNotifier(mqtt_client)
        if webhook_url:
            self._notifiers["webhook"] = WebhookNotifier(webhook_url)
        if feishu_url:
            self._notifiers["feishu"] = FeishuNotifier(feishu_url)

    async def dispatch(self, alert: AlertRecord, channels: list[str] | None = None) -> dict[str, bool]:
        """分发告警到指定渠道.

        Args:
            alert: 告警记录
            channels: 渠道列表，默认 ["log"]

        Returns:
            {"log": True, "mqtt": False, ...}
        """
        target_channels = channels or ["log"]
        results: dict[str, bool] = {}

        for ch in target_channels:
            notifier = self._notifiers.get(ch)
            if notifier is None:
                logger.warning("unknown_channel", channel=ch)
                results[ch] = False
                continue

            try:
                results[ch] = await notifier.send(alert)
            except Exception as e:
                logger.error("notify_error", channel=ch, error=str(e))
                results[ch] = False

        return results
