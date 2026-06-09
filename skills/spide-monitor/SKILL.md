---
name: spide-monitor
description: >
  关键词监控与告警 — 基于规则引擎对采集数据进行关键词匹配，
  通过 Log / MQTT / Webhook / 飞书多渠道推送告警。
  当用户要求监控热点话题、设置关键词告警、配置通知渠道时使用此技能。
category: automation
---

# Spide Monitor — 关键词监控与告警

## 触发条件

用户要求：
- 监控特定关键词（如品牌名、竞品、突发事件）
- 配置告警规则（包含/排除/正则）
- 设置多渠道通知（飞书/MQTT/Webhook）
- 启动/停止定时监控

时自动激活。

## 用法

### CLI 方式

```bash
# 单次执行监控（不循环）
spide monitor --once

# 启动持续监控（前台运行）
spide monitor

# 指定自定义规则文件
spide monitor --rules configs/alert_rules.yaml

# 后台守护模式
spide monitor --daemon
```

### 配置文件（configs/alert_rules.yaml）

```yaml
rules:
  # 规则 1: 包含关键词 "AI" 的话题
  - name: "AI 热点"
    keywords: ["AI", "大模型", "LLM", "GPT"]
    sources: ["weibo", "zhihu", "bilibili"]
    min_hot_value: 100000
    action: "log"
  
  # 规则 2: 排除关键词（竞品过滤）
  - name: "竞品告警"
    keywords: ["某品牌A", "某品牌B"]
    exclude: ["广告", "推广"]
    action: "feishu"
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  
  # 规则 3: 正则匹配
  - name: "突发事件"
    pattern: "(地震|暴雨|事故|疫情).*?(.{0,20})(发生|爆发|蔓延)"
    sources: ["weibo", "douyin"]
    action: "mqtt"
    mqtt_topic: "spide/alerts/urgent"

# 通知渠道配置
channels:
  log:
    level: "INFO"
    format: "json"
  mqtt:
    broker: "mqtt://broker.emqx.io:1883"
    username: ""
    password: ""
  webhook:
    url: "https://example.com/webhook"
    method: "POST"
    headers:
      Authorization: "Bearer xxx"
  feishu:
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
    at_all: false
```

## 规则字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 规则名（告警时显示） |
| `keywords` | list[str] | 二选一 | 包含关键词列表（OR 关系） |
| `pattern` | str | 二选一 | 正则表达式 |
| `exclude` | list[str] | 否 | 排除关键词列表 |
| `sources` | list[str] | 否 | 限定平台（默认全平台） |
| `min_hot_value` | int | 否 | 最低热度阈值 |
| `action` | enum | 是 | `log` / `mqtt` / `webhook` / `feishu` |
| `webhook_url` | str | 条件必填 | webhook / feishu 时必填 |
| `mqtt_topic` | str | 条件必填 | mqtt 时必填 |
| `at_all` | bool | 否 | 飞书 @所有人（默认 false） |

## 通知渠道对比

| 渠道 | 实时性 | 配置复杂度 | 适用场景 |
|------|--------|------------|----------|
| **Log** | 同步 | 极简 | 开发调试 / 本地查看 |
| **MQTT** | 实时 | 中等 | IoT 集成 / 多消费者 |
| **Webhook** | 实时 | 中等 | 集成到第三方系统（如 n8n） |
| **飞书** | 实时 | 简单 | 团队群通知（推荐） |

## 工作流程

```
采集数据（UAPI/MediaCrawler）
  ↓
规则引擎匹配（关键词/正则/排除/热度）
  ↓
触发告警 → 多渠道并发通知
  ├─→ Log: 结构化日志输出
  ├─→ MQTT: 发布到 spide/alerts/*
  ├─→ Webhook: POST 到 URL
  └─→ 飞书: 发送交互式卡片
```

## 前置条件

- 项目已初始化：`spide init`
- 已运行过至少一次采集（`spide crawl --all --save`）
- 配置文件 `configs/alert_rules.yaml` 已编辑

## 注意事项

- 告警频率建议 ≤ 1 次/分钟，避免刷屏
- MQTT 渠道需要 broker 在线（EMQX Cloud / 本地 mosquitto）
- 飞书 Webhook 限额 100 req/min
- 规则支持热加载（修改 yaml 后无需重启）
- 历史告警记录在 `spide_data.db` 的 `alerts` 表
