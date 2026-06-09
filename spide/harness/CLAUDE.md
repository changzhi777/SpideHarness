# Harness 调度引擎

> [根目录](../../CLAUDE.md) > [spide](../) > **harness**

## 职责

核心调度引擎，管理 RuntimeBundle 生命周期和管道编排（采集/深度采集/增量/深度追踪/跨平台分析/LLM 对话）。是整个 CLI 命令的"胶水层"。

## 文件清单（2 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 Engine + RuntimeBundle |
| `engine.py` | Engine + RuntimeBundle 核心实现 |

## 核心类

### RuntimeBundle（运行时状态容器）

封装单次 Agent 会话的全部依赖：

```python
@dataclass
class RuntimeBundle:
    session_id: str = ""                  # 12 位 hex
    settings: Settings                     # 全局配置
    workspace: str = ""                    # 工作空间路径
    system_prompt: str = ""                # 系统提示词
    messages: list[dict[str, str]] = []    # LLM 对话历史
    crawled_urls: list[str] = []           # 已采集 URL
    progress: float = 0.0                  # 0.0 ~ 1.0
    # 延迟初始化（start() 时填充）
    llm: LLMClient | None = None
    uapi: UAPIClient | None = None
    session_storage: SessionStorage | None = None
```

### Engine（生命周期 + 管道编排）

```python
from spide.harness import Engine
from spide.config import load_settings

engine = Engine(load_settings())
bundle = await engine.start(workspace=workspace)

# 采集管道
results = await engine.crawl(sources=["weibo", "baidu"])

# 深度采集管道
results = await engine.deep_crawl(platform="xhs", keywords=["AI"], max_notes=20)

# 增量采集管道
results = await engine.crawl_diff(sources=["weibo"])
# results = {platform: {"topics": [...], "changes": [...], "snapshot": ..., "report": ...}}

# 深度追踪管道
tracks = await engine.track_deep(topics, top_n=10)

# 跨平台关联分析管道
clusters = await engine.cross_analyze({"weibo": topics1, "zhihu": topics2})

# LLM 对话
response = await engine.chat("分析今日热搜")
stream = engine.chat_stream("分析趋势")  # 同步迭代器

await engine.stop()  # 保存会话快照 + 关闭所有组件
```

## 管道编排详解

| 管道 | 入参 | 出参 | 内部依赖 |
|------|------|------|----------|
| `crawl` | sources: list[str] | dict[source, list[HotTopic]] | UAPIClient |
| `deep_crawl` | platform, mode, keywords, content_ids, creator_ids, max_notes, enable_comments, headless | dict {contents, comments, creators} | MediaCrawlerAdapter |
| `crawl_diff` | sources: list[str] | dict {topics, changes, snapshot, report} | UAPIClient + IncrementalDetector + SqliteRepository |
| `track_deep` | topics, top_n | list[TopicDeepTrack] | DeepTopicTracker |
| `cross_analyze` | topics_by_source | list[TopicCluster] | CrossPlatformAnalyzer |
| `chat` | user_message | LLM Response (zhipuai Response) | LLMClient (via to_thread) |
| `chat_stream` | user_message | StreamResponse 迭代器 | LLMClient (sync) |

## 依赖

- `spide.config` (Settings) — 全局配置
- `spide.llm` (LLMClient) — LLM 调用
- `spide.spider.uapi_client` (UAPIClient) — 热搜采集
- `spide.spider.media_crawler_adapter` (MediaCrawlerAdapter) — 深度采集（延迟导入）
- `spide.spider.incremental` (IncrementalDetector) — 增量检测
- `spide.spider.deep_tracker` (DeepTopicTracker) — 深度追踪
- `spide.analysis.cross_platform` (CrossPlatformAnalyzer) — 跨平台分析
- `spide.session_storage` (SessionStorage) — 会话持久化
- `spide.prompts` (build_system_prompt) — 系统提示词组装
- `spide.workspace` (get_workspace_root) — 工作空间解析
- `spide.exceptions` (SpideError) — 异常

## 设计原则

- **KISS** — Engine 仅做编排，具体实现委托给各模块
- **SOLID** — 单一职责（编排），依赖倒置（依赖抽象 Settings / HotTopic）
- **延迟加载** — heavy 依赖（MediaCrawlerAdapter / DeepTopicTracker / CrossPlatformAnalyzer）在调用时再 import
- **生命周期管理** — start/stop 配对，stop 时自动保存会话快照并关闭所有组件

## 测试

- `tests/unit/test_engine.py` — Engine 生命周期 + crawl/deep_crawl/chat
- `tests/integration/test_engine_lifecycle.py` — Engine 集成测试
