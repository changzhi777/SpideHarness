# SpideHarness Agent Skills 安装与使用指南

> AI Agent Skill 支持：OpenClaw / Claude Code 一键安装，7 个技能开箱即用

## 目录

- [概述](#概述)
- [Skills 列表](#skills-列表)
- [快速开始](#快速开始)
- [安装方式](#安装方式)
  - [一键安装（推荐）](#一键安装推荐)
  - [手动安装](#手动安装)
- [各平台使用方法](#各平台使用方法)
  - [Claude Code](#claude-code)
  - [OpenClaw](#openclaw)
  - [Cursor / Windsurf](#cursor--windsurf)
- [Skills 详细说明](#skills-详细说明)
- [SKILL.md 格式规范](#skillmd-格式规范)
- [自定义 Skill](#自定义-skill)
- [卸载](#卸载)
- [常见问题](#常见问题)

---

## 概述

SpideHarness Agent Skills 基于 **AgentSkills 开放规范**，将 Spide 的 7 项核心能力打包为标准化技能目录。每个技能包含一个 `SKILL.md` 文件（YAML 元数据 + Markdown 指令），可被 AI Agent 框架自动发现和调用。

**设计原则：**

- **即插即用** — 一条命令完成安装，无需额外配置
- **跨平台兼容** — 同一份 Skill 文件适配 OpenClaw、Claude Code、Cursor、Windsurf 等
- **渐进式加载** — 元数据常驻（~100 tokens），完整指令按需加载（~500 tokens），不浪费上下文窗口

---

## Skills 列表

| Skill | 斜杠命令 | 功能 |
|-------|----------|------|
| `spide-crawl` | `/spide-crawl` | 热搜采集 — 微博/百度/抖音/知乎/B站 |
| `spide-deep-crawl` | `/spide-deep-crawl` | 深度采集 — 小红书/抖音/快手/B站/微博/贴吧/知乎 |
| `spide-analyze` | `/spide-analyze` | AI 分析 — 趋势/摘要/情感/智能策略 |
| `spide-export` | `/spide-export` | 数据导出 — JSON/CSV/Excel |
| `spide-wordcloud` | `/spide-wordcloud` | 词云生成 — jieba 分词 + wordcloud 可视化 |
| `spide-batch` | `/spide-batch` | 批量并行采集 — 多平台并发 |
| `spide-schedule` | `/spide-schedule` | 定时调度 — Cron-like 采集任务 |

---

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd a_Spide_agent

# 2. 安装到当前环境的 Claude Code
./install-skills.sh --claude

# 3. 在 Claude Code 中使用
> /spide-crawl 采集微博热搜
> /spide-analyze 分析百度热搜趋势
```

---

## 安装方式

### 一键安装（推荐）

使用项目自带的 `install-skills.sh` 脚本：

```bash
# 赋予执行权限（首次）
chmod +x install-skills.sh

# 同时安装到 OpenClaw + Claude Code
./install-skills.sh

# 仅安装到 Claude Code（当前项目）
./install-skills.sh --claude

# 仅安装到 OpenClaw（全局）
./install-skills.sh --openclaw

# 验证安装状态
./install-skills.sh --verify

# 查看帮助
./install-skills.sh --help
```

**安装位置：**

| 平台 | 安装路径 | 作用域 |
|------|----------|--------|
| Claude Code | `<project>/.claude/skills/spide-*/` | 项目级 |
| OpenClaw | `~/.openclaw/skills/spide-*/` | 用户级（全局） |

脚本使用符号链接（Linux/macOS）或目录副本（Windows）指向 `skills/` 源目录，更新 Skill 内容后无需重新安装。

### 手动安装

如果安装脚本不适用于你的环境，可手动操作：

**Claude Code：**

```bash
# 在项目根目录执行
mkdir -p .claude/skills

# 为每个 Skill 创建符号链接
ln -s ../../skills/spide-crawl .claude/skills/spide-crawl
ln -s ../../skills/spide-deep-crawl .claude/skills/spide-deep-crawl
ln -s ../../skills/spide-analyze .claude/skills/spide-analyze
ln -s ../../skills/spide-export .claude/skills/spide-export
ln -s ../../skills/spide-wordcloud .claude/skills/spide-wordcloud
ln -s ../../skills/spide-batch .claude/skills/spide-batch
ln -s ../../skills/spide-schedule .claude/skills/spide-schedule
```

**OpenClaw：**

```bash
mkdir -p ~/.openclaw/skills

# 为每个 Skill 创建符号链接
ln -s /path/to/a_Spide_agent/skills/spide-crawl ~/.openclaw/skills/spide-crawl
ln -s /path/to/a_Spide_agent/skills/spide-deep-crawl ~/.openclaw/skills/spide-deep-crawl
# ... 其余类推
```

**Windows（无符号链接支持时）：**

```powershell
# 使用目录复制代替符号链接
New-Item -ItemType Directory -Force -Path .claude\skills
Copy-Item -Recurse skills\spide-crawl .claude\skills\
Copy-Item -Recurse skills\spide-deep-crawl .claude\skills\
Copy-Item -Recurse skills\spide-analyze .claude\skills\
Copy-Item -Recurse skills\spide-export .claude\skills\
Copy-Item -Recurse skills\spide-wordcloud .claude\skills\
Copy-Item -Recurse skills\spide-batch .claude\skills\
Copy-Item -Recurse skills\spide-schedule .claude\skills\
```

> 注意：使用复制方式时，更新 Skill 源文件后需重新复制。

---

## 各平台使用方法

### Claude Code

安装后，Skills 自动注册为斜杠命令，在对话中直接输入即可触发。

**触发方式：**

```
# 斜杠命令触发
> /spide-crawl
> /spide-deep-crawl
> /spide-analyze

# 自然语言触发（Agent 根据 description 自动匹配）
> 帮我采集微博热搜
> 分析一下百度热搜的趋势
> 把数据导出为 Excel
```

**目录结构：**

```
a_Spide_agent/
├── .claude/
│   ├── skills/                    # Claude Code Skills
│   │   ├── spide-crawl/          # → ../../skills/spide-crawl
│   │   ├── spide-deep-crawl/     # → ../../skills/spide-deep-crawl
│   │   └── ...
│   └── settings.json              # Claude Code 项目设置
├── skills/                        # Skill 源文件
│   ├── spide-crawl/SKILL.md
│   ├── spide-deep-crawl/SKILL.md
│   └── ...
└── install-skills.sh
```

### OpenClaw

OpenClaw 使用 `~/.openclaw/skills/` 全局目录，安装后所有项目均可使用。

**触发方式：**

```
# 在 OpenClaw 对话中
> 使用 spide-crawl 采集热搜
> /spide-analyze 分析知乎热榜
```

### Cursor / Windsurf

Cursor 和 Windsurf 支持 `.cursor/rules/` 或 `.windsurfrules` 格式的规则文件。可以将 `SKILL.md` 内容整合到规则文件中：

```bash
# Cursor：将 SKILL.md 内容追加到 .cursor/rules/
mkdir -p .cursor/rules
cat skills/spide-crawl/SKILL.md >> .cursor/rules/spide-crawl.mdc
cat skills/spide-analyze/SKILL.md >> .cursor/rules/spide-analyze.mdc
```

---

## Skills 详细说明

### spide-crawl — 热搜采集

从 5 大平台采集实时热搜数据。

```bash
# 基础用法
spide crawl -s weibo              # 微博热搜
spide crawl -s baidu              # 百度热搜
spide crawl -s douyin             # 抖音热点
spide crawl -s zhihu              # 知乎热榜
spide crawl -s bilibili           # B站热搜
spide crawl -a                    # 采集所有源
spide crawl -s weibo --save       # 采集并保存到数据库
```

### spide-deep-crawl — 深度采集

通过 MediaCrawler 从 7 个平台深度采集内容、评论、创作者信息。

```bash
# 搜索模式
spide deep-crawl -p xhs -m search -k "AI编程"          # 小红书搜索
spide deep-crawl -p dy -m search -k "新能源,汽车"        # 抖音搜索

# 详情模式
spide deep-crawl -p bili -m detail -u "video_id1,video_id2"  # B站详情

# 创作者模式
spide deep-crawl -p wb -m creator -c "user_id1,user_id2"     # 微博创作者

# 保存到数据库
spide deep-crawl -p xhs -m search -k "AI" --save
```

**支持平台：** `xhs`（小红书）/ `dy`（抖音）/ `ks`（快手）/ `bili`（B站）/ `wb`（微博）/ `tieba`（贴吧）/ `zhihu`（知乎）

### spide-analyze — AI 分析

基于 GLM-5.1 模型的智能分析，包括趋势、摘要、情感、采集策略。

```bash
spide analyze -s weibo            # 趋势分析 + 摘要
spide analyze -s baidu --strategy # + 智能采集策略
spide analyze -k "AI,大模型"       # 关键词分析
```

### spide-export — 数据导出

将采集数据导出为多种格式。

```bash
spide export -s weibo -f json              # JSON
spide export -s weibo -f csv               # CSV
spide export -s weibo -f excel             # Excel (.xlsx)
spide export -s weibo -f json -o ./output  # 指定输出目录
```

### spide-wordcloud — 词云生成

基于热搜或自定义文本生成词云可视化。

```bash
spide wordcloud -s weibo                  # 从热搜生成词云
spide wordcloud -t "AI,技术,大模型"         # 从文本生成
spide wordcloud -s weibo --top-keywords   # 仅输出高频关键词
```

### spide-batch — 批量并行采集

多平台并发搜索，Semaphore 控制并发数。

```bash
spide batch-crawl -p xhs,dy,bili -k "AI编程"     # 3平台并行
spide batch-crawl -p xhs,dy -c 2 --save           # 并发2，保存
spide batch-crawl -p xhs,dy -e json -o ./output   # 导出JSON
```

### spide-schedule — 定时调度

Cron-like 定时采集任务。

```bash
spide schedule start                          # 默认调度（微博/百度/知乎）
spide schedule start -c schedule.yaml -d 3600 # 自定义配置，运行1小时
spide schedule status                         # 查看状态
spide schedule stop                           # 停止
```

---

## SKILL.md 格式规范

每个 Skill 目录包含一个 `SKILL.md` 文件，遵循 AgentSkills 开放规范：

```
skills/
└── <skill-name>/
    └── SKILL.md
```

**文件结构：**

```markdown
---
name: <skill-name>
description: >
  技能描述 — 触发条件摘要。
  当用户要求 ... 时使用。
---

# Skill 标题 — 简要说明

## 触发条件
自动激活的条件描述。

## 用法
\```bash
命令示例
\```

## 工作流程
1. 步骤一
2. 步骤二

## 注意事项
- 约束和前提条件
```

**关键要素：**

| 要素 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | Skill 唯一标识，对应目录名和斜杠命令 |
| `description` | 是 | 功能描述 + 触发场景，Agent 用于自动匹配 |
| 触发条件 | 是 | 明确什么场景下激活此 Skill |
| 用法 | 是 | 可执行的命令示例 |
| 工作流程 | 否 | 推荐的执行步骤 |
| 注意事项 | 否 | 前提条件和限制 |

**加载机制：**

1. **元数据加载（常驻）** — YAML frontmatter 的 `name` + `description`，约 100 tokens
2. **指令加载（按需）** — 用户触发后加载完整 Markdown 内容，约 500 tokens
3. **资源加载（按需）** — 如需额外文件，由 Skill 指令引导读取

---

## 自定义 Skill

如需创建新的 Skill，在 `skills/` 目录下新建子目录：

```bash
# 1. 创建目录
mkdir -p skills/my-custom-skill

# 2. 编写 SKILL.md
cat > skills/my-custom-skill/SKILL.md << 'EOF'
---
name: my-custom-skill
description: >
  自定义技能描述 — 当用户要求 ... 时使用。
---

# My Custom Skill

## 触发条件
...

## 用法
\```bash
spide my-command --option
\```
EOF

# 3. 重新运行安装脚本
./install-skills.sh --claude
```

**注意事项：**

- `name` 必须与目录名一致
- `description` 应包含触发场景，便于 Agent 自动匹配
- 文件编码使用 UTF-8
- 避免在 YAML frontmatter 中使用特殊字符

---

## 卸载

```bash
# 卸载所有平台的 Skills
./install-skills.sh --uninstall

# 手动卸载 Claude Code Skills
rm -rf .claude/skills/spide-*

# 手动卸载 OpenClaw Skills
rm -rf ~/.openclaw/skills/spide-*
```

卸载后斜杠命令将不再可用，但 `skills/` 源文件不受影响，可随时重新安装。

---

## 常见问题

### Q: 安装后斜杠命令不可用？

检查以下几点：
1. 确认 `.claude/skills/` 目录下存在对应的 Skill 目录
2. 确认每个目录下有 `SKILL.md` 文件
3. 运行 `./install-skills.sh --verify` 检查安装状态
4. 重启 Claude Code 会话

### Q: Windows 下符号链接失败？

Windows Git Bash 的 `ln -s` 会创建目录副本而非真正的符号链接。这不影响功能，但更新源文件后需要重新运行安装脚本：

```bash
./install-skills.sh --claude
```

或使用 PowerShell 手动复制（参见[手动安装](#手动安装)）。

### Q: 如何更新 Skill？

修改 `skills/` 目录下的源文件即可。如果使用符号链接（Linux/macOS），更新自动生效；如果使用目录副本（Windows），需重新运行安装脚本。

### Q: Skill 支持哪些 AI Agent 平台？

| 平台 | 支持方式 | 状态 |
|------|----------|------|
| Claude Code | `.claude/skills/` 原生支持 | 已验证 |
| OpenClaw | `~/.openclaw/skills/` 原生支持 | 已验证 |
| Cursor | `.cursor/rules/*.mdc` 规则文件 | 手动配置 |
| Windsurf | `.windsurfrules` 规则文件 | 手动配置 |
| Codex (OpenAI) | AgentSkills 规范兼容 | 兼容 |

### Q: Skill 文件太大，会影响性能吗？

不会。采用渐进式加载：
- 元数据（`name` + `description`）常驻上下文，每个 Skill 约 50-100 tokens
- 完整指令仅在触发时加载，约 300-500 tokens
- 7 个 Skills 常驻开销仅约 350-700 tokens，对上下文窗口影响极小

### Q: 深度采集 Skill 需要额外环境？

是的。`spide-deep-crawl` 和 `spide-batch` 依赖 MediaCrawler，需要：
- Playwright 浏览器环境
- 对应平台的登录 Cookie
- 详见 `skills/spide-deep-crawl/SKILL.md` 中的注意事项
