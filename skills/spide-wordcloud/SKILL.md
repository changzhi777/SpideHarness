---
name: spide-wordcloud
description: >
  词云生成 — 基于热搜或文本数据生成可视化词云。
  当用户要求生成词云、可视化关键词、查看高频词时使用。
---

# Spide Wordcloud — 词云生成

## 触发条件

用户要求生成词云、可视化关键词分布或查看高频词时自动激活。

## 用法

```bash
# 从热搜标题生成词云
spide wordcloud -s weibo
spide wordcloud -s baidu
spide wordcloud -s douyin

# 从自定义文本生成词云
spide wordcloud -t "AI,大模型,芯片,技术,编程,开发"

# 仅输出高频关键词（不生成图片）
spide wordcloud -s weibo --top-keywords

# 指定输出路径
spide wordcloud -s weibo -o ./output/wordcloud.png
```

## 功能特点

| 功能 | 说明 |
|------|------|
| 中文分词 | jieba 分词，精确切分中文文本 |
| 停用词过滤 | 自动过滤常见无意义词汇 |
| 高频词提取 | 提取 Top N 关键词及频率 |
| 词云渲染 | wordcloud 生成可视化图片 |

## 支持的数据源

| 数据源 | 标识 |
|--------|------|
| 微博热搜 | `weibo` |
| 百度热搜 | `baidu` |
| 抖音热点 | `douyin` |
| 知乎热榜 | `zhihu` |
| B站热搜 | `bilibili` |

## 工作流程

1. 确认数据来源（热搜源或自定义文本）
2. 运行 `spide wordcloud` 命令
3. 查看生成的词云图片路径
4. 如仅需关键词列表，使用 `--top-keywords`

## 注意事项

- 首次使用会下载 jieba 词典
- 生成图片使用 matplotlib Agg 后端（无需 GUI 环境）
- 支持 PNG 格式输出
