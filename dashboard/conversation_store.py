"""会话存储（SQLite 多轮记忆）。

表结构：
- chat_sessions: 会话元信息（session_id, user_id, chat_id, created_at, updated_at）
- chat_messages: 消息历史（id, session_id, role, content, tool_calls, created_at）
"""

from __future__ import annotations

import json
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_DB_PATH = "spide_data.db"
MAX_HISTORY = 20  # 多轮记忆窗口


@dataclass
class ChatMessage:
    """会话消息。"""

    role: str  # system / user / assistant / tool
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # tool name (when role=tool)


class ConversationStore:
    """会话存储（异步 SQLite）。"""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = str(db_path)

    async def init(self) -> None:
        """初始化表结构。"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id, created_at)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id, chat_id)"
            )
            await db.commit()
        logger.info("conversation_store_initialized", db=self.db_path)

    @staticmethod
    def make_session_id(user_id: str, chat_id: str) -> str:
        """生成稳定 session_id（同一用户在同一群中的对话归一）。"""
        return f"{chat_id}:{user_id}"

    async def get_or_create_session(
        self,
        user_id: str,
        chat_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """获取或创建会话。返回 session_id。"""
        session_id = self.make_session_id(user_id, chat_id)
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                await db.execute(
                    """
                    INSERT INTO chat_sessions (session_id, user_id, chat_id, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        chat_id,
                        now,
                        now,
                        json.dumps(metadata or {}, ensure_ascii=False),
                    ),
                )
                await db.commit()
                logger.info("session_created", session_id=session_id)
        return session_id

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        """追加消息到会话。"""
        now = time.time()
        tool_calls_json = (
            json.dumps(message.tool_calls, ensure_ascii=False) if message.tool_calls else None
        )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO chat_messages
                (session_id, role, content, tool_calls, tool_call_id, name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    message.role,
                    message.content,
                    tool_calls_json,
                    message.tool_call_id,
                    message.name,
                    now,
                ),
            )
            await db.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            await db.commit()

    async def get_history(
        self,
        session_id: str,
        limit: int = MAX_HISTORY,
    ) -> list[dict[str, Any]]:
        """获取最近 N 条消息（按时间正序，OpenAI 格式）。"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, content, tool_calls, tool_call_id, name
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()

        messages: list[dict[str, Any]] = []
        for row in reversed(rows):
            msg: dict[str, Any] = {"role": row["role"], "content": row["content"]}
            if row["tool_calls"]:
                with suppress(json.JSONDecodeError):
                    msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["name"]:
                msg["name"] = row["name"]
            messages.append(msg)
        return messages

    async def clear_session(self, session_id: str) -> int:
        """清空会话历史（保留 session 元信息）。返回删除条数。"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,),
            )
            await db.commit()
            return cursor.rowcount or 0

    async def list_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """列出会话（管理用途）。"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if user_id:
                query = "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC"
                params: tuple[Any, ...] = (user_id,)
            else:
                query = "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
                params = ()
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


_store: ConversationStore | None = None


def get_conversation_store(db_path: str | Path = DEFAULT_DB_PATH) -> ConversationStore:
    """获取全局会话存储单例。"""
    global _store
    if _store is None:
        _store = ConversationStore(db_path)
    return _store


def reset_conversation_store() -> None:
    """重置存储（测试用）。"""
    global _store
    _store = None
