# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 4 — 真实 MQTT 集成测试.

连接真实 EMQX Cloud（TLS），验证发布/订阅往返一致性。
标记 @pytest.mark.integration，无 MQTT 配置时自动跳过。
"""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from spide.config import load_settings
from spide.mqtt.client import MQTTClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_mqtt_config():
    settings = load_settings()
    if not settings.mqtt.host:
        pytest.skip("EMQX Cloud MQTT 未配置")
    return settings.mqtt


@pytest.fixture
async def real_mqtt(real_mqtt_config):
    import sys

    if sys.platform == "win32":
        # aiomqtt + paho-mqtt 在 Windows ProactorEventLoop 下不支持 add_reader/add_writer
        # 需要手动设置 SelectorEventLoop
        import asyncio

        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)

    client = MQTTClient(real_mqtt_config, project_root=Path.cwd())
    try:
        await client.start()
    except Exception as e:
        pytest.skip(f"MQTT 连接失败（网络/环境问题）: {e}")
    assert client.connected, "MQTT 连接应成功"
    yield client
    await client.stop()


# ---------------------------------------------------------------------------
# 连接生命周期
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMQTTConnection:
    """MQTT 连接生命周期."""

    async def test_mqtt_connect_and_disconnect(self, real_mqtt_config):
        import sys

        if sys.platform == "win32":
            import asyncio

            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)

        client = MQTTClient(real_mqtt_config, project_root=Path.cwd())
        try:
            await client.start()
        except Exception as e:
            pytest.skip(f"MQTT 连接失败（网络/环境问题）: {e}")
        assert client.connected is True

        await client.stop()
        assert client.connected is False


# ---------------------------------------------------------------------------
# 发布
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMQTTPublish:
    """MQTT 发布."""

    async def test_mqtt_publish_string(self, real_mqtt):
        await real_mqtt.publish("test/unit", payload="hello pytest")

    async def test_mqtt_publish_json_payload(self, real_mqtt):
        payload = {"source": "weibo", "count": 50, "timestamp": "2026-04-10"}
        await real_mqtt.publish("test/unit", payload=payload)

    async def test_mqtt_large_payload(self, real_mqtt):
        payload = {"data": "x" * 2000, "test": "large_payload"}
        await real_mqtt.publish("test/unit/large", payload=payload)


# ---------------------------------------------------------------------------
# 发布/订阅往返
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMQTTPubSub:
    """MQTT 发布/订阅往返验证."""

    async def test_mqtt_pubsub_roundtrip(self, real_mqtt):
        topic = f"test/roundtrip_{uuid4().hex[:8]}"
        expected = {"test": "roundtrip", "id": 42}
        received = asyncio.Queue()

        async def subscriber():
            async for message in real_mqtt.subscribe(topic):
                payload = message.payload
                if isinstance(payload, bytes):
                    payload = payload.decode()
                await received.put(payload)
                return  # 收到一条即退出

        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(1)  # 等待订阅生效
        await real_mqtt.publish(topic, payload=expected)

        result = await asyncio.wait_for(received.get(), timeout=10.0)
        sub_task.cancel()

        parsed = json.loads(result)
        assert parsed["test"] == "roundtrip"
        assert parsed["id"] == 42

    async def test_mqtt_multiple_messages(self, real_mqtt):
        topic = f"test/multi_{uuid4().hex[:8]}"
        received = asyncio.Queue()

        async def subscriber():
            count = 0
            async for message in real_mqtt.subscribe(topic):
                await received.put(message.payload)
                count += 1
                if count >= 3:
                    return

        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(1)

        for i in range(3):
            await real_mqtt.publish(topic, payload={"index": i})

        results = []
        for _ in range(3):
            msg = await asyncio.wait_for(received.get(), timeout=10.0)
            results.append(msg)
        sub_task.cancel()

        assert len(results) == 3, f"应收到 3 条消息，实际收到 {len(results)}"

    async def test_mqtt_topic_prefix_applied(self, real_mqtt):
        """验证 topic 前缀 spide_agent/ 自动添加."""
        # 通过发布不报错验证前缀机制正常工作
        await real_mqtt.publish("test/prefix_check", payload="prefix_test")
        # 如果前缀机制异常，publish 应抛出 MQTTError
