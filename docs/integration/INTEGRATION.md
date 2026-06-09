# SpideHarness Agent — 集成手册（INTEGRATION）

> 版本: V3.1.1 | 更新: 2026-06-09 | 受众: 开发者 + 终端用户 + AI Agent

本文档是 **SpideHarness Agent 集成的中央入口**，面向三类受众提供差异化集成路径。新用户**必读 §1 快速开始**，再按身份选择对应章节。

---

## 目录

- [1. 快速开始（5 分钟）](#1-快速开始5-分钟)
- [2. 你是谁？— 集成路径决策树](#2-你是谁集成路径决策树)
- [3. 开发者视角](#3-开发者视角)
- [4. 终端用户视角](#4-终端用户视角)
- [5. AI Agent 视角](#5-ai-agent-视角)
- [6. 5 个集成场景（端到端示例）](#6-5-个集成场景端到端示例)
- [7. 故障排除速查](#7-故障排除速查)
- [8. 文档索引](#8-文档索引)
- [9. API 版本与变更日志](#9-api-版本与变更日志)

---

## 1. 快速开始（5 分钟）

### 1.1 一句话介绍

**SpideHarness Agent** 是一个**可被其他 Agent 自动发现和调用**的热点新闻数据后端。它同时提供 4 种集成方式，让任何 AI 客户端、桌面应用、HTTP 客户端都能以**最低成本**接入：

| 集成方式 | 适合谁 | 学习成本 | 数据格式 |
|----------|--------|----------|----------|
| **Auto-Config API** | AI Agent | 1 分钟 | 单一 JSON 端点 |
| **MCP JSON-RPC** | Claude Desktop / Cursor / Cline | 5 分钟 | JSON-RPC 2.0 |
| **HTTP REST** | Web 前端 / 第三方系统 | 5 分钟 | JSON over HTTP |
| **AI Skills** | Claude / GPT 等对话式 AI | 0 分钟 | 自然语言 |

### 1.2 三步启动

```bash
# 1. 克隆与安装
git clone https://gitea.example.com/iotchange/Spide_agent.git
cd Spide_agent && uv sync

# 2. 初始化 + 配置 API Key
spide init
# 按提示编辑 configs/uapi.yaml 和 configs/llm.yaml

# 3. 启动服务（任选其一）
spide mcp-serve                 # MCP 模式（供 Claude Desktop 等客户端）
# 或
uvicorn dashboard.api:app --port 8765   # HTTP 模式（供 Web/Agent）
```

### 1.3 验证集成

```bash
# 验证 MCP Server
spide doctor
# 期望: ✓ MCP Server 启动正常

# 验证 HTTP API
curl http://localhost:8765/api/dashboard | jq .total_count

# 验证 Auto-Discovery
curl http://localhost:8765/.well-known/agent.json | jq .agent.name
# 期望: "SpideHarness Agent"
```

✅ **完成！** 你已经准备好集成 SpideHarness Agent 了。

---

## 2. 你是谁？— 集成路径决策树

```
你是谁？
  │
  ├─ 🤖 AI Agent（程序化发现与调用）
  │   └─→ §5 AI Agent 视角（5 分钟）
  │       └─ GET /.well-known/agent.json
  │
  ├─ 👨‍💻 开发者（构建 Web/移动/桌面应用）
  │   └─→ §3 开发者视角
  │       ├─ A. HTTP REST API → docs/http-api-reference.md
  │       └─ B. MCP JSON-RPC → docs/mcp-api-reference.md
  │
  └─ 🧑‍💼 终端用户（想在 Claude Desktop / Cursor 中用）
      └─→ §4 终端用户视角
          └─ docs/integration/claude-desktop-config.md
```

---

## 3. 开发者视角

### 3.1 HTTP REST API（推荐起点）

**适用**：Web 前端、移动 App、第三方系统、自动化脚本。

**Base URL**：`http://<host>:8765`

**核心端点**（10 个）：

| 端点 | 方法 | 用途 |
|------|------|------|
| `/.well-known/agent.json` | GET | AI Agent 自发现（推荐入口） |
| `/api/dashboard` | GET | Dashboard 全量数据 |
| `/api/topics` | GET | 话题列表（分页/筛选） |
| `/api/sources` | GET | 数据源平台 |
| `/api/crawl` | POST | 触发全量采集 |
| `/api/github/trending` | GET | GitHub AI 热点 |
| `/api/github/push` | POST | GitHub 热点 → 飞书 |
| `/api/github/webhook` | POST | 设置飞书 Webhook |
| `/api/feishu/event` | POST | 飞书事件回调 |
| `/api/feishu/command` | POST | 飞书通用命令 |

**5 行快速集成**：

```python
import httpx

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8765") as c:
        # 1. 自发现
        agent = (await c.get("/.well-known/agent.json")).json()
        # 2. 触发采集
        result = (await c.post("/api/crawl")).json()
        # 3. 获取 Top 10
        topics = (await c.get("/api/topics", params={"source": "weibo", "limit": 10})).json()
        for t in topics["items"]:
            print(f"[{t['source']}] {t['title']} ({t['hot_value']:,})")

asyncio.run(main())
```

📖 **完整参考**：[docs/http-api-reference.md](../http-api-reference.md)（871 行）

### 3.2 MCP JSON-RPC（适合 AI 客户端）

**适用**：Claude Desktop、Cursor、Cline、Continue 等支持 MCP 协议的 AI 客户端。

**8 个工具**：

| 工具 | 认证 | 用途 |
|------|------|------|
| `crawl_hot_topics` | UAPI Key | 热搜采集 |
| `web_search` | 智谱 API Key | 智谱联网搜索 |
| `web_search_enhanced` | 免认证 | DuckDuckGo/智谱搜索 |
| `fetch_web_page` | 免认证 | 网页内容抓取 |
| `fetch_repo_info` | 免认证 | GitHub 仓库信息 |
| `manage_memory` | 免认证 | 记忆管理 |
| `health_check` | 免认证 | 健康检查 |
| `deep_crawl_hot_topics` | 免认证 | 深度采集（7 平台） |

**配置示例**（`claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"]
    }
  }
}
```

📖 **完整参考**：[docs/mcp-api-reference.md](../mcp-api-reference.md)（含 SSE 规划、JSON-RPC 错误码、故障排除 FAQ）

### 3.3 SDK 选择

| 语言 | HTTP 客户端 | MCP 客户端 |
|------|-------------|------------|
| **Python** | `httpx` / `aiohttp` | `spide.mcp.client.MCPClient` |
| **JavaScript** | `fetch` / `axios` | `@modelcontextprotocol/sdk` |
| **Go** | `net/http` | `github.com/modelcontextprotocol/go-sdk` |
| **Java** | `OkHttp` | `io.modelcontextprotocol:client` |
| **Rust** | `reqwest` | `mcp-rs` |

---

## 4. 终端用户视角

### 4.1 适用客户端

| 客户端 | 平台 | 配置文件路径 |
|--------|------|--------------|
| **Claude Desktop** | macOS/Win/Linux | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Cursor** | macOS/Win/Linux | `~/.cursor/mcp.json` |
| **Cline** (VS Code) | 全平台 | VS Code → Cline → MCP Servers |
| **Continue.dev** | VS Code / JetBrains | `~/.continue/config.json` |
| **Zed** | macOS/Linux | `~/.config/zed/settings.json` |

### 4.2 一键安装

📖 **完整指南**：[docs/integration/claude-desktop-config.md](./claude-desktop-config.md)（566 行，含脚本、故障排除）

**5 步快速集成**：

1. 克隆项目：`git clone ... && cd Spide_agent && uv sync`
2. 初始化：`spide init`
3. 配置 API Key：编辑 `configs/uapi.yaml` 和 `configs/llm.yaml`
4. 验证：`spide doctor`（全部 ✓）
5. 配置 MCP 客户端（见上表），重启客户端

### 4.3 自然语言使用示例

```
你: 用 spide-agent 采集微博热搜并保存
Claude: ✓ 调用 crawl_hot_topics(source="weibo", save=true)，已保存 50 条

你: 分析这些热搜的趋势
Claude: ✓ 调用 web_search 查询背景，结合当前数据生成趋势报告

你: 深度采集小红书"AI编程"关键词
Claude: ✓ 调用 deep_crawl_hot_topics(platform="xhs", mode="search", keywords="AI编程")

你: 搜 Python asyncio 教程
Claude: ✓ 调用 web_search_enhanced(query="Python asyncio 教程", engine="duckduckgo")

你: 帮我看 spide-agent 提供了哪些能力
Claude: ✓ 调用 fetch_web_page(url="http://localhost:8765/.well-known/agent.json")
```

---

## 5. AI Agent 视角

### 5.1 Auto-Discovery 协议

SpideHarness Agent 实现**类 OpenAPI Discovery 风格**的 AI Agent 自发现协议。**只需一个 GET 请求**，即可获取所有能力清单。

**端点**：`GET /.well-known/agent.json`

**响应结构**：

```json
{
  "agent": {
    "name": "SpideHarness Agent",
    "version": "3.1.1",
    "description": "热点新闻信息抓取与智能整理 Agent"
  },
  "capabilities": {
    "mcp": {
      "transport": ["stdio"],
      "command": "spide mcp-serve",
      "tools": [
        {
          "name": "crawl_hot_topics",
          "description": "采集热搜榜单数据",
          "inputSchema": { "type": "object", "properties": {...}, "required": [...] },
          "auth": "uapi_key",
          "category": "data_collection"
        }
        // ... 共 8 个工具
      ]
    },
    "http": {
      "base_url": "http://localhost:8765",
      "endpoints": [/* 10 个 HTTP 端点 */]
    },
    "skills": [/* 17 个 Skills 索引 */]
  },
  "discovery": {
    "docs": "docs/integration/INTEGRATION.md",
    "mcp_reference": "docs/mcp-api-reference.md",
    "http_reference": "docs/http-api-reference.md",
    "skills_index": "skills/README.md"
  }
}
```

### 5.2 集成代码（任何语言）

**Python**（使用 httpx）：

```python
import httpx

async def integrate_spide_agent(base_url: str = "http://localhost:8765"):
    """AI Agent 自动发现并调用 SpideHarness Agent."""
    async with httpx.AsyncClient(base_url=base_url) as c:
        # 1. 发现能力
        manifest = (await c.get("/.well-known/agent.json")).json()
        print(f"Agent: {manifest['agent']['name']} v{manifest['agent']['version']}")

        # 2. 查找需要的工具
        crawl_tool = next(
            t for t in manifest["capabilities"]["mcp"]["tools"]
            if t["name"] == "crawl_hot_topics"
        )
        print(f"工具: {crawl_tool['name']} - {crawl_tool['description']}")

        # 3. 通过 HTTP 端点调用（更简单）
        result = (await c.post("/api/crawl")).json()
        print(f"已保存 {result['saved']} 条记录")

        # 4. 获取数据
        topics = (await c.get("/api/topics", params={"source": "weibo", "limit": 10})).json()
        return topics
```

**JavaScript**（使用 fetch）：

```javascript
async function integrateSpideAgent(baseUrl = "http://localhost:8765") {
  // 1. 发现能力
  const manifest = await fetch(`${baseUrl}/.well-known/agent.json`).then(r => r.json());
  console.log(`Agent: ${manifest.agent.name} v${manifest.agent.version}`);

  // 2. 调用 HTTP 端点
  const crawlResult = await fetch(`${baseUrl}/api/crawl`, { method: "POST" }).then(r => r.json());
  console.log(`Saved ${crawlResult.saved} records`);

  // 3. 读取数据
  const topics = await fetch(`${baseUrl}/api/topics?source=weibo&limit=10`).then(r => r.json());
  return topics;
}
```

### 5.3 Agent 决策建议

**何时使用 Auto-Discovery？**
- ✅ 第一次集成（无需先读文档）
- ✅ 能力频繁演进（动态获取最新工具列表）
- ✅ 跨多个 SpideHarness 实例（不同版本/不同配置）

**何时使用硬编码调用？**
- ✅ 已知工具集（8 个工具已稳定）
- ✅ 性能敏感（避免每次启动都 HTTP 请求）
- ✅ 离线场景（Auto-Discovery 需要 HTTP 服务在线）

---

## 6. 5 个集成场景（端到端示例）

### 场景 1：自动化热搜采集（cron + 邮件）

**目标**：每天 9:00 采集微博热搜，结果发邮件。

```python
# daily_crawl.py
import asyncio
import httpx
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

SPIDE_API = "http://localhost:8765"

async def crawl_and_email():
    async with httpx.AsyncClient(base_url=SPIDE_API, timeout=180) as c:
        # 1. 触发采集
        result = (await c.post("/api/crawl")).json()
        saved = result.get("saved", 0)

        # 2. 拉取 Top 20
        topics = (await c.get("/api/topics", params={"limit": 20})).json()

        # 3. 生成 HTML 邮件
        html = "<h2>今日热搜 Top 20</h2><ol>"
        for t in topics["items"]:
            html += f'<li><a href="{t["url"]}">{t["title"]}</a> (热度: {t["hot_value"]:,})</li>'
        html += "</ol>"

        # 4. 发送邮件
        msg = MIMEText(html, "html")
        msg["Subject"] = f"热搜日报 - {datetime.now():%Y-%m-%d}"
        msg["From"] = "spide@example.com"
        msg["To"] = "you@example.com"
        with smtplib.SMTP("smtp.example.com") as s:
            s.send_message(msg)
        print(f"✓ 已发送 {saved} 条热搜日报")

asyncio.run(crawl_and_email())
```

**cron 配置**：
```bash
# 每天 9:00 执行
0 9 * * * cd /path/to/Spide_agent && uv run python daily_crawl.py
```

### 场景 2：AI 智能摘要（GLM-5.1）

**目标**：对当日 Top 10 热搜自动生成摘要。

```python
# ai_summary.py
import asyncio, httpx, json
from zai import ZaiClient

SPIDE_API = "http://localhost:8765"
ZAI_KEY = "your.zhipu.api.key"

async def summarize_top_topics():
    async with httpx.AsyncClient(base_url=SPIDE_API) as c:
        # 1. 拉取 Top 10
        topics = (await c.get("/api/topics", params={"limit": 10})).json()

        # 2. 拼装 prompt
        topic_list = "\n".join([
            f"{i+1}. {t['title']} (热度: {t['hot_value']:,})"
            for i, t in enumerate(topics["items"])
        ])
        prompt = f"""请基于以下今日热搜，生成一段 200 字的趋势摘要：

{topic_list}

要求：识别 2-3 个主要话题方向，预测可能的发展趋势。"""

        # 3. 调用 GLM-5.1
        client = ZaiClient(api_key=ZAI_KEY)
        response = client.chat.completions.create(
            model="glm-5.1",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        summary = response.choices[0].message.content
        print("=== 今日热搜趋势摘要 ===\n")
        print(summary)

asyncio.run(summarize_top_topics())
```

### 场景 3：关键词告警推送到飞书

**目标**：监控包含"AI"关键词的热搜，触发时推送飞书。

`configs/alert_rules.yaml`：
```yaml
rules:
  - name: "AI 热点告警"
    keywords: ["AI", "大模型", "GPT", "LLM"]
    min_hot_value: 500000
    action: "feishu"
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/your-key"
    at_all: false
```

**运行**：
```bash
# 前台运行（持续监控）
spide monitor

# 单次执行（cron）
spide monitor --once
```

**飞书群收到**：
```
🔔 AI 热点告警触发
[1] 某 AI 话题 (热度: 8,765,432)
[2] GPT-5 发布预告 (热度: 5,432,109)
...
```

### 场景 4：GitHub 热点日报（每日推送）

**目标**：每天 18:00 采集 GitHub AI 热点并推送到飞书。

`daily_github.sh`：
```bash
#!/bin/bash
set -e

# 1. 设置飞书 Webhook
curl -s -X POST http://localhost:8765/api/github/webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "'$FEISHU_WEBHOOK'"}' > /dev/null

# 2. 采集 + 推送
curl -s -X POST http://localhost:8765/api/github/push | jq .
```

**cron 配置**：
```bash
# 每天 18:00 执行
0 18 * * * /path/to/daily_github.sh
```

### 场景 5：嵌入式 Dashboard（iframe 集成）

**目标**：在现有 Web 系统中嵌入 Spide Dashboard。

```html
<!-- your-portal.html -->
<!DOCTYPE html>
<html>
<head>
  <title>My Portal</title>
  <style>
    .spide-dashboard { width: 100%; height: 800px; border: 0; }
  </style>
</head>
<body>
  <h1>热点数据看板</h1>
  <iframe
    class="spide-dashboard"
    src="http://spide.example.com:8765/"
  ></iframe>
</body>
</html>
```

**或通过 API 渲染自定义卡片**：
```javascript
// dashboard-data.js
async function loadDashboardData() {
  const data = await fetch("http://localhost:8765/api/dashboard").then(r => r.json());
  document.getElementById("total").textContent = data.total_count;
  document.getElementById("platforms").textContent = data.stats_summary.platforms;
  const topList = data.top_topics.slice(0, 10).map((t, i) =>
    `<li>${i+1}. ${t.title} (${t.hot_value.toLocaleString()})</li>`
  ).join("");
  document.getElementById("top-list").innerHTML = topList;
}
loadDashboardData();
setInterval(loadDashboardData, 60000);  // 每分钟刷新
```

---

## 7. 故障排除速查

| 症状 | 原因 | 解决 |
|------|------|------|
| Claude Desktop 看不到工具 | 路径错误 | 用绝对路径 `which spide` |
| `crawl_hot_topics` 返回 `UAPI Key not configured` | `configs/uapi.yaml` 缺 Key | 编辑 yaml 或用 ENV 注入 |
| `web_search` 返回 401 | 智谱 Key 无效 | 检查 `configs/llm.yaml` |
| `fetch_repo_info` 返回空 | GitHub 60/h 限额 | 配置 `GITHUB_TOKEN` |
| `deep_crawl_hot_topics` 失败 | 缺 Playwright | `playwright install chromium` |
| `MCP Server 启动失败` | 端口冲突 | `lsof -i :8765` 检查 |
| HTTP API 504 超时 | crawl > 120s | 减少 `--max-notes` 或调整 timeout |
| `agent.json` 返回 404 | 旧版本（< V3.1.1） | 升级到最新代码 |
| 飞书回调 403 | Token 验证失败 | 检查 `set_feishu_config()` |
| Dashboard 加载慢 | SQLite 索引缺失 | 运行 `spide dedup` + `VACUUM` |

📖 **详细故障排除**：
- MCP 协议问题 → [docs/mcp-api-reference.md §10](../mcp-api-reference.md#10-故障排除faq)
- 客户端集成问题 → [docs/integration/claude-desktop-config.md §8](./claude-desktop-config.md#8-故障排除)
- HTTP API 问题 → [docs/http-api-reference.md §9](../http-api-reference.md#9-部署清单)

---

## 8. 文档索引

### 8.1 集成文档（按受众）

| 文档 | 受众 | 行数 |
|------|------|------|
| **本文档 (INTEGRATION.md)** | 所有人 | — |
| [claude-desktop-config.md](./claude-desktop-config.md) | 终端用户 | 566 |
| [mcp-api-reference.md](../mcp-api-reference.md) | 开发者 / 终端用户 | 871 |
| [http-api-reference.md](../http-api-reference.md) | 开发者 | 500+ |
| [skills/README.md](../../skills/README.md) | 终端用户 / AI | 258 |

### 8.2 项目文档

- [CLAUDE.md](../../CLAUDE.md) — 项目主文档
- [spider/CLAUDE.md](../../spide/spider/CLAUDE.md) — 采集引擎模块
- [mcp/CLAUDE.md](../../spide/mcp/CLAUDE.md) — MCP 协议层模块
- [monitor/CLAUDE.md](../../spide/monitor/CLAUDE.md) — 告警监控模块
- [dashboard/CLAUDE.md](../../dashboard/CLAUDE.md) — Dashboard Web 应用
- [tests/CLAUDE.md](../../tests/CLAUDE.md) — 测试模块

### 8.3 源码参考

- `dashboard/capability_registry.py` — 能力注册表
- `dashboard/api.py` — FastAPI 入口
- `dashboard/feishu_handler.py` — 飞书事件回调
- `dashboard/github_trending.py` — GitHub 热点采集
- `spide/mcp/server.py` — MCP Server 实现
- `spide/mcp/tools.py` — 8 个工具的 JSON Schema

---

## 9. API 版本与变更日志

### 9.1 版本号语义

- **V3.x** — 集成层（HTTP API / MCP / Skills）
- **1.1.x** — Python 包版本（`pyproject.toml`）
- **V3.1.1 (DEV)** — 奇数次版本 = 开发测试版

### 9.2 集成层变更日志

| 版本 | 日期 | 变更 |
|------|------|------|
| **V3.1.1** | 2026-06-09 | 🆕 **集成层完整化** |
|  |  | - 新增 Auto-Config API (`/.well-known/agent.json`) |
|  |  | - 新增 HTTP REST 完整文档（10 端点） |
|  |  | - 新增 MCP 文档（SSE 规划 / JSON-RPC 错误码 / FAQ） |
|  |  | - 新增 Claude Desktop / Cursor / Cline 配置手册 |
|  |  | - 新增 3 个 Skills (trending / monitor / feishu) |
|  |  | - 4 个核心 Skills 添加"通过 MCP 调用"章节 |
|  |  | - 新增 `skills/README.md` 索引（17 Skills） |
|  |  | - 新增 `docs/integration/INTEGRATION.md`（本文件） |
| V3.0.x | 2026-05-20 ~ 2026-05-27 | Dashboard Web + 飞书 Bot + GitHub 热点 |
| V2.x | 2026-04-08 ~ 2026-05-20 | MCP Server 8 工具 + 基础 Skills |

### 9.3 兼容性矩阵

| SpideHarness | Python | FastAPI | mcp-sdk | Node | 浏览器 |
|--------------|--------|---------|---------|------|--------|
| V3.1.1+ | 3.12+ | 0.115+ | 1.27+ | 18+ | Chrome 120+ |
| V3.0.x | 3.12+ | 0.110+ | 1.20+ | 18+ | Chrome 120+ |
| V2.x | 3.11+ | 0.100+ | 1.10+ | 16+ | Chrome 100+ |

### 9.4 路线图

- [ ] **SSE Transport** — MCP Server 支持远程 HTTP+SSE 模式（替代 stdio）
- [ ] **OAuth 2.0** — HTTP API 的统一鉴权
- [ ] **WebSocket** — Dashboard 实时数据推送（替代轮询）
- [ ] **OpenTelemetry** — 分布式追踪（采集 → 存储 → LLM → 推送）
- [ ] **Dify / Coze 适配器** — 一键发布到 AI 智能体平台

---

## 10. 反馈与支持

- **GitHub Issues**: [github.com/iotchange/Spide_agent/issues](https://github.com)
- **Email**: 14455975@qq.com
- **作者**: 外星动物（常智）/ IoTchange

---

*Copyright (C) 2026 IoTchange - All Rights Reserved*
