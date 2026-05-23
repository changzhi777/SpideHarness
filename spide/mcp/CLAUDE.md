# MCP 协议层

> [根目录](../../CLAUDE.md) → `spide/mcp/`

## 职责

Model Context Protocol 实现，提供 stdio MCP Server 和 Client，供外部 AI 模型调用 Spide 能力。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 4 | 导出 create_mcp_server, serve_mcp |
| `server.py` | ~315 | MCP Server — 工具注册、调用分发（8 个工具）、stdio transport |
| `client.py` | 103 | MCP Client — 连接外部 MCP Server |
| `tools.py` | ~220 | 工具定义 (JSON Schema) — 8 个工具 |
| `search_provider.py` | ~327 | 搜索适配器层 — WebSearchProvider / WebContentProvider / RepoInfoProvider |

## MCP 工具清单（8 个）

| 工具名 | 功能 | 参数 | 认证 |
|--------|------|------|------|
| `crawl_hot_topics` | 热搜采集 | source (平台标识) | UAPI Key |
| `web_search` | 智谱联网搜索 | query, engine, count | 智谱 API Key |
| `web_search_enhanced` | 增强联网搜索 | query, engine, limit | DuckDuckGo 免认证 |
| `fetch_web_page` | 网页内容抓取 | url, extract_links | 免认证 |
| `fetch_repo_info` | GitHub 仓库信息 | repo, info_type | 免认证（有速率限制） |
| `manage_memory` | 记忆管理 | action, title, content | 免认证 |
| `health_check` | 健康检查 | 无 | 免认证 |
| `deep_crawl_hot_topics` | 深度采集 | platform, mode, keywords, ... | 免认证 |

## 启动方式

```bash
spide mcp-serve  # stdio 模式，供 Claude Desktop 等 MCP 客户端连接
```

## 内部实现

`server.py` 中 `_dispatch_tool()` 分发到：
- `_tool_crawl()` → UAPIClient.fetch_hotboard()
- `_tool_search()` → LLMClient.web_search()
- `_tool_search_enhanced()` → WebSearchProvider.search()（DuckDuckGo / 智谱）
- `_tool_fetch_page()` → WebContentProvider.fetch_page()
- `_tool_repo_info()` → RepoInfoProvider（summary / readme / full）
- `_tool_memory()` → spide.memory 模块
- `_tool_deep_crawl()` → Engine.deep_crawl()
- `_tool_health()` → 版本/状态信息

## search_provider.py 架构

```
WebSearchProvider          WebContentProvider        RepoInfoProvider
├── search()               ├── fetch_page()          ├── fetch_repo_info()
│   └── _search_ddgs()     │   → 提取 title/text/links│   → GitHub API 元数据
│       └── POST DDGS      └── fetch_github_readme() └── fetch_repo_summary()
└── _parse_ddgs_html()         → GitHub REST API README  → dict 摘要
```

**数据模型：**
- `SearchResult` — title / url / description / source
- `PageContent` — url / title / text / links
- `RepoInfo` — repo / description / stars / language / readme

## API 对接文档

外部程序对接请参考：[docs/mcp-api-reference.md](../../docs/mcp-api-reference.md)

## 依赖

- mcp-sdk (Python)
- aiohttp (HTTP 请求)
- zai-sdk (LLMClient)
- spide.config, spide.llm, spide.spider, spide.memory, spide.harness.engine

## 测试

- `tests/unit/test_mcp_server.py` — Server 工具注册 + 分发
- `tests/unit/test_search_provider.py` — 3 个 Provider 单元测试（15 个用例）
- `tests/unit/test_mcp_search_tools.py` — MCP 搜索工具分发测试（4 个用例）
