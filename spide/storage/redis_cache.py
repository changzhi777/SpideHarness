# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Redis 缓存与去重 — redis 异步驱动.

用法:
    from spide.storage.redis_cache import RedisCache

    cache = RedisCache(url="redis://localhost:6379/0", prefix="spide:")
    await cache.start()
    await cache.set("key", "value", ttl=300)
    await cache.add_to_set("urls:crawled", "https://example.com/1")
    is_dup = await cache.is_in_set("urls:crawled", "https://example.com/1")
    await cache.stop()
"""

from __future__ import annotations

import redis.asyncio as aioredis

from spide.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis 异步缓存后端."""

    def __init__(
        self,
        *,
        url: str = "redis://localhost:6379/0",
        prefix: str = "spide:",
    ) -> None:
        self._url = url
        self._prefix = prefix
        self._client: aioredis.Redis | None = None

    async def start(self) -> None:
        """初始化 Redis 连接."""
        self._client = aioredis.from_url(self._url, decode_responses=True)
        await self._client.ping()
        logger.debug("redis_connected", url=self._url)

    async def stop(self) -> None:
        """关闭 Redis 连接."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _key(self, key: str) -> str:
        """添加前缀."""
        return f"{self._prefix}{key}"

    # -----------------------------------------------------------------------
    # CacheBackend 接口实现
    # -----------------------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """获取缓存值."""
        return await self._client.get(self._key(key))

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """设置缓存值."""
        k = self._key(key)
        if ttl:
            await self._client.setex(k, ttl, value)
        else:
            await self._client.set(k, value)

    async def delete(self, key: str) -> bool:
        """删除缓存."""
        return await self._client.delete(self._key(key)) > 0

    async def exists(self, key: str) -> bool:
        """检查 key 是否存在."""
        return await self._client.exists(self._key(key)) > 0

    async def add_to_set(self, key: str, *members: str) -> int:
        """添加到集合."""
        if not members:
            return 0
        return await self._client.sadd(self._key(key), *members)  # type: ignore[misc]

    async def is_in_set(self, key: str, member: str) -> bool:
        """检查成员是否在集合中."""
        return await self._client.sismember(self._key(key), member)  # type: ignore[misc]

    # -----------------------------------------------------------------------
    # 爬虫专用方法
    # -----------------------------------------------------------------------

    async def is_url_crawled(self, url: str) -> bool:
        """检查 URL 是否已爬取（去重）."""
        return await self.is_in_set("urls:crawled", url)

    async def mark_url_crawled(self, url: str) -> None:
        """标记 URL 为已爬取."""
        await self.add_to_set("urls:crawled", url)

    async def get_task_state(self, task_id: str) -> dict | None:
        """获取任务状态."""
        data = await self.get(f"task:{task_id}")
        if data is None:
            return None
        import json
        return json.loads(data)

    async def set_task_state(self, task_id: str, state: dict, ttl: int = 3600) -> None:
        """设置任务状态."""
        import json
        await self.set(f"task:{task_id}", json.dumps(state), ttl=ttl)
