# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""定时搜索服务 — 每日定时采集热搜 + 搜索关联新闻 + 持久化.

用法:
    from spide.spider.timed_search import TimedSearchService

    svc = TimedSearchService(db_path="spide_data.db")
    await svc.start()
    result = await svc.run_once(schedule_time="09:00", sources=["weibo", "baidu"])
    await svc.stop()
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from spide.logging import get_logger
from spide.storage.models import (
    TimedSearchBatch,
    TimedSearchRecord,
    TopicSource,
)

logger = get_logger(__name__)

# 默认采集源
_DEFAULT_SOURCES = ["weibo", "baidu", "zhihu", "douyin", "bilibili"]
# 每个平台取 Top N 热搜做关联搜索
_DEFAULT_TOP_N = 5
# 每个热搜搜索关联新闻数量
_DEFAULT_SEARCH_LIMIT = 5


class TimedSearchService:
    """定时搜索服务 — 采集热搜 + 搜索关联新闻 + 保存记录."""

    def __init__(self, *, db_path: str = "spide_data.db") -> None:
        self._db_path = db_path
        self._batch_repo: Any = None
        self._record_repo: Any = None

    async def start(self) -> None:
        from spide.storage.sqlite_repo import SqliteRepository

        self._batch_repo = SqliteRepository(TimedSearchBatch, db_path=self._db_path)
        self._record_repo = SqliteRepository(TimedSearchRecord, db_path=self._db_path)
        await self._batch_repo.start()
        await self._record_repo.start()

    async def stop(self) -> None:
        if self._batch_repo:
            await self._batch_repo.stop()
        if self._record_repo:
            await self._record_repo.stop()

    async def run_once(
        self,
        *,
        schedule_time: str = "09:00",
        sources: list[str] | None = None,
        top_n: int = _DEFAULT_TOP_N,
        search_limit: int = _DEFAULT_SEARCH_LIMIT,
    ) -> dict[str, Any]:
        """执行一次定时搜索.

        Args:
            schedule_time: 调度时间标识 ("09:00" / "18:00")
            sources: 采集的平台列表
            top_n: 每个平台取 Top N 热搜
            search_limit: 每条热搜搜索关联新闻数量

        Returns:
            执行结果摘要
        """
        sources = sources or _DEFAULT_SOURCES
        now = datetime.now()
        batch_key = f"{now.strftime('%Y-%m-%d')}_{schedule_time.replace(':', '')}"

        batch = TimedSearchBatch(
            batch_key=batch_key,
            schedule_time=schedule_time,
            platforms=sources,
            status="running",
            started_at=now,
        )
        batch_id = await self._batch_repo.save(batch)

        total_topics = 0
        search_count = 0
        records: list[TimedSearchRecord] = []

        try:
            # 步骤 1: 采集各平台热搜
            topics = await self._fetch_all_topics(sources)
            total_topics = len(topics)

            # 步骤 2: 取 Top N 做关联搜索
            top_topics = topics[:top_n * len(sources)]

            # 步骤 3: 对每条热搜搜索关联新闻
            sem = asyncio.Semaphore(3)

            async def search_one(topic: dict[str, Any]) -> list[TimedSearchRecord]:
                async with sem:
                    results = await self._search_related(topic["title"], search_limit)
                    return [
                        TimedSearchRecord(
                            batch_id=batch_id,
                            topic_title=topic["title"],
                            topic_source=topic["source"],
                            topic_hot_value=topic.get("hot_value"),
                            topic_rank=topic.get("rank"),
                            search_title=r.title,
                            search_url=r.url,
                            search_snippet=r.description,
                            schedule_time=schedule_time,
                        )
                        for r in results
                    ]

            all_results = await asyncio.gather(
                *[search_one(t) for t in top_topics],
                return_exceptions=True,
            )

            for result in all_results:
                if isinstance(result, Exception):
                    logger.warning("search_one_failed", error=str(result))
                else:
                    records.extend(result)

            search_count = len(records)

            # 步骤 4: 批量保存搜索记录
            if records:
                await self._record_repo.save_many(records)

            # 更新批次状态
            batch.id = batch_id
            batch.total_topics = total_topics
            batch.search_count = search_count
            batch.status = "completed"
            batch.completed_at = datetime.now()
            await self._batch_repo.save(batch)

            logger.info(
                "timed_search_completed",
                batch_key=batch_key,
                total_topics=total_topics,
                search_count=search_count,
            )

        except Exception as e:
            logger.error("timed_search_failed", batch_key=batch_key, error=str(e))
            batch.id = batch_id
            batch.total_topics = total_topics
            batch.search_count = search_count
            batch.status = "failed"
            batch.error_message = str(e)
            batch.completed_at = datetime.now()
            await self._batch_repo.save(batch)

        return {
            "batch_id": batch_id,
            "batch_key": batch_key,
            "schedule_time": schedule_time,
            "total_topics": total_topics,
            "search_count": search_count,
            "status": batch.status,
        }

    async def query_records(
        self,
        *,
        schedule_time: str | None = None,
        batch_key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """查询定时搜索记录."""
        filters: dict[str, Any] = {}
        if schedule_time:
            filters["schedule_time"] = schedule_time
        if batch_key:
            filters["batch_key"] = batch_key

        records = await self._record_repo.query(limit=limit, **filters)
        return [r.model_dump(mode="json") for r in records]

    async def query_batches(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """查询搜索批次列表."""
        batches = await self._batch_repo.query(limit=limit)
        return [b.model_dump(mode="json") for b in batches]

    async def _fetch_all_topics(self, sources: list[str]) -> list[dict[str, Any]]:
        """采集各平台热搜."""
        all_topics: list[dict[str, Any]] = []

        try:
            from spide.config import load_settings
            from spide.spider.uapi_client import UAPIClient

            settings = load_settings()
            client = UAPIClient(settings.uapi)
            await client.start()
            try:
                for source in sources:
                    try:
                        topics = await client.fetch_hotboard(source)
                        for t in topics:
                            all_topics.append({
                                "title": t.title,
                                "source": t.source.value,
                                "hot_value": t.hot_value,
                                "rank": t.rank,
                                "url": t.url,
                            })
                    except Exception as e:
                        logger.warning("fetch_source_failed", source=source, error=str(e))
            finally:
                await client.stop()
        except Exception as e:
            logger.warning("uapi_unavailable", error=str(e))

        # 按热度降序排列
        all_topics.sort(key=lambda x: x.get("hot_value") or 0, reverse=True)
        return all_topics

    @staticmethod
    async def _search_related(query: str, limit: int) -> list[Any]:
        """搜索关联新闻."""
        try:
            from spide.mcp.search_provider import WebSearchProvider

            provider = WebSearchProvider()
            return await provider.search(query, limit=limit)
        except Exception as e:
            logger.debug("search_related_failed", query=query[:30], error=str(e))
            return []
