# 数据存储模块

> [根目录](../../CLAUDE.md) > [spide](../) > **storage**

## 职责

数据持久化层，包含 Pydantic 数据模型、SQLite 异步仓库、Redis 缓存、抽象仓库接口和数据导出（JSON/JSONL/CSV/Excel）。

## 文件清单（5 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出核心模型、Repository、CacheBackend、工厂函数 |
| `models.py` | Pydantic v2 数据模型 — 15 实体 + 6 枚举 |
| `sqlite_repo.py` | SqliteRepository — aiosqlite 异步 CRUD（自动建表/类型映射） |
| `redis_cache.py` | RedisCache — aioredis 缓存与去重 |
| `repository.py` | AbstractRepository — 抽象仓库接口 |
| `exporter.py` | DataExporter — JSON/JSONL/CSV/Excel 导出 |

## 数据模型 (models.py)

### 枚举（6 个）
- `TopicSource` — 热搜数据源平台：weibo/baidu/douyin/zhihu/bilibili/kuaishou/tieba/web_search/custom
- `Platform` — 深度采集平台：xhs/dy/ks/bili/wb/tieba/zhihu（对应 MediaCrawler）
- `CrawlMode` — 深度采集模式：search/detail/creator
- `TaskStatus` — 任务状态：pending/running/completed/failed/cancelled
- `ArticleCategory` — 新闻分类：society/tech/finance/entertainment/sports/international/science/health/other
- `TopicStatus` — 话题状态变化：new/rising/falling/stable/dropped

### 实体（15 个）
- **HotTopic** — 热搜话题（title, source, hot_value, url, rank）
- **NewsArticle** — 新闻文章（title, url, content, summary, keywords）
- **CrawlTask** — 爬取任务（name, source, status, params）
- **CrawlSession** — 会话快照（session_id, messages, progress, crawled_urls）
- **DeepContent** — 深度采集内容（7 平台统一，含 extra dict）
- **DeepComment** — 深度采集评论
- **DeepCreator** — 深度采集创作者
- **HotTopicChange** — 话题变更记录（NEW/RISING/FALLING/DROPPED 标记）
- **CrawlSnapshot** — 采集快照（含 changes 列表）
- **AlertRule** — 告警规则
- **AlertRecord** — 告警记录
- **TopicDeepTrack** — 话题深度追踪记录
- **TopicCluster** — 跨平台话题聚类
- **TimedSearchBatch** — 定时搜索批次
- **TimedSearchRecord** — 定时搜索记录

## SqliteRepository

```python
from spide.storage import create_sqlite_repo
from spide.storage.models import HotTopic

repo = create_sqlite_repo(HotTopic, db_path="spide_data.db")
await repo.start()

# CRUD
topic_id = await repo.save(topic)
topics = await repo.query(source="weibo", limit=10)
count = await repo.count(source="weibo")
ok = await repo.delete(id)
exists = await repo.exists(title="xxx")

# 批量保存（支持去重 upsert）
ids = await repo.save_many(topics, dedup_fields=["title", "source"])

await repo.stop()
```

特性：
- 自动建表（Pydantic 模型反射 → SQLite DDL）
- Pydantic → SQLite 类型映射（int/str/datetime/list[dict] 自动 JSON 序列化）
- 集合类型（list[str] / dict）自动 JSON 序列化
- `save_many` 支持 `dedup_fields` 实现 upsert

## DataExporter

```python
from spide.storage.exporter import DataExporter

exporter = DataExporter(output_dir="data/export")
filepath = await exporter.export(topics, filename="weibo_hot", fmt="excel")
# 支持: json, jsonl, csv, excel
```

支持格式：
- `json` — 格式化 JSON 数组
- `jsonl` — 换行分隔 JSON
- `csv` — UTF-8 BOM CSV
- `excel` — `.xlsx` (openpyxl)

## RedisCache

```python
from spide.storage import create_redis_cache

cache = create_redis_cache(url="redis://localhost:6379/0", prefix="spide:")
await cache.connect()
await cache.set("key", {"data": 1}, ttl=300)
value = await cache.get("key")
await cache.disconnect()
```

## 依赖

- aiosqlite — SQLite 异步
- redis (aioredis) — Redis 缓存
- openpyxl — Excel 导出
- pydantic (v2) — 数据模型

## 测试

- `tests/unit/test_models.py` — Pydantic 模型验证
- `tests/unit/test_sqlite_repo.py` — SqliteRepository CRUD + upsert
- `tests/unit/test_exporter.py` — DataExporter JSON/CSV/Excel
