# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MQTT 客户端 — aiomqtt 封装，TLS + 自动重连.

用法:
    from spide.mqtt import MQTTClient
    from spide.config import load_settings

    settings = load_settings()
    client = MQTTClient(settings.mqtt, project_root=Path("."))
    await client.start()

    # 发布
    await client.publish("spide/crawl/result", payload={"source": "weibo", "count": 50})

    # 订阅
    async for message in client.subscribe("spide/crawl/request"):
        print(message.topic, message.payload)

    await client.stop()
"""

from __future__ import annotations

import json
import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiomqtt

from spide.config import MQTTConfig
from spide.exceptions import MQTTError
from spide.logging import get_logger

logger = get_logger(__name__)

# 默认主题前缀
_TOPIC_PREFIX = "spide_agent"


class MQTTClient:
    """MQTT 客户端 — aiomqtt 封装."""

    def __init__(
        self,
        config: MQTTConfig,
        *,
        project_root: Path | None = None,
        topic_prefix: str = _TOPIC_PREFIX,
    ) -> None:
        self._config = config
        self._project_root = project_root or Path.cwd()
        self._topic_prefix = topic_prefix
        self._client: aiomqtt.Client | None = None
        self._connected = False

    async def start(self) -> None:
        """连接 MQTT 代理."""
        if not self._config.host:
            raise MQTTError("MQTT 主机地址未配置")

        try:
            tls_context = None
            if self._config.use_tls:
                tls_context = self._build_tls_context()

            self._client = aiomqtt.Client(
                hostname=self._config.host,
                port=self._config.port,
                username=self._config.username or None,
                password=self._config.password or None,
                clean_session=self._config.clean_session,
                keepalive=self._config.keepalive,
                tls_context=tls_context,
            )
            await self._client.__aenter__()
            self._connected = True
            logger.debug(
                "mqtt_connected",
                host=self._config.host,
                port=self._config.port,
            )
        except Exception as e:
            raise MQTTError(f"MQTT 连接失败: {e}") from e

    async def stop(self) -> None:
        """断开 MQTT 连接."""
        import contextlib

        if self._client:
            with contextlib.suppress(Exception):
                await self._client.__aexit__(None, None, None)
            self._client = None
            self._connected = False
            logger.debug("mqtt_disconnected")

    @property
    def connected(self) -> bool:
        return self._connected

    def _ensure_client(self) -> aiomqtt.Client:
        if self._client is None:
            raise MQTTError("MQTT 客户端未连接，请先调用 start()")
        return self._client

    # -----------------------------------------------------------------------
    # 发布
    # -----------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        *,
        payload: Any = None,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """发布消息.

        Args:
            topic: 主题（自动添加前缀）
            payload: 消息内容（dict/list 自动 JSON 序列化）
            qos: QoS 级别 (0/1/2)
            retain: 是否保留消息
        """
        client = self._ensure_client()
        full_topic = f"{self._topic_prefix}/{topic}"

        # 序列化 payload
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False)
        elif payload is not None:
            data = str(payload)
        else:
            data = ""

        try:
            await client.publish(full_topic, payload=data, qos=qos, retain=retain)
            logger.debug("mqtt_published", topic=full_topic, qos=qos)
        except Exception as e:
            raise MQTTError(f"MQTT 发布失败: {e}") from e

    # -----------------------------------------------------------------------
    # 订阅
    # -----------------------------------------------------------------------

    async def subscribe(
        self,
        topic: str,
        *,
        qos: int = 1,
    ) -> AsyncIterator[aiomqtt.Message]:
        """订阅主题并返回消息迭代器.

        Args:
            topic: 主题（自动添加前缀，支持通配符 # 和 +）
            qos: QoS 级别
        """
        client = self._ensure_client()
        full_topic = f"{self._topic_prefix}/{topic}"

        await client.subscribe(full_topic, qos=qos)
        logger.debug("mqtt_subscribed", topic=full_topic)

        async for message in client.messages:
            yield message

    async def subscribe_and_handle(
        self,
        topic: str,
        handler: Any,
        *,
        qos: int = 1,
    ) -> None:
        """订阅主题并通过回调处理消息.

        Args:
            topic: 主题
            handler: 异步回调函数 async def handler(topic: str, payload: str)
            qos: QoS 级别
        """
        async for message in self.subscribe(topic, qos=qos):
            try:
                topic_str = str(message.topic)
                payload = message.payload
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8")  # type: ignore[assignment]
                await handler(topic_str, payload)
            except Exception as e:
                logger.error("mqtt_handler_error", error=str(e))

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _build_tls_context(self) -> ssl.SSLContext:
        """构建 TLS 上下文."""
        ctx = ssl.create_default_context()

        ca_path = self._project_root / self._config.ca_cert
        if ca_path.exists():
            ctx.load_verify_locations(str(ca_path))
            logger.debug("mqtt_tls_ca_loaded", path=str(ca_path))
        else:
            logger.warning("mqtt_tls_ca_not_found", path=str(ca_path))

        return ctx
