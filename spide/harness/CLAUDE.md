# Harness 调度引擎

> [根目录](../../CLAUDE.md) → `spide/harness/`

## 职责

核心调度引擎，管理 RuntimeBundle 生命周期和管道编排（采集、深度采集、LLM 对话）。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 3 | 导出 Engine |
| `engine.py` | 277 | Engine + RuntimeBundle |

## 核心类

### RuntimeBundle
运行时状态容器，封装单次 Agent 会话的全部依赖：
- `session_id`, `settings`, `workspace`, `system_prompt`
- `messages` (对话历史), `crawled_urls`, `progress`
- 延迟初始化: `llm` (LLMClient), `uapi` (UAPIClient), `session_storage`

### Engine
```python
engine = Engine(settings)
bundle = await engine.start(workspace=workspace)

# 采集管道
results = await engine.crawl(sources=["weibo", "baidu"])

# 深度采集管道
results = await engine.deep_crawl(platform="xhs", keywords=["AI"])

# LLM 对话
response = await engine.chat("分析今日热搜")
stream = engine.chat_stream("分析趋势")  # 同步迭代器

await engine.stop()  # 保存会话快照 + 关闭组件
```

## 依赖

- `spide.config` (Settings)
- `spide.llm` (LLMClient)
- `spide.spider.uapi_client` (UAPIClient)
- `spide.spider.media_crawler_adapter` (deep_crawl 时延迟导入)
- `spide.session_storage` (SessionStorage)
- `spide.prompts` (build_system_prompt)
- `spide.storage.models` (HotTopic, Platform, CrawlMode)

## 测试

- `tests/unit/test_engine.py`
- `tests/integration/test_engine_lifecycle.py`
