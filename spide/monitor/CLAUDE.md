# 监控告警模块

> [根目录](../../CLAUDE.md) → `spide/monitor/`

## 职责

关键词监控与多渠道告警通知，支持规则引擎评估和多通知渠道分发。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 8 | 导出 AlertEngine, Notifier 类 |
| `alert_engine.py` | 175 | AlertEngine — 规则加载 + 三种匹配（关键词/热度/状态） |
| `notifier.py` | 212 | Log/MQTT/Webhook/飞书通知 + NotifierDispatcher |

## 核心接口

### AlertEngine
```python
engine = AlertEngine(rules=rules)
alerts = engine.evaluate(topics, changes=changes)

rules = AlertEngine.load_rules("configs/alert_rules.yaml")
```

### NotifierDispatcher
```python
dispatcher = NotifierDispatcher(mqtt_client=client, webhook_url="...", feishu_url="...")
results = await dispatcher.dispatch(alert, channels=["log", "mqtt"])
```

## 告警匹配逻辑

1. **keyword_match** — 话题标题包含规则关键词（OR 匹配）
2. **hot_value_exceed** — 热度超过阈值
3. **status_change** — 话题状态变化在触发列表中（依赖 IncrementalDetector）

## 配置

`configs/alert_rules.yaml` — YAML 格式规则定义

## 依赖

- yaml — 规则文件解析
- aiohttp — Webhook/飞书 HTTP 调用
- spide.storage.models — AlertRule, AlertRecord
- spide.logging — structlog

## 测试

- `tests/unit/test_alert_engine.py`
- `tests/unit/test_notifier.py`
