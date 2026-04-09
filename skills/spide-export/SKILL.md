---
name: spide-export
description: >
  数据导出 — 将采集数据导出为 JSON / CSV / Excel 格式。
  当用户要求导出数据、下载报告、生成文件时使用。
---

# Spide Export — 数据导出

## 触发条件

用户要求将采集的热搜或深度采集数据导出为文件时自动激活。

## 用法

```bash
# 导出 JSON
spide export -s weibo -f json
spide export -s baidu -f json

# 导出 CSV
spide export -s weibo -f csv
spide export -s douyin -f csv

# 导出 Excel
spide export -s weibo -f excel
spide export -s zhihu -f excel

# 指定输出目录
spide export -s weibo -f json -o ./output

# 导出深度采集数据
spide export -s xhs -f excel
spide export -s dy -f csv -o ./reports
```

## 支持的格式

| 格式 | 标识 | 说明 |
|------|------|------|
| JSON | `json` | 结构化 JSON，适合程序处理 |
| JSONL | `jsonl` | 每行一条记录，适合流式处理 |
| CSV | `csv` | 表格格式，Excel 兼容 |
| Excel | `excel` | .xlsx 格式，含样式表头 |

## 支持的数据源

所有热搜源和深度采集平台均支持导出。

热搜源：`weibo` / `baidu` / `douyin` / `zhihu` / `bilibili`

## 工作流程

1. 确认要导出的数据源和格式
2. 运行 `spide export` 命令
3. 查看导出文件路径和大小
4. 如需指定目录，使用 `-o` 参数

## 注意事项

- 导出前需确保已有采集数据（先 `spide crawl` 或 `spide deep-crawl`）
- Excel 导出依赖 `openpyxl` 库
- 大数据量导出可能需要较长时间
