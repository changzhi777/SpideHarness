# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""SQLite 持久化仓库 — aiosqlite 异步驱动.

用法:
    from spide.storage.sqlite_repo import SqliteRepository
    from spide.storage.models import HotTopic

    repo = SqliteRepository(HotTopic, db_path="spide_data.db")
    await repo.start()
    topic_id = await repo.save(topic)
    topics = await repo.query(source="weibo", limit=10)
    await repo.stop()
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, TypeVar, get_type_hints

import aiosqlite
from pydantic import BaseModel

from spide.exceptions import StorageError
from spide.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# 集合类型基类集合
_COLLECTION_TYPES = frozenset({list, dict, set, frozenset})

# 表名映射
_TABLE_MAP: dict[str, str] = {
    "HotTopic": "hot_topics",
    "NewsArticle": "news_articles",
    "CrawlTask": "crawl_tasks",
    "DeepContent": "deep_contents",
    "DeepComment": "deep_comments",
    "DeepCreator": "deep_creators",
}


class SqliteRepository:
    """SQLite 异步持久化仓库."""

    def __init__(self, model_class: type[T], *, db_path: str = "spide_data.db") -> None:
        self._model = model_class
        self._table = _TABLE_MAP.get(model_class.__name__, model_class.__name__.lower())
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._type_hints: dict[str, Any] = {}

    async def start(self) -> None:
        """初始化数据库连接和表结构."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        self._type_hints = get_type_hints(self._model)
        await self._create_table()
        logger.debug("sqlite_opened", path=self._db_path, table=self._table)

    async def stop(self) -> None:
        """关闭数据库连接."""
        if self._db:
            await self._db.close()
            self._db = None

    # -----------------------------------------------------------------------
    # Repository 接口实现
    # -----------------------------------------------------------------------

    async def save(self, item: T) -> int:
        """保存单条记录."""
        self._ensure_db()
        data = self._serialize_dump(item)

        if item.id is not None:  # type: ignore[attr-defined]
            sets = ", ".join(f"{k} = :{k}" for k in data if k != "id")
            await self._db.execute(f"UPDATE {self._table} SET {sets} WHERE id = :id", data)
            await self._db.commit()
            return item.id  # type: ignore[attr-defined]

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data)
        cursor = await self._db.execute(
            f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})", data
        )
        await self._db.commit()
        return cursor.lastrowid

    async def save_many(self, items: list[T]) -> list[int]:
        """批量保存 — 单事务提交."""
        self._ensure_db()
        start = time.monotonic()
        ids: list[int] = []
        for item in items:
            data = self._serialize_dump(item)
            if item.id is not None:  # type: ignore[attr-defined]
                sets = ", ".join(f"{k} = :{k}" for k in data if k != "id")
                await self._db.execute(f"UPDATE {self._table} SET {sets} WHERE id = :id", data)
                ids.append(item.id)  # type: ignore[attr-defined]
            else:
                columns = ", ".join(data.keys())
                placeholders = ", ".join(f":{k}" for k in data)
                cursor = await self._db.execute(
                    f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})", data
                )
                ids.append(cursor.lastrowid)
        await self._db.commit()
        duration_ms = (time.monotonic() - start) * 1000
        logger.debug("save_many_duration", duration_ms=round(duration_ms, 1), record_count=len(items), table=self._table)
        return ids

    async def get(self, id: int) -> T | None:
        """按 ID 获取."""
        self._ensure_db()
        cursor = await self._db.execute(f"SELECT * FROM {self._table} WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return self._row_to_model(row) if row else None

    async def query(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[T]:
        """按条件查询."""
        self._ensure_db()
        sql = f"SELECT * FROM {self._table}"
        params = self._build_where_params(filters)
        if params:
            sql += " WHERE " + params.where_clause

        sql += f" ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
        cursor = await self._db.execute(sql, params.values if params else [])
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def count(self, **filters: Any) -> int:
        """统计记录数."""
        self._ensure_db()
        sql = f"SELECT COUNT(*) FROM {self._table}"
        params = self._build_where_params(filters)
        if params:
            sql += " WHERE " + params.where_clause

        cursor = await self._db.execute(sql, params.values if params else [])
        row = await cursor.fetchone()
        return row[0]

    async def delete(self, id: int) -> bool:
        """按 ID 删除."""
        self._ensure_db()
        cursor = await self._db.execute(f"DELETE FROM {self._table} WHERE id = ?", (id,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def exists(self, **filters: Any) -> bool:
        """检查是否存在."""
        return await self.count(**filters) > 0

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _ensure_db(self) -> None:
        """检查数据库连接状态."""
        if self._db is None:
            raise StorageError("数据库未初始化，请先调用 start()")

    def _serialize_dump(self, item: BaseModel) -> dict[str, Any]:
        """将 Pydantic 模型序列化为 SQLite 兼容的字典."""
        data = item.model_dump(mode="json", exclude={"id"} if item.id is None else set())  # type: ignore[attr-defined]
        serialized: dict[str, Any] = {}
        for k, v in data.items():
            annotation = self._type_hints.get(k, str)
            base = getattr(annotation, "__origin__", annotation)
            if base in _COLLECTION_TYPES and not isinstance(v, str):
                serialized[k] = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, datetime):
                serialized[k] = v.isoformat()
            elif hasattr(v, "value"):  # Enum
                serialized[k] = v.value
            else:
                serialized[k] = v
        return serialized

    def _row_to_model(self, row: aiosqlite.Row) -> T:  # type: ignore[type-var]
        """将数据库行转换为 Pydantic 模型."""
        data = dict(row)
        for field_name in self._model.model_fields:
            if field_name not in data or data[field_name] is None:
                continue
            annotation = self._type_hints.get(field_name, str)
            base = getattr(annotation, "__origin__", annotation)
            if base in _COLLECTION_TYPES and isinstance(data[field_name], str):
                import contextlib

                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    data[field_name] = json.loads(data[field_name])
        return self._model(**data)  # type: ignore[return-value]

    async def _create_table(self) -> None:
        """根据 Pydantic 模型自动创建表."""
        columns: list[str] = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for field_name in self._model.model_fields:
            if field_name == "id":
                continue
            col_type = self._pydantic_to_sqlite_type(field_name)
            columns.append(f"{field_name} {col_type}")

        sql = f"CREATE TABLE IF NOT EXISTS {self._table} ({', '.join(columns)})"
        await self._db.execute(sql)
        await self._db.commit()

    def _pydantic_to_sqlite_type(self, field_name: str) -> str:
        """将 Pydantic 字段类型映射到 SQLite 类型."""
        annotation = self._type_hints.get(field_name, str)

        # 提取 Optional 内部类型
        args = getattr(annotation, "__args__", ())
        if args and type(None) in args:
            annotation = next(a for a in args if a is not type(None))

        type_map: dict[type, str] = {
            int: "INTEGER",
            float: "REAL",
            bool: "INTEGER",
            datetime: "TEXT",
            str: "TEXT",
        }

        base = getattr(annotation, "__origin__", annotation)
        if base in _COLLECTION_TYPES:
            return "TEXT"

        return type_map.get(annotation, "TEXT")

    @staticmethod
    def _build_where_params(filters: dict[str, Any]) -> _WhereClause | None:
        """构建 WHERE 子句 — 统一 query() 和 count() 的过滤逻辑."""
        if not filters:
            return None
        conditions: list[str] = []
        values: list[Any] = []
        for key, value in filters.items():
            if isinstance(value, list):
                placeholders = ", ".join("?" for _ in value)
                conditions.append(f"{key} IN ({placeholders})")
                values.extend(value)
            else:
                conditions.append(f"{key} = ?")
                values.append(value)
        return _WhereClause(" AND ".join(conditions), values)


class _WhereClause:
    """WHERE 子句 + 参数值."""

    __slots__ = ("values", "where_clause")

    def __init__(self, where_clause: str, values: list[Any]) -> None:
        self.where_clause = where_clause
        self.values = values

    def __bool__(self) -> bool:
        return bool(self.where_clause)
