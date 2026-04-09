---
name: spide-usage
description: >
  OpenCLI 使用参考 — 覆盖安装、命令参考和输出格式，涵盖 79+ 网站适配器。
  当用户需要查询 OpenCLI 命令用法、查看支持的网站/桌面应用时使用。
---

# Spide Usage — OpenCLI 使用参考

> 让任何网站或 Electron 应用成为你的 CLI。复用 Chrome 登录，零风险，AI 驱动的发现。

## 安装与运行

```bash
# npm 全局安装（推荐）
npm install -g @jackwener/opencli
opencli <command>

# 或从源码
cd ~/code/opencli && npm install
npx tsx src/main.ts <command>

# 更新到最新
npm update -g @jackwener/opencli
```

## 前提条件

浏览器命令需要：
1. Chrome 浏览器运行中**（已登录目标站点）**
2. **opencli Browser Bridge** Chrome 扩展已安装
3. 守护进程在首次浏览器命令时自动启动

公开 API 命令（`hackernews`, `v2ex`）不需要浏览器。

## 按能力速查

| 能力 | 平台（部分列表） |
|------|----------------|
| **搜索** | Bilibili, Twitter, Reddit, 小红书, 知乎, YouTube, Google, arXiv, LinkedIn, Pixiv 等 |
| **热门/趋势** | Bilibili, Twitter, 微博, HackerNews, Reddit, V2EX, 雪球, 豆瓣 |
| **信息流/时间线** | Twitter, Reddit, 小红书, 雪球, 即刻, Facebook, Instagram, Medium |
| **用户/资料** | Twitter, Reddit, Instagram, TikTok, Facebook, Bilibili, Pixiv |
| **发帖/创建** | Twitter, 即刻, 抖音, 微博 |
| **AI 对话** | Grok, 豆包, ChatGPT, Gemini, Cursor, Codex, NotebookLM |
| **金融/股票** | 雪球, Yahoo Finance, Barchart, 新浪财经, Bloomberg |
| **网页抓取** | `opencli web read --url <url>` — 任意 URL 转 Markdown |
| **GitHub/DevOps** | `opencli gh`, `opencli docker`, `opencli vercel` |
| **协作** | `opencli lark-cli`, `opencli dws`, `opencli wecom-cli` |

## 命令速查

用法：`opencli <site> <command> [args] [--limit N] [-f json|yaml|md|csv|table]`

类型图例：🌐 = 浏览器（需要 Chrome 登录） · ✅ = 公开 API（无需浏览器） · 🖥️ = 桌面（Electron/CDP） · 🔧 = 外部 CLI（透传）

### 网站适配器

完整命令列表见 **[commands.md](commands.md)**。

### 桌面应用

完整桌面应用命令见 **[desktop.md](desktop.md)**。

### 外部 CLI（透传）

OpenCLI 可发现、自动安装和透传外部 CLI 工具命令：

```bash
opencli install gh              # 自动安装 gh CLI
opencli register my-tool        # 注册本地自定义 CLI
opencli gh pr list --limit 5    # 透传到 gh
```

详见 **[plugins.md](plugins.md)**。

### 管理

```bash
opencli list [-f json|yaml]     # 列出所有命令
opencli validate [site]         # 验证适配器定义
opencli doctor                  # 诊断浏览器桥接
opencli explore <url>           # AI 驱动的 API 发现
opencli record <url>            # 手动录制 API 调用
```

所有命令支持：`--format` / `-f`，可选 `table` `json` `yaml` `md` `csv`

## 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLI_DAEMON_PORT` | `19825` | 守护进程-扩展桥接端口 |
| `OPENCLI_WINDOW_FOCUSED` | `false` | `1` = 前台打开自动化窗口 |
| `OPENCLI_BROWSER_CONNECT_TIMEOUT` | `30` | 浏览器连接超时（秒） |
| `OPENCLI_BROWSER_COMMAND_TIMEOUT` | `60` | 单命令超时（秒） |
| `OPENCLI_VERBOSE` | `false` | 详细日志（`-v` 标志也可） |
| `OPENCLI_DIAGNOSTIC` | `false` | `1` = 失败时结构化诊断 |

## 自修复

如果命令因站点变更而失败（选择器、API 或响应结构），**自动修复适配器并重试**。详见 **spide-autofix** skill。

## 相关 Skills

- **spide-browser** — 浏览器自动化（导航、点击、输入、提取）
- **spide-explorer** — 适配器探索式开发（API 发现、认证策略、TS 编写）
- **spide-oneshot** — 从 URL 快速生成单个命令
- **spide-autofix** — 命令失败时自动修复适配器
- **spide-search** — 智能搜索路由（AI + 多源）
