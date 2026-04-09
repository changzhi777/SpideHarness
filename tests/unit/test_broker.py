# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 消息总线."""

import asyncio

import pytest

from spide.queue.broker import MessageBroker


class TestBroker:
    """消息总线."""

    @pytest.mark.asyncio
    async def test_pub_sub(self):
        broker = MessageBroker()
        received = []

        async def sub():
            async for event in broker.subscribe("topic.a"):
                received.append(event.data)
                if len(received) >= 2:
                    broker.stop()

        task = asyncio.create_task(sub())
        await asyncio.sleep(0.05)

        await broker.publish("topic.a", "msg1")
        await broker.publish("topic.a", "msg2")
        await task

        assert received == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_wildcard(self):
        broker = MessageBroker()
        received = []

        async def sub():
            async for event in broker.subscribe("events.*"):
                received.append(event.topic)
                broker.stop()

        task = asyncio.create_task(sub())
        await asyncio.sleep(0.05)

        await broker.publish("events.click", "data")
        await task

        assert received == ["events.click"]

    @pytest.mark.asyncio
    async def test_no_match(self):
        broker = MessageBroker()
        count = await broker.publish("no.match", "data")
        assert count == 0

    @pytest.mark.asyncio
    async def test_multi_subscribers(self):
        broker = MessageBroker()
        r1, r2 = [], []

        async def sub1():
            async for event in broker.subscribe("shared"):
                r1.append(event.data)
                if len(r1) >= 1:
                    broker.stop()

        async def sub2():
            async for event in broker.subscribe("shared"):
                r2.append(event.data)

        t1 = asyncio.create_task(sub1())
        t2 = asyncio.create_task(sub2())
        await asyncio.sleep(0.05)

        count = await broker.publish("shared", "broadcast")
        assert count == 2

        broker.stop()
        await t1
        await t2
        assert r1 == ["broadcast"]
        assert r2 == ["broadcast"]
