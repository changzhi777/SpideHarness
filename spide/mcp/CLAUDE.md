# MCP 协议层

> [根目录](../../CLAUDE.md) → `spide/mcp/`

## 职责

Model Context Protocol 实现，提供 stdio MCP Server 和 Client，供外部 AI 模型调用 Spide 能力。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 4 | 导出 create_mcp_server, serve_mcp |
| `server.py` | 253 | MCP Server — 工具注册、调用分发、stdio transport |
| `client.py` | 102 | MCP Client — 连接外部 MCP Server |
| `tools.py` | 136 | 工具定义 (JSON Schema) — 5 个工具 |

## MCP 工具清单

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `crawl_hot_topics` | 热搜采集 | source (平台标识) |
| `web_search` | 联网搜索 | query, engine, count |
| `manage_memory` | 记忆管理 | action (add/remove/list/get), title, content |
| `health_check` | 健康检查 | 无 |
| `deep_crawl_hot_topics` | 深度采集 | platform, mode, keywords, content_ids, creator_ids, max_notes, enable_comments |

## 启动方式

```bash
spide mcp-serve  # stdio 模式，供 Claude Desktop 等 MCP 客户端连接
```

## 内部实现

`server.py` 中 `_dispatch_tool()` 分发到：
- `_tool_crawl()` → UAPIClient.fetch_hotboard()
- `_tool_search()` → LLMClient.web_search()
- `_tool_memory()` → spide.memory 模块
- `_tool_deep_crawl()` → Engine.deep_crawl()
- `_tool_health()` → 版本/状态信息

## 依赖

- mcp-sdk (Python)
- zai-sdk (LLMClient)
- spide.config, spide.llm, spide.spider, spide.memory, spide.harness.engine

## 测试

- `tests/unit/test_mcp_server.py`
