# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Layer 1 — 真实热搜采集集成测试.

调用真实 UAPI 热搜 API，验证 5 平台数据采集和数据结构。
标记 @pytest.mark.integration，无 API Key 时自动跳过。
"""

import asyncio

import pytest

from spide.config import load_settings
from spide.storage.models import HotTopic
from spide.storage.sqlite_repo import SqliteRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_settings():
    settings = load_settings()
    if not settings.uapi.api_key:
        pytest.skip("UAPI API Key 未配置")
    return settings


@pytest.fixture
async def real_uapi(real_settings):
    from spide.spider.uapi_client import UAPIClient

    client = UAPIClient(real_settings.uapi)
    await client.start()
    yield client
    await client.stop()


# ---------------------------------------------------------------------------
# 单平台采集
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRealHotTopicFetch:
    """各平台真实热搜采集."""

    async def test_fetch_weibo_hotboard(self, real_uapi):
        topics = await real_uapi.fetch_hotboard("weibo")
        assert len(topics) > 0, "微博热搜应返回非空列表"
        assert topics[0].title, "第一条热搜应有标题"

    async def test_fetch_baidu_hotboard(self, real_uapi):
        topics = await real_uapi.fetch_hotboard("baidu")
        assert len(topics) > 0, "百度热搜应返回非空列表"

    async def test_fetch_douyin_hotboard(self, real_uapi):
        try:
            topics = await real_uapi.fetch_hotboard("douyin")
            assert isinstance(topics, list), "抖音应返回列表"
        except Exception:
            pytest.skip("抖音 API 暂时不可用")

    async def test_fetch_zhihu_hotboard(self, real_uapi):
        topics = await real_uapi.fetch_hotboard("zhihu")
        assert len(topics) > 0, "知乎热搜应返回非空列表"

    async def test_fetch_bilibili_hotboard(self, real_uapi):
        topics = await real_uapi.fetch_hotboard("bilibili")
        assert len(topics) > 0, "B站热搜应返回非空列表"


# ---------------------------------------------------------------------------
# 数据结构验证
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHotTopicStructure:
    """热搜数据结构完整性."""

    async def test_hot_topic_data_structure(self, real_uapi):
        topics = await real_uapi.fetch_hotboard("weibo")
        assert len(topics) > 0

        for topic in topics[:5]:
            assert isinstance(topic.title, str), f"title 应为 str: {type(topic.title)}"
            assert len(topic.title) > 0, "title 不应为空"
            assert topic.source is not None, "source 不应为 None"

    async def test_crawl_all_sources_concurrent(self, real_uapi):
        platforms = ["weibo", "baidu", "douyin", "zhihu", "bilibili"]
        tasks = [real_uapi.fetch_hotboard(p) for p in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue  # 个别平台失败不影响整体
            assert isinstance(result, list), f"{platforms[i]} 应返回列表"

    async def test_fetch_all_method(self, real_uapi):
        all_topics = await real_uapi.fetch_all()
        assert isinstance(all_topics, dict), "fetch_all 应返回 dict"
        assert len(all_topics) > 0, "应至少返回一个平台的数据"


# ---------------------------------------------------------------------------
# 持久化验证
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCrawlPersist:
    """采集 → SQLite 持久化."""

    async def test_crawl_and_save_to_sqlite(self, real_uapi, tmp_db):
        topics = await real_uapi.fetch_hotboard("weibo")
        assert len(topics) > 0

        repo = SqliteRepository(HotTopic, db_path=str(tmp_db))
        await repo.start()
        try:
            ids = await repo.save_many(topics)
            assert len(ids) > 0, "save_many 应返回非空 ID 列表"

            count = await repo.count()
            assert count > 0, "保存后 count 应 > 0"

            stored = await repo.query(limit=5)
            assert len(stored) > 0
            assert stored[0].title, "回读数据应有标题"
        finally:
            await repo.stop()


# ---------------------------------------------------------------------------
# 异常处理
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCrawlErrors:
    """采集错误路径."""

    async def test_crawl_invalid_platform(self, real_uapi):
        from spide.exceptions import SpiderError

        with pytest.raises(SpiderError):
            await real_uapi.fetch_hotboard("nonexistent_platform_xyz")
