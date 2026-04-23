# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""存储层 — 工厂函数和公共导出.

用法:
    from spide.storage import create_repo
    from spide.storage.models import HotTopic

    repo = create_repo(HotTopic, storage_config=settings.storage)
    await repo.start()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from spide.storage.models import (
    ArticleCategory,
    CrawlSession,
    CrawlTask,
    DeepComment,
    DeepContent,
    DeepCreator,
    HotTopic,
    NewsArticle,
    TaskStatus,
    TopicSource,
)
from spide.storage.redis_cache import RedisCache
from spide.storage.repository import CacheBackend, Repository
from spide.storage.sqlite_repo import SqliteRepository
from spide.storage.supabase_repo import SupabaseRepository

if TYPE_CHECKING:
    from spide.config import StorageConfig

__all__ = [
    "ArticleCategory",
    "CacheBackend",
    "CrawlSession",
    "CrawlTask",
    "DeepComment",
    "DeepContent",
    "DeepCreator",
    "HotTopic",
    "NewsArticle",
    "RedisCache",
    "Repository",
    "SqliteRepository",
    "SupabaseRepository",
    "TaskStatus",
    "TopicSource",
    "create_redis_cache",
    "create_repo",
    "create_sqlite_repo",
]


def create_repo(
    model_class: type,
    *,
    storage_config: StorageConfig | None = None,
    db_path: str = "spide_data.db",
    sync: bool = False,
) -> Repository:
    """统一仓库工厂 — 优先 Supabase，降级到 SQLite.

    Args:
        model_class: Pydantic 数据模型类
        storage_config: 存储配置（提供时自动判断 Supabase/SQLite）
        db_path: SQLite 数据库路径（降级时使用）
        sync: 是否使用同步模式（Dashboard 用）
    """
    if storage_config and storage_config.supabase_url:
        return SupabaseRepository(
            model_class,
            url=storage_config.supabase_url,
            key=storage_config.supabase_service_key,
            sync=sync,
        )
    return SqliteRepository(model_class, db_path=db_path or (storage_config.sqlite_path if storage_config else "spide_data.db"))


def create_sqlite_repo(model_class: type, *, db_path: str = "spide_data.db") -> SqliteRepository:
    """创建 SQLite 仓库实例."""
    return SqliteRepository(model_class, db_path=db_path)


def create_redis_cache(*, url: str = "redis://localhost:6379/0", prefix: str = "spide:") -> RedisCache:
    """创建 Redis 缓存实例."""
    return RedisCache(url=url, prefix=prefix)
