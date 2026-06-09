# Spide CLI 使用指南

> SpideHarness Agent — 热点新闻抓取 Agent CLI
> 版本：v1.1.1 | 更新：2026-04-13

---

## 目录

- [快速开始](#快速开始)
- [全局选项](#全局选项)
- [命令总览](#命令总览)
- [命令详解](#命令详解)
  - [init — 初始化](#init--初始化)
  - [config — 配置](#config--配置)
  - [doctor — 环境检查](#doctor--环境检查)
  - [crawl — 热搜采集](#crawl--热搜采集)
  - [deep-crawl — 深度采集](#deep-crawl--深度采集)
  - [run — Agent 任务](#run--agent-任务)
  - [dashboard — 数据看板](#dashboard--数据看板)
  - [dedup — 数据去重](#dedup--数据去重)
  - [analyze — AI 分析](#analyze--ai-分析)
  - [export — 数据导出](#export--数据导出)
  - [wordcloud — 词云生成](#wordcloud--词云生成)
  - [batch-crawl — 批量采集](#batch-crawl--批量采集)
  - [schedule — 定时调度](#schedule--定时调度)
  - [mcp-serve — MCP 服务](#mcp-serve--mcp-服务)
  - [memory — 记忆管理](#memory--记忆管理)
  - [mqtt — MQTT 通讯](#mqtt--mqtt-通讯)
- [API 服务](#api-服务)
- [典型工作流](#典型工作流)

---

## 快速开始

```bash
# 安装（项目目录下）
uv sync

# 初始化工作空间
spide init

# 环境检查
spide doctor

# 采集微博热搜
spide crawl -s weibo

# 采集所有平台并保存
spide crawl --all --save

# 生成数据看板
spide dashboard

# 启动 Dashboard API 服务
uvicorn dashboard.api:app --host 0.0.0.0 --port 8765 --reload
```

---

## 全局选项

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--version` | `-v` | 显示版本号 |
| `--help` | | 查看帮助信息 |

---

## 命令总览

| 命令 | 说明 | 必填参数 |
|------|------|----------|
| `spide init` | 初始化工作空间 | — |
| `spide config` | 配置向导 | — |
| `spide doctor` | 环境健康检查 | — |
| `spide crawl` | 采集热搜数据 | `-s` 或 `--all` |
| `spide deep-crawl` | 深度采集（MediaCrawler） | `-p` |
| `spide run` | 运行 Agent 任务 | `PROMPT` |
| `spide dashboard` | 生成数据看板 | — |
| `spide dedup` | 清理重复记录 | — |
| `spide analyze` | AI 分析 | `-s` 或 `-k` |
| `spide export` | 导出数据 | `-s` |
| `spide wordcloud` | 生成词云 | `-s` 或 `-t` |
| `spide batch-crawl` | 批量多平台采集 | `-p` |
| `spide schedule` | 定时采集调度 | `ACTION` |
| `spide mcp-serve` | 启动 MCP Server | — |
| `spide memory list` | 查看记忆列表 | — |
| `spide memory add` | 添加记忆 | `TITLE` `CONTENT` |
| `spide mqtt pub` | 发布 MQTT 消息 | `TOPIC` `PAYLOAD` |
| `spide mqtt sub` | 订阅 MQTT 消息 | `TOPIC` |

---

## 命令详解

### init — 初始化

初始化 SpideHarness Agent 工作空间，创建模板文件。

```bash
spide init
spide init -w /path/to/workspace
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**创建的文件：**
- `soul.md` — 灵魂（Agent 行为定义）
- `user.md` — 用户画像
- `identity.md` — 身份信息
- `bootstrap.md` — 引导提示
- `memory_index.md` — 记忆索引

---

### config — 配置

检查当前配置文件状态。

```bash
spide config
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**配置文件结构（`configs/` 目录）：**

| 文件 | 说明 | 必需 |
|------|------|------|
| `default.yaml` | 默认配置 | 是 |
| `llm.yaml` | LLM API Key（智谱 AI） | 是 |
| `mqtt.yaml` | MQTT 凭证（EMQX Cloud） | 可选 |
| `uapi.yaml` | UAPI API Key（热搜数据） | 是 |

---

### doctor — 环境检查

检查工作空间、配置文件、Python 版本等环境状态。

```bash
spide doctor
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**检查项：**
1. 工作空间文件完整性
2. 配置文件（`llm.yaml` / `uapi.yaml` / `mqtt.yaml`）
3. Python 版本（>= 3.12）

---

### crawl — 热搜采集

从 UAPI 数据源采集热搜数据。

```bash
# 采集单个平台
spide crawl -s weibo
spide crawl -s baidu
spide crawl -s douyin

# 采集所有平台
spide crawl --all

# 采集并保存到数据库
spide crawl --all --save
spide crawl -s bilibili --save
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--source` | `-s` | — | 数据源平台（见下表） |
| `--all` | `-a` | `false` | 采集所有已配置的数据源 |
| `--save` | | `false` | 保存采集结果到 SQLite 数据库 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**支持的数据源平台：**

| 标识 | 平台 | 说明 |
|------|------|------|
| `weibo` | 微博 | 实时热搜话题 |
| `baidu` | 百度 | 热门搜索词 |
| `douyin` | 抖音 | 热门视频话题 |
| `zhihu` | 知乎 | 热门问答 |
| `bilibili` | B站 | 热门视频 |
| `kuaishou` | 快手 | 热门短视频 |
| `tieba` | 贴吧 | 热门话题 |

---

### deep-crawl — 深度采集

通过 MediaCrawler 进行深度内容采集，支持评论和创作者信息。

```bash
# 小红书搜索
spide deep-crawl -p xhs -k "美食,旅行" -m search --max 20

# 抖音视频详情
spide deep-crawl -p dy -u "VIDEO_ID" -m detail

# B站创作者
spide deep-crawl -p bili -c "CREATOR_ID" -m creator --no-comments

# 采集并保存
spide deep-crawl -p xhs -k "科技" --save
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--platform` | `-p` | — | **必填** 目标平台（见下表） |
| `--mode` | `-m` | `search` | 采集模式：`search` / `detail` / `creator` |
| `--keywords` | `-k` | — | 搜索关键词（逗号分隔） |
| `--urls` | `-u` | — | 内容 URL 或 ID（逗号分隔） |
| `--creators` | `-c` | — | 创作者 ID（逗号分隔） |
| `--max` | | `20` | 最大采集数量 |
| `--comments` / `--no-comments` | | `true` | 是否采集评论 |
| `--save` | | `false` | 保存到数据库 |
| `--headless` / `--no-headless` | | `true` | 无头浏览器模式 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**支持的平台：**

| 标识 | 平台 | 模式 |
|------|------|------|
| `xhs` | 小红书 | search / detail / creator |
| `dy` | 抖音 | search / detail / creator |
| `ks` | 快手 | search / detail / creator |
| `bili` | B站 | search / detail / creator |
| `wb` | 微博 | search / detail / creator |
| `tieba` | 贴吧 | search / detail |
| `zhihu` | 知乎 | search / detail |

---

### run — Agent 任务

运行 AI Agent 任务，使用 GLM-5.1 模型进行对话交互。

```bash
# 流式输出（默认）
spide run "分析今日微博热搜趋势"

# 非流式输出
spide run "生成今日新闻摘要" --no-stream
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `PROMPT` | | — | **必填** Agent 任务描述 |
| `--stream` / `--no-stream` | | `true` | 流式输出 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### dashboard — 数据看板

从数据库生成数据看板并在浏览器中打开。

```bash
# 生成并打开看板
spide dashboard

# 指定输出路径
spide dashboard -o reports/dashboard.html

# 仅生成，不打开浏览器
spide dashboard --no-open
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--output` | `-o` | `dashboard/index.html` | 输出文件路径 |
| `--open` / `--no-open` | | `true` | 自动打开浏览器 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

> 注意：需先运行 `spide crawl --all --save` 采集数据。

---

### dedup — 数据去重

清理数据库中按 `title + source` 组合的重复记录，保留热度最高的一条。

```bash
# 预览重复记录
spide dedup --dry-run

# 执行清理
spide dedup
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--dry-run` | | `false` | 仅预览，不实际删除 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### analyze — AI 分析

使用 AI 模型进行趋势分析、内容摘要和智能采集策略推荐。

```bash
# 分析微博热搜趋势
spide analyze -s weibo

# 关键词分析
spide analyze -k "人工智能,新能源汽车,房价"

# 情感分析
spide analyze -s douyin --sentiment

# 生成采集策略
spide analyze -s weibo --strategy
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--source` | `-s` | — | 数据源平台 |
| `--keywords` | `-k` | — | 分析关键词（逗号分隔） |
| `--sentiment` | | `false` | 对评论做情感分析 |
| `--strategy` | | `false` | 生成智能采集策略 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### export — 数据导出

将热搜数据导出为 JSON / JSONL / CSV / Excel 格式。

```bash
# 导出微博热搜为 JSON
spide export -s weibo

# 导出为 Excel
spide export -s baidu -f excel -o reports/

# 自定义文件名
spide export -s douyin -f csv -n douyin_hot_0413
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--source` | `-s` | — | **必填** 数据源平台 |
| `--format` | `-f` | `json` | 导出格式：`json` / `jsonl` / `csv` / `excel` |
| `--output` | `-o` | `data/export` | 输出目录 |
| `--filename` | `-n` | `{source}_hot` | 文件名（不含扩展名） |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### wordcloud — 词云生成

从热搜标题或自定义文本生成可视化词云。

```bash
# 从微博热搜生成词云
spide wordcloud -s weibo

# 自定义文本生成词云
spide wordcloud -t "人工智能,机器学习,深度学习,大数据,云计算"

# 仅输出高频关键词
spide wordcloud -s baidu --top-keywords

# 自定义输出
spide wordcloud -s douyin -o images/ -n douyin_cloud --max-words 300
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--source` | `-s` | — | 数据源平台 |
| `--texts` | `-t` | — | 直接提供文本（逗号分隔） |
| `--output` | `-o` | `data/wordcloud` | 输出目录 |
| `--filename` | `-n` | `wordcloud` | 文件名 |
| `--max-words` | | `200` | 最大词数 |
| `--title` | | — | 词云标题 |
| `--top-keywords` | | `false` | 仅输出高频关键词 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### batch-crawl — 批量采集

多平台并发深度采集，支持并发控制和数据导出。

```bash
# 小红书+抖音+B站并行采集
spide batch-crawl -p xhs,dy,bili -k "科技" --max 15

# 全平台采集并保存
spide batch-crawl -p xhs,dy,ks,bili,wb -k "热点新闻" --save

# 采集并导出 Excel
spide batch-crawl -p xhs,dy -k "美食" -e excel -o data/reports/

# 控制并发数
spide batch-crawl -p xhs,dy,ks,bili -c 5
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--platforms` | `-p` | — | **必填** 平台列表（逗号分隔） |
| `--keywords` | `-k` | — | 搜索关键词（逗号分隔，所有平台共用） |
| `--mode` | `-m` | `search` | 采集模式：`search` / `detail` / `creator` |
| `--max` | | `10` | 每平台最大采集数 |
| `--concurrent` | `-c` | `3` | 最大并发数 |
| `--save` | | `false` | 保存到数据库 |
| `--export` | `-e` | — | 导出格式：`json` / `csv` / `excel` |
| `--output` | `-o` | `data/export` | 导出目录 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

---

### schedule — 定时调度

Cron-like 定时采集任务，支持自定义间隔和运行时长。

```bash
# 启动默认调度（微博/百度/知乎，每 5 分钟）
spide schedule start

# 使用配置文件启动
spide schedule start -c configs/schedule.yaml

# 限时运行（1 小时）
spide schedule start --duration 3600

# 查看状态
spide schedule status

# 停止（通过 Ctrl+C 或进程信号）
spide schedule stop
```

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `ACTION` | | — | **必填** 操作：`start` / `status` / `stop` |
| `--config` | `-c` | — | 调度配置文件（YAML） |
| `--duration` | `-d` | `0` | 运行时长（秒），`0` = 手动停止 |
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**调度配置文件示例（`configs/schedule.yaml`）：**

```yaml
jobs:
  - name: weibo_hot
    sources: [weibo]
    interval: 300   # 5 分钟
    save: true

  - name: multi_hot
    sources: [weibo, baidu, douyin, zhihu, bilibili]
    interval: 600   # 10 分钟
    save: true
```

---

### mcp-serve — MCP 服务

启动 MCP Server（stdio 模式），供外部 MCP 客户端连接。

```bash
spide mcp-serve
```

无额外参数。启动后通过标准输入/输出与 MCP 客户端通讯。

---

### memory — 记忆管理

管理 Agent 的持久化记忆文件。

```bash
# 查看记忆列表
spide memory list

# 添加记忆
spide memory add "技术偏好" "偏好 Python，使用 asyncio 异步框架"
```

**list 子命令：**

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `--workspace` | `-w` | `~/.spide_agent` | 工作空间路径 |

**add 子命令：**

| 参数 | 说明 |
|------|------|
| `TITLE` | **必填** 记忆标题 |
| `CONTENT` | **必填** 记忆内容 |
| `--workspace`, `-w` | 工作空间路径 |

---

### mqtt — MQTT 通讯

与 EMQX Cloud MQTT 服务交互。

```bash
# 发布消息
spide mqtt pub "spide/alert" '{"event":"hot_topic","title":"突发新闻"}'

# 订阅消息
spide mqtt sub "spide/#" -n 20
```

**pub 子命令：**

| 参数 | 说明 |
|------|------|
| `TOPIC` | **必填** 发布主题 |
| `PAYLOAD` | **必填** 消息内容 |
| `--qos` | QoS 级别，默认 `1` |

**sub 子命令：**

| 参数 | 缩写 | 默认 | 说明 |
|------|------|------|------|
| `TOPIC` | | — | **必填** 订阅主题 |
| `--count` | `-n` | `10` | 接收消息数量后退出 |

---

## API 服务

Dashboard 后端 API（独立于 CLI 启动），提供 RESTful 接口和前端静态文件托管。

### 启动方式

```bash
# 方式一：uvicorn 命令
uvicorn dashboard.api:app --host 0.0.0.0 --port 8765 --reload

# 方式二：Python 模块
python -m dashboard.api
```

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端 Dashboard 页面 |
| `GET` | `/api/dashboard` | 全量看板数据 |
| `GET` | `/api/topics` | 话题列表（支持筛选分页） |
| `GET` | `/api/sources` | 数据源平台列表 |
| `GET` | `/docs` | Swagger API 文档 |

**`/api/topics` 查询参数：**

| 参数 | 默认 | 说明 |
|------|------|------|
| `source` | — | 按平台筛选（如 `weibo`） |
| `limit` | `50` | 每页数量 |
| `offset` | `0` | 偏移量 |

**示例：**

```bash
# 获取全量看板数据
curl http://localhost:8765/api/dashboard

# 获取微博话题（前 20 条）
curl http://localhost:8765/api/topics?source=weibo&limit=20

# 获取数据源列表
curl http://localhost:8765/api/sources
```

---

## 典型工作流

### 工作流 1：热搜监控

```bash
# 1. 初始化
spide init && spide doctor

# 2. 采集所有平台并保存
spide crawl --all --save

# 3. 去重清理
spide dedup

# 4. 生成看板
spide dashboard

# 5. 启动 API 服务（实时查看）
uvicorn dashboard.api:app --port 8765 --reload
```

### 工作流 2：深度内容采集

```bash
# 1. 关键词搜索采集
spide deep-crawl -p xhs -k "AI工具,效率提升" --max 30 --save

# 2. 多平台批量采集
spide batch-crawl -p xhs,dy,bili -k "科技新闻" --max 20 --save

# 3. 导出数据
spide export -s weibo -f excel -o reports/
```

### 工作流 3：定时采集 + 分析

```bash
# 1. 启动定时调度
spide schedule start -c configs/schedule.yaml --duration 7200

# 2. 采集完成后分析
spide analyze -s weibo --strategy

# 3. 生成词云
spide wordcloud -s baidu -o reports/ -n baidu_cloud

# 4. 启动看板查看
uvicorn dashboard.api:app --port 8765
```

---

## 版本信息

- **当前版本：** v1.1.1
- **CLI 入口：** `spide`（通过 `pyproject.toml` → `[project.scripts]` 注册）
- **Python 版本：** >= 3.12
- **CLI 框架：** Typer
- **查看版本：** `spide --version` 或 `spide -v`
