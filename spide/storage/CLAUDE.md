# 数据存储模块

> [根目录](../../CLAUDE.md) → `spide/storage/`

## 职责

数据持久化层，包含 Pydantic 数据模型、SQLite 异步仓库、Redis 缓存、抽象仓库接口和数据导出。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 14 | 导出核心模型和仓库 |
| `models.py` | 223 | Pydantic v2 数据模型 — 9 个实体 + 6 个枚举 |
| `sqlite_repo.py` | 331 | SqliteRepository — aiosqlite 异步 CRUD |
| `redis_cache.py` | 111 | RedisCache — aioredis 缓存与去重 |
| `repository.py` | 87 | AbstractRepository — 抽象仓库接口 |
| `exporter.py` | 222 | DataExporter — JSON/JSONL/CSV/Excel 导出 |

## 数据模型 (models.py)

### 枚举
- `TopicSource`: weibo/baidu/douyin/zhihu/bilibili/kuaishou/tieba/web_search/custom
- `Platform`: xhs/dy/ks/bili/wb/tieba/zhihu (MediaCrawler 平台)
- `CrawlMode`: search/detail/creator
- `TaskStatus`: pending/running/completed/failed/cancelled
- `ArticleCategory`: society/tech/finance/entertainment/sports/international/science/health/other

### 实体
- **HotTopic** — 热搜话题（title, source, hot_value, url, rank）
- **NewsArticle** — 新闻文章（title, url, content, summary, keywords）
- **CrawlTask** — 爬取任务（name, source, status, params）
- **CrawlSession** — 会话快照（session_id, messages, progress）
- **DeepContent** — 深度采集内容（7 平台统一，含 extra dict）
- **DeepComment** — 深度采集评论
- **DeepCreator** — 深度采集创作者

## SqliteRepository

```python
repo = SqliteRepository(HotTopic, db_path="spide_data.db")
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

特性：自动建表、Pydantic→SQLite 类型映射、集合类型自动 JSON 序列化。

## DataExporter

```python
exporter = DataExporter(output_dir="data/export")
filepath = await exporter.export(topics, filename="weibo_hot", fmt="excel")
# 支持: json, jsonl, csv, excel
```

## 依赖

- aiosqlite, redis, openpyxl, pydantic

## 测试

- `tests/unit/test_models.py`
- `tests/unit/test_sqlite_repo.py`
- `tests/unit/test_exporter.py`
- `tests/test_storage.py`
