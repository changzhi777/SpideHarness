# Spider 引擎模块

> [根目录](../../CLAUDE.md) → `spide/spider/`

## 职责

热搜数据采集与深度采集引擎，包含数据抓取、清洗去重、UAPI 集成、MediaCrawler 适配、调度策略、增量检测、深度追踪和稳定性保障。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 10 | 导出 AsyncFetcher, UAPIClient, parse_hot_items, deduplicate_items |
| `fetcher.py` | 97 | AsyncFetcher — aiohttp + BeautifulSoup 异步抓取器 |
| `pipeline.py` | 218 | 数据清洗管道：clean_topics, deduplicate_items, parse_hot_items |
| `uapi_client.py` | 251 | UAPIClient — UAPI 热搜 REST（令牌桶限流 + 熔断保护） |
| `media_crawler_adapter.py` | 590 | MediaCrawler 深度采集适配器，7 平台统一接口 |
| `batch_scheduler.py` | 240 | BatchCrawlScheduler — 多平台并行调度（熔断 + 断点恢复） |
| `task_scheduler.py` | 233 | TaskScheduler — 定时采集调度器 |
| `rate_limiter.py` | 317 | RateLimiter(令牌桶) + CircuitBreaker(熔断) + CheckpointManager(断点) |
| `incremental.py` | 201 | IncrementalDetector — 增量检测 + 状态标记 + 快照 |
| `deep_tracker.py` | 173 | DeepTopicTracker — 搜索 + LLM 摘要 + 情感分析 |
| `timed_search.py` | 245 | TimedSearchService — 定时搜索热搜 + 关联新闻 + 持久化 |

## 核心接口

### UAPIClient（限流 + 熔断）
```python
client = UAPIClient(settings.uapi)
await client.start()
topics = await client.fetch_hotboard("weibo")
all_data = await client.fetch_all()
await client.stop()
```

### IncrementalDetector（增量检测）
```python
detector = IncrementalDetector()
changes = detector.detect_changes(current_topics, previous_topics, TopicSource.WEIBO)
snapshot = detector.build_snapshot(topics, TopicSource.WEIBO, changes)
report = detector.generate_diff_report(changes)
```

### DeepTopicTracker（深度追踪）
```python
tracker = DeepTopicTracker(llm=llm_client, max_concurrent=3)
tracks = await tracker.track_topics(topics, top_n=10)
```

### TimedSearchService（定时搜索）
```python
svc = TimedSearchService(db_path="spide_data.db")
await svc.start()
result = await svc.run_once(schedule_time="09:00", sources=["weibo", "baidu"])
await svc.stop()
```

### RateLimiter / CircuitBreaker / CheckpointManager
```python
limiter = RateLimiter(max_rpm=30, max_concurrent=5)
async with limiter:
    await fetch(url)

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
result = await breaker.call(api_fetch, source="weibo")

ckpt = CheckpointManager(db_path="spide_data.db")
await ckpt.start()
await ckpt.save_checkpoint("batch_id", state)
```

## 依赖关系

- `uapi_client.py` → aiohttp, `spide.spider.rate_limiter`, `spide.spider.pipeline`
- `batch_scheduler.py` → `media_crawler_adapter.py`, `spide.spider.rate_limiter`
- `deep_tracker.py` → `spide.llm`, `spide.analysis.summarizer`
- `timed_search.py` → `spide.storage.models` (TimedSearchBatch, TimedSearchRecord), `spide.storage.sqlite_repo`
- `incremental.py` → `spide.storage.models`

## 测试

- `tests/unit/test_uapi_client.py`
- `tests/unit/test_fetcher.py`
- `tests/unit/test_pipeline.py`
- `tests/unit/test_deep_crawl.py`
- `tests/unit/test_batch_scheduler.py`
- `tests/unit/test_task_scheduler.py`
- `tests/unit/test_rate_limiter.py`
- `tests/unit/test_incremental.py`
- `tests/unit/test_deep_tracker.py`
- `tests/unit/test_timed_search.py`
- `tests/integration/test_uapi_real.py`
- `tests/integration/test_real_crawl.py`
