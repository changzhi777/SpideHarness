# SpideHarness Agent — MCP Server API 对接文档

> 版本: V3.1.1 | 更新: 2026-06-09 | 协议: MCP (Model Context Protocol)

本文档面向第三方程序/Agent，说明如何通过 MCP 协议对接 SpideHarness Agent 的工具服务。

> **快速发现**：AI Agent 可通过 `GET http://<host>:8765/.well-known/agent.json` 一次性获取 MCP / HTTP / Skills 清单（见 [INTEGRATION.md](./integration/INTEGRATION.md) 第 4 节）。

---

## 1. 概述

SpideHarness Agent 提供 **MCP Server**，通过 stdio transport 暴露 8 个工具。外部程序可作为 MCP Client 连接，调用热搜采集、联网搜索、网页抓取、仓库信息查询等能力。

### 通信方式

| 项 | 值 |
|---|---|
| 协议 | MCP (Model Context Protocol) |
| Transport | `stdio`（已实现）/ `sse`（规划中，见 §11） |
| 服务名 | `spide-agent` |
| 版本 | `0.1.0` |
| Capabilities | `tools` |

---

## 2. 启动 MCP Server

### 方式一：CLI 命令

```bash
spide mcp-serve
```

### 方式二：Python 代码

```python
from spide.mcp import create_mcp_server

server = create_mcp_server()
# 在 async 环境中启动
await server.run(read_stream, write_stream, init_options)
```

---

## 3. 客户端连接

### Python 客户端示例

```python
from spide.mcp.client import MCPClient

async with MCPClient(
    server_command="spide",
    args=["mcp-serve"],
) as client:
    # 列出可用工具
    tools = await client.list_tools()

    # 调用工具
    result = await client.call_tool("web_search_enhanced", {
        "query": "Python asyncio",
        "engine": "duckduckgo",
        "limit": 10,
    })
    print(result)
```

### Claude Desktop / Cursor 配置

在 MCP 客户端配置文件中添加：

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

> **详细配置说明**（含路径、ENV、TLS、故障排除）见 [docs/integration/claude-desktop-config.md](./integration/claude-desktop-config.md)。

### 3.1 Cursor 配置

`~/.cursor/mcp.json`（macOS/Linux）或 `%APPDATA%\Cursor\User\mcp.json`（Windows）：

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Spide_agent"
      }
    }
  }
}
```

> **要点**：
> - `PYTHONPATH` 必须指向 Spide_agent 根目录，否则 `spide` 命令找不到
> - 使用 `which spide` 验证可执行文件位置

### 3.2 Cline (VS Code) 配置

VS Code → Cline 扩展 → MCP Servers → 添加：

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "disabled": false
    }
  }
}
```

### 3.3 环境变量注入

如需传递 API Key（推荐通过 `configs/*.yaml` 而非环境变量）：

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {
        "SPIDE_LLM__COMMON__API_KEY": "your-zhipu-key",
        "SPIDE_UAPI__COMMON__API_KEY": "your-uapi-key"
      }
    }
  }
}
```

> 环境变量优先级高于 `configs/*.yaml`，使用 `SPIDE_<SECTION>__<KEY>` 双下划线语法。

### 通用 MCP Client SDK

任何支持 MCP stdio transport 的客户端均可连接：

```python
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

params = StdioServerParameters(command="spide", args=["mcp-serve"])

async with stdio_client(params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()

        # 调用工具
        result = await session.call_tool("fetch_web_page", {
            "url": "https://example.com",
        })
```

---

## 4. 工具清单

| # | 工具名 | 功能 | 需要认证 |
|---|--------|------|----------|
| 1 | `crawl_hot_topics` | 热搜采集（微博/百度/抖音/知乎/B站） | UAPI Key |
| 2 | `web_search` | 智谱联网搜索 | 智谱 API Key |
| 3 | **`web_search_enhanced`** | 增强联网搜索（DuckDuckGo/智谱） | DuckDuckGo 免认证 |
| 4 | **`fetch_web_page`** | 网页内容抓取 | 免认证 |
| 5 | **`fetch_repo_info`** | GitHub 仓库信息查询 | 免认证（有速率限制） |
| 6 | `manage_memory` | 记忆管理 | 免认证 |
| 7 | `health_check` | 健康检查 | 免认证 |
| 8 | `deep_crawl_hot_topics` | 深度采集（需浏览器） | 免认证 |

> 加粗为本次新增工具，**无需 API Key** 即可使用。

---

## 4.1 工具 JSON Schema 速查表

> **完整定义**见 `spide/mcp/tools.py`。下表为简化版（必填项 + 关键参数）。

| 工具 | 必填参数 | 可选参数 | 认证 |
|------|----------|----------|------|
| `crawl_hot_topics` | `source: enum[weibo\|baidu\|douyin\|zhihu\|bilibili]` | `save: bool=false` | UAPI Key |
| `web_search` | `query: str` | `engine: str=search_pro`, `count: int=10` | 智谱 API Key |
| `web_search_enhanced` | `query: str` | `engine: enum[duckduckgo\|zhipu]=duckduckgo`, `limit: int=10` | DuckDuckGo 免认证 |
| `fetch_web_page` | `url: str` | `extract_links: bool=false` | 免认证 |
| `fetch_repo_info` | `repo: str`（owner/repo） | `info_type: enum[summary\|readme\|full]=summary` | 免认证 |
| `manage_memory` | `action: enum[add\|remove\|list\|get]` | `title: str`, `content: str` | 免认证 |
| `health_check` | — | — | 免认证 |
| `deep_crawl_hot_topics` | `platform: enum[xhs\|dy\|ks\|bili\|wb\|tieba\|zhihu]` | `mode: enum[search\|detail\|creator]=search`, `keywords`, `content_ids`, `creator_ids`, `max_notes: int=20`, `enable_comments: bool=true` | 免认证 |

### 完整 inputSchema 示例

```json
{
  "crawl_hot_topics": {
    "type": "object",
    "properties": {
      "source": {"type": "string", "enum": ["weibo", "baidu", "douyin", "zhihu", "bilibili"]},
      "save": {"type": "boolean", "default": false}
    },
    "required": ["source"]
  },
  "web_search_enhanced": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "engine": {"type": "string", "enum": ["duckduckgo", "zhipu"], "default": "duckduckgo"},
      "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50}
    },
    "required": ["query"]
  },
  "deep_crawl_hot_topics": {
    "type": "object",
    "properties": {
      "platform": {"type": "string", "enum": ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]},
      "mode": {"type": "string", "enum": ["search", "detail", "creator"], "default": "search"},
      "keywords": {"type": "string", "description": "逗号分隔"},
      "content_ids": {"type": "string"},
      "creator_ids": {"type": "string"},
      "max_notes": {"type": "integer", "default": 20},
      "enable_comments": {"type": "boolean", "default": true}
    },
    "required": ["platform"]
  }
}
```

> 完整 8 工具 schema 见 [spide/mcp/tools.py](../spide/mcp/tools.py)。

---

## 5. 工具详细说明

### 5.1 `web_search_enhanced` — 增强联网搜索

多引擎网页搜索，返回结构化结果（标题/URL/摘要）。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | **是** | — | 搜索关键词 |
| `engine` | string | 否 | `"duckduckgo"` | 搜索引擎：`duckduckgo`（免费）/ `zhipu`（需 API Key） |
| `limit` | integer | 否 | `10` | 返回结果数量（1-50） |

**请求示例：**

```json
{
  "query": "Python asyncio 教程",
  "engine": "duckduckgo",
  "limit": 5
}
```

**响应示例：**

```json
{
  "query": "Python asyncio 教程",
  "engine": "duckduckgo",
  "count": 3,
  "items": [
    {
      "title": "Python asyncio 官方文档",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "description": "asyncio is a library to write concurrent code using the async/await syntax..."
    },
    {
      "title": "Python Asyncio 入门教程",
      "url": "https://example.com/asyncio-tutorial",
      "description": "本教程详细介绍了 Python asyncio 的核心概念..."
    },
    {
      "title": "Real Python - Async IO in Python",
      "url": "https://realpython.com/async-io-python/",
      "description": "A Complete Guide to Asynchronous Programming in Python..."
    }
  ]
}
```

**引擎说明：**

| 引擎 | 说明 | 限制 |
|------|------|------|
| `duckduckgo` | DuckDuckGo HTML 搜索，免费 | 无需 API Key，依赖 HTML 解析 |
| `zhipu` | 智谱 Web Search API | 需要 `configs/llm.yaml` 中配置 API Key |

---

### 5.2 `fetch_web_page` — 网页内容抓取

抓取指定 URL 的网页内容，提取标题、正文、链接。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `url` | string | **是** | — | 目标网页 URL |
| `extract_links` | boolean | 否 | `false` | 是否提取页面中的链接 |

**请求示例：**

```json
{
  "url": "https://docs.python.org/3/library/asyncio.html",
  "extract_links": true
}
```

**响应示例：**

```json
{
  "url": "https://docs.python.org/3/library/asyncio.html",
  "title": "asyncio — Asynchronous I/O — Python 3.12 documentation",
  "content": "asyncio is a library to write concurrent code using the async/await syntax...",
  "links": [
    "https://docs.python.org/3/library/asyncio-task.html",
    "https://docs.python.org/3/library/asyncio-stream.html",
    "https://github.com/python/cpython"
  ]
}
```

**说明：**
- 正文最长 5000 字符（MCP 返回时截断）
- 链接最多返回 50 条
- 自动清理 HTML 标签，保留纯文本
- 非文本内容（PDF、图片等）可能返回空结果

---

### 5.3 `fetch_repo_info` — GitHub 仓库信息

获取 GitHub 开源仓库的元数据和 README 内容。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `repo` | string | **是** | — | 仓库路径，格式：`owner/repo` |
| `info_type` | string | 否 | `"summary"` | 信息类型：`summary` / `readme` / `full` |

**info_type 说明：**

| 值 | 返回内容 |
|----|----------|
| `summary` | 仓库描述、Stars、语言、README 前 1000 字符 |
| `readme` | README 全文（最长 5000 字符） |
| `full` | 仓库描述、Stars、语言、README 全文 |

**请求示例（summary）：**

```json
{
  "repo": "zhipu/zai-sdk-python",
  "info_type": "summary"
}
```

**响应示例（summary）：**

```json
{
  "repo": "zhipu/zai-sdk-python",
  "description": "智谱 AI Python SDK — ZhipuAI API Python Client",
  "stars": 1520,
  "language": "Python",
  "readme_preview": "# ZAI SDK Python\n\n智谱 AI 官方 Python SDK...\n\n## 安装\n\n```bash\npip install zai\n```\n\n## 快速开始\n\n..."
}
```

**请求示例（readme）：**

```json
{
  "repo": "zhipu/zai-sdk-python",
  "info_type": "readme"
}
```

**响应示例（readme）：**

```json
{
  "repo": "zhipu/zai-sdk-python",
  "readme": "# ZAI SDK Python\n\n智谱 AI 官方 Python SDK，支持 GLM-5.1 / GLM-5V 等模型...\n\n## 安装\n...\n## 使用\n..."
}
```

**说明：**
- 使用 GitHub REST API（未认证限额 60 次/小时）
- README 返回原始 Markdown 文本
- 如果仓库无 README，`readme` 字段为空字符串

---

### 5.4 `crawl_hot_topics` — 热搜采集

采集指定平台的实时热搜榜单。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `source` | string | **是** | — | 平台：`weibo` / `baidu` / `douyin` / `zhihu` / `bilibili` |

**响应示例：**

```json
{
  "source": "weibo",
  "count": 20,
  "items": [
    {
      "rank": 1,
      "title": "热搜话题标题",
      "hot_value": 1234567,
      "url": "https://weibo.com/..."
    }
  ]
}
```

**前置条件：** 需在 `configs/uapi.yaml` 配置 UAPI API Key。

---

### 5.5 `web_search` — 智谱联网搜索

通过智谱 Web Search API 搜索。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | **是** | — | 搜索关键词 |
| `engine` | string | 否 | `"search_pro"` | 搜索引擎变体 |
| `count` | integer | 否 | `10` | 返回数量 |

**前置条件：** 需在 `configs/llm.yaml` 配置智谱 API Key。

---

### 5.6 `manage_memory` — 记忆管理

管理 Agent 的持久化记忆（文件系统）。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | **是** | `add` / `remove` / `list` / `get` |
| `title` | string | 条件必填 | add/remove/get 时必填 |
| `content` | string | 条件必填 | add 时必填 |

---

### 5.7 `health_check` — 健康检查

**参数：** 无

**响应示例：**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "python": "3.12"
}
```

---

### 5.8 `deep_crawl_hot_topics` — 深度采集

通过 MediaCrawler 采集指定平台的详细内容（需浏览器环境）。

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `platform` | string | **是** | — | 平台：`xhs` / `dy` / `ks` / `bili` / `wb` / `tieba` / `zhihu` |
| `mode` | string | 否 | `"search"` | 模式：`search` / `detail` / `creator` |
| `keywords` | string | 否 | — | 搜索关键词（逗号分隔，search 模式必填） |
| `content_ids` | string | 否 | — | 内容 ID（逗号分隔，detail 模式必填） |
| `creator_ids` | string | 否 | — | 创作者 ID（逗号分隔，creator 模式必填） |
| `max_notes` | integer | 否 | `20` | 最大采集数量 |
| `enable_comments` | boolean | 否 | `true` | 是否采集评论 |

---

## 6. Python SDK 直接调用

除 MCP 协议外，也可直接 import Provider 类使用：

### 6.1 WebSearchProvider — 网页搜索

```python
from spide.mcp.search_provider import WebSearchProvider

provider = WebSearchProvider()

# DuckDuckGo 搜索（免费，无需 API Key）
results = await provider.search("Python asyncio", engine="duckduckgo", limit=10)

for r in results:
    print(f"[{r.title}]({r.url})")
    print(f"  {r.description}")
    print(f"  来源: {r.source}")
```

**类接口：**

```python
class WebSearchProvider:
    async def search(
        self, query: str, *, engine: str = "duckduckgo", limit: int = 10
    ) -> list[SearchResult]:
        """执行网页搜索."""

    @staticmethod
    def _parse_ddgs_html(html: str, limit: int) -> list[SearchResult]:
        """解析 DuckDuckGo HTML 结果."""
```

**SearchResult 数据模型：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 搜索结果标题 |
| `url` | `str` | 结果链接 |
| `description` | `str` | 结果摘要 |
| `source` | `str` | 来源引擎 |

---

### 6.2 WebContentProvider — 网页抓取

```python
from spide.mcp.search_provider import WebContentProvider

# 抓取网页内容
page = await WebContentProvider.fetch_page(
    "https://docs.python.org/3/library/asyncio.html",
    extract_links=True,
)

print(f"标题: {page.title}")
print(f"正文: {page.text[:500]}")
print(f"链接: {page.links[:10]}")

# 获取 GitHub README
readme = await WebContentProvider.fetch_github_readme("zhipu/zai-sdk-python")
print(readme[:500])
```

**类接口：**

```python
class WebContentProvider:
    @staticmethod
    async def fetch_page(
        url: str, *, extract_links: bool = False, max_length: int = 10000
    ) -> PageContent:
        """抓取网页内容."""

    @staticmethod
    async def fetch_github_readme(repo: str) -> str:
        """获取 GitHub 仓库 README."""
```

**PageContent 数据模型：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | `str` | 页面 URL |
| `title` | `str` | 页面标题 |
| `text` | `str` | 正文纯文本 |
| `links` | `list[str]` | 页面中的链接列表 |

---

### 6.3 RepoInfoProvider — 仓库信息

```python
from spide.mcp.search_provider import RepoInfoProvider

# 获取完整仓库信息
info = await RepoInfoProvider.fetch_repo_info("zhipu/zai-sdk-python")
print(f"Stars: {info.stars}")
print(f"Language: {info.language}")
print(f"Description: {info.description}")

# 获取摘要（轻量）
summary = await RepoInfoProvider.fetch_repo_summary("zhipu/zai-sdk-python")
print(summary)  # dict: repo, description, stars, language, readme_preview
```

**类接口：**

```python
class RepoInfoProvider:
    @staticmethod
    async def fetch_repo_info(repo: str) -> RepoInfo:
        """获取仓库元数据 + README."""

    @staticmethod
    async def fetch_repo_summary(repo: str) -> dict[str, Any]:
        """获取仓库摘要 dict."""
```

**RepoInfo 数据模型：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `repo` | `str` | 仓库路径 (owner/repo) |
| `description` | `str` | 仓库描述 |
| `stars` | `int` | Star 数量 |
| `language` | `str` | 主要编程语言 |
| `readme` | `str` | README 内容 |

---

## 7. 错误处理

所有工具调用失败时返回包含 `error` 字段的 JSON：

```json
{
  "error": "错误描述信息"
}
```

| 场景 | 返回 |
|------|------|
| 未知工具名 | `{"error": "未知工具: xxx"}` |
| 网络超时（15s） | 返回空结果（`items: []` 或 `text: ""`） |
| HTTP 404/500 | 返回空结果 |
| GitHub API 限流 | 返回空结果 |
| 缺少必填参数 | MCP 协议层报错 |

### 7.1 JSON-RPC 错误码（MCP 协议层）

MCP 协议标准错误码（来自 `mcp.shared.exceptions`）：

| 错误码 | 名称 | 含义 | 触发场景 |
|--------|------|------|----------|
| `-32700` | `ParseError` | JSON 解析失败 | 客户端发送非 JSON 字符串 |
| `-32600` | `InvalidRequest` | 请求格式错误 | 缺 `jsonrpc` 字段 / `id` 缺失 |
| `-32601` | `MethodNotFound` | 方法不存在 | 客户端调用 `tools/call` 之外的未知方法 |
| `-32602` | `InvalidParams` | 参数错误 | 工具必填参数缺失 / 参数类型不匹配 |
| `-32603` | `InternalError` | 服务器内部错误 | 工具内部异常（被 `call_tool` 装饰器捕获并转为 `{"error": str(e)}`） |
| `-32000` ~ `-32099` | `ServerError` | 服务器自定义错误 | 实现特定错误（如工具业务异常） |

**Server-side 行为**：本 MCP Server 的 `call_tool` 装饰器**捕获所有 Exception** 并转为：

```json
{
  "error": "工具执行失败的具体原因"
}
```

返回 `TextContent(text=<上述 JSON>)`，**协议层不抛 -32603**。客户端解析 `text` 字段即可获知错误。

**Client-side 验证建议**：调用 `call_tool` 前先 `validate_arguments(name, arguments)`，避免触发 `-32602 InvalidParams`。

---

## 8. 速率限制与注意事项

---

## 8. 速率限制与注意事项

| 工具 | 限制 |
|------|------|
| `web_search_enhanced` (duckduckgo) | 建议 ≤1 QPS，过高可能被反爬 |
| `fetch_web_page` | 建议 ≤1 QPS，超时 15s |
| `fetch_repo_info` | GitHub 未认证限额 60 次/小时 |
| `crawl_hot_topics` | 受 UAPI 配额限制 |
| `deep_crawl_hot_topics` | 受平台反爬限制 |

---

## 9. 完整调用示例

### 示例 1：搜索 + 抓取文章

```python
import asyncio
from spide.mcp.client import MCPClient

async def main():
    async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
        # 1. 搜索
        search_result = await client.call_tool("web_search_enhanced", {
            "query": "Python asyncio 最佳实践",
            "engine": "duckduckgo",
            "limit": 3,
        })

        # 2. 抓取第一个结果
        if search_result[0].text:
            import json
            data = json.loads(search_result[0].text)
            if data.get("items"):
                page_result = await client.call_tool("fetch_web_page", {
                    "url": data["items"][0]["url"],
                })
                print(page_result[0].text)

asyncio.run(main())
```

### 示例 2：热搜采集 + 深度追踪

```python
async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    # 采集微博热搜
    hot = await client.call_tool("crawl_hot_topics", {"source": "weibo"})

    # 对第一个话题搜索更多背景
    import json
    topics = json.loads(hot[0].text)
    if topics.get("items"):
        detail = await client.call_tool("web_search_enhanced", {
            "query": topics["items"][0]["title"],
            "limit": 5,
        })
        print(detail[0].text)
```

### 示例 3：技术选型调研

```python
async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    # 获取仓库信息
    info = await client.call_tool("fetch_repo_info", {
        "repo": "modelcontextprotocol/python-sdk",
        "info_type": "full",
    })
    print(info[0].text)
```

---

## 10. 故障排除（FAQ）

### Q1: Claude Desktop 启动后看不到 `spide-agent` 工具？

**A**: 检查 4 步：
1. **路径正确**：`spide` 命令在系统 PATH 中。运行 `which spide` 应输出绝对路径。
2. **配置格式**：JSON 必须含 `mcpServers` 顶层键，键名拼写正确。
3. **重启客户端**：Claude Desktop 改完配置后**必须完全退出并重新打开**（不关闭窗口，需 ⌘Q / Alt+F4）。
4. **日志查看**：macOS `~/Library/Logs/Claude/mcp*.log`；Windows `%APPDATA%\Claude\Logs\mcp*.log`。

### Q2: 调用 `crawl_hot_topics` 返回 `{"error": "UAPI Key not configured"}`？

**A**: `configs/uapi.yaml` 未配置或 Key 错误。检查：
```bash
spide config       # 应列出 uapi.api_key
spide doctor       # 检查 API Key 格式
```

### Q3: `web_search` 返回 `401 Unauthorized`？

**A**: 智谱 API Key 错误或过期。检查 `configs/llm.yaml`：
```yaml
llm:
  common:
    api_key: "your.zhipu.api.key"
    base_url: "https://open.bigmodel.cn/api/paas/v4"
```

### Q4: `fetch_repo_info` 返回空结果？

**A**: GitHub 未认证 60 次/小时限额。解决：
- 配置 `GITHUB_TOKEN` 环境变量（5000 次/小时）
- 或在 MCP 配置中传入：`"env": {"GITHUB_TOKEN": "ghp_xxx"}`

### Q5: `deep_crawl_hot_topics` 超时或失败？

**A**: 需要浏览器环境（Playwright + Chromium）。检查：
```bash
playwright install chromium
```
且 `MediaCrawler/` 目录存在并已安装依赖。

### Q6: `mcp-sdk` 版本不兼容错误 `ImportError: cannot import name 'InitializationOptions'`？

**A**: 升级到 `mcp-sdk >= 1.27.0`：
```bash
uv add 'mcp>=1.27.0'
```
本项目代码已从 `mcp.types.InitializationOptions` 迁移至 `mcp.server.InitializationOptions`。

### Q7: 工具返回成功但结果为空 `{"items": []}`？

**A**: 可能是网络问题或 API 限流。建议：
- 重试 1-2 次（间隔 5s+）
- 切换引擎（`web_search_enhanced` 用 `engine: "zhipu"` 替代 `duckduckgo`）
- 查看 `spide_data.log` 日志

---

## 11. Transport 扩展性 — SSE 模式（规划）

**当前状态**：本 MCP Server **仅实现 stdio transport**（见 §1 概述）。`agent.json` 自发现端点声明 `["stdio", "sse"]`，其中 `sse` 为**规划中能力**。

### 11.1 规划架构

```
┌──────────────┐         SSE/HTTP          ┌──────────────────┐
│ MCP Client   │  ──────GET /sse──────►   │ SpideHarness     │
│ (Remote)     │  ◄─────event-stream───   │ MCP SSE Server   │
└──────────────┘         POST /msg         └──────────────────┘
```

### 11.2 启用 SSE 的前置条件

1. **服务端**：实现 `sse_server.py`（基于 `mcp.server.sse.SseServerTransport`）
2. **部署**：HTTP 服务需绑定 `0.0.0.0:<port>` + TLS 终结（nginx/Caddy）
3. **鉴权**：Bearer Token / mTLS（stdio 模式无此问题）
4. **CORS**：允许跨域（MCP 客户端可能从浏览器发起）

### 11.3 客户端配置（待实现）

```json
{
  "mcpServers": {
    "spide-agent-remote": {
      "url": "https://spide.example.com/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer ${SPIDE_API_TOKEN}"
      }
    }
  }
}
```

### 11.4 进度跟踪

SSE transport 实现请关注项目 README 变更日志。当前推荐使用 stdio 模式 + 远程隧道（ssh / ngrok）作为临时方案。

---

## 附录：依赖信息

| 依赖 | 版本 | 用途 |
|------|------|------|
| `mcp` | mcp-sdk | MCP 协议实现 |
| `aiohttp` | ≥3.9 | 异步 HTTP 请求 |
| `zai` | zai-sdk | 智谱 LLM API |
| Python | ≥3.12 | 运行时 |

---

*Copyright (C) 2026 IoTchange - All Rights Reserved*
