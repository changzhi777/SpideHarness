# Dashboard Web 应用 + 飞书智能体

> [根目录](../CLAUDE.md) → `dashboard/`

最后更新：2026-06-11

## 职责

FastAPI Web 后端，承载三大职能：

1. **Dashboard REST API** — 从 SQLite 读取热搜数据，前端单文件 SPA 渲染
2. **飞书智能体** — ReAct Agent（多轮记忆 + 工具调用）+ WebSocket 长连接接收消息 + 主动定时推送
3. **GitHub AI 热点采集** — 9 个查询（5 主题 + 4 trending）+ 飞书卡片格式化

## 文件清单（12 个 .py + 1 个 .html）

| 文件 | 行数 | 职责 |
|------|------|------|
| `api.py` | 695 | FastAPI 主应用 — Dashboard API + 采集触发 + GitHub 热点 + 飞书路由 + `lifespan` 启动 LLM/Agent/Scheduler/WS |
| `feishu_agent.py` | 280 | **ReAct Agent** — LLM + 工具循环（最多 5 轮）+ 多轮记忆 + 关键词降级 |
| `feishu_handler.py` | 477 | 飞书事件回调（HTTP Webhook + WebSocket 两种模式）+ 指令解析 + 子进程执行 |
| `feishu_ws_client.py` | 135 | **WebSocket 长连接** — `lark-oapi` SDK 主动出站连接，无需公网 URL |
| `feishu_card.py` | 187 | 飞书 Interactive Card v2 模板（text/error/topics_list/agent_response/daily_brief） |
| `tool_router.py` | 305 | **8 个 MCP 工具**异步路由 + CLI subprocess 兜底 + Function Calling schema |
| `capability_registry.py` | 195 | AI Agent 自发现协议（`/.well-known/agent.json`，单例） |
| `conversation_store.py` | 224 | SQLite 多轮记忆（`chat_sessions` + `chat_messages` 表） |
| `llm_client.py` | 253 | OpenAI 兼容客户端（vLLM/Ollama）+ JSON Action 兜底 + 启动健康检查 |
| `scheduler.py` | 268 | APScheduler 主动推送（cron 触发 → 工具调用 → 卡片渲染 → 飞书群推送） |
| `secrets.py` | 87 | `${ENV_VAR[:default]}` 占位符解析（避免密钥硬编码到 Git） |
| `github_trending.py` | 248 | GitHub AI 热点采集（9 查询 + 飞书卡片） |
| `index.html` | ~1000 | 前端 SPA（React 18 UMD + Tailwind CDN + Chart.js 4 + Inter 字体） |

**源码合计**：~3354 行 Python + ~1000 行 HTML

## 启动方式

```bash
# 启动 Dashboard + 飞书 WebSocket + 主动推送调度器（一体化）
uvicorn dashboard.api:app --reload --port 8765

# 仅启动主动推送（独立测试）
python -m dashboard.scheduler
```

访问 `http://localhost:8765/` 查看 Dashboard。

## 启动生命周期（`api.py:lifespan`）

```
1. 加载 configs/feishu.yaml → 解析 ${ENV_VAR} 占位符
2. 初始化 LLMClient（OpenAI 兼容端点）+ health_check
3. 注入飞书凭证到 feishu_handler（set_feishu_config）
4. 启动 FeishuPushScheduler（cron jobs，需 app_secret）
5. 启动飞书 WebSocket 长连接（init_ws_client + register_message_handler + 独立线程）
6. 服务就绪 — 同一端口同时提供 HTTP + WS + Dashboard
```

## 技术栈

### 后端
- **FastAPI** + **uvicorn** — Web 框架
- **aiohttp** — GitHub API + 飞书 REST API
- **lark-oapi** ≥ 1.6 — 飞书官方 SDK（WebSocket 长连接 + 消息发送）
- **apscheduler** ≥ 3.10 — 定时推送调度器
- **aiosqlite** — 异步多轮记忆存储
- **sqlite3**（标准库）— Dashboard 数据读取
- **subprocess** — 调用 `python -m spide <cmd>` CLI 兜底

### LLM
- **OpenAI 兼容协议** — 支持 vLLM / Ollama / LM Studio 等本地服务
- 默认模型 `gemma-4-e4b-it-4bit`（MLX 4-bit 量化，~0.15 token/s）
- **弱模型适配** — `supports_function_calling=false` 时启用 JSON Action 提示词兜底

### 前端
- **React 18** UMD（CDN 加载，无构建步骤）
- **Tailwind CSS**（CDN JIT）
- **Chart.js 4** — 平台分布柱状图 + 分类饼图
- **Inter** 字体（Google Fonts）
- **设计语言**：深色主题（`#0f181f` 渐变背景 + 绿色点缀）

## API 端点

### Dashboard 数据（`api.py`）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard` | GET | Dashboard 全量数据（平台统计/Top 话题/分类/趋势） |
| `/api/topics` | GET | 话题列表（支持分页/筛选） |
| `/api/sources` | GET | 所有数据源平台 |
| `/api/crawl` | POST | 触发全量热搜采集 |
| `/.well-known/agent.json` | GET | **AI Agent 自发现** — MCP/HTTP/Skills 能力清单 |
| `/` | GET | 前端页面（注入 `__DASHBOARD_DATA__`） |

### 飞书 Bot（`feishu_handler.py`）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/feishu/event` | GET/POST | 飞书 HTTP Webhook 回调（兼容模式 — 需公网 URL） |
| `/api/feishu/command` | POST | 通用命令执行接口（`text` 自动解析 或 `command` 直接指定） |

> **推荐模式**：WebSocket 长连接（无需公网 URL）。HTTP Webhook 作为兜底兼容方案。

### GitHub 热点（`github_trending.py`）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/github/trending` | GET | 获取 GitHub AI 热点仓库 |
| `/api/github/push` | POST | 采集 GitHub 热点并推送到飞书 |
| `/api/github/webhook` | POST | 设置飞书 Webhook URL |

## 飞书智能体架构（核心特性 V3.1.1+）

### 消息处理双路径（`feishu_handler._process_and_reply`）

```
飞书消息
  ├─ 命中 _COMMAND_RE (crawl|analyze|status|track|export|help|batch) → 关键词路径
  │     ↓ parse_command → execute_command → 子进程调用 spide CLI
  │     ↓ send_message 回复纯文本
  └─ 非指令（自然语言） → Agent 路径
        ↓ get_feishu_agent().chat()
        ↓ ReAct 循环：LLM → 工具调用 → 持久化 → 回 LLM
        ↓ 渲染 agent_response_card → send_message 推送卡片
```

### ReAct Agent（`feishu_agent.FeishuAgent`）

**循环流程**：
1. 加载会话历史（最近 20 条）
2. 拼接 `system_prompt + history + user_message`
3. 调用 LLM（带 tools 或 JSON Action 兜底）
4. 若返回 tool_calls：执行工具 → 追加结果 → 回 LLM（最多 `max_iterations=5` 次）
5. 返回 `AgentResult{answer, tool_calls, iterations, status}`

**关键设计**：
- **多轮记忆** — `ConversationStore` SQLite 持久化（`session_id = chat_id:user_id` 稳定归一）
- **超时保护** — 单次工具调用 `step_timeout=30s`
- **防死循环** — `max_iterations=5` 上限
- **降级策略** — LLM 不可用时调用 `_fallback_keyword()` 走指令路径
- **拟人化 UI** — `_short_task_id()`（call_id 后 3 位）+ `_friendly_action()`（人类可读动作描述）
- **完整追踪** — `tool_calls` 字段保留完整 call_id（数据库层）

### 8 个工具路由（`tool_router._TOOL_ROUTES`）

| 工具名 | 实现方式 | 用途 |
|--------|---------|------|
| `crawl_hot_topics` | 复用 `UAPIClient`（CLI 兜底） | 热搜采集 |
| `web_search` | 复用 `LLMClient.web_search`（智谱） | 联网搜索 |
| `web_search_enhanced` | 复用 `WebSearchProvider`（DuckDuckGo） | 增强搜索 |
| `fetch_web_page` | 复用 `WebContentProvider.fetch_page` | 网页抓取 |
| `fetch_repo_info` | 复用 `RepoInfoProvider`（+ README 模式） | GitHub 仓库信息 |
| `manage_memory` | 复用 `spide.memory` | 记忆 CRUD |
| `health_check` | 直接返回平台信息 | 健康检查 |
| `deep_crawl_hot_topics` | subprocess（避免 Playwright 阻塞事件循环） | 深度采集 |

**统一入口**：`call_tool(name, arguments, timeout=60)` — `asyncio.wait_for` 包装超时。

### 多轮记忆（`conversation_store.ConversationStore`）

**表结构**：
- `chat_sessions(session_id PK, user_id, chat_id, created_at, updated_at, metadata)`
- `chat_messages(id PK, session_id FK, role, content, tool_calls, tool_call_id, name, created_at)`
- 索引：`idx_messages_session(session_id, created_at)` + `idx_sessions_user(user_id, chat_id)`

**API**：
- `get_or_create_session(user_id, chat_id)` — `session_id = f"{chat_id}:{user_id}"`（同用户同群归一）
- `append_message(session_id, ChatMessage)` — 追加 + 更新 `updated_at`
- `get_history(session_id, limit=20)` — 按时间正序返回 OpenAI 格式消息
- `clear_session(session_id)` — 清空历史（保留 session 元信息）

### 飞书富文本卡片（`feishu_card.py`）

| 函数 | 用途 |
|------|------|
| `text_card(title, content, template)` | 纯文本卡片 |
| `error_card(title, error)` | 错误提示（红色 template） |
| `topics_list_card(title, source, items)` | 热搜列表（带排名/热度/链接） |
| `agent_response_card(answer, tool_calls, iterations)` | **Agent 响应卡片**（拟人化，隐藏机械标识） |
| `daily_brief_card(title, sections)` | 每日简报（多 section） |

**品牌化**：所有卡片底部统一脚注 `青沐信息官 · SpideHarness V3.1.1 | YYYY-MM-DD HH:MM:SS`。

### 主动推送调度器（`scheduler.FeishuPushScheduler`）

**配置加载**：`configs/feishu.yaml:scheduler.jobs` → `JobSpec(name, cron, action, params, push_card, target_chat_id)`

**Job 执行流程**：
1. APScheduler `AsyncIOScheduler` 按 cron 触发（时区 `Asia/Shanghai`）
2. 调用 `call_tool(job.action, job.params, timeout=120)`
3. `_render_card(job, result)` 根据工具类型选模板
4. `push_card(chat_id, card)` — 携 `tenant_access_token`（带缓存，提前 5 分钟续期）

**默认 Job**（`configs/feishu.yaml`）：
- `daily_morning_brief` — `0 9 * * *` 采集微博热搜 → 推送
- `daily_evening_brief` — `0 18 * * *` 采集微博热搜 → 推送

### 敏感信息保护（`secrets.py`）

支持 `${ENV_VAR}` / `${ENV_VAR:default}` 占位符，加载时从环境变量注入：

```yaml
feishu:
  app_id: cli_a976c6aaaa7adcbb
  app_secret: ${SPIDE_FEISHU__APP_SECRET}              # 必填，缺失抛 SecretError
  encrypt_key: ${SPIDE_FEISHU__ENCRYPT_KEY:}           # 选填，默认空字符串
```

- `resolve_secrets(value)` — 字符串解析
- `resolve_secrets_in_obj(obj)` — 递归 dict/list/str
- `required_env(name)` — 必需变量（缺失抛 `SecretError`）

### AI Agent 自发现（`capability_registry.py`）

单例 `CapabilityRegistry`，三个核心方法：`register_mcp_tool` / `register_http_endpoint` / `register_skill`。

**输出**（`GET /.well-known/agent.json`）— OpenAPI Discovery 风格：
```json
{
  "$schema": ".../agent-discovery-v1.json",
  "agent": {"name": "SpideHarness Agent", "version": "3.1.1", "description": "..."},
  "capabilities": {
    "mcp": {"transport": ["stdio", "sse"], "command": "spide mcp-serve", "tools": [...]},
    "http": {"base_url": "", "endpoints": [...]},
    "skills": [...]
  },
  "discovery": {"docs": "docs/integration/INTEGRATION.md", ...}
}
```

## 飞书 WebSocket 长连接（V3.1.2+，`feishu_ws_client.py`）

**优势**：替换 HTTP Webhook 模式，**无需公网 URL / Cloudflare Tunnel**。服务端主动发起出站 WebSocket 连接到飞书服务器接收事件。

**API**：
| 函数 | 用途 |
|------|------|
| `init_ws_client(app_id, app_secret, log_level)` | 初始化 API 客户端（用于 `send_message`） |
| `register_message_handler(handler)` | 注册 `P2ImMessageReceiveV1` 事件回调 |
| `start_ws_client(app_id, app_secret)` | 启动 WebSocket 长连接（**阻塞式**，需在独立线程调用） |
| `stop_ws_client()` | 停止连接 |
| `send_message(chat_id, text, msg_type)` | 通过 SDK 发送消息（返回 `{status, message_id?}`） |
| `reset_ws_client()` | 重置全局状态（测试用） |

**事件回调链**：`lark.ws.Client` → `on_feishu_message_event` → `_process_and_reply`（异步任务）→ 走双路径（指令 / Agent）→ `send_message` 推送。

## 飞书 Bot 指令解析（`feishu_handler`）

**指令正则**：`^(crawl|analyze|status|track|export|help|batch)\s*(.*)`（忽略大小写）

| 指令 | 格式 | 默认值 | CLI 调用 |
|------|------|--------|----------|
| `help` | `help` | — | 返回帮助文本 |
| `status` | `status` | — | 直接查 SQLite（话题数/平台数/最近采集） |
| `crawl` | `crawl <source\|all>` | `all` | `spide crawl --all --save` / `spide crawl -s <src> --save` |
| `analyze` | `analyze <source>` | `weibo` | `spide analyze -s <src>` (timeout 180s) |
| `track` | `track <source> [N]` | `weibo`, `N=10` | `spide track -s <src> --top <N>` (timeout 180s) |
| `export` | `export <source>` | `weibo` | `spide export -s <src> -f excel` (timeout 60s) |
| `batch` | `batch <p1,p2>` | `["xhs", "dy"]` | `spide batch-crawl -p <p1>,<p2>` (timeout 300s) |

**子进程执行**：`_run_spide_sync()` 用 `subprocess.run([sys.executable, "-m", "spide"] + args, cwd=PROJECT_ROOT)`，通过 `loop.run_in_executor` 转异步避免阻塞事件循环。

**配置动态注入**：`set_feishu_config(app_id, app_secret, verification_token, encrypt_key)` 运行时设置全局变量，密钥支持 `${ENV_VAR}` 占位符。

## GitHub AI 热点采集（`github_trending.py`）

**5 主题查询**（TOPIC_QUERIES）— 按 `stars` 排序，每方向 5 条：
| 主题 | Query |
|------|-------|
| AI 人工智能 | `topic:ai+topic:agent&sort=stars&order=desc&per_page=5` |
| 大模型 LLM | `topic:llm+topic:large-language-model&sort=stars&order=desc&per_page=5` |
| Agent 智能体 | `topic:ai-agent&sort=stars&order=desc&per_page=5` |
| MCP 协议 | `topic:mcp+topic:model-context-protocol&sort=stars&order=desc&per_page=5` |
| MLX 苹果AI | `topic:mlx&sort=stars&order=desc&per_page=5` |

**4 备用查询**（TRENDING_QUERIES）— 最近 7 天高星新项目（`created:>2026-05-20`）。

**`collect()` 流程**：遍历 9 个查询 → 每个限制前 10 条 → 全局去重 → 按 `stars` 降序。

## 前端页面结构（`index.html`）

**单文件 SPA**（无构建）— 注入数据后 React.createElement 渲染。

| 组件 | 功能 |
|------|------|
| `Header` | 顶部导航（蜘蛛 logo + 标题 + v3.1.1 DEV 徽章 + 实时时钟） |
| `Clock` | 实时日期/时钟（每秒更新） |
| `StatsRow` | 4 张统计卡片（总话题/平台数/今日新增/平均热度） |
| `PlatformChart` | Chart.js 水平柱状图（平台分布） |
| `CategoryPie` | Chart.js 环形饼图（分类占比，中心显示分类数） |
| `RankingTable` | 热搜排行榜 Top 20（前 3 名金银铜配色） |
| `PlatformTop3Group` | 各平台 Top 3 卡片（左侧 3px 颜色条） |
| `EmptyState` | 空数据状态（提示运行 `spide crawl --all`） |
| `Footer` | 版权信息 |

**平台配色映射**（PLATFORM_MAP）：
- weibo `#E6162D` / baidu `#4E6EF2` / douyin `#FE2C55` / zhihu `#0066FF`
- bilibili `#00A1D6` / kuaishou `#FF8C00` / tieba `#4879BD`

## 依赖（`pyproject.toml`）

```
fastapi>=0.136.3    uvicorn>=0.44.0    aiohttp>=3.9
lark-oapi>=1.6      apscheduler>=3.10  aiosqlite>=0.20
structlog>=24.0     pyyaml>=6.0
```

### 前端 CDN
- React 18 UMD：`unpkg.com/react@18`
- ReactDOM 18 UMD：`unpkg.com/react-dom@18`
- Tailwind CSS：`cdn.tailwindcss.com`
- Chart.js 4：`cdn.jsdelivr.net/npm/chart.js@4`
- Inter 字体：`fonts.googleapis.com`

## 配置文件

`configs/feishu.yaml` — 飞书智能体全部配置：
- `feishu.*` — App ID/Secret（占位符）、WebSocket 启用、默认推送目标
- `llm.*` — OpenAI 兼容端点配置（`base_url`/`model`/`supports_function_calling`）
- `agent.*` — ReAct 循环参数（`max_iterations=5`/`max_history=20`/`step_timeout=30`）+ system_prompt
- `scheduler.*` — 主动推送 Job 列表（cron + action + params + target_chat_id）
- `storage.conversation_db` — 多轮记忆数据库路径（复用 `spide_data.db`）

## 测试覆盖（`tests/unit/`）

| 测试文件 | 覆盖模块 |
|---------|---------|
| `test_feishu_agent.py` | ReAct 循环 + 降级 + 多轮记忆 |
| `test_feishu_card.py` | 5 种卡片模板 |
| `test_feishu_ws.py` | WebSocket 客户端 + 事件回调 + 双路径处理 |
| `test_tool_router.py` | 8 工具路由 + 超时 + 兜底 |
| `test_scheduler.py` | APScheduler + token 缓存 + 卡片渲染 |
| `test_llm_client.py` | OpenAI 兼容协议 + JSON Action 兜底 |
| `test_secrets.py` | `${ENV_VAR}` 占位符解析 |
| `test_conversation_store.py` | SQLite 多轮记忆 CRUD |
| `test_dashboard_api.py`（e2e） | FastAPI 启动 + 全端点 |

## 注意

- 此目录独立于 `spide/dashboard/`（HTML 看板生成模块）
- 数据库路径：`../spide_data.db`（同时存储热搜 + 会话记忆）
- 飞书凭证通过 `set_feishu_config()` 动态设置（默认空字符串，不启用签名验证）
- 前端数据通过 `window.__DASHBOARD_DATA__` 在 HTML 渲染时注入（无运行时 API 调用）
- 9 个 GitHub 查询全部串行执行（无并发）
- **WebSocket 模式优先于 HTTP Webhook** — 部署在 PVE/无公网环境时无需 Cloudflare Tunnel
- 卡片模板统一 `template: "blue"`（飞书固定配色），错误用 `"red"`，空数据用 `"grey"`
