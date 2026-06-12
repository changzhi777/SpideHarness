# 测试模块

> [根目录](../CLAUDE.md) > **tests**

## 职责

分层测试套件，覆盖所有 `spide/` 子模块 + `dashboard/` Web API。包含单元测试、集成测试和端到端测试，共 58 个测试文件、536 个测试用例。

## 结构

```
tests/
├── conftest.py                    # 共享 fixtures (tmp_db, tmp_workspace, real_settings, mock_aiohttp_response, skip_if_*)
├── unit/                          # 单元测试（42 个文件，416 用例）
│   ├── test_alert_engine.py       # AlertEngine 规则匹配 + YAML 加载
│   ├── test_analysis.py           # ContentSummarizer/TrendAnalyzer/SmartCrawlStrategy
│   ├── test_batch_scheduler.py    # BatchCrawlScheduler + BatchTask/Result
│   ├── test_broker.py             # MessageBroker pub/sub + 通配符匹配
│   ├── test_config.py             # Settings 加载 + 环境变量覆盖
│   ├── test_conversation_store.py # SQLite 多轮记忆 CRUD
│   ├── test_cross_platform.py     # CrossPlatformAnalyzer 跨平台聚类
│   ├── test_dashboard.py          # DataCollector 聚合 + 渲染
│   ├── test_deep_crawl.py         # MediaCrawlerAdapter 深度采集
│   ├── test_deep_tracker.py       # DeepTopicTracker 深度追踪
│   ├── test_engine.py             # Engine 生命周期 + crawl/deep_crawl/chat
│   ├── test_exceptions.py         # 异常层级验证
│   ├── test_exporter.py           # DataExporter JSON/CSV/Excel
│   ├── test_feishu_agent.py       # ReAct 循环 + 降级 + 多轮记忆（53 用例）
│   ├── test_feishu_card.py        # 5 种卡片模板
│   ├── test_feishu_ws.py          # WebSocket 客户端 + 事件回调 + 双路径处理
│   ├── test_fetcher.py            # AsyncFetcher HTTP 抓取
│   ├── test_incremental.py        # IncrementalDetector 增量检测
│   ├── test_llm.py                # LLMClient Mock 测试
│   ├── test_llm_client.py         # OpenAI 兼容协议 + JSON Action 兜底
│   ├── test_logging.py            # structlog 配置 + get_logger
│   ├── test_mcp_search_tools.py   # MCP 搜索工具分发
│   ├── test_mcp_server.py         # MCP Server 工具注册
│   ├── test_memory.py             # 文件系统记忆 CRUD
│   ├── test_models.py             # Pydantic 模型验证
│   ├── test_mqtt_client.py        # MQTTClient 连接/发布/订阅
│   ├── test_notifier.py           # Log/MQTT/Webhook/飞书通知 + Dispatcher
│   ├── test_pipeline.py           # clean_topics/deduplicate/parse
│   ├── test_prompts.py            # Prompt 层叠组装
│   ├── test_rate_limiter.py       # RateLimiter + CircuitBreaker + CheckpointManager
│   ├── test_scheduler.py          # APScheduler + token 缓存 + 卡片渲染
│   ├── test_search_provider.py    # WebSearchProvider / WebContentProvider
│   ├── test_secrets.py            # ${ENV_VAR} 占位符解析
│   ├── test_session_storage.py    # 会话快照保存/加载
│   ├── test_sqlite_repo.py        # SqliteRepository CRUD + upsert
│   ├── test_task_scheduler.py     # TaskScheduler 定时调度
│   ├── test_timed_search.py       # TimedSearchService 定时搜索
│   ├── test_title_similarity.py   # Jaccard + 编辑距离相似度
│   ├── test_tool_router.py        # 8 工具路由 + 超时 + 兜底
│   ├── test_uapi_client.py        # UAPIClient 热搜 + 限流
│   ├── test_wordcloud.py          # WordCloudGenerator 词云
│   └── test_workspace.py          # 工作空间初始化/健康检查
├── integration/                   # 集成测试（6 个文件，38 用例，需网络/真实服务）
│   ├── test_crawl_pipeline.py     # 采集管道集成
│   ├── test_engine_lifecycle.py   # Engine 生命周期
│   ├── test_real_crawl.py         # @integration 真实 UAPI 采集（429 跳过）
│   ├── test_real_llm.py           # @integration 真实 GLM-5.1 调用（401 跳过）
│   ├── test_real_mqtt.py          # @integration 真实 MQTT 连接
│   └── test_uapi_real.py          # @integration 真实 UAPI API
└── e2e/                           # 端到端测试（6 个文件，82 用例）
    ├── test_cli_advanced.py       # 高级 CLI（crawl-diff/dedup/monitor/track/dashboard/cross-analyze）
    ├── test_cli_e2e.py            # CLI 命令端到端（version/init/doctor/config/memory/crawl）
    ├── test_cli_errors.py         # CLI 错误处理（缺参数/无效输入）
    ├── test_dashboard_api.py      # Dashboard Web API（FastAPI + 飞书 Handler + GitHub Trending）
    ├── test_env_precheck.py       # 环境预检（version/init/doctor/config/help）
    └── test_full_pipeline.py      # 全流程测试（Mock + 真实 API）
```

## 运行方式

```bash
uv run pytest                      # 全部测试（536 passed）
uv run pytest tests/unit/          # 仅单元测试
uv run pytest tests/integration/   # 集成测试（需 API Key）
uv run pytest tests/e2e/           # E2E 测试（需完整环境）
uv run pytest -m integration       # 按 marker 筛选
uv run pytest -k "test_uapi"       # 按名称筛选
uv run pytest --lf                 # last-failed 模式
uv run pytest -x                   # 失败即停
uv run pytest --cov=spide          # 覆盖率报告
```

## 测试标记（Markers）

- `@pytest.mark.integration` — 集成测试（需要网络，真实 API 调用）
- `@pytest.mark.e2e` — 端到端测试（完整 CLI 流程）

## 配置（pyproject.toml）

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"      # 无需 @pytest.mark.asyncio
testpaths = ["tests"]
addopts = "-ra -q --tb=short"
```

**Mock 策略**：
- HTTP：使用 `unittest.mock.AsyncMock` + `aiohttp` MagicMock 模拟
- MQTT：使用 `unittest.mock`
- LLM：使用 `unittest.mock` 包装 `zai-sdk` ZaiClient

## Fixtures (conftest.py)

| Fixture | 作用域 | 用途 |
|---------|--------|------|
| `tmp_db` | function | 临时 SQLite 数据库路径（`tmp_path / "test.db"`） |
| `tmp_workspace` | function | 临时工作空间目录（设置 `SPIDE_WORKSPACE` 环境变量 + `initialize_workspace`） |
| `mock_aiohttp_response` | function | **工厂 fixture** — 返回 helper 函数，用于构建 aiohttp `ClientSession.get` mock（处理 `__aenter__/__aexit__` 异步上下文） |
| `real_settings` | function | 从 `configs/` 加载真实配置（`load_settings()`） |
| `skip_if_no_uapi` | function | UAPI API Key 未配置时 `pytest.skip` |
| `skip_if_no_llm` | function | 智谱 LLM API Key 未配置时 `pytest.skip` |
| `skip_if_no_mqtt` | function | MQTT 配置未设置时 `pytest.skip` |

### `mock_aiohttp_response` 工厂模式

```python
def test_xxx(self, mock_aiohttp_response):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"data": 1})
    with patch("aiohttp.ClientSession.get", new=mock_aiohttp_response(mock_resp)):
        result = await fetch_data()
```

**实现要点**：
- 模拟 `async with session.get(url) as resp:` 异步上下文协议
- 内部用 `AsyncMock` 设置 `__aenter__`（返回 resp）和 `__aexit__`（返回 False）

## 集成测试标记

集成测试需要真实 API/服务，使用 `skip_if_no_*` fixture 在无 Key 时优雅跳过：

```python
@pytest.mark.integration
async def test_real_uapi_call(real_settings, skip_if_no_uapi):
    # skip_if_no_uapi 自动检查 api_key 并跳过
    ...
```

## 统计

- **总文件**: 58 个（unit 42 + integration 6 + e2e 6 + conftest 1，含 3 个 __init__.py）
- **总行数**: ~7,100 行
- **测试用例**: 536 个（unit 416 + integration 38 + e2e 82）
- **覆盖率**: 100% 覆盖 spide/ 所有子模块 + dashboard/ Web API

## 设计原则

- **KISS** — 工厂 fixture 模式简化 aiohttp mock
- **DRY** — `skip_if_no_*` fixtures 消除重复的跳过逻辑
- **隔离性** — `tmp_db` / `tmp_workspace` 用 `tmp_path` 确保测试间无状态污染
- **真实集成** — `@integration` marker 区分纯单元测试与需网络的测试
- **自动异步** — `asyncio_mode = "auto"` 减少样板代码
