# Dashboard Web 应用

> [根目录](../CLAUDE.md) → `dashboard/`

## 职责

FastAPI Web 后端，从 SQLite 数据库提供 Dashboard REST API，同时集成飞书 Bot 事件回调和 GitHub AI 热点采集功能。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `api.py` | 314 | FastAPI 主应用 — Dashboard API + 采集触发 + GitHub 热点 + 飞书 Webhook |
| `feishu_handler.py` | 358 | 飞书 Bot 事件回调 — 指令解析 + 命令执行 + 事件订阅 |
| `github_trending.py` | 248 | GitHub AI 热点采集 — 5 方向 topic 搜索 + 飞书卡片推送 |
| `index.html` | 434 | 前端 Dashboard 页面 |

## 启动方式

```bash
uvicorn dashboard.api:app --reload --port 8765
```

## API 端点

### Dashboard 数据
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dashboard` | GET | Dashboard 全量数据（平台统计/Top 话题/分类/趋势） |
| `/api/topics` | GET | 话题列表（支持分页/筛选） |
| `/api/sources` | GET | 所有数据源平台 |
| `/api/crawl` | POST | 触发全量热搜采集 |
| `/` | GET | 前端页面 |

### 飞书 Bot（feishu_handler.py）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/feishu/event` | POST | 飞书事件回调（URL 验证 + 消息接收） |
| `/api/feishu/command` | POST | 通用命令执行接口 |

### GitHub 热点（github_trending.py）
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/github/trending` | GET | 获取 GitHub AI 热点仓库 |
| `/api/github/push` | POST | 采集 GitHub 热点并推送到飞书 |
| `/api/github/webhook` | POST | 设置飞书 Webhook URL |

## 飞书 Bot 支持的指令

通过飞书消息发送即可触发：

| 指令 | 说明 |
|------|------|
| `crawl <source\|all>` | 采集指定平台热搜 |
| `analyze <source>` | AI 分析指定平台 |
| `status` | 查看系统状态 |
| `track <source> [N]` | 深度追踪 Top N 话题 |
| `export <source>` | 导出数据 |
| `batch <p1,p2>` | 批量采集 |
| `help` | 显示帮助 |

## GitHub 热点采集方向

AI 人工智能 / 大模型 LLM / Agent 智能体 / MCP 协议 / MLX 苹果AI，加上近期热门新项目（7 天内高星）。

## 依赖

- FastAPI + uvicorn
- aiohttp（GitHub API + 飞书 Webhook）
- SQLite（读取热搜数据）

## 注意

- 此目录独立于 `spide/dashboard/`（HTML 看板生成模块）
- 数据库路径: `../spide_data.db`
- 飞书凭证通过 `set_feishu_config()` 动态设置
