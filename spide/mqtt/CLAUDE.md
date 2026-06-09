# MQTT 通讯模块

> [根目录](../../CLAUDE.md) > [spide](../) > **mqtt**

## 职责

MQTT 通讯客户端封装，支持 TLS 加密连接到 EMQX Cloud，提供发布/订阅能力。用于跨节点消息广播（告警、采集结果、状态同步）。

## 文件清单（2 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 MQTTClient |
| `client.py` | MQTTClient — aiomqtt 封装，TLS + 发布/订阅 |

## 核心接口

```python
from spide.mqtt import MQTTClient

client = MQTTClient(settings.mqtt, project_root=Path("."))
await client.start()

# 发布（自动添加 spide_agent/ 前缀，dict 自动 JSON 序列化）
await client.publish("crawl/result", payload={"source": "weibo", "count": 50})
await client.publish("alert/notification", payload=alert_dict, qos=1)

# 订阅（异步迭代器）
async for message in client.subscribe("crawl/request"):
    print(message.topic, message.payload)

# 回调模式
async def handler(topic, payload):
    print(f"received: {topic} → {payload}")
await client.subscribe_and_handle("crawl/request", handler=handler)

await client.stop()
```

## 特性

- **TLS 加密**: SSL 上下文加载 CA 证书
- **自动重连**: 指数退避策略（`reconnect.backoff_base` × 2^attempt）
- **主题前缀**: 自动添加 `spide_agent/` 前缀避免冲突
- **自动序列化**: `dict` payload 自动 JSON 编码；`str` 直接发送；`bytes` 直接发送
- **回调模式**: `subscribe_and_handle()` 自动 ack

## 配置

连接配置位于 `configs/mqtt.yaml`：

- **连接**: EMQX Cloud (阿里云杭州)
- **TLS 端口**: 8883
- **WSS 端口**: 8084
- **CA 证书**: `CA/emqxsl-ca.crt`
- **主题前缀**: `spide_agent/`
- **凭证**: 用户名 + 密码

`MQTTConfig` 字段：
- `host`, `port`, `ws_port`
- `username`, `password`
- `use_tls: bool = True`
- `ca_cert: str = "CA/emqxsl-ca.crt"`
- `keepalive: int = 60`
- `clean_session: bool = True`
- `reconnect.max_retries: int = 10`
- `reconnect.backoff_base: float = 2.0`
- `reconnect.backoff_max: float = 60.0`

## 依赖

- aiomqtt — 异步 MQTT 客户端
- ssl (标准库) — TLS 上下文
- `spide.config` — MQTTConfig
- `spide.exceptions` — MQTTError
- `spide.logging` — structlog

## 测试

- `tests/unit/test_mqtt_client.py` — 连接/发布/订阅 Mock 测试
- `tests/integration/test_real_mqtt.py` — 需真实 MQTT 连接（@integration）
