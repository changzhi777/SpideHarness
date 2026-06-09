# 监控告警模块

> [根目录](../../CLAUDE.md) > [spide](../) > **monitor**

## 职责

关键词监控与多渠道告警通知，支持规则引擎评估（关键词/热度/状态变化三种匹配方式）和多通知渠道分发（Log/MQTT/Webhook/飞书）。

## 文件清单（3 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 AlertEngine, LogNotifier, MQTTNotifier, WebhookNotifier |
| `alert_engine.py` | AlertEngine — 规则加载 + 三种匹配逻辑 |
| `notifier.py` | Log/MQTT/Webhook/飞书通知 + NotifierDispatcher |

## 核心接口

### AlertEngine
```python
from spide.monitor.alert_engine import AlertEngine

engine = AlertEngine(rules=rules)
alerts = engine.evaluate(topics, changes=changes)  # 评估告警

# 从 YAML 加载规则
rules = AlertEngine.load_rules("configs/alert_rules.yaml")
```

### NotifierDispatcher
```python
from spide.monitor.notifier import NotifierDispatcher

dispatcher = NotifierDispatcher(
    mqtt_client=client,        # 可选
    webhook_url="https://...", # 可选
    feishu_url="https://...",  # 可选
)
results = await dispatcher.dispatch(alert, channels=["log", "mqtt", "webhook", "feishu"])
```

支持的 Notifier：
- `LogNotifier` — 结构化日志
- `MQTTNotifier` — 发布到 MQTT 主题 `spide_agent/alert/`
- `WebhookNotifier` — HTTP POST JSON
- `FeishuNotifier` — 飞书机器人 Webhook（带签名验证）

## 告警匹配逻辑

1. **keyword_match** — 话题标题包含规则关键词（OR 匹配）
2. **hot_value_exceed** — 热度超过 `hot_value_threshold`
3. **status_change** — 话题状态变化在 `status_trigger` 列表中（依赖 `IncrementalDetector`）

## 配置

`configs/alert_rules.yaml` — YAML 格式规则定义：
```yaml
rules:
  - name: "AI 热点"
    keywords: ["AI", "大模型", "ChatGPT"]
    sources: ["weibo", "zhihu"]
    hot_value_threshold: 100000
    status_trigger: ["new", "rising"]
    enabled: true
```

`configs/alert.yaml` — 通知渠道配置：
- `webhook_url` — 通用 Webhook
- `feishu_url` — 飞书机器人 URL
- `channels` — 默认启用的渠道列表

## 依赖

- yaml — 规则文件解析
- aiohttp — Webhook/飞书 HTTP 调用
- `spide.storage.models` — AlertRule, AlertRecord
- `spide.logging` — structlog
- `spide.config` — AlertConfig
- `spide.mqtt.client` — MQTTNotifier (可选)

## 测试

- `tests/unit/test_alert_engine.py` — 规则匹配 + YAML 加载
- `tests/unit/test_notifier.py` — Log/MQTT/Webhook/飞书通知 + Dispatcher
