# 测试模块

> [根目录](../CLAUDE.md) → `tests/`

## 结构

```
tests/
├── conftest.py                    # 共享 fixtures
├── unit/                          # 单元测试 (22 个文件)
│   ├── test_analysis.py
│   ├── test_batch_scheduler.py
│   ├── test_broker.py
│   ├── test_config.py
│   ├── test_dashboard.py
│   ├── test_deep_crawl.py
│   ├── test_engine.py
│   ├── test_exceptions.py
│   ├── test_exporter.py
│   ├── test_fetcher.py
│   ├── test_llm.py
│   ├── test_mcp_server.py
│   ├── test_memory.py
│   ├── test_models.py
│   ├── test_mqtt_client.py
│   ├── test_pipeline.py
│   ├── test_prompts.py
│   ├── test_session_storage.py
│   ├── test_sqlite_repo.py
│   ├── test_task_scheduler.py
│   ├── test_uapi_client.py
│   ├── test_wordcloud.py
│   └── test_workspace.py
├── integration/                   # 集成测试 (需网络/真实服务)
│   ├── test_crawl_pipeline.py
│   ├── test_engine_lifecycle.py
│   ├── test_real_crawl.py         # @pytest.mark.integration
│   ├── test_real_llm.py           # @pytest.mark.integration
│   ├── test_real_mqtt.py          # @pytest.mark.integration
│   └── test_uapi_real.py          # @pytest.mark.integration
├── e2e/                           # 端到端测试
│   ├── test_cli_e2e.py
│   ├── test_cli_errors.py
│   ├── test_env_precheck.py
│   └── test_full_pipeline.py
├── test_iteration3.py             # 迭代 3 功能验证
├── test_iteration4.py             # 迭代 4 功能验证
└── test_storage.py                # 存储层测试
```

## 运行方式

```bash
uv run pytest                      # 全部测试
uv run pytest tests/unit/          # 仅单元测试
uv run pytest tests/integration/   # 集成测试（需 API Key）
uv run pytest tests/e2e/           # E2E 测试（需完整环境）
uv run pytest -m integration       # 按 marker 筛选
```

## 测试标记

- `@pytest.mark.integration` — 集成测试（需要网络，真实 API 调用）
- `@pytest.mark.e2e` — 端到端测试（完整 CLI 流程）

## 配置

- `asyncio_mode = "auto"` (pyproject.toml)
- `testpaths = ["tests"]`
- Mock 策略: HTTP 用 aioresponses, MQTT 用 mock

## 统计

- 总文件: 27 个
- 总行数: ~4950 行
- 覆盖范围: 所有 spide/ 子模块
