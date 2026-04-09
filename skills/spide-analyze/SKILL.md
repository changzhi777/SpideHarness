---
name: spide-analyze
description: >
  AI 分析 — 趋势分析、内容摘要、情感分析、智能采集策略。
  当用户要求分析热搜趋势、生成摘要、获取采集建议时使用。
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
