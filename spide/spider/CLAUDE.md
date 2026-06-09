# Spider 引擎模块

> [根目录](../../CLAUDE.md) > [spide](../) > **spider**

## 职责

热搜数据采集与深度采集引擎，包含数据抓取、清洗去重、UAPI 集成、MediaCrawler 适配、调度策略、增量检测、深度追踪和稳定性保障（限流+熔断+断点恢复）。

## 文件清单（11 个文件，~2574 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | — | 导出 AsyncFetcher, UAPIClient, parse_hot_items, deduplicate_items |
| `fetcher.py` | ~180 | AsyncFetcher — aiohttp + BeautifulSoup 异步抓取器 |
| `pipeline.py` | ~150 | 数据清洗管道：clean_topics, deduplicate_items, parse_hot_items |
| `uapi_client.py` | ~330 | UAPIClient — UAPI 热搜 REST（令牌桶限流 + 熔断保护） |
| `media_crawler_adapter.py` | 591 | MediaCrawler 深度采集适配器（子进程桥接 + 7 平台映射） |
| `batch_scheduler.py` | 241 | BatchCrawlScheduler — 多平台并行调度（熔断 + 断点恢复 + 进度回调） |
| `task_scheduler.py` | 234 | TaskScheduler — 定时采集调度器（interval + cron_times 双模式） |
| `rate_limiter.py` | 318 | RateLimiter(令牌桶+信号量) + CircuitBreaker(熔断) + CheckpointManager(断点) |
| `incremental.py` | ~180 | IncrementalDetector — 增量检测 + 状态标记 + 快照 |
| `deep_tracker.py` | ~210 | DeepTopicTracker — 搜索 + LLM 摘要 + 情感分析 |
| `timed_search.py` | ~280 | TimedSearchService — 定时搜索热搜 + 关联新闻 + 持久化 |

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

特性：5 平台映射（weibo/baidu/douyin/zhihu/bilibili），自动重试（指数退避），失败熔断。

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

### MediaCrawlerAdapter（7 平台深度采集 + 3 模式）
```python
from spide.spider.media_crawler_adapter import MediaCrawlerAdapter, DeepCrawlResult
from spide.storage.models import Platform, CrawlMode

adapter = MediaCrawlerAdapter(media_crawler_root="MediaCrawler")
result: DeepCrawlResult = await adapter.deep_crawl(
    platform=Platform.XHS,
    mode=CrawlMode.SEARCH,
    keywords=["AI编程", "副业"],
    max_notes=20,
    enable_comments=True,
    headless=True,
    timeout=600,
)
# result.contents / result.comments / result.creators
```

**7 平台映射**（Spide Platform → MediaCrawler 标识）：
| Spide | MediaCrawler |
|-------|--------------|
| `Platform.XHS` | xhs |
| `Platform.DOUYIN` | dy |
| `Platform.KUAISHOU` | ks |
| `Platform.BILIBILI` | bili |
| `Platform.WEIBO` | wb |
| `Platform.TIEBA` | tieba |
| `Platform.ZHIHU` | zhihu |

**3 采集模式**（CrawlMode）：SEARCH（搜索关键词）/ DETAIL（按内容ID）/ CREATOR（按创作者ID）

**内部数据映射函数**（私有，模块内调用）：
- `_map_content()` — 内容数据 → `DeepContent`（含 ID/URL/媒体/标签/计数/IP位置）
- `_map_comment()` — 评论数据 → `DeepComment`（含父子关系/IP位置/点赞）
- `_map_creator()` — 创作者数据 → `DeepCreator`（含粉丝/关注/互动/简介）
- `_is_comment()` / `_is_creator()` — 自动类型判断（基于字段特征）

**设计策略**：子进程桥接（`uv run -m mediacrawler`）+ JSON/JSONL/CSV 文件交换，避免与 MediaCrawler 的 Playwright/httpx 重型依赖冲突。

### BatchCrawlScheduler（批量并行 + 断点续采 + 进度回调）
```python
from spide.spider.batch_scheduler import BatchCrawlScheduler, BatchTask, BatchResult

scheduler = BatchCrawlScheduler(max_concurrent=3)
scheduler.enable_checkpoint(db_path="spide_data.db")  # 启用断点

result: BatchResult = await scheduler.run(
    tasks=[
        BatchTask(platform="xhs", mode="search", keywords=["AI"]),
        BatchTask(platform="dy", mode="search", keywords=["AI"]),
    ],
    on_progress=my_progress_callback,  # async (done, total, platform, status) -> None
    resume_task_id="batch_20260609",  # 断点恢复
)
# result.succeeded / result.failed / result.contents / result.comments / result.creators
```

**特性**：
- `asyncio.Semaphore` 控制并发数（默认 3）
- 内置 `CircuitBreaker`（failure_threshold=3, recovery_timeout=60s）
- 支持断点恢复（`resume_task_id` 过滤已完成平台）
- 进度回调签名：`async (completed: int, total: int, platform: str, status: str) -> None`
  - status: "running" / "done" / "failed"

### TaskScheduler（定时采集 + 任务编排）
```python
from spide.spider.task_scheduler import TaskScheduler, ScheduledJob

scheduler = TaskScheduler()
scheduler.add_job(ScheduledJob(
    name="微博热搜",
    platforms=["xhs"],          # 深度采集平台
    sources=["weibo"],            # UAPI 热搜源
    interval_seconds=300,         # interval 模式
    cron_times=["09:00", "18:00"], # cron 模式（与 interval 二选一）
    save_to_db=True,
    export_format="excel",        # 空=不导出
    max_runs=0,                   # 0=无限
    enabled=True,
))
scheduler.on_result(my_result_callback)  # async (result) -> None
await scheduler.start()
# ... 运行 ...
await scheduler.stop()
```

**特性**：
- 双定时模式：`interval_seconds`（间隔）或 `cron_times`（每日时刻，逗号分隔 HH:MM）
- 多任务并行（每个任务独立 asyncio.Task）
- 最大运行次数限制（`max_runs`，0=无限）
- 内部调用 `UAPIClient.fetch_hotboard` + `BatchCrawlScheduler.run`

**ScheduledJob.next_wait_seconds() 算法**：
- cron 模式：计算到下一个 cron 时刻的秒数（今天的时刻已过则 +86400s）
- interval 模式：返回 `interval_seconds`

### RateLimiter（令牌桶 + 信号量双重控制）
```python
from spide.spider.rate_limiter import RateLimiter

limiter = RateLimiter(max_rpm=30, max_concurrent=5)
async with limiter:
    await fetch(url)

# 也可手动获取/释放
await limiter.acquire()
try:
    await fetch(url)
finally:
    limiter.release()
```

**双重控制机制**：
1. `asyncio.Semaphore(max_concurrent)` — 并发连接数
2. 令牌桶（token bucket）— 每分钟请求数（`max_rpm`）

令牌补充：按 `elapsed * (max_rpm / 60.0)` 计算，无令牌时按 `(1 - tokens) * (60 / max_rpm)` 等待。

### CircuitBreaker（熔断器 — CLOSED/OPEN/HALF_OPEN 状态机）
```python
from spide.spider.rate_limiter import CircuitBreaker, CircuitBreakerOpenError

breaker = CircuitBreaker(
    failure_threshold=5,      # 失败阈值
    recovery_timeout=60.0,    # 熔断后恢复探测时间
    name="uapi",              # 日志标识
)

try:
    result = await breaker.call(api_fetch, source="weibo")
except CircuitBreakerOpenError as e:
    logger.warning("breaker_open", error=str(e))
```

**状态机转换**：
```
CLOSED ──(连续失败 ≥ threshold)──> OPEN
OPEN ──(recovery_timeout 后被调用)──> HALF_OPEN
HALF_OPEN ──(成功)──> CLOSED
HALF_OPEN ──(失败)──> OPEN
```

| 状态 | 行为 |
|------|------|
| CLOSED | 正常调用，记录失败次数 |
| OPEN | 直接抛 `CircuitBreakerOpenError`（`recovery_timeout` 内） |
| HALF_OPEN | 允许一次探测调用 |

### CheckpointManager（断点恢复 — SQLite 持久化）
```python
from spide.spider.rate_limiter import CheckpointManager

ckpt = CheckpointManager(db_path="spide_data.db")
await ckpt.start()
await ckpt.save_checkpoint("batch_20260609", {"completed_platforms": ["xhs", "dy"], "pending": ["bili"]})
state = await ckpt.load_checkpoint("batch_20260609")
all_ckpts = await ckpt.list_checkpoints()
deleted = await ckpt.delete_checkpoint("batch_20260609")
await ckpt.stop()
```

**表结构**：
```sql
CREATE TABLE checkpoints (
    task_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,        -- JSON 序列化
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

`save_checkpoint` 使用 `ON CONFLICT(task_id) DO UPDATE` 实现 upsert。

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

## 依赖关系

- `uapi_client.py` → aiohttp, `spide.spider.rate_limiter`, `spide.spider.pipeline`, `spide.config.UAPIConfig`
- `media_crawler_adapter.py` → MediaCrawler (子进程), `spide.storage.models` (Platform/CrawlMode/DeepContent/DeepComment/DeepCreator)
- `batch_scheduler.py` → `media_crawler_adapter.py`, `spide.spider.rate_limiter` (CircuitBreaker + CheckpointManager)
- `task_scheduler.py` → `spide.config`, `spide.spider.uapi_client`, `spide.spider.batch_scheduler`
- `deep_tracker.py` → `spide.llm`, `spide.analysis.summarizer`, `spide.mcp.search_provider`
- `timed_search.py` → `spide.storage.models` (TimedSearchBatch, TimedSearchRecord), `spide.storage.sqlite_repo`
- `incremental.py` → `spide.storage.models` (HotTopicChange, CrawlSnapshot, TopicStatus)

## 设计原则

- **KISS** — 每个类职责单一，配置项用 dataclass 简洁定义
- **稳定性优先** — 限流/熔断/断点三位一体保障长时间采集
- **可降级** — 熔断/超时均有降级路径，不阻塞其他平台
- **异步优先** — 全部 `async/await`，子进程桥接避开依赖冲突

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
