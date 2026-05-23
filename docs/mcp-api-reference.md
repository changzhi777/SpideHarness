# SpideHarness Agent — MCP Server API 对接文档

> 版本: V3.1.1 | 更新: 2026-05-23 | 协议: MCP (Model Context Protocol)

本文档面向第三方程序/Agent，说明如何通过 MCP 协议对接 SpideHarness Agent 的工具服务。

---

## 1. 概述

SpideHarness Agent 提供 **MCP Server**，通过 stdio transport 暴露 8 个工具。外部程序可作为 MCP Client 连接，调用热搜采集、联网搜索、网页抓取、仓库信息查询等能力。

### 通信方式

| 项 | 值 |
|---|---|
| 协议 | MCP (Model Context Protocol) |
| Transport | stdio（标准输入/输出） |
| 服务名 | `spide-agent` |
| 版本 | `0.1.0` |

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

## 附录：依赖信息

| 依赖 | 版本 | 用途 |
|------|------|------|
| `mcp` | mcp-sdk | MCP 协议实现 |
| `aiohttp` | ≥3.9 | 异步 HTTP 请求 |
| `zai` | zai-sdk | 智谱 LLM API |
| Python | ≥3.12 | 运行时 |

---

*Copyright (C) 2026 IoTchange - All Rights Reserved*
