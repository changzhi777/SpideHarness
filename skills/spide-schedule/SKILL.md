---
name: spide-schedule
description: >
  定时调度 — Cron-like 定时采集任务，支持自定义间隔和运行次数。
  当用户要求定时采集、自动刷新热搜、周期性抓取时使用。
---

# Spide Schedule — 定时调度

## 触发条件

用户要求设置定时采集任务、自动刷新热搜或周期性数据抓取时自动激活。

## 用法

```bash
# 启动默认调度（微博/百度/知乎 每5分钟）
spide schedule start

# 自定义调度配置
spide schedule start -c schedule.yaml

# 限制运行时长（秒）
spide schedule start -d 3600

# 查看调度状态
spide schedule status

# 停止调度
spide schedule stop
```

## 调度配置

默认调度任务：

| 数据源 | 间隔 | 说明 |
|--------|------|------|
| 微博热搜 | 5 分钟 | 实时热搜 |
| 百度热搜 | 5 分钟 | 热门搜索 |
| 知乎热榜 | 5 分钟 | 热门问答 |

自定义配置文件 `schedule.yaml` 示例：

```yaml
jobs:
  - source: weibo
    interval_seconds: 300
    max_runs: 10
    enabled: true
  - source: baidu
    interval_seconds: 300
    enabled: true
  - source: douyin
    interval_seconds: 180
    enabled: true
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c` | 调度配置文件路径 | 内置默认 |
| `-d` | 最大运行时长（秒） | 无限制 |
| `--save` | 自动保存采集结果 | false |

## 工作流程

1. 确认调度需求（数据源、间隔、时长）
2. 如需自定义，创建调度配置文件
3. 运行 `spide schedule start` 启动调度
4. 使用 `spide schedule status` 查看运行状态
5. 使用 `spide schedule stop` 停止调度

## 注意事项

- 调度期间程序持续运行，需保持终端会话
- 建议配合 `--save` 自动保存采集结果
- 运行时长建议设置上限，避免无限运行
- 数据源刷新间隔不宜过短，避免 API 限流
