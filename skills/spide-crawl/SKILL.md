---
name: spide-crawl
description: >
  采集热搜数据 — 从微博/百度/抖音/知乎/B站采集实时热搜话题。
  当用户要求采集热搜、获取热门话题、查看趋势时使用此技能。
category: data_collection
---

# Spide Crawl — 热搜采集

## 触发条件

用户要求采集热点新闻、热搜榜单、热门话题时自动激活。

## 用法

```bash
# 单源采集
spide crawl --source weibo

# 采集所有热搜源
spide crawl --all

# 采集并保存到数据库
spide crawl -s weibo --save
spide crawl -s baidu --save
spide crawl -s douyin --save
spide crawl -s zhihu --save
spide crawl -s bilibili --save
```

## 支持的数据源

| 数据源 | 标识 | 刷新间隔 |
|--------|------|----------|
| 微博热搜 | `weibo` | 5 分钟 |
| 百度热搜 | `baidu` | 5 分钟 |
| 抖音热点 | `douyin` | 3 分钟 |
| 知乎热榜 | `zhihu` | 5 分钟 |
| B站热搜 | `bilibili` | 5 分钟 |

## 工作流程

1. 确认用户需要采集的数据源
2. 运行 `spide crawl -s <source>` 采集数据
3. 展示采集结果（标题、热度、排名）
4. 如果用户需要保存，加上 `--save` 参数

## 前提条件

- 项目已初始化：`spide init`
- UAPI 配置已完成：`configs/uapi.yaml`
- 运行 `spide doctor` 检查环境

## 通过 MCP 调用

如已配置 Claude Desktop / Cursor 等 MCP 客户端，可直接调用 `crawl_hot_topics` 工具：

```python
# 方式 1: Python MCP Client
from spide.mcp.client import MCPClient

async with MCPClient(server_command="spide", args=["mcp-serve"]) as client:
    result = await client.call_tool("crawl_hot_topics", {
        "source": "weibo",   # weibo/baidu/douyin/zhihu/bilibili
        "save": True,         # 是否持久化到 SQLite
    })
    # result[0].text 是 JSON 字符串
    topics = json.loads(result[0].text)
    for t in topics["items"][:5]:
        print(f"[{t['rank']}] {t['title']} (热度: {t['hot_value']:,})")
```

```javascript
// 方式 2: Claude Desktop 自然语言
// 用户输入: "用 spide-agent 采集微博热搜并保存"
// Claude 自动调用 crawl_hot_topics({source: "weibo", save: true})
```

**MCP 工具 vs CLI 对比**：

| 维度 | CLI (`spide crawl`) | MCP 工具 (`crawl_hot_topics`) |
|------|---------------------|-------------------------------|
| 鉴权 | UAPI Key 读 `configs/uapi.yaml` | 同上（Server 进程统一加载） |
| 返回 | Rich 表格 / 进度条 | 结构化 JSON |
| 适用 | 终端交互、批处理脚本 | AI Agent 工具调用、对话集成 |
| 数据库写入 | `--save` 参数 | `save: true` 参数 |

**完整配置**：[docs/integration/claude-desktop-config.md](../../docs/integration/claude-desktop-config.md)
