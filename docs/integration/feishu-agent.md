# 飞书智能体集成指南

> 适用版本：SpideHarness Agent V3.1.1+
> 集成时间：2026-06-10
> 受众：开发者 / 运维

## 概述

将 SpideHarness Agent 升级为**完整的飞书 AI 智能体**，使其在飞书群中可作为 LLM 驱动的 Agent 自主调用工具。

### 4 大能力

| 能力 | 说明 |
|------|------|
| **自然语言对话** | ReAct 循环：用户提问 → LLM 推理 → 调用 MCP 工具 → 返回富文本卡片 |
| **多轮上下文记忆** | SQLite 持久化（`chat_sessions` / `chat_messages`），跨会话保留 |
| **主动定时推送** | APScheduler cron 触发 → 执行工具 → 推送到飞书群 |
| **富文本卡片交互** | Interactive Message Card v2（蓝色 / 红色 / 灰色模板） |

### 架构图

```
                    ┌──────────────────────────┐
                    │  Feishu Tenant/Group    │
                    │   (@机器人 / webhook)    │
                    └────────────┬─────────────┘
                                 │ 飞书事件
                                 ↓
        ┌────────────────────────────────────────────┐
        │  dashboard/feishu_handler.py              │
        │  ├─ im.message.receive_v1                 │
        │  │   ├─ 命中指令格式 → execute_command     │
        │  │   └─ 自然语言 → FeishuAgent.chat       │
        │  └─ url_verification → challenge 回包      │
        └────────────┬───────────────────────────────┘
                     │
        ┌────────────↓───────────────────────────────┐
        │  FeishuAgent (dashboard/feishu_agent.py)  │
        │  ├─ LLMClient (OpenAI 兼容, 端口 8001)     │
        │  │   ├─ Function Calling                  │
        │  │   └─ JSON Action 兜底                  │
        │  ├─ ToolRouter (8 个 MCP 工具)             │
        │  │   ├─ crawl_hot_topics                  │
        │  │   ├─ web_search / web_search_enhanced  │
        │  │   ├─ fetch_web_page / fetch_repo_info  │
        │  │   ├─ manage_memory / health_check      │
        │  │   └─ deep_crawl_hot_topics             │
        │  └─ ConversationStore (SQLite)            │
        │      ├─ chat_sessions                     │
        │      └─ chat_messages                     │
        └────────────┬───────────────────────────────┘
                     │ 调用结果
                     ↓
        ┌────────────────────────────────────────────┐
        │  feishu_card.py 渲染富文本卡片              │
        │  ├─ text_card / error_card                │
        │  ├─ topics_list_card                      │
        │  ├─ agent_response_card                   │
        │  └─ daily_brief_card                      │
        └────────────────────────────────────────────┘
```

## 快速开始

### 前置条件

1. **本地 LLM 服务**（OpenAI 兼容）
   - 默认：`http://localhost:8001`（vLLM / Ollama / llama.cpp 均可）
   - 模型示例：Google Gemma 3 4B IT（4-bit 量化）

2. **飞书企业自建应用**
   - App ID：`cli_a976c6aaaa7adcbb`（已配置）
   - App Secret：待补充（无 secret 也能运行 webhook 模式）
   - 应用权限：`im:message:receive_v1`（接收消息）+ `im:message:send`（主动推送）
   - 事件订阅：`im.message.receive_v1`
   - 机器人能力：启用"接收消息"

3. **公网回调地址**（HTTPS）
   - 用 nginx + Let's Encrypt 反向代理
   - URL 示例：`https://<your-domain>/api/feishu/event`

### 启动服务

```bash
# 1. 安装依赖
uv sync

# 2. 配置飞书凭证（可选，无 secret 也能运行）
export FEISHU_APP_ID="cli_a976c6aaaa7adcbb"
export FEISHU_APP_SECRET=""  # 留空 → 仅 webhook 模式
export FEISHU_VERIFICATION_TOKEN=""
export FEISHU_ENCRYPT_KEY=""

# 3. 启动 Dashboard Web（含飞书 Agent）
uvicorn dashboard.api:app --host 0.0.0.0 --port 8765

# 4. 验证 Agent 状态
curl http://localhost:8765/api/feishu/agent/status
```

### 配置说明（configs/feishu.yaml）

```yaml
feishu:
  app_id: cli_a976c6aaaa7adcbb
  app_secret: ""                       # 留空 → 主动推送禁用
  default_chat_id: ""                  # 主动推送目标

llm:
  base_url: http://localhost:8001      # OpenAI 兼容端点
  model: google/gemma-3-4b-it
  api_key: EMPTY                       # 本地服务通常无鉴权
  supports_function_calling: false     # Gemma 3 4B 弱 → JSON Action 兜底

agent:
  max_iterations: 5                    # ReAct 最大迭代次数
  max_history: 20                      # 多轮记忆窗口
  step_timeout: 30                     # 单工具调用超时（秒）

scheduler:
  enabled: true                        # 主动推送总开关
  jobs:
    - name: daily_morning_brief
      cron: "0 9 * * *"                # 每日 09:00
      action: crawl_hot_topics
      params: {source: weibo, limit: 10}
      push_card: true
```

## API 端点

### 1. 智能体对话

```bash
POST /api/feishu/agent
Content-Type: application/json

{
  "user_id": "u_123",
  "chat_id": "oc_456",
  "message": "今天微博上有哪些热门 AI 话题？"
}
```

**返回**：
```json
{
  "answer": "已采集微博热搜 Top 10...",
  "iterations": 2,
  "tool_calls": [
    {"name": "crawl_hot_topics", "arguments": {"source": "weibo"}, "summary": "ok: count=10"}
  ],
  "status": "ok",
  "error": null
}
```

**status 枚举**：
- `ok` — 正常返回
- `error` — LLM 错误
- `max_iter` — 达到最大迭代次数
- `llm_down` — LLM 不可用，已降级

### 2. 清空会话

```bash
POST /api/feishu/agent/clear
Content-Type: application/json

{"user_id": "u_123", "chat_id": "oc_456"}
```

### 3. 健康检查

```bash
GET /api/feishu/agent/status
```

**返回**：
```json
{
  "llm_healthy": true,
  "llm_config": {
    "base_url": "http://localhost:8001",
    "model": "gemma-3-4b-it",
    "supports_function_calling": false
  },
  "tools_available": [
    "crawl_hot_topics", "web_search", "web_search_enhanced",
    "fetch_web_page", "fetch_repo_info", "manage_memory",
    "health_check", "deep_crawl_hot_topics"
  ],
  "scheduler_configured": false
}
```

### 4. 主动推送调度器

```bash
# 启动（按 configs/feishu.yaml 中 cron jobs）
POST /api/feishu/scheduler/start

# 停止
POST /api/feishu/scheduler/stop
```

> ⚠️ 需要在 `configs/feishu.yaml` 中配置 `app_secret` 才能启用。

## 数据库结构

智能体使用 `spide_data.db` 复用主数据库，新增 2 张表：

```sql
-- 会话元信息
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,    -- "{chat_id}:{user_id}"
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    metadata TEXT                   -- JSON
);

-- 消息历史
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,             -- system/user/assistant/tool
    content TEXT NOT NULL,
    tool_calls TEXT,                -- JSON
    tool_call_id TEXT,
    name TEXT,                      -- 工具名（role=tool 时）
    created_at REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);
```

## 故障排除

| 现象 | 原因 | 解决 |
|------|------|------|
| `llm_healthy: false` | LLM 服务未启动 / 端口不通 | `curl http://localhost:8001/v1/models` |
| Agent 一直返回 `llm_down` | LLM 健康检查失败 | 检查 `configs/feishu.yaml` 中 `base_url` |
| 工具调用超时 | LLM 推理慢 / 工具实现慢 | 调大 `agent.step_timeout` |
| 多轮记忆失效 | SQLite 写入失败 | 检查 `spide_data.db` 权限 |
| 主动推送 403 | app_secret 缺失 | 填入后重启服务 |
| 飞书卡片 400 | 字段缺失 | 检查 `feishu_card.py` 模板完整性 |
| 事件回调签名失败 | token 不匹配 | 配置 `FEISHU_VERIFICATION_TOKEN` |

## 测试覆盖

- 53 个新增单元测试（`tests/unit/test_*`）
- 覆盖：LLM 客户端、会话存储、卡片模板、工具路由、Agent ReAct 循环、调度器

```bash
uv run pytest tests/unit/test_llm_client.py \
                tests/unit/test_conversation_store.py \
                tests/unit/test_feishu_card.py \
                tests/unit/test_tool_router.py \
                tests/unit/test_feishu_agent.py \
                tests/unit/test_scheduler.py
```

## 相关文件

| 文件 | 职责 |
|------|------|
| `dashboard/feishu_handler.py` | 飞书事件回调（指令 + Agent 路由） |
| `dashboard/feishu_agent.py` | ReAct 循环 Agent 核心 |
| `dashboard/llm_client.py` | OpenAI 兼容 LLM 客户端 |
| `dashboard/conversation_store.py` | SQLite 多轮记忆 |
| `dashboard/tool_router.py` | 8 个 MCP 工具本地路由 |
| `dashboard/feishu_card.py` | 飞书富文本卡片模板 |
| `dashboard/scheduler.py` | APScheduler 主动推送 |
| `configs/feishu.yaml` | 飞书 + LLM 配置 |
| `skills/spide-feishu/SKILL.md` | 飞书 Bot 技能说明 |
| `docs/integration/INTEGRATION.md` | 集成总入口 |
