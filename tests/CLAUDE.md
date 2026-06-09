# 测试模块

> [根目录](../CLAUDE.md) → `tests/`

## 结构

```
tests/
├── conftest.py                    # 共享 fixtures (tmp_db, tmp_workspace, real_settings, mock_aiohttp_response)
├── unit/                          # 单元测试 (34 个)
│   ├── test_analysis.py           # ContentSummarizer/TrendAnalyzer/SmartCrawlStrategy
│   ├── test_batch_scheduler.py    # BatchCrawlScheduler + BatchTask/Result
│   ├── test_broker.py             # MessageBroker pub/sub + 通配符匹配
│   ├── test_config.py             # Settings 加载 + 环境变量覆盖
│   ├── test_dashboard.py          # DataCollector 聚合 + 渲染
│   ├── test_deep_crawl.py         # MediaCrawlerAdapter 深度采集
│   ├── test_engine.py             # Engine 生命周期 + crawl/deep_crawl/chat
│   ├── test_exceptions.py         # 异常层级验证
│   ├── test_exporter.py           # DataExporter JSON/CSV/Excel
│   ├── test_fetcher.py            # AsyncFetcher HTTP 抓取
│   ├── test_llm.py                # LLMClient Mock 测试
│   ├── test_logging.py            # structlog 配置 + get_logger
│   ├── test_mcp_server.py         # MCP Server 工具注册
│   ├── test_memory.py             # 文件系统记忆 CRUD
│   ├── test_mqtt_client.py        # MQTTClient 连接/发布/订阅
│   ├── test_pipeline.py           # clean_topics/deduplicate/parse
│   ├── test_prompts.py            # Prompt 层叠组装
│   ├── test_session_storage.py    # 会话快照保存/加载
│   ├── test_sqlite_repo.py        # SqliteRepository CRUD + upsert
│   ├── test_task_scheduler.py     # TaskScheduler 定时调度
│   ├── test_uapi_client.py        # UAPIClient 热搜 + 限流
│   ├── test_wordcloud.py          # WordCloudGenerator 词云
│   ├── test_workspace.py          # 工作空间初始化/健康检查
│   ├── test_rate_limiter.py       # RateLimiter + CircuitBreaker + CheckpointManager
│   ├── test_incremental.py        # IncrementalDetector 增量检测
│   ├── test_alert_engine.py       # AlertEngine 规则匹配 + YAML 加载
│   ├── test_notifier.py           # Log/MQTT/Webhook/飞书通知 + Dispatcher
│   ├── test_deep_tracker.py       # DeepTopicTracker 深度追踪
│   ├── test_cross_platform.py     # CrossPlatformAnalyzer 跨平台聚类
│   ├── test_title_similarity.py   # Jaccard + 编辑距离相似度
│   ├── test_models.py             # Pydantic 模型验证
│   ├── test_search_provider.py    # WebSearchProvider / WebContentProvider
│   ├── test_mcp_search_tools.py   # MCP 搜索工具分发
│   └── test_timed_search.py       # TimedSearchService 定时搜索
├── integration/                   # 集成测试 (6 个, 需网络/真实服务)
│   ├── test_crawl_pipeline.py     # 采集管道集成
│   ├── test_engine_lifecycle.py   # Engine 生命周期
│   ├── test_real_crawl.py         # @integration 真实 UAPI 采集 (429 跳过)
│   ├── test_real_llm.py           # @integration 真实 GLM-5.1 调用 (401 跳过)
│   ├── test_real_mqtt.py          # @integration 真实 MQTT 连接
│   └── test_uapi_real.py          # @integration 真实 UAPI API
└── e2e/                           # 端到端测试 (6 个文件)
    ├── test_cli_e2e.py            # CLI 命令端到端（version/init/doctor/config/memory/crawl）
    ├── test_cli_errors.py         # CLI 错误处理（缺参数/无效输入）
    ├── test_cli_advanced.py       # 高级 CLI（crawl-diff/dedup/monitor/track/dashboard/cross-analyze）
    ├── test_dashboard_api.py      # Dashboard Web API（FastAPI + 飞书 Handler + GitHub Trending）
    ├── test_env_precheck.py       # 环境预检（version/init/doctor/config/help）
    └── test_full_pipeline.py      # 全流程测试（Mock + 真实 API）
```

## 运行方式

```bash
uv run pytest                      # 全部测试 (471 passed)
uv run pytest tests/unit/          # 仅单元测试
uv run pytest tests/integration/   # 集成测试（需 API Key）
uv run pytest tests/e2e/           # E2E 测试（需完整环境）
uv run pytest -m integration       # 按 marker 筛选
```

## 测试标记

- `@pytest.mark.integration` — 集成测试（需要网络，真实 API 调用）
- `@pytest.mark.e2e` — 端到端测试（完整 CLI 流程）

## 配置

- `asyncio_mode = "auto"` (pyproject.toml) — 无需 `@pytest.mark.asyncio`
- `testpaths = ["tests"]`
- Mock 策略: HTTP 用 aioresponses, MQTT 用 mock, LLM 用 mock

## Fixtures (conftest.py)

| Fixture | 作用域 | 用途 |
|---------|--------|------|
| `tmp_db` | function | 临时 SQLite 数据库路径 |
| `tmp_workspace` | function | 临时工作空间目录 |
| `real_settings` | session | 从 configs/ 加载真实配置 |
| `skip_if_no_uapi` | — | UAPI API Key 未配置时跳过 |
| `skip_if_no_llm` | — | LLM API Key 未配置时跳过 |
| `skip_if_no_mqtt` | — | MQTT 未配置时跳过 |

## 统计

- 总文件: 50 个
- 总行数: ~6,484 行
- 测试用例: 471 个 (unit 350 + integration 38 + e2e 82)
- 覆盖范围: 所有 spide/ 子模块 + dashboard/ Web API
