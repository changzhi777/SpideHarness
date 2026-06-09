# 消息队列模块

> [根目录](../../CLAUDE.md) > [spide](../) > **queue**

## 职责

基于 `asyncio.Queue` 的进程内消息总线，支持主题发布/订阅和通配符匹配。用于模块间解耦通讯（Engine、Monitor、Spider 等）。

## 文件清单（2 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 Event, MessageBroker |
| `broker.py` | MessageBroker + Event |

## 核心接口

```python
from spide.queue.broker import MessageBroker

broker = MessageBroker(max_queue_size=100)

# 订阅（异步迭代器，支持 * 通配符）
async for event in broker.subscribe("crawl.*"):
    print(event.topic, event.data, event.timestamp)

# 发布
count = await broker.publish(
    "crawl.completed",
    {"source": "weibo", "count": 50},
    source="engine",
)

# 停止（向所有订阅者发送 __stop__ 终止信号）
broker.stop()
```

## 数据模型

### Event
```python
@dataclass
class Event:
    topic: str                  # 主题名
    data: Any                   # 事件数据
    timestamp: datetime         # 事件时间
    source: str = ""            # 来源标识
```

### MessageBroker
- `subscribers: dict[str, list[asyncio.Queue]]` — 主题 → 订阅者队列
- `max_queue_size: int = 100` — 每队列容量
- 属性：`topic_count`, `subscriber_count`

## 特性

- **精确匹配** + `*` 通配符（单段匹配）
  - `crawl.*` 匹配 `crawl.completed`、`crawl.failed`
  - `crawl.*` 不匹配 `crawl.deep.completed`（单段）
- **队列满时自动跳过**并记录 `logger.warning`
- **优雅关闭**: `broker.stop()` 向所有队列发送 `__stop__` 终止信号，订阅者退出循环
- **延迟注册**: 订阅时可指定 `max_queue_size`

## 主题设计示例

```
crawl.started        # 采集开始
crawl.completed      # 采集完成
crawl.failed         # 采集失败
alert.triggered      # 告警触发
alert.notified       # 告警已通知
spider.error         # 爬虫错误
```

订阅模式：
- `crawl.*` — 接收所有 crawl 主题
- `*` — 接收所有主题
- `crawl.completed` — 精确订阅

## 依赖

- asyncio (标准库)
- dataclasses (标准库)
- `spide.logging` — structlog

## 设计原则

- **KISS** — 仅 pub/sub + 通配符，不做持久化/分布式
- **零依赖** — 纯 asyncio，不引入 Redis/RabbitMQ
- **YAGNI** — 不做跨进程通讯（用 MQTT 做）

## 测试

- `tests/unit/test_broker.py` — pub/sub + 通配符匹配 + 停止信号
