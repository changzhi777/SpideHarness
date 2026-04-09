# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""迭代 4 验证测试 — MQTT + Message Bus + MCP."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Message Broker 测试
# ---------------------------------------------------------------------------


class TestMessageBroker:
    """消息总线测试."""

    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        from spide.queue.broker import MessageBroker

        broker = MessageBroker()
        received = []

        async def subscriber():
            async for event in broker.subscribe("test.topic"):
                received.append(event)
                if len(received) >= 2:
                    broker.stop()

        # 启动订阅者
        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.05)

        # 发布消息
        await broker.publish("test.topic", {"key": "value1"})
        await broker.publish("test.topic", {"key": "value2"})

        await sub_task

        assert len(received) == 2
        assert received[0].data["key"] == "value1"
        assert received[1].data["key"] == "value2"

    @pytest.mark.asyncio
    async def test_wildcard_subscribe(self):
        from spide.queue.broker import MessageBroker

        broker = MessageBroker()
        received = []

        async def subscriber():
            async for event in broker.subscribe("test.*"):
                received.append(event)
                if len(received) >= 1:
                    broker.stop()

        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.05)

        await broker.publish("test.hello", "wildcard_match")

        await sub_task

        assert len(received) == 1
        assert received[0].data == "wildcard_match"

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        from spide.queue.broker import MessageBroker

        broker = MessageBroker()
        count = await broker.publish("no.subscribers", "data")
        assert count == 0

    @pytest.mark.asyncio
    async def test_topic_count(self):
        from spide.queue.broker import MessageBroker

        broker = MessageBroker()
        received = []

        async def sub1():
            async for event in broker.subscribe("topic.a"):
                received.append(event)
                broker.stop()

        async def sub2():
            async for event in broker.subscribe("topic.b"):
                received.append(event)

        t1 = asyncio.create_task(sub1())
        t2 = asyncio.create_task(sub2())
        await asyncio.sleep(0.05)

        assert broker.topic_count == 2
        assert broker.subscriber_count == 2

        await broker.publish("topic.a", "stop")
        await t1
        # sub2 still pending but stop sent
        broker.stop()
        await t2


# ---------------------------------------------------------------------------
# MQTT Client 测试（mock）
# ---------------------------------------------------------------------------


class TestMQTTClient:
    """MQTT 客户端测试."""

    @pytest.mark.asyncio
    async def test_not_started(self):
        from spide.config import MQTTConfig
        from spide.exceptions import MQTTError
        from spide.mqtt.client import MQTTClient

        client = MQTTClient(MQTTConfig())
        with pytest.raises(MQTTError, match="未连接"):
            await client.publish("test/topic")

    @pytest.mark.asyncio
    async def test_no_host_configured(self):
        from spide.config import MQTTConfig
        from spide.exceptions import MQTTError
        from spide.mqtt.client import MQTTClient

        client = MQTTClient(MQTTConfig())
        with pytest.raises(MQTTError, match="未配置"):
            await client.start()

    @pytest.mark.asyncio
    async def test_publish_mock(self):
        from spide.config import MQTTConfig
        from spide.mqtt.client import MQTTClient

        config = MQTTConfig(
            host="test.mqtt.local",
            port=8883,
            username="test",
            password="test",
        )
        client = MQTTClient(config)

        # Mock aiomqtt.Client
        with patch("spide.mqtt.client.aiomqtt.Client") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.publish = AsyncMock()
            mock_cls.return_value = mock_instance

            await client.start()
            assert client.connected

            await client.publish("test/topic", payload={"key": "value"})
            mock_instance.publish.assert_called_once()

            # 验证 payload 被序列化
            call_args = mock_instance.publish.call_args
            assert "spide_agent/test/topic" in call_args[0][0]

            await client.stop()


# ---------------------------------------------------------------------------
# MCP Server 测试
# ---------------------------------------------------------------------------


class TestMCPServer:
    """MCP Server 测试."""

    def test_create_server(self):
        from spide.mcp import create_mcp_server

        server = create_mcp_server()
        assert server is not None
        assert server.name == "spide-agent"

    def test_tools_definitions(self):
        from spide.mcp.tools import ALL_TOOLS

        assert len(ALL_TOOLS) == 5
        tool_names = [t["name"] for t in ALL_TOOLS]
        assert "crawl_hot_topics" in tool_names
        assert "web_search" in tool_names
        assert "manage_memory" in tool_names
        assert "health_check" in tool_names
        assert "deep_crawl_hot_topics" in tool_names

    def test_tool_schemas(self):
        from spide.mcp.tools import CRAWL_TOOL, SEARCH_TOOL

        assert "source" in CRAWL_TOOL["inputSchema"]["properties"]
        assert CRAWL_TOOL["inputSchema"]["required"] == ["source"]

        assert "query" in SEARCH_TOOL["inputSchema"]["properties"]
        assert SEARCH_TOOL["inputSchema"]["required"] == ["query"]


# ---------------------------------------------------------------------------
# MCP Client 测试（mock）
# ---------------------------------------------------------------------------


class TestMCPClient:
    """MCP Client 测试."""

    @pytest.mark.asyncio
    async def test_client_not_connected(self):
        from spide.exceptions import MCPError
        from spide.mcp.client import MCPClient

        client = MCPClient(server_command="python", args=["server.py"])
        with pytest.raises(MCPError, match="未连接"):
            await client.list_tools()


# ---------------------------------------------------------------------------
# Config 更新测试
# ---------------------------------------------------------------------------


class TestConfigUpdate:
    """配置更新测试."""

    def test_mqtt_reconnect_config(self):
        from spide.config import MQTTConfig, MQTTReconnectConfig

        config = MQTTConfig(
            host="test.local",
            reconnect=MQTTReconnectConfig(max_retries=5, backoff_base=3.0),
        )
        assert config.reconnect.max_retries == 5
        assert config.reconnect.backoff_base == 3.0

    def test_default_mqtt_reconnect(self):
        from spide.config import MQTTConfig

        config = MQTTConfig()
        assert config.reconnect.max_retries == 10
        assert config.reconnect.backoff_max == 60.0
