# SpideHarness Agent v1.1.1 — 需求文档

> 版本: 1.1.1 (开发版)
> 日期: 2026-04-09
> 作者: 外星动物（常智） / IoTchange / 14455975@qq.com
> 状态: 已实现

---

## 一、引言

SpideHarness Agent 是一个基于 **Harness Engineering** 架构的热点新闻信息抓取与智能整理 Agent CLI 工具。本文档对 v1.1.1 已实现的核心功能进行正式需求归档。

### 产品愿景

为自媒体创作者、品牌营销团队、数据分析师、开发者提供**开源免费、AI 原生、12 数据源聚合**的热点新闻采集与分析工具，对标万元级舆情 SaaS。

### 技术栈概述

| 层面 | 技术选型 |
|------|----------|
| 语言 | Python 3.12+ |
| CLI | Typer |
| 异步 | asyncio + aiohttp |
| 数据模型 | Pydantic v2 |
| 持久化 | SQLite (aiosqlite) |
| 缓存 | Redis (aioredis) |
| MQTT | aiomqtt (EMQX Cloud) |
| MCP | mcp-sdk (stdio transport) |
| LLM | GLM-5.1 (文本) + GLM-5V-Turbo (视觉) |
| 热搜数据源 | UApiPro REST API |
| 深度采集 | MediaCrawler (Playwright 子进程) |
| 联网搜索 | 智谱 Web Search API |

---

## 二、需求清单

### R1 — 热搜数据采集

**用户故事:** 作为数据分析师，我想一键采集多平台热搜榜单，以便快速掌握全网热点动态。

#### R1.1 多平台热搜采集

**验收标准:**

1. WHEN 用户执行 `spide crawl -s <source>` THEN 系统 SHALL 从指定平台采集热搜数据并返回 `list[HotTopic]`
2. WHEN source 为 `weibo` / `baidu` / `douyin` / `zhihu` / `bilibili` 之一 THEN 系统 SHALL 采集对应平台的实时热搜榜单
3. WHEN 用户执行 `spide crawl -a` THEN 系统 SHALL 并发采集全部 5 个热搜源
4. WHEN 用户指定 `--save` THEN 系统 SHALL 将采集结果持久化到 SQLite

**数据模型 — HotTopic:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (UUID) | 唯一标识 |
| title | str | 热搜标题 |
| source | TopicSource (enum) | 数据源（weibo/baidu/douyin/zhihu/bilibili） |
| hot_value | int | 热度值 |
| url | str | 原文链接 |
| rank | int | 排名 |
| category | ArticleCategory? | AI 分类 |
| summary | str? | AI 摘要 |
| fetched_at | datetime | 采集时间 |
| extra | dict | 扩展字段 |

**技术约束:**

- UApiPro API 并发限制：5 并发 / 30 RPM
- 重试策略：3 次，指数退避
- HTTP 客户端：aiohttp + Semaphore 限流

#### R1.2 联网搜索

**验收标准:**

1. WHEN AI Agent 调用 `web_search` MCP 工具 THEN 系统 SHALL 通过智谱 Web Search API 返回结构化搜索结果
2. IF 用户指定搜索引擎（search_std / search_pro / search_pro_sogou / search_pro_quark）THEN 系统 SHALL 使用对应引擎执行搜索
3. WHEN 返回搜索结果 THEN 系统 SHALL 包含标题、摘要、URL、网站名、图标、发布日期

---

### R2 — 深度内容采集

**用户故事:** 作为品牌营销人员，我想深度采集指定平台的用户评论和创作者信息，以便进行竞品分析和舆情监控。

#### R2.1 多平台深度采集

**验收标准:**

1. WHEN 用户执行 `spide deep-crawl -p <platform> -m <mode>` THEN 系统 SHALL 通过 MediaCrawler 子进程执行深度采集
2. WHEN platform 为 `xhs` / `dy` / `ks` / `bili` / `wb` / `tieba` / `zhihu` 之一 THEN 系统 SHALL 采集对应平台数据
3. WHEN mode 为 `search` THEN 系统 SHALL 基于关键词搜索内容（必填: keywords）
4. WHEN mode 为 `detail` THEN 系统 SHALL 采集指定内容详情（必填: content_ids / urls）
5. WHEN mode 为 `creator` THEN 系统 SHALL 采集创作者主页内容（必填: creator_ids）
6. WHEN 用户指定 `--save` THEN 系统 SHALL 将结果持久化到 SQLite

#### R2.2 深度采集数据模型

**数据模型 — DeepContent:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (UUID) | 唯一标识 |
| platform | Platform (enum) | 平台标识 |
| content_id | str | 平台内容 ID |
| content_type | str | 内容类型（图文/视频） |
| title | str | 标题 |
| content | str | 正文内容 |
| url | str | 原文链接 |
| author_id / author_name | str | 作者信息 |
| like/comment/share/collect/view_count | int | 互动数据 |
| ip_location | str? | IP 属地 |
| media_urls | list[str] | 媒体资源 |
| tags | list[str] | 标签 |
| publish_time | datetime? | 发布时间 |
| fetched_at | datetime | 采集时间 |

**数据模型 — DeepComment:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (UUID) | 唯一标识 |
| platform | Platform (enum) | 平台 |
| comment_id | str | 评论 ID |
| content_id | str | 关联内容 ID |
| parent_comment_id | str? | 父评论 ID |
| content | str | 评论正文 |
| user_id / nickname | str | 评论者 |
| like_count / sub_comment_count | int | 互动数据 |
| ip_location | str? | IP 属地 |

**数据模型 — DeepCreator:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (UUID) | 唯一标识 |
| platform | Platform (enum) | 平台 |
| user_id | str | 用户 ID |
| nickname | str | 昵称 |
| description | str? | 简介 |
| gender | str? | 性别 |
| ip_location | str? | IP 属地 |
| follows / fans / interaction | int | 关注/粉丝/互动数 |

**技术约束:**

- MediaCrawler 以子进程方式运行（`python -m mediacrawler`）
- 数据交换格式：JSON / JSONL / CSV 文件
- 支持 `--headless` / `--no-headless` 浏览器模式
- 支持子评论采集（`--comments`）

---

### R3 — 批量并行调度

**用户故事:** 作为数据分析师，我想同时从多个平台并行采集数据，以便提高采集效率。

#### R3.1 多平台并发采集

**验收标准:**

1. WHEN 用户执行 `spide batch-crawl -p xhs,dy,bili -k "AI"` THEN 系统 SHALL 并行采集 3 个平台数据
2. WHEN 用户指定 `-c 2` THEN 系统 SHALL 使用 Semaphore 限制最大并发数为 2
3. WHEN 任务完成 THEN 系统 SHALL 返回 `BatchResult`，包含 total_contents / total_comments / total_creators / succeeded / failed
4. IF 部分任务失败 THEN 系统 SHALL 记录失败信息但不影响其他任务
5. WHEN 用户指定 `--save` THEN 系统 SHALL 保存全部成功结果到 SQLite
6. WHEN 用户指定 `-e json` 和 `-o ./output` THEN 系统 SHALL 将结果导出到指定目录

**技术约束:**

- 默认并发数: 3
- 异步进度回调支持: `on_progress(completed, total, platform, status)`

---

### R4 — 定时任务调度

**用户故事:** 作为品牌营销人员，我想设置定时采集任务，以便自动持续监控全网热点。

#### R4.1 Cron-like 定时调度

**验收标准:**

1. WHEN 用户执行 `spide schedule start` THEN 系统 SHALL 启动默认调度任务（微博/百度/知乎，间隔 300 秒）
2. WHEN 用户指定 `-c schedule.yaml` THEN 系统 SHALL 从 YAML 配置加载调度任务
3. WHEN 用户指定 `-d 3600` THEN 系统 SHALL 在 3600 秒后自动停止
4. WHEN 用户执行 `spide schedule status` THEN 系统 SHALL 显示当前任务状态
5. WHEN 用户执行 `spide schedule stop` THEN 系统 SHALL 停止调度器
6. WHEN 单次采集完成 THEN 系统 SHALL 触发 `on_result` 回调

**ScheduledJob 配置项:**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 任务名称 |
| platforms | list[Platform] | 深度采集平台 |
| sources | list[TopicSource] | 热搜源 |
| interval_seconds | int | 采集间隔（默认 300） |
| save_to_db | bool | 是否持久化 |
| export_format | str? | 导出格式 |
| max_runs | int | 最大运行次数（0=无限） |
| enabled | bool | 是否启用 |

---

### R5 — AI 智能分析

**用户故事:** 作为自媒体创作者，我想让 AI 帮我分析热点趋势、生成摘要和情感分析，以便快速判断哪些热点值得跟进。

#### R5.1 内容摘要与分类

**验收标准:**

1. WHEN AI Agent 调用 `ContentSummarizer.summarize(title, content)` THEN 系统 SHALL 返回 100-200 字摘要 + 3-5 个关键词 + 分类标签
2. WHEN 分类完成 THEN 系统 SHALL 将话题归入以下类别之一: 科技/财经/社会/娱乐/体育/国际/科学/健康/其他

#### R5.2 趋势分析

**验收标准:**

1. WHEN 用户执行 `spide analyze -s weibo` THEN 系统 SHALL 分析指定平台的热点趋势
2. IF 无历史数据 THEN 系统 SHALL 返回 top_categories / hot_domains / analysis / recommendations
3. IF 有历史数据 THEN 系统 SHALL 计算对比指标: rising / falling / new_entries / disappeared / persisted_count

#### R5.3 智能采集策略

**验收标准:**

1. WHEN 用户执行 `spide analyze -s weibo --strategy` THEN 系统 SHALL 根据当前热搜推荐采集策略
2. THEN 系统 SHALL 返回 trending_topics / recommended_sources / search_keywords / analysis

**技术约束:**

- LLM 模型: GLM-5.1
- temperature=0.3, max_tokens=1024
- 输出格式: JSON

---

### R6 — 数据导出

**用户故事:** 作为数据分析师，我想将采集数据导出为多种格式，以便在 BI 工具和办公软件中使用。

#### R6.1 多格式导出

**验收标准:**

1. WHEN 用户执行 `spide export -s weibo -f json` THEN 系统 SHALL 导出 JSON 格式文件
2. WHEN 用户执行 `spide export -s weibo -f csv` THEN 系统 SHALL 导出 CSV 格式文件（UTF-8-BOM 编码）
3. WHEN 用户执行 `spide export -s weibo -f excel` THEN 系统 SHALL 导出 xlsx 格式文件（自动列宽）
4. WHEN 用户执行 `spide export -s weibo -f jsonl` THEN 系统 SHALL 导出 JSONL 格式文件
5. WHEN 用户指定 `-o ./output` THEN 系统 SHALL 导出到指定目录
6. WHEN 用户指定 `-n 50` THEN 系统 SHALL 限制导出条数

**技术约束:**

- Excel 使用 openpyxl + 自动列宽调整
- CSV 使用 utf-8-sig 编码（兼容 Excel）
- 异步写入: `asyncio.to_thread`

---

### R7 — 词云生成

**用户故事:** 作为自媒体创作者，我想生成热搜词云图，以便直观展示高频关键词。

#### R7.1 词云可视化

**验收标准:**

1. WHEN 用户执行 `spide wordcloud -s weibo` THEN 系统 SHALL 从热搜标题生成词云图（PNG）
2. WHEN 用户执行 `spide wordcloud -t "AI,技术,大模型"` THEN 系统 SHALL 从直接输入文本生成词云
3. WHEN 用户指定 `--max-words 100` THEN 系统 SHALL 限制最大词数
4. WHEN 用户指定 `--top-keywords` THEN 系统 SHALL 仅输出高频关键词列表（不生成图片）
5. WHEN 用户指定 `-n 50` THEN 系统 SHALL 限制数据条数

**技术约束:**

- jieba 中文分词 + 60+ 内置中文停用词
- wordcloud 渲染 + matplotlib Agg 后端（线程安全）
- 异步渲染: `asyncio.to_thread`
- 默认: 800×600, 200 词, 白色背景

---

### R8 — MCP 协议支持

**用户故事:** 作为开发者，我想通过 MCP 协议将 SpideHarness 接入 AI 模型，以便在 AI 对话中直接调用采集和分析能力。

#### R8.1 MCP Server

**验收标准:**

1. WHEN 用户执行 `spide mcp-serve` THEN 系统 SHALL 启动 MCP Server（stdio transport）
2. WHEN MCP Client 调用 `crawl_hot_topics` THEN 系统 SHALL 采集指定平台热搜
3. WHEN MCP Client 调用 `web_search` THEN 系统 SHALL 执行联网搜索
4. WHEN MCP Client 调用 `deep_crawl_hot_topics` THEN 系统 SHALL 执行深度采集
5. WHEN MCP Client 调用 `manage_memory` THEN 系统 SHALL 管理 Agent 记忆（add/remove/list/get）
6. WHEN MCP Client 调用 `health_check` THEN 系统 SHALL 返回服务健康状态

**已注册 MCP 工具 (5 个):**

| 工具 | 入参 | 返回 |
|------|------|------|
| crawl_hot_topics | source, save | 热搜列表 JSON |
| web_search | query, engine, count | 搜索结果 JSON |
| deep_crawl_hot_topics | platform, mode, keywords, ... | 深度采集结果 JSON |
| manage_memory | action, title, content | 记忆操作结果 |
| health_check | 无 | 健康状态 JSON |

---

### R9 — MQTT 通讯

**用户故事:** 作为开发者，我想通过 MQTT 协议接收采集结果和发送控制指令，以便将 SpideHarness 集成到 IoT 系统。

#### R9.1 MQTT 发布/订阅

**验收标准:**

1. WHEN 用户执行 `spide mqtt pub <topic> <payload>` THEN 系统 SHALL 发布消息到 EMQX Cloud（自动添加 `spide_agent/` 前缀）
2. WHEN payload 为 dict/list THEN 系统 SHALL 自动序列化为 JSON
3. WHEN 用户执行 `spide mqtt sub <topic> -n 10` THEN 系统 SHALL 订阅主题并接收 10 条消息
4. WHEN 连接 MQTT Broker THEN 系统 SHALL 使用 TLS 加密（CA 证书验证）
5. WHEN 指定 `--qos 1` THEN 系统 SHALL 使用 QoS 1 消息质量

**技术约束:**

- Broker: EMQX Cloud（阿里云杭州）
- TLS 端口: 8883 / WSS 端口: 8084
- QoS 支持: 0 / 1 / 2
- 通配符: `#` (多级) / `+` (单级)

---

### R10 — Agent 对话模式

**用户故事:** 作为用户，我想用自然语言与 Agent 对话，以便直接描述需求并获得结果。

#### R10.1 自然语言交互

**验收标准:**

1. WHEN 用户执行 `spide run "帮我分析今日热搜趋势"` THEN 系统 SHALL 调用 LLM 理解意图并执行对应操作
2. WHEN 用户指定 `--stream` THEN 系统 SHALL 流式输出 LLM 响应
3. WHEN LLM 判断需要采集数据 THEN 系统 SHALL 自动调用 MCP 工具执行采集
4. WHEN 对话完成 THEN 系统 SHALL 保存会话状态到 `SessionStorage`

**技术约束:**

- LLM: GLM-5.1 (Function Call)
- 系统提示词: 由 `build_system_prompt()` 动态构建
- 会话存储: JSON 文件（含 messages / usage / crawled_urls / task_ids）

---

### R11 — 数据持久化

**用户故事:** 作为用户，我想将采集数据持久化存储，以便后续查询和分析。

#### R11.1 SQLite 异步存储

**验收标准:**

1. WHEN 用户指定 `--save` THEN 系统 SHALL 将数据写入 SQLite
2. WHEN 写入 HotTopic THEN 系统 SHALL 按 (source, title, fetched_at) 去重
3. WHEN 写入 DeepContent / DeepComment / DeepCreator THEN 系统 SHALL 按 (platform, content_id/user_id/comment_id) 去重
4. WHEN 查询数据 THEN 系统 SHALL 支持按 source / platform / 时间范围 / 关键词过滤

#### R11.2 Redis 缓存（可选）

**验收标准:**

1. WHEN Redis 可用 THEN 系统 SHALL 缓存热搜数据并用于 URL 去重
2. IF Redis 不可用 THEN 系统 SHALL 降级为纯 SQLite 模式，不影响核心功能

---

### R12 — CLI 基础设施

**用户故事:** 作为用户，我想通过简单的 CLI 命令管理工作空间和配置。

#### R12.1 工作空间管理

**验收标准:**

1. WHEN 用户执行 `spide init` THEN 系统 SHALL 初始化工作空间目录结构
2. WHEN 用户执行 `spide doctor` THEN 系统 SHALL 检查 Python 版本 / 依赖 / Redis / MQTT / LLM 配置状态
3. WHEN 用户执行 `spide config` THEN 系统 SHALL 显示当前配置或启动配置向导
4. WHEN 用户执行 `spide -v` THEN 系统 SHALL 显示版本号 `1.1.1`

---

## 三、非功能性需求

### NFR1 — 性能

- 热搜采集: 单平台 < 5 秒，全平台并发 < 10 秒
- 深度采集: 单任务超时默认 300 秒，可配置
- AI 分析: 单次分析 < 10 秒（取决于 LLM 响应）
- 并发控制: Semaphore 限流，默认并发 3，可配置

### NFR2 — 可靠性

- HTTP 请求: 3 次指数退避重试
- 部分失败隔离: 批量任务中单个平台失败不影响其他平台
- Redis 降级: Redis 不可用时自动降级到 SQLite
- MediaCrawler 子进程隔离: 子进程异常不导致主进程崩溃

### NFR3 — 安全

- API Key 外置: `configs/llm.yaml` / `configs/uapi.yaml` / `configs/mqtt.yaml`，不入 Git
- MQTT TLS 加密: CA 证书验证
- .gitignore 排除: configs/ 敏感文件 / CA/ 证书 / .venv/

### NFR4 — 可测试性

- 测试用例: 238 个（unit + integration + e2e）
- HTTP Mock: aioresponses
- MQTT Mock: unittest.mock
- 测试覆盖率目标: >= 80%

### NFR5 — 可维护性

- Python 3.12+ 类型注解全覆盖
- Ruff lint + format
- mypy 严格模式检查
- structlog 结构化日志
- Pydantic v2 数据验证

### NFR6 — 代码架构

- **单一职责**: 每个模块/文件职责明确
- **依赖注入**: 模块通过接口依赖，不直接引用具体实现
- **配置外置**: 所有配置项从 `configs/` 加载
- **Harness 架构**: 中心调度器 + 插件化模块 + 消息总线
- **异步优先**: I/O 密集 asyncio，CPU 密集多线程

---

## 四、需求追溯矩阵

| 需求 ID | 功能 | CLI 命令 | 核心模块 | 测试覆盖 |
|---------|------|----------|----------|----------|
| R1 | 热搜采集 | `spide crawl` | `spider/uapi_client.py` | unit + integration |
| R2 | 深度采集 | `spide deep-crawl` | `spider/media_crawler_adapter.py` | unit + integration |
| R3 | 批量调度 | `spide batch-crawl` | `spider/batch_scheduler.py` | unit |
| R4 | 定时调度 | `spide schedule` | `spider/task_scheduler.py` | unit |
| R5 | AI 分析 | `spide analyze` | `analysis/summarizer.py` | unit |
| R6 | 数据导出 | `spide export` | `storage/exporter.py` | unit |
| R7 | 词云生成 | `spide wordcloud` | `analysis/wordcloud_generator.py` | unit |
| R8 | MCP 协议 | `spide mcp-serve` | `mcp/server.py`, `mcp/tools.py` | unit |
| R9 | MQTT 通讯 | `spide mqtt pub/sub` | `mqtt/client.py` | unit |
| R10 | Agent 对话 | `spide run` | `harness/engine.py`, `llm.py` | unit + e2e |
| R11 | 数据持久化 | `--save` | `storage/sqlite_repo.py`, `storage/redis_cache.py` | unit + integration |
| R12 | CLI 基础 | `init/doctor/config` | `cli.py`, `workspace.py` | unit + e2e |
