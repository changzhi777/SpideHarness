# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""存储层 — 工厂函数和公共导出.

用法:
    from spide.storage import create_sqlite_repo, create_redis_cache
    from spide.storage.models import HotTopic

    repo = create_sqlite_repo(HotTopic)
    cache = create_redis_cache()
"""

from spide.storage.models import (
    ArticleCategory,
    CrawlSession,
    CrawlTask,
    HotTopic,
    NewsArticle,
    TaskStatus,
    TopicSource,
)
from spide.storage.redis_cache import RedisCache
from spide.storage.repository import CacheBackend, Repository
from spide.storage.sqlite_repo import SqliteRepository

__all__ = [
    "ArticleCategory",
    "CacheBackend",
    "CrawlSession",
    "CrawlTask",
    "HotTopic",
    "NewsArticle",
    "RedisCache",
    "Repository",
    "SqliteRepository",
    "TaskStatus",
    "TopicSource",
    "create_redis_cache",
    "create_sqlite_repo",
]


def create_sqlite_repo(model_class: type, *, db_path: str = "spide_data.db") -> SqliteRepository:
    """创建 SQLite 仓库实例."""
    return SqliteRepository(model_class, db_path=db_path)


def create_redis_cache(*, url: str = "redis://localhost:6379/0", prefix: str = "spide:") -> RedisCache:
    """创建 Redis 缓存实例."""
    return RedisCache(url=url, prefix=prefix)
