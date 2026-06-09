# MQTT 通讯模块

> [根目录](../../CLAUDE.md) → `spide/mqtt/`

## 职责

MQTT 通讯客户端封装，支持 TLS 加密连接到 EMQX Cloud，提供发布/订阅能力。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 7 | 导出 MQTTClient |
| `client.py` | 209 | MQTTClient — aiomqtt 封装，TLS + 发布/订阅 |

## 核心接口

```python
client = MQTTClient(settings.mqtt, project_root=Path("."))
await client.start()

# 发布（自动添加 spide_agent/ 前缀，dict 自动 JSON 序列化）
await client.publish("crawl/result", payload={"source": "weibo", "count": 50})

# 订阅（异步迭代器）
async for message in client.subscribe("crawl/request"):
    print(message.topic, message.payload)

# 回调模式
await client.subscribe_and_handle("crawl/request", handler=async_handler)

await client.stop()
```

## 配置

- 连接: EMQX Cloud (阿里云杭州), TLS 端口 8883, WSS 端口 8084
- CA 证书: `CA/emqxsl-ca.crt`
- 主题前缀: `spide_agent/`
- 凭证: `configs/mqtt.yaml`

## 依赖

- aiomqtt
- ssl (TLS 上下文)
- spide.config (MQTTConfig)
- spide.exceptions (MQTTError)

## 测试

- `tests/unit/test_mqtt_client.py`
- `tests/integration/test_real_mqtt.py` — 需真实 MQTT 连接
