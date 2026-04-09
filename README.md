# Spide Agent

> 热点新闻信息抓取与智能整理 Agent CLI 工具

基于 **Harness Engineering** 架构的热点新闻采集 Agent，支持 12 个数据源（5 个热搜 API + 7 个深度采集平台），AI 智能分析，MCP 协议，MQTT 通讯，多格式导出。

## 特性

- **多源热搜采集** — 微博/百度/抖音/知乎/B站，5 分钟自动刷新
- **7 平台深度采集** — 小红书/抖音/快手/B站/微博/贴吧/知乎（MediaCrawler 子进程桥接）
- **批量并行调度** — 多平台并发采集，Semaphore 控制并发数
- **定时任务** — Cron-like 调度器，可配置间隔和运行次数
- **AI 分析** — 内容摘要/情感分析/趋势分析/智能采集策略（GLM-5.1）
- **词云生成** — jieba 分词 + wordcloud 可视化
- **多格式导出** — JSON / JSONL / CSV / Excel
- **MCP 协议** — Model Context Protocol Server/Client，5 个工具注册
- **MQTT 通讯** — EMQX Cloud TLS 加密连接，发布/订阅模式
- **双模型驱动** — GLM-5.1（文本）+ GLM-5V-Turbo（视觉多模态）
- **SQLite 持久化** — aiosqlite 异步存储，Pydantic v2 数据模型
- **Redis 缓存** — URL 去重，热数据缓存

## 架构

```
CLI (Typer)
  └─ Harness Engine (调度器)
       ├─ Spider 引擎
       │    ├─ UAPI 客户端 (5 热搜源)
       │    ├─ MediaCrawler 适配器 (7 深度平台)
       │    ├─ BatchScheduler (并行调度)
       │    ├─ TaskScheduler (定时任务)
       │    └─ Pipeline (解析 + 去重)
       ├─ AI 分析
       │    ├─ ContentSummarizer (摘要)
       │    ├─ SentimentAnalyzer (情感)
       │    ├─ TrendAnalyzer (趋势)
       │    ├─ SmartCrawlStrategy (策略)
       │    └─ WordCloudGenerator (词云)
       ├─ MCP 协议层
       │    ├─ Server (工具注册)
       │    └─ Client (模型调用)
       ├─ MQTT 通讯
       │    ├─ Publisher
       │    └─ Subscriber
       ├─ 存储层
       │    ├─ SQLite (aiosqlite)
       │    ├─ Redis (aioredis)
       │    └─ Exporter (JSON/CSV/Excel)
       └─ 消息总线 (asyncio.Queue)
```

## 快速开始

### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Redis 7.0+（可选，用于缓存）

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd a_Spide_agent

# 安装依赖
uv sync

# 初始化工作空间
spide init

# 环境检查
spide doctor
```

### 配置

在 `configs/` 目录下创建配置文件：

```bash
configs/
├── default.yaml    # 默认配置
├── llm.yaml        # 智谱 AI API Key
├── mqtt.yaml       # EMQX Cloud 凭证
└── uapi.yaml       # UAPI API Key
```

配置模板参见 `configs/default.yaml`。

## 命令参考

### 基础命令

```bash
spide init                       # 初始化工作空间
spide doctor                     # 环境健康检查
spide config                     # 配置向导
spide -v                         # 显示版本号
```

### 热搜采集

```bash
spide crawl -s weibo             # 采集微博热搜
spide crawl -s baidu             # 采集百度热搜
spide crawl -a                   # 采集所有热搜源
spide crawl -s weibo --save      # 采集并保存到 SQLite
```

支持的数据源：`weibo` / `baidu` / `douyin` / `zhihu` / `bilibili`

### 深度采集

```bash
spide deep-crawl -p xhs -m search -k "AI编程"     # 小红书搜索
spide deep-crawl -p dy -m detail -u "URL1,URL2"    # 抖音详情
spide deep-crawl -p bili -m creator -c "UID1"      # B站创作者
spide deep-crawl -p xhs -k "关键词" --save          # 采集并保存
```

支持的平台：`xhs` / `dy` / `ks` / `bili` / `wb` / `tieba` / `zhihu`

### 批量采集

```bash
spide batch-crawl -p xhs,dy,bili -k "AI"           # 3平台并行采集
spide batch-crawl -p xhs,dy -c 2 --save             # 并发2，保存到数据库
spide batch-crawl -p xhs,dy -e json -o ./output     # 导出 JSON
```

### 定时调度

```bash
spide schedule start                                # 默认: 微博/百度/知乎 每5分钟
spide schedule start -c schedule.yaml -d 3600       # 自定义配置，运行1小时
spide schedule status                               # 查看状态
```

### AI 分析

```bash
spide analyze -s weibo                              # 趋势分析 + 摘要
spide analyze -s weibo --strategy                   # + 智能采集策略
spide analyze -k "AI,大模型"                         # 关键词分析
```

### 数据导出

```bash
spide export -s weibo -f json                       # 导出 JSON
spide export -s weibo -f csv -o ./output            # 导出 CSV
spide export -s weibo -f excel                      # 导出 Excel
```

### 词云生成

```bash
spide wordcloud -s weibo                            # 从热搜标题生成词云
spide wordcloud -t "AI,技术,大模型"                   # 从文本生成词云
spide wordcloud -s weibo --top-keywords             # 仅输出高频关键词
```

### 其他

```bash
spide run "帮我分析今日热搜趋势"                      # Agent 对话模式
spide mcp-serve                                     # 启动 MCP Server
spide mqtt pub <topic> <payload>                    # MQTT 发布
spide mqtt sub <topic> -n 10                        # MQTT 订阅
spide memory list                                   # 查看记忆
spide memory add <title> <content>                  # 添加记忆
```

## 项目结构

```
a_Spide_agent/
├── spide/                          # 主包
│   ├── cli.py                      # CLI 入口 (14 命令)
│   ├── config.py                   # YAML 配置加载
│   ├── harness/engine.py           # Harness 调度引擎
│   ├── spider/                     # 爬虫引擎
│   │   ├── uapi_client.py          # UAPI 热搜客户端
│   │   ├── media_crawler_adapter.py # MediaCrawler 桥接
│   │   ├── batch_scheduler.py      # 批量并行调度
│   │   ├── task_scheduler.py       # 定时任务调度
│   │   ├── fetcher.py              # HTTP 抓取器
│   │   └── pipeline.py             # 数据解析+去重
│   ├── analysis/                   # AI 分析
│   │   ├── summarizer.py           # 摘要/情感/趋势/策略
│   │   └── wordcloud_generator.py  # 词云生成
│   ├── storage/                    # 数据存储
│   │   ├── models.py               # Pydantic 数据模型
│   │   ├── sqlite_repo.py          # SQLite 异步仓库
│   │   ├── redis_cache.py          # Redis 缓存
│   │   └── exporter.py             # 多格式导出
│   ├── mcp/                        # MCP 协议
│   │   ├── server.py               # MCP Server
│   │   ├── client.py               # MCP Client
│   │   └── tools.py                # 工具定义
│   ├── mqtt/                       # MQTT 通讯
│   │   └── client.py               # MQTT 客户端
│   ├── queue/                      # 消息总线
│   │   └── broker.py               # asyncio.Queue 封装
│   └── ...
├── tests/                          # 测试 (238 用例)
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   └── e2e/                        # 端到端测试
├── configs/                        # 配置文件 (不入 Git)
├── MediaCrawler/                   # MediaCrawler 子项目
└── pyproject.toml                  # 项目依赖
```

## 技术栈

| 层面 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.12+ | 主开发语言 |
| CLI | Typer | 命令行界面 |
| 异步 | asyncio + aiohttp | HTTP 抓取与协程调度 |
| 数据模型 | Pydantic v2 | 数据验证与序列化 |
| 存储 | SQLite (aiosqlite) | 持久化存储 |
| 缓存 | Redis (aioredis) | URL 去重与热数据缓存 |
| MQTT | aiomqtt | EMQX Cloud 消息通讯 |
| MCP | mcp-sdk | Model Context Protocol |
| LLM | GLM-5.1 + GLM-5V-Turbo | 文本/视觉 AI |
| 数据源 | UApiPro | 100+ 免费 API |
| 深度采集 | MediaCrawler | 7 平台 Playwright 爬虫 |
| 分词 | jieba | 中文分词 |
| 词云 | wordcloud | 可视化 |
| 导出 | openpyxl | Excel 生成 |
| 测试 | pytest + pytest-asyncio | 238 测试用例 |
| Lint | Ruff | 代码检查与格式化 |

## AI Agent Skills

Spide Agent 提供 7 个标准化 AI Skills，支持 OpenClaw / Claude Code 一键安装：

```bash
# 一键安装到 Claude Code + OpenClaw
./install-skills.sh

# 仅安装到 Claude Code
./install-skills.sh --claude

# 验证安装
./install-skills.sh --verify
```

| Skill | 命令 | 功能 |
|-------|------|------|
| `spide-crawl` | `/spide-crawl` | 热搜采集 |
| `spide-deep-crawl` | `/spide-deep-crawl` | 深度采集 |
| `spide-analyze` | `/spide-analyze` | AI 分析 |
| `spide-export` | `/spide-export` | 数据导出 |
| `spide-wordcloud` | `/spide-wordcloud` | 词云生成 |
| `spide-batch` | `/spide-batch` | 批量并行采集 |
| `spide-schedule` | `/spide-schedule` | 定时调度 |

详细安装与使用说明参见 [docs/skills-guide.md](docs/skills-guide.md)。

## 开发

```bash
# 安装开发依赖
uv sync --extra dev

# 运行测试
uv run pytest

# 代码检查
uv run ruff check spide/ tests/

# 格式化
uv run ruff format spide/ tests/
```

## 许可证

Copyright (C) 2026 IoTchange - All Rights Reserved

Author: 外星动物（常智） / IoTchange / 14455975@qq.com

本软件为专有软件，未经授权不得复制、修改或分发。
