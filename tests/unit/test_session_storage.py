# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 会话持久化."""

from pathlib import Path

import pytest

from spide.session_storage import SessionStorage


class TestSessionStorage:
    """会话快照完整覆盖."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        await storage.save_snapshot(
            session_id="test-001",
            session_key="weibo:daily",
            model="glm-5.1",
            messages=[{"role": "user", "content": "采集微博热搜"}],
            crawled_urls=["https://weibo.com/1"],
            progress=0.5,
        )

        latest = await storage.load_latest()
        assert latest is not None
        assert latest["session_id"] == "test-001"
        assert latest["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_load_by_session_key(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        await storage.save_snapshot(session_id="s1", session_key="weibo:hot")
        await storage.save_snapshot(session_id="s2", session_key="baidu:hot")

        weibo = await storage.load_latest_for_session_key("weibo:hot")
        assert weibo["session_id"] == "s1"

        baidu = await storage.load_latest_for_session_key("baidu:hot")
        assert baidu["session_id"] == "s2"

    @pytest.mark.asyncio
    async def test_load_by_id(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        await storage.save_snapshot(session_id="unique-123", summary="测试会话")

        loaded = await storage.load_by_id("unique-123")
        assert loaded is not None
        assert loaded["summary"] == "测试会话"

        assert await storage.load_by_id("not-exist") is None

    @pytest.mark.asyncio
    async def test_list_snapshots(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))

        storage = SessionStorage()
        for i in range(5):
            await storage.save_snapshot(session_id=f"snap-{i}")

        snapshots = await storage.list_snapshots(limit=3)
        assert len(snapshots) == 3

    @pytest.mark.asyncio
    async def test_no_latest(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("SPIDE_WORKSPACE", str(tmp_path))
        storage = SessionStorage()
        assert await storage.load_latest() is None
