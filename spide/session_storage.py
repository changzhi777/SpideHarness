# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""会话持久化 — JSON 快照存储.

用法:
    from spide.session_storage import SessionStorage

    storage = SessionStorage()
    await storage.save_snapshot(session_id="abc", messages=[...], crawled_urls=["..."])
    session = await storage.load_latest()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path

from spide.logging import get_logger
from spide.storage.models import CrawlSession
from spide.workspace import get_sessions_dir, get_workspace_root

logger = get_logger(__name__)


class SessionStorage:
    """文件系统会话存储."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        self._workspace = get_workspace_root(workspace)

    def get_session_dir(self, cwd: str = "") -> Path:
        """获取会话目录."""
        d = get_sessions_dir(self._workspace)
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save_snapshot(
        self,
        *,
        session_id: str,
        session_key: str | None = None,
        cwd: str = "",
        model: str = "glm-5.1",
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        usage: dict | None = None,
        summary: str | None = None,
        crawled_urls: list[str] | None = None,
        task_ids: list[int] | None = None,
        progress: float = 0.0,
    ) -> Path:
        """保存会话快照."""
        session = CrawlSession(
            session_id=session_id,
            session_key=session_key,
            cwd=cwd,
            model=model,
            system_prompt=system_prompt,
            messages=messages or [],
            usage=usage or {},
            created_at=datetime.now(),
            summary=summary,
            crawled_urls=crawled_urls or [],
            task_ids=task_ids or [],
            progress=progress,
        )

        session_dir = self.get_session_dir(cwd)
        data = session.model_dump(mode="json")
        content = json.dumps(data, ensure_ascii=False, indent=2)

        # 写入会话文件
        session_file = session_dir / f"session-{session_id}.json"
        await self._write_json(session_file, content)

        # 更新 latest 指针
        await self._write_json(session_dir / "latest.json", content)

        # 如果有 session_key，额外保存一份
        if session_key:
            key_token = _session_key_token(session_key)
            await self._write_json(session_dir / f"latest-{key_token}.json", content)

        logger.debug("session_saved", session_id=session_id, key=session_key)
        return session_file

    async def load_latest(self, cwd: str = "") -> dict | None:
        """加载最新的会话."""
        session_dir = self.get_session_dir(cwd)
        return await self._read_json(session_dir / "latest.json")

    async def load_latest_for_session_key(
        self, session_key: str, cwd: str = ""
    ) -> dict | None:
        """按 session_key 加载最新会话."""
        session_dir = self.get_session_dir(cwd)
        key_token = _session_key_token(session_key)
        return await self._read_json(session_dir / f"latest-{key_token}.json")

    async def list_snapshots(self, cwd: str = "", limit: int = 20) -> list[dict]:
        """列出最近 N 个快照."""
        session_dir = self.get_session_dir(cwd)
        files = await asyncio.to_thread(
            lambda: sorted(
                session_dir.glob("session-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:limit]
        )

        snapshots: list[dict] = []
        for f in files:
            data = await self._read_json(f)
            if data is not None:
                data["_file"] = str(f)
                snapshots.append(data)
        return snapshots

    async def load_by_id(self, session_id: str, cwd: str = "") -> dict | None:
        """按 session_id 加载."""
        session_dir = self.get_session_dir(cwd)
        return await self._read_json(session_dir / f"session-{session_id}.json")

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    @staticmethod
    async def _write_json(path: Path, content: str) -> None:
        """异步写入 JSON 文件."""
        await asyncio.to_thread(
            lambda: path.write_text(content, encoding="utf-8")
        )

    @staticmethod
    async def _read_json(path: Path) -> dict | None:
        """异步读取 JSON 文件."""
        if not path.exists():
            return None
        try:
            text = await asyncio.to_thread(lambda: path.read_text(encoding="utf-8"))
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return None


def _session_key_token(session_key: str) -> str:
    """生成 session_key 的短 token（用于文件名）."""
    return hashlib.sha1(session_key.encode()).hexdigest()[:12]
