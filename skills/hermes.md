# Hermes Agent Skills

## 概述

本技能提供对 Hermes Agent 工具的完整访问能力，包括技能管理、记忆系统、子 Agent 和定时任务。

## 技能列表

### hermes-skills

技能创建与管理技能。

**核心特性:**
- 内置学习循环：技能会根据使用自动改进
- 技能创建：定义名称、描述、指令和动作
- 技能运行：执行已创建的技能

**可用工具:**
- `hermes_skill_create` - 创建新技能
- `hermes_skill_run` - 运行技能
- `hermes_skill_list` - 列出所有技能
- `hermes_skill_improve` - 根据反馈改进技能

**使用示例:**
```
使用 hermes-skills 创建一个 "代码审查" 技能
```

---

### hermes-memory

记忆系统技能。

**核心特性:**
- 持久化：将重要信息存储到长期记忆
- 搜索：使用 FTS5 全文搜索 + LLM 摘要
- 回忆：根据用户画像跨会话回忆信息

**可用工具:**
- `hermes_memory_persist` - 持久化记忆
- `hermes_memory_search` - 搜索记忆
- `hermes_memory_recall` - 回忆相关信息

**使用示例:**
```
使用 hermes-memory 搜索所有关于 Python 优化的记忆
```

---

### hermes-subagent

子 Agent 管理技能。

**核心特性:**
- 并行处理：创建多个子 Agent 同时处理不同任务
- 隔离环境：每个子 Agent 在独立环境中运行
- RPC 调用：Python 脚本通过 RPC 调用工具

**可用工具:**
- `hermes_subagent_spawn` - 创建子 Agent
- `hermes_subagent_status` - 查看状态
- `hermes_subagent_result` - 获取结果

**使用示例:**
```
使用 hermes-subagent 创建 3 个子 Agent 并行搜索不同主题
```

---

### hermes-schedule

定时任务技能。

**核心特性:**
- 自然语言：使用自然语言描述任务
- 多渠道投递：结果发送到任意已配置渠道
- Cron 表达式：精确的时间控制

**可用工具:**
- `hermes_schedule_create` - 创建定时任务
- `hermes_schedule_list` - 列出所有任务
- `hermes_schedule_delete` - 删除任务

**使用示例:**
```
使用 hermes-schedule 创建每日技术新闻汇总任务
```

---

### hermes-model

模型管理技能。

**支持提供商:**

| 提供商 | 说明 |
|--------|------|
| nous | Nous Portal |
| openrouter | OpenRouter (200+ 模型) |
| openai | OpenAI |
| anthropic | Anthropic |
| nvidia | NVIDIA NIM (Nemotron) |
| xiaomi | Xiaomi MiMo |
| z.ai | 智谱 GLM |
| kimi | 月之暗面 Kimi |
| minimax | MiniMax |
| huggingface | Hugging Face |

**使用示例:**
```
使用 hermes-model 设置当前模型为 openrouter:qwen-max
```

---

## 连接方式

### HTTP 模式

```bash
# 启动 Hermes MCP Server
hermes mcp serve --port 8768

# 在 Spide Agent 中连接
spide mcp-connect --target hermes --url http://localhost:8768/mcp --action list
```

### stdio 模式

```bash
spide mcp-serve --transport stdio
```

---

## 高级特性

### 学习循环

Hermes 的独特之处在于其内置的学习循环：

1. **技能自改进**：技能在每次使用后会自动分析并改进
2. **记忆持久化**：重要信息自动持久化到长期记忆
3. **用户建模**：使用 Honcho 进行用户画像建模

### 终端后端

Hermes 支持多种运行方式：

| 后端 | 说明 |
|------|------|
| local | 本地运行 |
| Docker | Docker 容器 |
| SSH | 远程 SSH |
| Daytona | Daytona 沙箱 |
| Singularity | Singularity 容器 |
| Modal | Modal 无服务器 |

---

## 安全提示

- 子 Agent 在隔离环境中运行
- 技能权限需要明确授权
- 敏感操作需要确认
