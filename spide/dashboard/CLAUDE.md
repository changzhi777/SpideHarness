# Dashboard 数据看板模块

> [根目录](../../CLAUDE.md) → `spide/dashboard/`

## 职责

生成 HTML 数据看板，从 SQLite 聚合热搜数据并渲染为交互式网页。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 16 | 导出 collect_dashboard_data, render_dashboard |
| `collector.py` | 196 | DashboardCollector — SQLite 数据聚合 |
| `template.py` | 445 | HTML 模板 — 嵌入式 CSS/JS 的单页面看板 |
| `renderer.py` | 52 | write_dashboard — HTML 写入文件 |

## 使用方式

```bash
spide dashboard                  # 采集数据 → 生成看板 → 打开浏览器
spide dashboard -o report.html   # 指定输出路径
spide dashboard --no-open        # 不自动打开浏览器
```

## 数据聚合 (collector.py)

`collect_dashboard_data(db_path)` 从 SQLite 聚合：
- 各平台热搜统计（数量、最新热度）
- 时间分布趋势
- 高频关键词排名
- 平台对比数据

返回结构:
```python
{
    "total_count": int,
    "stats_summary": {"platforms": int, "time_range": str},
    "platform_stats": [...],
    "trend_data": [...],
    "top_keywords": [...],
}
```

## HTML 模板 (template.py)

嵌入式单页面设计（无外部依赖），包含：
- 平台统计卡片
- 热搜趋势折线图
- 平台对比柱状图
- 高频关键词词云（纯 CSS）
- 去重统计

## 依赖

- aiosqlite (数据读取)
- 标准库 (html, pathlib, webbrowser)

## 测试

- `tests/unit/test_dashboard.py`
