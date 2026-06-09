# Dashboard Web 应用

> [根目录](../CLAUDE.md) → `dashboard/`

## 职责

FastAPI Web 后端，从 SQLite 数据库提供 Dashboard REST API，同时集成飞书 Bot 事件回调和 GitHub AI 热点采集功能。前端为单文件 SPA（React 18 UMD + Tailwind CDN + Chart.js 4）。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `api.py` | 314 | FastAPI 主应用 — Dashboard API + 采集触发 + GitHub 热点 + 飞书 Webhook 路由注册 |
| `feishu_handler.py` | 359 | 飞书 Bot 事件回调 — 指令解析（regex）+ 子进程命令执行 + 事件订阅 |
| `github_trending.py` | 249 | GitHub AI 热点采集 — 9 个查询（5 主题 + 4 trending）+ 飞书卡片格式化 |
| `index.html` | 434 | 前端 Dashboard 页面（React 18 UMD + Tailwind CDN + Chart.js 4 + Inter 字体） |

## 启动方式

```bash
uvicorn dashboard.api:app --reload --port 8765
```

访问 `http://localhost:8765/` 查看 Dashboard。

## 技术栈

### 后端
- **FastAPI** + **uvicorn** — Web 框架
- **aiohttp** — GitHub API + 飞书 Webhook 推送
- **sqlite3**（标准库）— 读取 `spide_data.db`
- **subprocess** — 调用 `python -m spide <cmd>` 子进程执行 CLI 命令

### 前端
- **React 18** UMD（CDN 加载，无构建步骤）
- **Tailwind CSS**（CDN JIT）
- **Chart.js 4** — 平台分布柱状图 + 分类饼图
- **Inter** 字体（Google Fonts）
- **设计语言**：深色主题（`#0f181f` 渐变背景 + `rgba(64,190,122,0.x)` 绿色点缀）

## 数据流

```
数据库 spide_data.db
  ↓
FastAPI 读取 + 聚合（api.py）
  ↓
window.__DASHBOARD_DATA__ 注入（HTML 渲染时）
  ↓
React 18 UMD 渲染（index.html）
  ↓
Chart.js 4 绘制图表 + 排行榜
```

后端在 `api.py` 启动时计算 Dashboard 全量数据（平台统计/Top 话题/分类/平台榜单/最近采集时间），序列化为 JSON 注入到 `window.__DASHBOARD_DATA__`。前端读此变量直接渲染（无 fetch，无 API 轮询）。

## API 端点

### Dashboard 数据（api.py）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard` | GET | Dashboard 全量数据（平台统计/Top 话题/分类/趋势） |
| `/api/topics` | GET | 话题列表（支持分页/筛选） |
| `/api/sources` | GET | 所有数据源平台 |
| `/api/crawl` | POST | 触发全量热搜采集 |
| `/` | GET | 前端页面（注入 `__DASHBOARD_DATA__`） |

### 飞书 Bot（feishu_handler.py）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/feishu/event` | POST | 飞书事件回调（URL 验证 `url_verification` + 消息接收 `im.message.receive_v1`） |
| `/api/feishu/command` | POST | 通用命令执行接口（支持 `text` 自动解析 或 `command` 直接指定） |

### GitHub 热点（github_trending.py）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/github/trending` | GET | 获取 GitHub AI 热点仓库 |
| `/api/github/push` | POST | 采集 GitHub 热点并推送到飞书 |
| `/api/github/webhook` | POST | 设置飞书 Webhook URL |

## 飞书 Bot 指令解析（feishu_handler.py）

**指令正则**：`^(crawl|analyze|status|track|export|help|batch)\s*(.*)`（忽略大小写）

| 指令 | 格式 | 默认值 | CLI 调用 |
|------|------|--------|----------|
| `help` | `help` | — | 返回帮助文本 |
| `status` | `status` | — | 直接查 SQLite（话题数/平台数/最近采集） |
| `crawl` | `crawl <source\|all>` | `all` | `spide crawl --all --save` / `spide crawl -s <src> --save` |
| `analyze` | `analyze <source>` | `weibo` | `spide analyze -s <src>` (timeout 180s) |
| `track` | `track <source> [N]` | `weibo`, `N=10` | `spide track -s <src> --top <N>` (timeout 180s) |
| `export` | `export <source>` | `weibo` | `spide export -s <src> -f excel` (timeout 60s) |
| `batch` | `batch <p1,p2>` | `["xhs", "dy"]` | `spide batch-crawl -p <p1>,<p2>` (timeout 300s) |

**消息解析**：
- 文本消息（`text`）— 直接取 `content.text`
- 富文本消息（`post`）— 提取 `title` + 所有 line_blocks 的 `text` 拼接
- 其他类型 — 尝试取 `content.text`

**子进程执行**：`_run_spide_sync()` 用 `subprocess.run([sys.executable, "-m", "spide"] + args, cwd=PROJECT_ROOT)`，通过 `loop.run_in_executor` 转异步避免阻塞事件循环。

**飞书事件验证**：
- `url_verification` — 校验 `token`（如配置了 `_FEISHU_VERIFICATION_TOKEN`）后回 `challenge`
- 消息事件 — 调用 `parse_command()` → `execute_command()` → 返回 JSON 响应

**配置动态注入**：`set_feishu_config(app_id, app_secret, verification_token, encrypt_key)` 运行时设置全局变量。

## GitHub AI 热点采集（github_trending.py）

**5 主题查询**（TOPIC_QUERIES）— 按 `stars` 排序，每方向 5 条：
| 主题 | Query |
|------|-------|
| AI 人工智能 | `topic:ai+topic:agent&sort=stars&order=desc&per_page=5` |
| 大模型 LLM | `topic:llm+topic:large-language-model&sort=stars&order=desc&per_page=5` |
| Agent 智能体 | `topic:ai-agent&sort=stars&order=desc&per_page=5` |
| MCP 协议 | `topic:mcp+topic:model-context-protocol&sort=stars&order=desc&per_page=5` |
| MLX 苹果AI | `topic:mlx&sort=stars&order=desc&per_page=5` |

**4 备用查询**（TRENDING_QUERIES）— 最近 7 天高星新项目（`created:>2026-05-20`）：
- AI Agent 热门 / LLM 新项目 / MCP 新项目 / MLX 新项目（各 5-8 条）

**GitHubRepo 模型**：
- `full_name` / `description` / `stars` / `forks` / `language` / `html_url` / `topics` / `updated_at` / `category`

**`collect()` 流程**：
1. 遍历 TOPIC_QUERIES + TRENDING_QUERIES（共 9 个查询）
2. 每个查询限制前 10 条
3. 全局去重（按 `full_name`）
4. 按 `stars` 降序排序

**飞书卡片格式**（`format_feishu_card`）：
- 标题：`<方向> | YYYY-MM-DD`（蓝色 template）
- 概览：仓库数 / 方向数
- 每个分类一个区块（最多 5 个 repo + 60 字描述 + ⭐/🍴）
- 底部：SpideHarness 标识 + UTC 时间戳

**API 配置**：`_GITHUB_API = "https://api.github.com"`，`_TIMEOUT = 20s`，`_HEADERS = {Accept, User-Agent: SpideAgent/3.1}`

## 前端页面结构（index.html）

**单文件 SPA**（无构建）— 注入数据后 React.createElement 渲染。

| 组件 | 功能 |
|------|------|
| `Header` | 顶部导航（蜘蛛 logo + 标题 + v3.1.1 DEV 徽章 + 实时时钟） |
| `Clock` | 实时日期/时钟（每秒更新） |
| `StatsRow` | 4 张统计卡片（总话题/平台数/今日新增/平均热度） |
| `PlatformChart` | Chart.js 水平柱状图（平台分布） |
| `CategoryPie` | Chart.js 环形饼图（分类占比，中心显示分类数） |
| `RankingTable` | 热搜排行榜 Top 20（前 3 名金银铜配色） |
| `PlatformTop3Group` | 各平台 Top 3 卡片（左侧 3px 颜色条） |
| `EmptyState` | 空数据状态（提示运行 `spide crawl --all`） |
| `Footer` | 版权信息 |

**平台配色映射**（PLATFORM_MAP）：
- weibo `#E6162D` 红色 / baidu `#4E6EF2` 蓝色 / douyin `#FE2C55` 粉红
- zhihu `#0066FF` / bilibili `#00A1D6` 青色 / kuaishou `#FF8C00` 橙色
- tieba `#4879BD` / web_search `#34D399` / custom `#FBBF24`

**工具函数**：
- `fmt(n)` — 千分位格式化
- `shortTime(iso)` — ISO 时间 → HH:MM
- `hexToRgba(hex, alpha)` — 颜色转 rgba

**背景装饰**：3 个 `blur-3xl` 模糊光斑（绿色 `rgba(64,190,122,0.04~0.08)`）增强视觉层次。

## 依赖

### Python
- `fastapi` + `uvicorn` — Web 框架
- `aiohttp` — GitHub API + 飞书 Webhook
- `subprocess`（标准库）— 调用 spide CLI

### 前端 CDN
- React 18 UMD：`unpkg.com/react@18`
- ReactDOM 18 UMD：`unpkg.com/react-dom@18`
- Tailwind CSS：`cdn.tailwindcss.com`
- Chart.js 4：`cdn.jsdelivr.net/npm/chart.js@4`
- Inter 字体：`fonts.googleapis.com`

## 注意

- 此目录独立于 `spide/dashboard/`（HTML 看板生成模块）
- 数据库路径: `../spide_data.db`
- 飞书凭证通过 `set_feishu_config()` 动态设置（默认空字符串，不启用签名验证）
- 前端数据通过 `window.__DASHBOARD_DATA__` 在 HTML 渲染时注入（无运行时 API 调用）
- 9 个 GitHub 查询全部串行执行（无并发）
- 卡片模板：`template: "blue"`（飞书固定配色）
