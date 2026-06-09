# SpideHarness Agent — Skills 索引

> 版本: V3.1.1 | 更新: 2026-06-09 | 数量: 17 个 Skills

本文档列出 SpideHarness Agent 提供的全部 AI Skills，按场景分类。每个 Skill 是 `SKILL.md` 描述的**结构化能力单元**，可被 Claude Desktop、Cursor、Cline 等 MCP 客户端自动发现和调用。

---

## 1. 分类总览

| 分类 | 数量 | Skills |
|------|------|--------|
| **数据采集** | 5 | spide-crawl, spide-deep-crawl, spide-batch, spide-trending, spide-search-fallback |
| **AI 分析** | 1 | spide-analyze |
| **搜索路由** | 1 | spide-search |
| **数据导出** | 2 | spide-export, spide-wordcloud |
| **自动化** | 4 | spide-schedule, spide-oneshot, spide-monitor, spide-browser |
| **集成** | 1 | spide-feishu |
| **元能力** | 3 | spide-usage, spide-explorer, spide-autofix |
| **总计** | **17** | — |

---

## 2. 完整 Skills 清单

### 2.1 数据采集（5 个）

#### [spide-crawl](./spide-crawl/SKILL.md)
**热搜采集** — 从微博/百度/抖音/知乎/B站采集实时热搜话题。
- **CLI**: `spide crawl -s weibo --save`
- **MCP**: `crawl_hot_topics({source, save})`
- **触发**: "采集微博热搜" / "获取热门话题" / "查看今日热搜"

#### [spide-deep-crawl](./spide-deep-crawl/SKILL.md)
**深度采集** — 通过 MediaCrawler 从 7 平台采集内容/评论/创作者。
- **CLI**: `spide deep-crawl -p xhs -m search -k "AI"`
- **MCP**: `deep_crawl_hot_topics({platform, mode, keywords, max_notes})`
- **触发**: "深度采集小红书" / "抓抖音评论"

#### [spide-batch](./spide-batch/SKILL.md)
**批量并行采集** — 多平台并发搜索，支持并发控制和断点续采。
- **CLI**: `spide batch-crawl -p xhs,dy,bili -k "AI"`
- **触发**: "同时采集多个平台" / "批量抓取关键词"

#### [spide-trending](./spide-trending/SKILL.md)
**GitHub AI 热点采集** — 跟踪 AI/LLM/Agent/MCP/MLX 方向的热门仓库。
- **CLI**: `spide trending --top 30 --push`
- **HTTP**: `POST /api/github/trending` / `POST /api/github/push`
- **触发**: "GitHub 热门项目" / "AI 趋势" / "推送到飞书"

#### [spide-search-fallback](./spide-search-fallback/SKILL.md)
**错误恢复搜索** — 采集失败 3 次后，从 GitHub 搜索类似代码并生成新适配器。
- **CLI**: 通过搜索 + LLM 自动激活
- **MCP**: `web_search_enhanced` + `fetch_repo_info` 组合
- **触发**: "采集失败" / "去 GitHub 找方案"

### 2.2 AI 分析（1 个）

#### [spide-analyze](./spide-analyze/SKILL.md)
**AI 分析** — 趋势分析、内容摘要、情感分析、智能采集策略。
- **CLI**: `spide analyze -s weibo --strategy`
- **MCP**: `web_search` + 调用方 LLM 推理
- **触发**: "分析热搜趋势" / "生成摘要" / "推荐下一步"

### 2.3 搜索路由（1 个）

#### [spide-search](./spide-search/SKILL.md)
**智能搜索路由器** — 基于话题和场景，将查询路由到最佳的 opencli 搜索源。
- **CLI**: 通过 `opencli` 命令调用
- **前置**: `npm install -g @jackwener/opencli`
- **触发**: "搜索" / "查询" / "查找资料"

### 2.4 数据导出（2 个）

#### [spide-export](./spide-export/SKILL.md)
**数据导出** — 导出为 JSON / CSV / Excel / JSONL 格式。
- **CLI**: `spide export -s weibo -f excel`
- **触发**: "导出数据" / "下载报告" / "生成 Excel"

#### [spide-wordcloud](./spide-wordcloud/SKILL.md)
**词云生成** — 从话题标题生成可视化词云图。
- **CLI**: `spide wordcloud -s weibo`
- **触发**: "生成词云" / "话题可视化"

### 2.5 自动化（4 个）

#### [spide-schedule](./spide-schedule/SKILL.md)
**定时调度** — Cron 表达式定时执行采集任务。
- **CLI**: `spide schedule start`
- **触发**: "定时采集" / "每天 9 点抓热搜"

#### [spide-oneshot](./spide-oneshot/SKILL.md)
**一次性任务** — 快速运行一次性采集或分析任务。
- **CLI**: `spide oneshot "采集微博热搜"`
- **触发**: "快速跑一次" / "临时任务"

#### [spide-monitor](./spide-monitor/SKILL.md)
**关键词监控与告警** — 规则引擎 + 多渠道通知（Log/MQTT/Webhook/飞书）。
- **CLI**: `spide monitor --rules configs/alert_rules.yaml`
- **触发**: "监控关键词" / "设置告警" / "推送到飞书"

#### [spide-browser](./spide-browser/SKILL.md)
**浏览器自动化** — 通过 Playwright 访问网页（登录、交互、截图）。
- **CLI**: `spide browser <url>`
- **触发**: "打开网页" / "浏览器操作"

### 2.6 集成（1 个）

#### [spide-feishu](./spide-feishu/SKILL.md)
**飞书 Bot 集成** — 通过飞书事件回调执行 spide 命令（自然语言指令）。
- **HTTP**: `POST /api/feishu/event` / `POST /api/feishu/command`
- **触发**: "飞书集成" / "机器人指令" / "群通知"

### 2.7 元能力（3 个）

#### [spide-usage](./spide-usage/SKILL.md)
**使用指南** — CLI 命令速查、最佳实践。
- **CLI**: `spide --help`
- **触发**: "怎么用" / "命令列表"

#### [spide-explorer](./spide-explorer/SKILL.md)
**项目探索** — 全仓扫描、模块索引、架构理解。
- **CLI**: 自动激活
- **触发**: "项目结构" / "模块列表"

#### [spide-autofix](./spide-autofix/SKILL.md)
**自动修复** — 常见错误自动诊断与修复。
- **CLI**: 自动激活
- **触发**: "修复" / "出错" / "不工作"

---

## 3. MCP 工具映射

下表展示 **8 个 MCP 工具 ↔ 17 个 Skills** 的对应关系：

| MCP 工具 | 主要 Skill | 间接关联 |
|----------|------------|----------|
| `crawl_hot_topics` | spide-crawl | spide-batch, spide-trending |
| `web_search` | spide-analyze | spide-search |
| `web_search_enhanced` | spide-search-fallback | spide-search |
| `fetch_web_page` | (直接调用) | spide-browser, spide-search |
| `fetch_repo_info` | spide-search-fallback | spide-trending |
| `manage_memory` | (基础设施) | 所有 Skills |
| `health_check` | (基础设施) | spide-usage |
| `deep_crawl_hot_topics` | spide-deep-crawl | spide-batch |

> **注意**：4 个核心 Skills（spide-crawl / spide-analyze / spide-search-fallback / spide-deep-crawl）的 `SKILL.md` 已包含完整的 **"通过 MCP 调用"** 章节，含 Python 代码示例 + Claude Desktop 自然语言示例。

---

## 4. CLI 命令映射

| CLI 命令 (24 个) | 对应 Skill |
|------------------|------------|
| `spide init` / `spide doctor` / `spide config` | spide-usage |
| `spide crawl` | spide-crawl |
| `spide crawl-diff` | spide-crawl |
| `spide deep-crawl` | spide-deep-crawl |
| `spide batch-crawl` | spide-batch |
| `spide run` | spide-oneshot |
| `spide analyze` | spide-analyze |
| `spide monitor` | spide-monitor |
| `spide track` | spide-analyze |
| `spide cross-analyze` | spide-analyze |
| `spide export` | spide-export |
| `spide wordcloud` | spide-wordcloud |
| `spide dedup` | spide-autofix |
| `spide dashboard` | spide-usage |
| `spide schedule` | spide-schedule |
| `spide timed-search` | spide-schedule |
| `spide mcp-serve` | (基础设施) |
| `spide mqtt` | spide-monitor |
| `spide memory` | (基础设施) |
| `spide trending` (新增) | spide-trending |
| `spide search` (CLI 子命令) | spide-search |

---

## 5. 如何使用 Skills

### 5.1 在 Claude Desktop 中

Skills 通过 MCP 工具暴露。Claude 自动根据用户输入选择合适的工具：
```
用户: "采集微博热搜"
Claude: (自动调用 crawl_hot_topics 工具)
```

无需手动激活 Skills。Claude 会根据工具的 `description` 自动匹配。

### 5.2 在 Cursor / Cline 中

类似 Claude Desktop。打开 Composer / Cline 面板，自然语言描述任务即可。

### 5.3 在自定义 MCP Client 中

```python
from spide.mcp.client import MCPClient

async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    tools = await client.list_tools()
    # 选择需要的工具并调用
    result = await client.call_tool("crawl_hot_topics", {"source": "weibo"})
```

### 5.4 直接读 SKILL.md

每个 Skill 目录下都有 `SKILL.md`，是**人/AI 都能读**的结构化文档。包含：
- **YAML frontmatter** — `name` + `description`（AI 用于自动匹配）
- **触发条件** — 何时使用
- **用法** — CLI / HTTP / MCP 三种调用方式
- **参数** — 必填/可选
- **示例** — 命令、JSON、代码
- **前置条件 / 注意事项** — 部署与限制

---

## 6. 添加新 Skill

新 Skill 需满足：

1. **目录结构**：`skills/<skill-name>/SKILL.md`
2. **frontmatter 格式**：
   ```yaml
   ---
   name: spide-xxx
   description: >
     一句话描述 + 触发场景（AI 用于自动匹配）
   ---
   ```
3. **章节结构**（推荐）：
   - `# Spide XXX — 标题`
   - `## 触发条件`
   - `## 用法`（CLI / HTTP / MCP）
   - `## 参数说明` / `## 支持的 X`
   - `## 工作流程`
   - `## 前提条件`
   - `## 通过 MCP 调用`（如适用）
   - `## 注意事项`

4. **更新 capability_registry.py**：在 `dashboard/api.py` 的 `_SKILL_CATEGORY_MAP` 中添加 category 映射。

5. **验证**：`curl http://localhost:8765/.well-known/agent.json | jq .capabilities.skills` 应包含新 Skill。

---

## 7. 相关文档

- [INTEGRATION.md](../docs/integration/INTEGRATION.md) — 三视角综合集成
- [mcp-api-reference.md](../docs/mcp-api-reference.md) — MCP 协议对接
- [http-api-reference.md](../docs/http-api-reference.md) — HTTP REST API
- [claude-desktop-config.md](../docs/integration/claude-desktop-config.md) — 客户端配置手册
- [CLAUDE.md](../CLAUDE.md) — 项目主文档

---

*Copyright (C) 2026 IoTchange - All Rights Reserved*
