# 消息队列模块

> [根目录](../../CLAUDE.md) → `spide/queue/`

## 职责

基于 asyncio.Queue 的进程内消息总线，支持主题发布/订阅和通配符匹配。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 7 | 导出 Event, MessageBroker |
| `broker.py` | 142 | MessageBroker + Event |

## 核心接口

```python
broker = MessageBroker(max_queue_size=100)

# 订阅（异步迭代器，支持 * 通配符）
async for event in broker.subscribe("crawl.*"):
    print(event.topic, event.data, event.timestamp)

# 发布
count = await broker.publish("crawl.completed", {"source": "weibo"}, source="engine")

# 停止（向所有订阅者发送终止信号）
broker.stop()
```

## Event 数据类

- `topic: str` — 主题名
- `data: Any` — 事件数据
- `timestamp: datetime` — 事件时间
- `source: str` — 来源标识

## 特性

- 精确匹配 + `*` 通配符（单段匹配，如 `crawl.*` 匹配 `crawl.completed`）
- 队列满时自动跳过并记录警告
- `broker.stop()` 向所有队列发送 `__stop__` 终止信号
- 属性: `topic_count`, `subscriber_count`

## 依赖

- asyncio (标准库)
- spide.logging

## 测试

- `tests/unit/test_broker.py`
