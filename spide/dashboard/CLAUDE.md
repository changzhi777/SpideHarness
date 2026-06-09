# Dashboard 数据看板模块（HTML 静态看板）

> [根目录](../../CLAUDE.md) > [spide](../) > **dashboard**

## 职责

生成静态 HTML 数据看板，从 SQLite 聚合热搜数据并渲染为交互式单页面网页（嵌入式 CSS/JS，无外部依赖）。由 `spide dashboard` CLI 命令调用。

> **注意**：此模块独立于 `dashboard/`（FastAPI Web 应用），两者职责不同：
> - `spide/dashboard/` — 生成单文件 HTML 看板，浏览器直接打开
> - `dashboard/` (Web) — FastAPI 后端 + 飞书 Bot + GitHub 热点采集

## 文件清单（3 个文件）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 导出 collect_dashboard_data, render_dashboard |
| `collector.py` | DashboardCollector — SQLite 数据聚合 |
| `template.py` | HTML 模板 — 嵌入式 CSS/JS 的单页面看板 |
| `renderer.py` | write_dashboard — HTML 写入文件 |

## 使用方式

```bash
spide dashboard                  # 采集数据 → 生成看板 → 打开浏览器
spide dashboard -o report.html   # 指定输出路径
spide dashboard --no-open        # 不自动打开浏览器
```

也可在 Python 中直接使用：
```python
from spide.dashboard import collect_dashboard_data, render_dashboard
from spide.dashboard.renderer import write_dashboard

data = await collect_dashboard_data(db_path="spide_data.db")
html = render_dashboard(data)
write_dashboard(html, Path("dashboard/index.html"))
```

## 数据聚合 (collector.py)

`collect_dashboard_data(db_path)` 从 SQLite 聚合：

- **总话题数** `total_count`
- **各平台统计** `platform_stats`（数量、最新热度、平台占比）
- **时间分布趋势** `trend_data`（按小时/天聚合）
- **高频关键词排名** `top_keywords`（jieba 分词 + 计数）
- **平台对比数据** `platform_comparison`

返回结构：
```python
{
    "total_count": int,
    "stats_summary": {"platforms": int, "time_range": str},
    "platform_stats": [{"source": "weibo", "count": 100, ...}],
    "trend_data": [{"time": "2026-06-09 09:00", "count": 50}],
    "top_keywords": [{"word": "AI", "count": 30}],
}
```

## HTML 模板 (template.py)

嵌入式单页面设计（无外部依赖），包含：

- **平台统计卡片** — 各平台话题数、最新热度
- **热搜趋势折线图** — Canvas 绘制
- **平台对比柱状图** — Canvas 绘制
- **高频关键词词云**（纯 CSS，无 wordcloud 图片依赖）
- **去重统计** — 数据质量指标
- **响应式布局** — 移动端适配

## 依赖

- aiosqlite (数据读取)
- jieba (中文分词)
- 标准库 (html, pathlib, webbrowser)

## 测试

- `tests/unit/test_dashboard.py` — DataCollector 聚合 + 渲染
