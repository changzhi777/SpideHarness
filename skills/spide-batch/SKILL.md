---
name: spide-batch
description: >
  批量并行采集 — 多平台并发搜索采集，支持并发控制和数据导出。
  当用户要求同时采集多个平台、批量搜索关键词时使用。
---

# Spide Batch — 批量并行采集

## 触发条件

用户要求同时采集多个平台内容、批量搜索关键词时自动激活。

## 用法

```bash
# 多平台并行搜索
spide batch-crawl -p xhs,dy,bili -k "AI编程"

# 指定并发数
spide batch-crawl -p xhs,dy -c 2 -k "新能源"

# 采集并保存到数据库
spide batch-crawl -p xhs,dy,bili -k "AI" --save

# 采集并导出
spide batch-crawl -p xhs,dy -k "技术" -e json -o ./output

# 全平台采集
spide batch-crawl -p xhs,dy,ks,bili,wb,tieba,zhihu -k "热门话题"
```

## 支持的平台

| 平台 | 标识 |
|------|------|
| 小红书 | `xhs` |
| 抖音 | `dy` |
| 快手 | `ks` |
| B站 | `bili` |
| 微博 | `wb` |
| 百度贴吧 | `tieba` |
| 知乎 | `zhihu` |

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p` | 目标平台，逗号分隔 | 必填 |
| `-k` | 搜索关键词 | 必填 |
| `-c` | 最大并发数 | 3 |
| `--save` | 保存到数据库 | false |
| `-e` | 导出格式 (json/csv/excel) | - |
| `-o` | 导出目录 | ./output |

## 工作流程

1. 确认目标平台和关键词
2. 根据平台数量调整并发数
3. 运行 `spide batch-crawl` 命令
4. 查看各平台采集结果汇总
5. 根据需要保存或导出数据

## 注意事项

- 并发数建议不超过 5，避免触发平台限制
- 深度采集需要浏览器环境（Playwright）
- 部分平台可能需要登录 Cookie
- 采集结果按平台汇总显示内容数/评论数/创作者数
