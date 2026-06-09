---
name: spide-analyze
description: >
  AI 分析 — 趋势分析、内容摘要、情感分析、智能采集策略。
  当用户要求分析热搜趋势、生成摘要、获取采集建议时使用。
category: ai_analysis
---

# Spide Analyze — AI 分析

## 触发条件

用户要求对采集数据进行分析、生成摘要、趋势洞察或智能采集策略时自动激活。

## 用法

```bash
# 基础分析 — 趋势分析 + 摘要
spide analyze -s weibo

# 多数据源分析
spide analyze -s baidu
spide analyze -s douyin
spide analyze -s zhihu
spide analyze -s bilibili

# 含智能采集策略
spide analyze -s weibo --strategy

# 按关键词分析
spide analyze -k "AI,大模型,芯片"

# 组合使用
spide analyze -s weibo -k "AI" --strategy
```

## 分析能力

| 能力 | 说明 |
|------|------|
| 趋势分析 | 识别热点话题趋势、排名变化、热度走势 |
| 内容摘要 | 自动生成热点事件摘要 |
| 情感分析 | 分析话题情感倾向（正面/负面/中性） |
| 采集策略 | 基于分析结果推荐下一步采集方向 |

## 支持的数据源

| 数据源 | 标识 |
|--------|------|
| 微博热搜 | `weibo` |
| 百度热搜 | `baidu` |
| 抖音热点 | `douyin` |
| 知乎热榜 | `zhihu` |
| B站热搜 | `bilibili` |

## 工作流程

1. 确认分析目标和数据源
2. 运行 `spide analyze` 命令
3. 查看分析报告（趋势、摘要、情感）
4. 如需采集策略，添加 `--strategy` 参数
5. 根据策略建议决定下一步采集方向

## 注意事项

- 分析依赖 GLM-5.1 模型，需配置 `configs/llm.yaml`
- 首次分析会先采集最新数据
- 分析结果会缓存，避免重复调用 API

## 通过 MCP 调用

AI 分析在 MCP 层由 `web_search` 工具（智谱联网搜索）提供底层数据获取能力，趋势/摘要由调用方的 LLM 完成：

```python
# 1. 通过 web_search 获取最新数据（智谱 Web Search API）
from spide.mcp.client import MCPClient

async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    search = await client.call_tool("web_search", {
        "query": "微博热搜 今日 AI 话题趋势",
        "engine": "search_pro",
        "count": 10,
    })
    # 2. 将搜索结果作为上下文传给 LLM 进行分析（Claude / GPT）
    # 注：趋势分析、摘要、情感分析由调用方 LLM 完成
```

```python
# 增强版：使用 web_search_enhanced（DuckDuckGo，免认证）
async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    search = await client.call_tool("web_search_enhanced", {
        "query": "百度热搜 今日 科技 趋势",
        "engine": "duckduckgo",
        "limit": 15,
    })
    data = json.loads(search[0].text)
    for item in data["items"]:
        print(f"- {item['title']}\n  {item['description']}")
```

**与 CLI 的差异**：
- `spide analyze` 内部使用 GLM-5.1 直接生成分析报告
- MCP 模式将数据获取与 LLM 推理**解耦**，让 Claude/GPT 等任意 LLM 都能做分析
- 适合跨模型协作场景（如用 GPT-4o 分析中文热搜）

**完整配置**：[docs/integration/claude-desktop-config.md](../../docs/integration/claude-desktop-config.md)
