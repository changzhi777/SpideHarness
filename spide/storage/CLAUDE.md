# 数据存储模块

> [根目录](../../CLAUDE.md) > [spide](../) > **storage**

## 职责

数据持久化层，包含 Pydantic 数据模型、SQLite 异步仓库、Redis 缓存、抽象仓库接口和数据导出（JSON/JSONL/CSV/Excel）。

## 文件清单（6 个文件，含 `__init__.py`）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出核心模型、Repository、CacheBackend、工厂函数 |
| `models.py` | Pydantic v2 数据模型 — 15 实体 + 6 枚举 |
| `sqlite_repo.py` | SqliteRepository — aiosqlite 异步 CRUD（自动建表/类型映射） |
| `redis_cache.py` | RedisCache — aioredis 缓存与去重 |
| `repository.py` | AbstractRepository — 抽象仓库接口 |
| `exporter.py` | DataExporter — JSON/JSONL/CSV/Excel 导出 |

## 数据模型 (models.py)

15 个 Pydantic BaseModel 实体 + 6 个 StrEnum 枚举。

### 实体（15）

| 实体 | 关键字段 | 用途 |
|------|----------|------|
| `HotTopic` | title, source, hot_value, url, rank, category, fetched_at | 热搜条目 |
| `NewsArticle` | title, content, url, source, published_at | 新闻文章 |
| `CrawlTask` | task_id, platform, mode, status, params | 采集任务 |
| `CrawlSession` | session_id, topics_count, status, started_at | 采集会话 |
| `DeepContent` | content_id, platform, text, media, author | 深度内容 |
| `DeepComment` | comment_id, content_id, text, likes | 深度评论 |
| `DeepCreator` | creator_id, platform, name, followers | 创作者 |
| `HotTopicChange` | topic_id, status, prev_value, new_value | 增量变化 |
| `CrawlSnapshot` | snapshot_id, source, data, taken_at | 采集快照 |
| `AlertRule` | rule_id, keyword, source, severity | 告警规则 |
| `AlertRecord` | record_id, rule_id, matched, sent_at | 告警记录 |
| `TopicDeepTrack` | topic_id, summary, sentiment, sources | 深度追踪 |
| `TopicCluster` | cluster_id, topics, theme, confidence | 跨平台聚类 |
| `TimedSearchBatch` | batch_id, query, run_at, result_count | 定时搜索批次 |
| `TimedSearchRecord` | record_id, batch_id, query, source, title, url | 定时搜索记录 |

### 枚举（6）

| 枚举 | 取值 |
|------|------|
| `TopicSource` | weibo / baidu / douyin / zhihu / bilibili |
| `TaskStatus` | pending / running / completed / failed |
| `ArticleCategory` | tech / entertainment / sports / finance / ... |
| `Platform` | xhs / dy / ks / bili / wb / tieba / zhihu |
| `CrawlMode` | search / detail / creator / comment |
| `TopicStatus` | NEW / RISING / STABLE / FALLING / DROPPED |

## SqliteRepository（sqlite_repo.py）

基于 aiosqlite 的异步仓库，自动建表、类型映射、upsert。

```python
from spide.storage import SqliteRepository, HotTopic

repo = SqliteRepository("spide_data.db")
await repo.init()           # 自动建表
await repo.upsert_topic(topic)
topics = await repo.list_topics(source="weibo", limit=50)
await repo.close()
```

**关键方法**：
- `init()` — 自动建表（id/topic/comment/creator/snapshot/alert/track/cluster/timed_search 等表）
- `upsert_topic(topic)` / `bulk_upsert(topics)` — 批量 upsert
- `list_topics(source, limit, since)` — 多条件查询
- `get_last_snapshot(source)` / `save_snapshot(...)` — 增量快照
- `list_alerts(rule_id, since)` / `record_alert(...)` — 告警 CRUD
- `save_timed_search(record)` / `list_timed_search(batch_id)` — 定时搜索
- `close()` — 关闭连接

## RedisCache（redis_cache.py）

基于 aioredis 的缓存层，提供 topic 去重（hash）、recent top N（sorted set）、增量指纹缓存。

```python
from spide.storage import RedisCache

cache = RedisCache(url="redis://localhost:6379/0")
await cache.connect()
fp = await cache.fingerprint(title)         # 标题指纹（去重键）
is_new = await cache.is_new(fp)             # True = 首次出现
await cache.set_recent(source, top_n, ttl=3600)
await cache.close()
```

## AbstractRepository（repository.py）

抽象接口，定义 `init / upsert / get / list / delete` 等方法，便于在测试中用内存实现替换 SQLite。

## DataExporter（exporter.py）

多格式导出器，支持 JSON / JSONL / CSV / Excel（openpyxl）。

```python
from spide.storage import DataExporter, ExportFormat

exporter = DataExporter(output_dir="./exports")
path = await exporter.export_topics(topics, fmt=ExportFormat.EXCEL, filename="weibo_2026_06")
```

## 依赖

- `aiosqlite>=0.20` — 异步 SQLite
- `redis[hiredis]>=5.0` — 异步 Redis
- `openpyxl>=3.1.5` — Excel 导出
- `pydantic>=2.0` — 数据模型

## 测试

- `tests/unit/test_models.py` — Pydantic 模型验证
- `tests/unit/test_sqlite_repo.py` — CRUD + upsert
- `tests/unit/test_exporter.py` — JSON/CSV/Excel
- `tests/integration/test_crawl_pipeline.py` — 端到端持久化

## 设计原则

- **Pydantic v2** — 强类型 + 自动验证
- **抽象层** — `AbstractRepository` 支持依赖反转（测试用 mock）
- **自动建表** — `init()` 一键建表，无需迁移脚本
- **Upsert** — 重复数据自动覆盖
- **多格式** — JSON/JSONL/CSV/Excel 统一接口

## 变更记录

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-05-20 | 初始化 | 模块文档首版 |
| 2026-06-12 | 计数修正 | 文件清单 5 → 6（含 `__init__.py`），与根级一致 |
