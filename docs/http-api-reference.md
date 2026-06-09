# SpideHarness Agent — HTTP REST API 对接文档

> 版本: V3.1.1 | 协议: HTTP/1.1 + JSON | 更新: 2026-06-09
> **Base URL**: `http://<host>:8765`（默认端口 8765）

本文档面向第三方程序/Agent，说明如何通过 HTTP REST API 对接 SpideHarness Agent。

> **快速发现**：AI Agent 可访问 `GET /.well-known/agent.json` 一次性获取所有能力清单（见 [INTEGRATION.md](./integration/INTEGRATION.md) 第 4 节）。

---

## 1. 概述

SpideHarness Agent 提供 **FastAPI 后端**，从 SQLite 数据库读取热搜数据并提供 10 个端点：

| 类别 | 端点数 | 鉴权 |
|------|--------|------|
| Dashboard 数据 | 3 | 无 |
| 采集触发 | 1 | 无（依赖子进程） |
| GitHub 热点 | 3 | 无 |
| 飞书 Bot | 2 | 飞书签名（可选） |
| AI 自发现 | 1 | 无 |

### Content-Type
所有请求/响应均为 `application/json; charset=utf-8`。

### CORS
默认无 CORS 限制（本地部署）。如部署到公网建议添加 nginx 反代并配置 CORS 头。

---

## 2. 快速开始

### 2.1 启动服务

```bash
# 默认端口 8765
uvicorn dashboard.api:app --host 0.0.0.0 --port 8765

# 开发模式（自动重载）
uvicorn dashboard.api:app --reload --port 8765
```

### 2.2 第一个请求

```bash
# 获取 Dashboard 全量数据
curl http://localhost:8765/api/dashboard

# 触发热搜采集
curl -X POST http://localhost:8765/api/crawl

# AI 自发现（推荐入口）
curl http://localhost:8765/.well-known/agent.json | jq
```

### 2.3 健康检查

```bash
curl -I http://localhost:8765/api/dashboard
# HTTP/1.1 200 OK
```

---

## 3. 鉴权

| 端点 | 鉴权方式 |
|------|----------|
| `/.well-known/agent.json` | 无 |
| `/api/dashboard` `/api/topics` `/api/sources` | 无 |
| `/api/crawl` | 无（依赖子进程；UAPI Key 在 `configs/uapi.yaml`） |
| `/api/github/*` | 无（GitHub API 有匿名速率限制） |
| `/api/feishu/event` | 飞书签名验证（通过 `set_feishu_config()` 注入 `_FEISHU_VERIFICATION_TOKEN`） |
| `/api/feishu/command` | 无（生产环境建议加 IP 白名单或 API Key） |

> **生产部署**：建议在 nginx 层添加基础认证（Basic Auth）或 IP 白名单。

---

## 4. 端点参考

### 4.1 `GET /.well-known/agent.json`

**AI Agent 自发现端点** — 单一端点返回所有 MCP / HTTP / Skills 能力清单。

**响应**（200）：
```json
{
  "$schema": "https://spide-agent.example/schemas/agent-discovery-v1.json",
  "agent": {
    "name": "SpideHarness Agent",
    "version": "3.1.1",
    "description": "热点新闻信息抓取与智能整理 Agent"
  },
  "capabilities": {
    "mcp": {
      "transport": ["stdio", "sse"],
      "command": "spide mcp-serve",
      "tools": [/* 8 个 MCP 工具完整定义 */]
    },
    "http": {
      "base_url": "http://localhost:8765",
      "endpoints": [/* 10 个 HTTP 端点 */]
    },
    "skills": [/* 14 个 Skills 索引 */]
  },
  "discovery": {
    "docs": "docs/integration/INTEGRATION.md",
    "mcp_reference": "docs/mcp-api-reference.md",
    "http_reference": "docs/http-api-reference.md",
    "skills_index": "skills/README.md"
  }
}
```

### 4.2 `GET /api/dashboard`

**获取 Dashboard 全量数据**（前端用）。

**响应**（200）：
```json
{
  "total_count": 1367,
  "platform_stats": [
    {"source": "bilibili", "label": "B站", "count": 320, "color": "#00A1D6"},
    {"source": "weibo", "label": "微博", "count": 232, "color": "#E6162D"}
  ],
  "top_topics": [
    {
      "rank": 1, "title": "...", "source": "douyin",
      "source_label": "抖音", "hot_value": 12104222,
      "url": "https://...", "fetched_at": "2026-04-13T17:19:10.704382"
    }
  ],
  "category_stats": [],
  "platform_ranks": {"weibo": [...], "douyin": [...]},
  "latest_fetch": "2026-04-27T15:22:16.490030",
  "stats_summary": {
    "total": 1367, "platforms": 7,
    "today_count": 0, "avg_hot_value": 4191442
  }
}
```

### 4.3 `GET /api/topics`

**获取话题列表**（分页/筛选）。

**Query 参数**：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `source` | str | — | 平台标识（weibo/baidu/...） |
| `limit` | int | 50 | 返回数量 |
| `offset` | int | 0 | 偏移量 |

**响应**（200）：
```json
{
  "total": 1367,
  "items": [
    {"id": 1, "title": "...", "source": "weibo", "hot_value": 99999, ...}
  ],
  "limit": 50,
  "offset": 0
}
```

### 4.4 `GET /api/sources`

**获取所有数据源平台**。

**响应**（200）：
```json
{
  "sources": [
    {"source": "weibo", "label": "微博", "color": "#E6162D", "count": 232, "latest_fetch": "..."}
  ]
}
```

### 4.5 `POST /api/crawl`

**触发全量热搜采集**（同步执行 `spide crawl --all --save`，超时 120s）。

**请求体**：无

**响应**（200）：
```json
{
  "status": "ok",
  "saved": 250,
  "output": "✓ 已保存 250 条记录\n..."
}
```

**错误**（504 超时 / 500 子进程错误）：
```json
{"status": "error", "message": "crawl timeout (>120s)"}
```

### 4.6 `GET /api/github/trending`

**获取 GitHub AI 热点仓库**。

**响应**（200）：
```json
{
  "total": 50,
  "repos": [
    {
      "full_name": "anthropics/claude-code",
      "description": "...",
      "stars": 12345, "forks": 678,
      "language": "TypeScript",
      "html_url": "https://github.com/...",
      "topics": ["ai", "claude"],
      "updated_at": "2026-05-20",
      "category": "AI 人工智能"
    }
  ]
}
```

### 4.7 `POST /api/github/push`

**一键采集 GitHub 热点并推送到飞书**。

**前提**：必须先调用 `/api/github/webhook` 设置飞书 Webhook URL。

**请求体**：无

**响应**（200）：
```json
{
  "total_repos": 50,
  "pushed_to_feishu": true,
  "repos": [/* 前 20 个仓库 */]
}
```

### 4.8 `POST /api/github/webhook`

**设置飞书 Webhook URL**（运行时动态注入）。

**请求体**：
```json
{"url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"}
```

**响应**（200）：
```json
{"status": "ok", "url_set": true}
```

**错误**（400）：
```json
{"error": "url is required"}
```

### 4.9 `POST /api/feishu/event`

**飞书事件回调**（URL 验证 + 消息接收）。

**请求体**（URL 验证）：
```json
{"type": "url_verification", "challenge": "xxx", "token": "yyy"}
```

**响应**（200）：
```json
{"challenge": "xxx"}
```

**请求体**（消息事件）：
```json
{
  "schema": "2.0",
  "header": {"event_type": "im.message.receive_v1"},
  "event": {
    "sender": {"sender_id": {"open_id": "..."}},
    "message": {
      "message_type": "text",
      "content": "{\"text\": \"crawl weibo\"}"
    }
  }
}
```

**响应**（200）：执行结果 JSON。

支持的指令：`crawl` / `analyze` / `status` / `track` / `export` / `batch` / `help`（详见 `dashboard/feishu_handler.py`）。

### 4.10 `POST /api/feishu/command`

**通用命令执行接口**（供飞书 Agent 或其他客户端调用）。

**请求体**（text 自动解析）：
```json
{"text": "crawl weibo"}
```

**请求体**（直接指定）：
```json
{"command": "crawl", "args": {"source": "weibo"}}
```

**响应**（200）：命令执行结果。

**错误**（400）：
```json
{"status": "error", "message": "需要 'text' 或 'command' 字段"}
```

---

## 5. 错误码

| 状态码 | 含义 | 触发条件 |
|--------|------|----------|
| 200 | 成功 | — |
| 400 | 请求错误 | 缺参数 / 字段类型错误 |
| 403 | 禁止访问 | 飞书签名验证失败 |
| 404 | 端点不存在 | 路径错误 |
| 500 | 服务器错误 | 子进程崩溃 / 未捕获异常 |
| 504 | 网关超时 | `POST /api/crawl` 超 120s |

**错误响应结构**：
```json
{"status": "error", "message": "...", "traceback": "..."}
```

---

## 6. Python SDK 示例

使用 `httpx` 异步客户端：

```python
import httpx

BASE_URL = "http://localhost:8765"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=130.0) as client:
        # 1. AI 自发现
        agent = (await client.get("/.well-known/agent.json")).json()
        print(f"Available MCP tools: {len(agent['capabilities']['mcp']['tools'])}")

        # 2. 触发采集
        result = (await client.post("/api/crawl")).json()
        print(f"Crawl result: {result['saved']} topics saved")

        # 3. 获取 Top 10 微博热搜
        topics = (await client.get("/api/topics", params={"source": "weibo", "limit": 10})).json()
        for t in topics["items"]:
            print(f"  [{t['source']}] {t['title']} (热度: {t['hot_value']:,})")

        # 4. 设置飞书 Webhook + 推送 GitHub 热点
        await client.post("/api/github/webhook", json={"url": "https://open.feishu.cn/..."})
        push_result = (await client.post("/api/github/push")).json()
        print(f"Pushed {push_result['total_repos']} repos to Feishu")

asyncio.run(main())
```

---

## 7. JavaScript SDK 示例

使用 `fetch`：

```javascript
const BASE_URL = "http://localhost:8765";

// 1. AI 自发现
const agent = await fetch(`${BASE_URL}/.well-known/agent.json`).then(r => r.json());
console.log(`Available MCP tools: ${agent.capabilities.mcp.tools.length}`);

// 2. 触发采集
const crawlResult = await fetch(`${BASE_URL}/api/crawl`, { method: "POST" }).then(r => r.json());
console.log(`Crawl result: ${crawlResult.saved} topics saved`);

// 3. 获取话题列表
const topics = await fetch(`${BASE_URL}/api/topics?source=weibo&limit=10`).then(r => r.json());
topics.items.forEach(t => console.log(`  [${t.source}] ${t.title} (热度: ${t.hot_value.toLocaleString()})`));

// 4. 设置飞书 Webhook
await fetch(`${BASE_URL}/api/github/webhook`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ url: "https://open.feishu.cn/..." })
});
```

---

## 8. 速率限制

当前版本**无内置速率限制**（依赖底层 UAPI / GitHub API 的限制）。

| 底层 API | 限制 |
|----------|------|
| UAPI 热搜 | 平台限制（通常 60 req/min） |
| GitHub API | 未认证 60 req/h / 认证 5000 req/h |
| 飞书 Webhook | 100 req/min |

> 生产环境建议在 nginx 层添加速率限制（`limit_req_zone`）。

---

## 9. 部署清单

- [ ] 修改默认端口（避免 8765 冲突）
- [ ] 配置 UAPI Key（`configs/uapi.yaml`）
- [ ] 配置 LLM Key（`configs/llm.yaml`）
- [ ] 配置飞书 Webhook URL（运行时 `/api/github/webhook`）
- [ ] 设置工作空间（`spide init`）
- [ ] 配置 nginx 反代（生产环境）
- [ ] 启用 HTTPS（Let's Encrypt）

---

## 10. 相关文档

- [INTEGRATION.md](./integration/INTEGRATION.md) — 三视角综合集成（开发者/终端用户/AI Agent）
- [mcp-api-reference.md](./mcp-api-reference.md) — MCP 协议对接文档
- [CLAUDE.md](../CLAUDE.md) — 项目主文档
- [dashboard/CLAUDE.md](../dashboard/CLAUDE.md) — Dashboard 模块文档
