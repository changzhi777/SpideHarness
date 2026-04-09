# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — MQTT 客户端."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.config import MQTTConfig
from spide.exceptions import MQTTError
from spide.mqtt.client import MQTTClient


class TestMQTTClient:
    """MQTT 客户端."""

    @pytest.mark.asyncio
    async def test_no_host(self):
        client = MQTTClient(MQTTConfig())
        with pytest.raises(MQTTError, match="未配置"):
            await client.start()

    @pytest.mark.asyncio
    async def test_not_connected(self):
        client = MQTTClient(MQTTConfig(host="test"))
        with pytest.raises(MQTTError, match="未连接"):
            await client.publish("topic")

    @pytest.mark.asyncio
    async def test_publish_json_payload(self):
        client = MQTTClient(MQTTConfig(host="test.local", port=8883))

        with patch("spide.mqtt.client.aiomqtt.Client") as mock_cls:
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=False)
            mock_inst.publish = AsyncMock()
            mock_cls.return_value = mock_inst

            await client.start()
            await client.publish("test/topic", payload={"key": "val"})

            call = mock_inst.publish.call_args
            assert "spide_agent/test/topic" in call[0][0]
            assert '"key"' in call[1]["payload"]

            await client.stop()

    @pytest.mark.asyncio
    async def test_tls_context_build(self, tmp_path):
        """验证 TLS 上下文构建逻辑（mock ssl）."""
        client = MQTTClient(
            MQTTConfig(host="test.local", use_tls=True, ca_cert="ca.crt"),
            project_root=tmp_path,
        )
        with patch("ssl.create_default_context") as mock_ssl:
            mock_ctx = MagicMock()
            mock_ssl.return_value = mock_ctx

            ctx = client._build_tls_context()
            assert ctx is mock_ctx
            mock_ssl.assert_called_once()
