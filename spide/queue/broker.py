# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""内部消息总线 — asyncio.Queue 发布/订阅模式.

用法:
    from spide.queue import MessageBroker

    broker = MessageBroker()

    # 订阅
    async for event in broker.subscribe("crawl.completed"):
        print(event)

    # 发布
    await broker.publish("crawl.completed", {"source": "weibo", "count": 50})

    broker.stop()
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from spide.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """消息事件."""

    topic: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


class MessageBroker:
    """异步消息总线 — 基于主题的发布/订阅."""

    def __init__(self, *, max_queue_size: int = 100) -> None:
        self._max_size = max_queue_size
        self._subscribers: dict[str, list[asyncio.Queue[Event]]] = defaultdict(list)
        self._running = True

    def stop(self) -> None:
        """停止消息总线."""
        self._running = False
        # 向所有订阅者发送终止信号
        for queues in self._subscribers.values():
            for q in queues:
                q.put_nowait(Event(topic="__stop__"))

    async def publish(self, topic: str, data: Any = None, *, source: str = "") -> int:
        """发布事件到指定主题.

        Args:
            topic: 主题名称
            data: 事件数据
            source: 事件来源标识

        Returns:
            收到事件的订阅者数量
        """
        if not self._running:
            return 0

        event = Event(topic=topic, data=data, source=source)
        count = 0

        # 精确匹配
        for q in self._subscribers.get(topic, []):
            try:
                q.put_nowait(event)
                count += 1
            except asyncio.QueueFull:
                logger.warning("broker_queue_full", topic=topic)

        # 通配符匹配
        for pattern, queues in self._subscribers.items():
            if pattern == topic:
                continue
            if self._match_pattern(pattern, topic):
                for q in queues:
                    try:
                        q.put_nowait(event)
                        count += 1
                    except asyncio.QueueFull:
                        logger.warning("broker_queue_full", topic=topic)

        if count > 0:
            logger.debug("broker_published", topic=topic, subscribers=count)

        return count

    async def subscribe(self, topic: str) -> AsyncIterator[Event]:
        """订阅主题（返回异步迭代器）.

        支持 * 通配符匹配单段主题。
        """
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._max_size)
        self._subscribers[topic].append(queue)

        try:
            while self._running:
                event = await queue.get()
                if event.topic == "__stop__":
                    break
                yield event
        finally:
            self._subscribers[topic].remove(queue)
            if not self._subscribers[topic]:
                del self._subscribers[topic]

    @property
    def topic_count(self) -> int:
        """当前活跃主题数."""
        return len(self._subscribers)

    @property
    def subscriber_count(self) -> int:
        """当前总订阅者数."""
        return sum(len(qs) for qs in self._subscribers.values())

    @staticmethod
    def _match_pattern(pattern: str, topic: str) -> bool:
        """简单的通配符匹配（* 匹配单段）."""
        if "*" not in pattern:
            return False
        pattern_parts = pattern.split(".")
        topic_parts = topic.split(".")
        if len(pattern_parts) != len(topic_parts):
            return False
        return all(
            p == "*" or p == t for p, t in zip(pattern_parts, topic_parts, strict=False)
        )
