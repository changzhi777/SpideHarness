---
name: spide-deep-crawl
description: >
  深度采集 — 通过 MediaCrawler 从小红书/抖音/快手/B站/微博/贴吧/知乎
  采集详细内容、评论和创作者信息。当用户需要深度抓取特定平台内容时使用。
---

# Spide Deep Crawl — 深度采集

## 触发条件

用户要求深度采集特定平台的内容、评论、创作者信息时自动激活。

## 用法

```bash
# 搜索模式 — 按关键词搜索
spide deep-crawl -p xhs -m search -k "AI编程"
spide deep-crawl -p dy -m search -k "新能源,汽车"

# 详情模式 — 按内容 URL/ID 采集
spide deep-crawl -p bili -m detail -u "video_id1,video_id2"

# 创作者模式 — 按创作者 ID 采集
spide deep-crawl -p wb -m creator -c "user_id1,user_id2"

# 采集并保存到数据库
spide deep-crawl -p xhs -m search -k "AI" --save

# 调整采集数量
spide deep-crawl -p xhs -m search -k "AI" --max 50
```

## 支持的平台

| 平台 | 标识 | 说明 |
|------|------|------|
| 小红书 | `xhs` | 笔记内容、评论 |
| 抖音 | `dy` | 短视频、评论 |
| 快手 | `ks` | 短视频、评论 |
| B站 | `bili` | 视频、评论 |
| 微博 | `wb` | 微博内容、评论 |
| 百度贴吧 | `tieba` | 帖子、评论 |
| 知乎 | `zhihu` | 问答、评论 |

## 采集模式

| 模式 | 标识 | 用途 |
|------|------|------|
| 搜索 | `search` | 按关键词搜索内容 |
| 详情 | `detail` | 采集指定内容的详细信息 |
| 创作者 | `creator` | 采集指定创作者的内容 |

## 工作流程

1. 确认目标平台和采集模式
2. 根据模式准备参数（关键词/URL/创作者ID）
3. 运行 `spide deep-crawl` 命令
4. 查看采集结果（内容数、评论数、创作者数）
5. 根据需要保存或导出数据

## 注意事项

- 深度采集需要浏览器环境（Playwright）
- 首次使用需要登录对应平台（Cookie）
- 建议使用 `--headless` 模式（默认开启）
- 采集大量数据时注意平台限制
