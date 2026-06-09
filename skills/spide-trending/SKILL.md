---
name: spide-trending
description: >
  GitHub AI 热点采集 — 从 GitHub 采集 AI / LLM / Agent / MCP / MLX 方向的热门仓库，
  支持趋势排序、按 stars 过滤、推送到飞书 Bot。当用户要求查看 GitHub 热门开源项目、
  跟踪 AI 技术趋势时使用此技能。
category: data_collection
---

# Spide Trending — GitHub AI 热点采集

## 触发条件

用户要求：
- 采集 GitHub 热门 AI / LLM / Agent 项目
- 跟踪技术趋势（哪些项目正在爆发）
- 把热点仓库推送到飞书群

时自动激活。

## 用法

### CLI 方式

```bash
# 采集 GitHub AI 热点（默认 50 个仓库）
spide trending

# 指定采集数量
spide trending --top 30

# 推送到飞书 Webhook
spide trending --push

# 设置飞书 Webhook URL
spide trending --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 同时采集 + 推送
spide trending --top 20 --push
```

### HTTP REST API 方式

```bash
# 获取 GitHub 热点仓库
curl http://localhost:8765/api/github/trending | jq

# 采集 + 一键推送飞书
curl -X POST http://localhost:8765/api/github/push | jq

# 设置 Webhook URL
curl -X POST http://localhost:8765/api/github/webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"}'
```

### 通过 MCP 调用

如已配置 Claude Desktop / Cursor 集成，可直接调用 MCP 工具：

```python
# 通过 MCP Client 调用（参考 spide.mcp.client.MCPClient）
result = await client.call_tool("fetch_repo_info", {
    "repo": "anthropics/claude-code",
    "info_type": "summary"
})
# 注意：GitHub 热点采集功能主要通过 HTTP API 暴露，
# MCP 端可用 fetch_repo_info 查询单个仓库详情
```

## 采集方向（5 主题 + 4 趋势）

| 方向 | 类别 | Query |
|------|------|-------|
| AI 人工智能 | `AI` | `topic:ai+topic:agent&sort=stars` |
| 大模型 LLM | `LLM` | `topic:llm+topic:large-language-model&sort=stars` |
| Agent 智能体 | `Agent` | `topic:ai-agent&sort=stars` |
| MCP 协议 | `MCP` | `topic:mcp+topic:model-context-protocol&sort=stars` |
| MLX 苹果AI | `MLX` | `topic:mlx&sort=stars` |
| 趋势新项目 | `trending` | `created:>YYYY-MM-DD&sort=stars`（最近 7 天） |

每方向默认 5-10 条，全局去重（按 `full_name`），按 `stars` 降序排序。

## 飞书卡片格式

推送时使用**交互式卡片**：
- **标题**：`<方向> | YYYY-MM-DD`（蓝色 template）
- **概览**：仓库数 / 方向数
- **每个分类一个区块**（最多 5 个 repo + 60 字描述 + ⭐/🍴）
- **底部**：SpideHarness 标识 + UTC 时间戳

## 前置条件

- 项目已初始化：`spide init`
- （可选）GitHub Token：`GITHUB_TOKEN`（提高 API 限额到 5000/h）
- （可选）飞书 Webhook URL：飞书群 → 群设置 → 机器人 → 添加机器人 → 自定义 Webhook

## 注意事项

- GitHub 未认证默认 60 次/小时，建议配置 `GITHUB_TOKEN`
- 飞书 Webhook 速率限制 100 req/min
- 采集结果会缓存在 `~/.spide_agent/cache/github_trending.json`（TTL 1h）
- 大数据量（>20 仓库）推送时飞书卡片可能截断，建议分批
