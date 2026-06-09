# Harness 调度引擎

> [根目录](../../CLAUDE.md) > [spide](../) > **harness**

## 职责

核心调度引擎，管理 RuntimeBundle 生命周期和管道编排（采集/深度采集/增量/深度追踪/跨平台分析/LLM 对话）。是整个 CLI 命令的"胶水层"。

## 文件清单（2 个文件，~414 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | — | 导出 Engine + RuntimeBundle |
| `engine.py` | 391 | Engine + RuntimeBundle 核心实现 + 7 个管道方法 |

## 核心类

### RuntimeBundle（运行时状态容器）

封装单次 Agent 会话的全部依赖，**延迟初始化**模式（`init=False`）：

```python
@dataclass
class RuntimeBundle:
    # 基础字段（构造时填充）
    session_id: str = ""                  # 12 位 hex (uuid.uuid4().hex[:12])
    settings: Settings                     # 全局配置
    workspace: str = ""                    # 工作空间路径
    system_prompt: str = ""                # 系统提示词（build_system_prompt 组装）
    messages: list[dict[str, str]] = []    # LLM 对话历史 [{role, content}]
    crawled_urls: list[str] = []           # 已采集 URL
    progress: float = 0.0                  # 0.0 ~ 1.0

    # 延迟初始化（start() 时填充，init=False 排除出 __init__）
    llm: LLMClient | None = None
    uapi: UAPIClient | None = None
    session_storage: SessionStorage | None = None
```

### Engine（生命周期 + 管道编排）

```python
from spide.harness import Engine
from spide.config import load_settings

engine = Engine(load_settings())
bundle = await engine.start(workspace=workspace, session_id="custom-id")
# bundle 包含已初始化的 llm / uapi / session_storage

# 7 个管道方法（详见下表）
results = await engine.crawl(sources=["weibo", "baidu"])
# ... 其他管道 ...

await engine.stop()  # 保存会话快照 + 关闭所有组件
```

## Engine.start() 初始化顺序

```python
async def start(self, *, workspace: str | None = None, session_id: str | None = None):
    ws = workspace or str(get_workspace_root())
    system_prompt = build_system_prompt(workspace=ws)  # Prompt 层叠组装

    bundle = RuntimeBundle(
        session_id=session_id or uuid.uuid4().hex[:12],
        settings=self._settings,
        workspace=ws,
        system_prompt=system_prompt,
    )

    # 1. LLM 客户端（必须有 LLMClient 配置）
    bundle.llm = LLMClient(self._settings.llm)
    await bundle.llm.start()

    # 2. UAPI 客户端（仅在 api_key 已配置时初始化）
    if self._settings.uapi.api_key:
        bundle.uapi = UAPIClient(self._settings.uapi)
        await bundle.uapi.start()

    # 3. 会话存储
    bundle.session_storage = SessionStorage(workspace=ws)

    self._bundle = bundle
    return bundle
```

**初始化顺序**：LLM → UAPI（如有 Key）→ SessionStorage

## Engine.stop() 关闭顺序

```python
async def stop(self):
    if self._bundle is None:
        return
    bundle = self._bundle

    # 1. 保存会话快照（messages + crawled_urls + progress）
    if bundle.session_storage:
        await bundle.session_storage.save_snapshot(
            session_id=bundle.session_id,
            session_key="spide:engine",
            model=bundle.settings.llm.text.model,
            system_prompt=bundle.system_prompt,
            messages=bundle.messages,
            crawled_urls=bundle.crawled_urls,
            progress=bundle.progress,
        )

    # 2. 关闭组件（逆序：UAPI → LLM）
    if bundle.uapi:
        await bundle.uapi.stop()
    if bundle.llm:
        await bundle.llm.stop()

    self._bundle = None
```

**关闭顺序**：保存快照 → 关闭 UAPI → 关闭 LLM（与 start 相反）

## 管道编排详解（7 个方法）

| 管道 | 签名 | 内部依赖 | 关键行为 |
|------|------|----------|----------|
| `crawl` | `crawl(sources: list[str] \| None) -> dict[source, list[HotTopic]]` | UAPIClient | `asyncio.gather` 并发采集，异常隔离（`return_exceptions=True`），source→空列表降级 |
| `deep_crawl` | `deep_crawl(platform, *, mode, keywords, content_ids, creator_ids, max_notes, enable_comments, headless) -> dict[contents, comments, creators]` | MediaCrawlerAdapter | 延迟导入；自动 str→Enum 转换（`Platform(x)` / `CrawlMode(x)`） |
| `crawl_diff` | `crawl_diff(sources) -> dict[source, {topics, changes, snapshot, report}]` | UAPIClient + IncrementalDetector + SqliteRepository | 查上一轮数据 → detect_changes → build_snapshot → generate_diff_report |
| `track_deep` | `track_deep(topics, top_n=10) -> list[TopicDeepTrack]` | DeepTopicTracker (max_concurrent=3) | 延迟导入 |
| `cross_analyze` | `cross_analyze(topics_by_source) -> list[TopicCluster]` | CrossPlatformAnalyzer | 延迟导入 |
| `chat` | `chat(user_message) -> Response` | LLMClient (via to_thread) | **自动维护 messages 历史**（user→assistant 自动追加），`asyncio.to_thread` 避免阻塞 |
| `chat_stream` | `chat_stream(user_message) -> StreamResponse 迭代器` | LLMClient (sync) | **返回同步迭代器**（ZaiClient 限制），调用者负责迭代 |

### chat() 消息历史维护

```python
async def chat(self, user_message: str):
    # 1. 追加 user 消息
    bundle.messages.append({"role": "user", "content": user_message})

    # 2. 构建完整消息列表（system + 历史 + 当前 user）
    full_messages = [
        {"role": "system", "content": bundle.system_prompt},
        *bundle.messages,
    ]

    # 3. 在线程池中调用同步 LLM（避免阻塞事件循环）
    response = await asyncio.to_thread(bundle.llm.chat, messages=full_messages)

    # 4. 提取并追加 assistant 消息
    assistant_content = response.choices[0].message.content
    bundle.messages.append({"role": "assistant", "content": assistant_content})

    return response
```

### chat_stream() 流式模式

**注意**：ZaiClient SDK 的流式接口是**同步迭代器**，不能 await。`chat_stream` 直接返回 `bundle.llm.chat_stream(messages=full_messages)`，调用方需要 `for chunk in stream: ...` 迭代处理。

## 异常处理

`bundle` 属性访问时检查 `_bundle is None`，未启动抛 `SpideError("引擎未启动，请先调用 start()")`。
各管道方法在 `bundle.llm` / `bundle.uapi` 为 None 时同样抛 `SpideError`。

## 依赖

- `spide.config` (Settings) — 全局配置
- `spide.llm` (LLMClient) — LLM 调用
- `spide.spider.uapi_client` (UAPIClient) — 热搜采集
- `spide.spider.media_crawler_adapter` (MediaCrawlerAdapter) — 深度采集（延迟导入）
- `spide.spider.incremental` (IncrementalDetector) — 增量检测（延迟导入）
- `spide.spider.deep_tracker` (DeepTopicTracker) — 深度追踪（延迟导入）
- `spide.analysis.cross_platform` (CrossPlatformAnalyzer) — 跨平台分析（延迟导入）
- `spide.session_storage` (SessionStorage) — 会话持久化
- `spide.prompts` (build_system_prompt) — 系统提示词组装
- `spide.workspace` (get_workspace_root) — 工作空间解析
- `spide.exceptions` (SpideError) — 异常
- `spide.storage.models` (HotTopic, Platform, CrawlMode, TopicSource) — 数据模型

## 设计原则

- **KISS** — Engine 仅做编排，具体实现委托给各模块
- **SOLID** — 单一职责（编排），依赖倒置（依赖抽象 Settings / HotTopic）
- **延迟加载** — heavy 依赖（MediaCrawlerAdapter / DeepTopicTracker / CrossPlatformAnalyzer）在调用时再 import，避免启动开销
- **生命周期管理** — start/stop 配对，stop 时自动保存会话快照并关闭所有组件
- **异常隔离** — `crawl()` 用 `asyncio.gather(return_exceptions=True)` 隔离单平台失败
- **消息历史** — `chat()` 自动维护 messages，调用方无需手动管理

## 测试

- `tests/unit/test_engine.py` — Engine 生命周期 + crawl/deep_crawl/chat
- `tests/integration/test_engine_lifecycle.py` — Engine 集成测试
- `tests/e2e/test_cli_e2e.py` — 通过 CLI `spide run` 间接测试
