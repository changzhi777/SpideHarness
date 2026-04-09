# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""统一存储接口 — Protocol 定义.

用法:
    from spide.storage.repository import Repository
    from spide.storage.models import HotTopic

    repo: Repository[HotTopic] = create_repository(HotTopic)
    await repo.save(topic)
    topics = await repo.query(source="weibo")
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Repository(Protocol):
    """通用存储仓库接口 (Protocol).

    所有存储后端必须实现此接口。
    """

    async def save(self, item: Any) -> int:
        """保存单条记录，返回记录 ID."""
        ...

    async def save_many(self, items: list[Any]) -> list[int]:
        """批量保存，返回记录 ID 列表."""
        ...

    async def get(self, id: int) -> Any | None:
        """按 ID 获取单条记录."""
        ...

    async def query(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[Any]:
        """按条件查询记录."""
        ...

    async def count(self, **filters: Any) -> int:
        """统计符合条件的记录数."""
        ...

    async def delete(self, id: int) -> bool:
        """按 ID 删除记录，返回是否成功."""
        ...

    async def exists(self, **filters: Any) -> bool:
        """检查是否存在符合条件的记录."""
        ...


@runtime_checkable
class CacheBackend(Protocol):
    """缓存后端接口."""

    async def get(self, key: str) -> str | None:
        """获取缓存值."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """设置缓存值，ttl 为秒数."""
        ...

    async def delete(self, key: str) -> bool:
        """删除缓存."""
        ...

    async def exists(self, key: str) -> bool:
        """检查 key 是否存在."""
        ...

    async def add_to_set(self, key: str, *members: str) -> int:
        """添加到集合，返回新增成员数."""
        ...

    async def is_in_set(self, key: str, member: str) -> bool:
        """检查成员是否在集合中."""
        ...
