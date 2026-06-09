# Spider 引擎模块

> [根目录](../../CLAUDE.md) > [spide](../) > **spider**

## 职责

热搜数据采集与深度采集引擎，包含数据抓取、清洗去重、UAPI 集成、MediaCrawler 适配、调度策略、增量检测、深度追踪和稳定性保障（限流+熔断+断点恢复）。

## 文件清单（11 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 AsyncFetcher, UAPIClient, parse_hot_items, deduplicate_items |
| `fetcher.py` | AsyncFetcher — aiohttp + BeautifulSoup 异步抓取器 |
| `pipeline.py` | 数据清洗管道：clean_topics, deduplicate_items, parse_hot_items |
| `uapi_client.py` | UAPIClient — UAPI 热搜 REST（令牌桶限流 + 熔断保护） |
| `media_crawler_adapter.py` | MediaCrawler 深度采集适配器，7 平台统一接口 |
| `batch_scheduler.py` | BatchCrawlScheduler — 多平台并行调度（熔断 + 断点恢复） |
| `task_scheduler.py` | TaskScheduler — 定时采集调度器（interval + cron） |
| `rate_limiter.py` | RateLimiter(令牌桶) + CircuitBreaker(熔断) + CheckpointManager(断点) |
| `incremental.py` | IncrementalDetector — 增量检测 + 状态标记 + 快照 |
| `deep_tracker.py` | DeepTopicTracker — 搜索 + LLM 摘要 + 情感分析 |
| `timed_search.py` | TimedSearchService — 定时搜索热搜 + 关联新闻 + 持久化 |

## 核心接口

### UAPIClient（限流 + 熔断）
```python
from spide.spider.uapi_client import UAPIClient
client = UAPIClient(settings.uapi)
await client.start()
topics = await client.fetch_hotboard("weibo")
all_data = await client.fetch_all()  # 并发采集所有已配置源
await client.stop()
```

特性：7 平台映射（weibo/baidu/douyin/zhihu/bilibili/kuaishou/tieba），自动重试（指数退避），失败熔断。

### AsyncFetcher
```python
from spide.spider.fetcher import AsyncFetcher
fetcher = AsyncFetcher(timeout=30, max_retries=3)
html = await fetcher.fetch("https://...")
text, links = await fetcher.fetch_text_with_links("https://...")
await fetcher.close()
```

### Pipeline（数据清洗）
```python
from spide.spider.pipeline import clean_topics, deduplicate_items, parse_hot_items

cleaned = clean_topics(raw_topics)        # 清洗 + 过滤 + 去重
unique = deduplicate_items(all_topics)    # 仅去重
parsed = parse_hot_items(items, source="weibo")  # 原始 dict → HotTopic
```

### IncrementalDetector（增量检测）
```python
detector = IncrementalDetector()
changes = detector.detect_changes(current_topics, previous_topics, TopicSource.WEIBO)
snapshot = detector.build_snapshot(topics, TopicSource.WEIBO, changes)
report = detector.generate_diff_report(changes)
```

状态标记：NEW / RISING / FALLING / STABLE / DROPPED

### DeepTopicTracker（深度追踪）
```python
tracker = DeepTopicTracker(llm=llm_client, max_concurrent=3)
tracks = await tracker.track_topics(topics, top_n=10)
# 返回 TopicDeepTrack 列表（含 summary, sentiment, keywords, related_articles）
```

### TimedSearchService（定时搜索）
```python
svc = TimedSearchService(db_path="spide_data.db")
await svc.start()
result = await svc.run_once(schedule_time="09:00", sources=["weibo", "baidu"], top_n=5)
batches = await svc.query_batches(limit=10)
records = await svc.query_records(limit=20, schedule_time="09:00")
await svc.stop()
```

### RateLimiter / CircuitBreaker / CheckpointManager
```python
limiter = RateLimiter(max_rpm=30, max_concurrent=5)
async with limiter:
    await fetch(url)

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0, name="uapi")
result = await breaker.call(api_fetch, source="weibo")

ckpt = CheckpointManager(db_path="spide_data.db")
await ckpt.start()
await ckpt.save_checkpoint("batch_id", state)
```

## 依赖关系

- `uapi_client.py` → aiohttp, `spide.spider.rate_limiter`, `spide.spider.pipeline`, `spide.config.UAPIConfig`
- `media_crawler_adapter.py` → MediaCrawler (Playwright)
- `batch_scheduler.py` → `media_crawler_adapter.py`, `spide.spider.rate_limiter`
- `deep_tracker.py` → `spide.llm`, `spide.analysis.summarizer`, `spide.mcp.search_provider`
- `timed_search.py` → `spide.storage.models` (TimedSearchBatch, TimedSearchRecord), `spide.storage.sqlite_repo`
- `incremental.py` → `spide.storage.models` (HotTopicChange, CrawlSnapshot, TopicStatus)
- `task_scheduler.py` → asyncio 定时（支持 interval + cron_times）

## 测试

- `tests/unit/test_uapi_client.py` — UAPI 热搜 + 限流
- `tests/unit/test_fetcher.py` — HTTP 抓取
- `tests/unit/test_pipeline.py` — clean_topics/deduplicate/parse
- `tests/unit/test_deep_crawl.py` — MediaCrawlerAdapter
- `tests/unit/test_batch_scheduler.py` — BatchCrawlScheduler
- `tests/unit/test_task_scheduler.py` — TaskScheduler
- `tests/unit/test_rate_limiter.py` — RateLimiter + CircuitBreaker + CheckpointManager
- `tests/unit/test_incremental.py` — IncrementalDetector
- `tests/unit/test_deep_tracker.py` — DeepTopicTracker
- `tests/unit/test_timed_search.py` — TimedSearchService
- `tests/integration/test_uapi_real.py` — 真实 UAPI 调用（@integration）
- `tests/integration/test_real_crawl.py` — 真实采集（@integration）
