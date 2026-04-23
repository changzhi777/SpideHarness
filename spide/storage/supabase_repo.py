# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Supabase (PostgreSQL) 持久化仓库 — supabase-py 同步/异步双模式.

用法:
    from spide.storage.supabase_repo import SupabaseRepository
    from spide.storage.models import HotTopic

    # CLI / 异步场景
    repo = SupabaseRepository(HotTopic, url="...", key="...")
    await repo.start()
    ids = await repo.save_many(topics)

    # Dashboard / 同步场景（FastAPI 同步路由）
    repo = SupabaseRepository(HotTopic, url="...", key="...", sync=True)
    repo.start_sync()
    ids = repo.save_many_sync(topics)
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel

from spide.exceptions import StorageError
from spide.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# 表名映射 — 与 SqliteRepository 保持一致
_TABLE_MAP: dict[str, str] = {
    "HotTopic": "hot_topics",
    "NewsArticle": "news_articles",
    "CrawlTask": "crawl_tasks",
    "DeepContent": "deep_contents",
    "DeepComment": "deep_comments",
    "DeepCreator": "deep_creators",
    "CrawlSession": "crawl_sessions",
}

# 每个模型对应的去重字段（用于 upsert on_conflict）
_DEDUP_FIELDS: dict[str, list[str]] = {
    "HotTopic": ["title", "source"],
    "NewsArticle": ["url", "source"],
    "DeepContent": ["platform", "content_id"],
    "DeepComment": ["platform", "comment_id"],
    "DeepCreator": ["platform", "user_id"],
}

# 批量 upsert 的单批大小（Supabase PostgREST 限制）
_BATCH_SIZE = 100


class SupabaseRepository:
    """Supabase (PostgreSQL) 仓库 — 支持异步和同步两种模式."""

    def __init__(
        self,
        model_class: type[T],
        *,
        url: str = "",
        key: str = "",
        sync: bool = False,
    ) -> None:
        self._model = model_class
        self._table = _TABLE_MAP.get(model_class.__name__, model_class.__name__.lower())
        self._url = url or os.environ.get("SUPABASE_URL", "")
        self._key = key or os.environ.get("SUPABASE_SERVICE_KEY", "")
        self._dedup = _DEDUP_FIELDS.get(model_class.__name__)
        self._sync = sync
        self._client: Any = None

    # ── 异步模式 ───────────────────────────────────────────────────

    async def start(self) -> None:
        """初始化 Supabase 异步客户端."""
        if not self._url or not self._key:
            raise StorageError("Supabase URL 或 Key 未配置")
        from supabase import create_async_client, AsyncClient

        self._client: AsyncClient = await create_async_client(self._url, self._key)
        logger.debug("supabase_opened", table=self._table, mode="async")

    async def stop(self) -> None:
        """关闭连接（AsyncClient 无显式 close，置空即可）."""
        self._client = None

    async def save(self, item: T) -> int:
        """保存单条记录."""
        self._ensure_client()
        data = self._serialize(item)

        if item.id is not None:  # type: ignore[attr-defined]
            resp = (
                self._client.table(self._table)
                .update(data)
                .eq("id", item.id)  # type: ignore[attr-defined]
                .execute()
            )
            return item.id  # type: ignore[attr-defined]

        data.pop("id", None)
        resp = self._client.table(self._table).insert(data).execute()
        return resp.data[0]["id"]

    async def save_many(
        self,
        items: list[T],
        *,
        dedup_fields: list[str] | None = None,
    ) -> list[int]:
        """批量保存 — 自动按模型类型 upsert 去重.

        Args:
            items: 待保存的记录列表
            dedup_fields: 去重字段（可选，默认使用模型级 _DEDUP_FIELDS）
        """
        self._ensure_client()
        start_t = time.monotonic()
        ids: list[int] = []
        dedup = dedup_fields or self._dedup
        on_conflict = ",".join(dedup) if dedup else None

        records = [self._serialize(item) for item in items]
        for r in records:
            if r.get("id") is None:
                r.pop("id", None)

        # 分批处理
        for i in range(0, len(records), _BATCH_SIZE):
            batch = records[i : i + _BATCH_SIZE]

            if on_conflict:
                resp = (
                    self._client.table(self._table)
                    .upsert(batch, on_conflict=on_conflict)
                    .execute()
                )
            else:
                resp = self._client.table(self._table).insert(batch).execute()

            for row in resp.data:
                ids.append(row["id"])

        duration_ms = (time.monotonic() - start_t) * 1000
        logger.debug(
            "save_many_duration",
            duration_ms=round(duration_ms, 1),
            record_count=len(items),
            table=self._table,
            on_conflict=on_conflict,
        )
        return ids

    async def get(self, id: int) -> T | None:
        """按 ID 获取."""
        self._ensure_client()
        resp = (
            self._client.table(self._table)
            .select("*")
            .eq("id", id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return self._row_to_model(resp.data[0])

    async def query(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[T]:
        """按条件查询."""
        self._ensure_client()
        q = self._client.table(self._table).select("*")
        q = self._apply_filters(q, filters)
        resp = q.order("id", desc=True).range(offset, offset + limit - 1).execute()
        return [self._row_to_model(row) for row in resp.data]

    async def count(self, **filters: Any) -> int:
        """统计记录数."""
        self._ensure_client()
        q = self._client.table(self._table).select("*", count="exact")
        q = self._apply_filters(q, filters)
        resp = q.execute()
        return resp.count or 0

    async def delete(self, id: int) -> bool:
        """按 ID 删除."""
        self._ensure_client()
        resp = self._client.table(self._table).delete().eq("id", id).execute()
        return len(resp.data) > 0

    async def exists(self, **filters: Any) -> bool:
        """检查是否存在."""
        return await self.count(**filters) > 0

    # ── 同步模式（用于 FastAPI 同步路由） ─────────────────────────────

    def start_sync(self) -> None:
        """初始化 Supabase 同步客户端."""
        if not self._url or not self._key:
            raise StorageError("Supabase URL 或 Key 未配置")
        from supabase import create_client, Client

        self._client: Client = create_client(self._url, self._key)
        logger.debug("supabase_opened", table=self._table, mode="sync")

    def query_sync(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[T]:
        """同步按条件查询."""
        self._ensure_client()
        q = self._client.table(self._table).select("*")
        q = self._apply_filters(q, filters)
        resp = q.order("id", desc=True).range(offset, offset + limit - 1).execute()
        return [self._row_to_model(row) for row in resp.data]

    def count_sync(self, **filters: Any) -> int:
        """同步统计."""
        self._ensure_client()
        q = self._client.table(self._table).select("*", count="exact")
        q = self._apply_filters(q, filters)
        resp = q.execute()
        return resp.count or 0

    # ── 内部方法 ────────────────────────────────────────────────────

    def _ensure_client(self) -> None:
        if self._client is None:
            raise StorageError("Supabase 未初始化，请先调用 start() 或 start_sync()")

    def _serialize(self, item: BaseModel) -> dict[str, Any]:
        """Pydantic 模型 → Supabase 兼容 dict."""
        data = item.model_dump(mode="json", exclude={"id"} if item.id is None else set())  # type: ignore[attr-defined]
        result: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(v, Enum):
                result[k] = v.value
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    def _row_to_model(self, row: dict[str, Any]) -> T:  # type: ignore[type-var]
        """Supabase row → Pydantic model."""
        # 处理 datetime 字符串 → datetime 对象
        from spide.storage.models import HotTopic, NewsArticle, CrawlTask, CrawlSession

        _datetime_models = {HotTopic, NewsArticle, CrawlTask, CrawlSession}
        if self._model in _datetime_models:
            for field_name, field_info in self._model.model_fields.items():
                if field_name not in row or row[field_name] is None:
                    continue
                ann = str(field_info.annotation)
                if "datetime" in ann and isinstance(row[field_name], str):
                    from datetime import datetime as _dt

                    with contextlib_suppress(ValueError):
                        row[field_name] = _dt.fromisoformat(row[field_name])

        return self._model(**row)  # type: ignore[return-value]

    @staticmethod
    def _apply_filters(query: Any, filters: dict[str, Any]) -> Any:
        """将 filters dict 应用到 Supabase 查询构建器."""
        for key, value in filters.items():
            if isinstance(value, list):
                query = query.in_(key, value)
            else:
                query = query.eq(key, value)
        return query


def contextlib_suppress(*exceptions: type[Exception]):
    """兼容 contextlib.suppress."""
    import contextlib

    return contextlib.suppress(*exceptions)
