---
name: spide-feishu
description: >
  飞书 Bot 集成 — 通过飞书事件回调（webhook）执行 spide 命令，
  支持自然语言指令解析（crawl/analyze/track/export/batch）。
  当用户需要在飞书群中触发热搜采集、AI 分析、定时任务时使用此技能。
category: integration
---

# Spide Feishu — 飞书 Bot 集成

## 触发条件

用户要求：
- 在飞书群中执行热搜采集
- 通过飞书消息触发 AI 分析
- 推送 GitHub 热点到飞书
- 配置飞书事件回调 / 加密 token

时自动激活。

## 用法

### 启动飞书事件回调服务

```bash
# 1. 启动 Dashboard Web（含飞书 handler）
uvicorn dashboard.api:app --host 0.0.0.0 --port 8765

# 2. 飞书开放平台 → 事件订阅 → Request URL 填写:
#    https://<your-domain>/api/feishu/event
```

### 飞书群中发送指令

| 指令 | 格式 | 示例 | 等价 CLI |
|------|------|------|----------|
| `help` | `help` | `help` | 返回帮助文本 |
| `status` | `status` | `status` | 查 SQLite 统计 |
| `crawl` | `crawl <source\|all>` | `crawl weibo` | `spide crawl -s weibo --save` |
| `analyze` | `analyze <source>` | `analyze baidu` | `spide analyze -s baidu` |
| `track` | `track <source> [N]` | `track weibo 5` | `spide track -s weibo --top 5` |
| `export` | `export <source>` | `export zhihu` | `spide export -s zhihu -f excel` |
| `batch` | `batch <p1,p2>` | `batch xhs,dy` | `spide batch-crawl -p xhs,dy` |

**示例对话**：
```
[用户 @机器人] crawl weibo
[机器人] 正在采集微博热搜...
[机器人] ✓ 已保存 50 条记录
         [1] 某热搜话题 (热度: 12,345,678)
         [2] 另一热搜 (热度: 9,876,543)
         ...
```

### HTTP REST API 方式

```bash
# 通用命令执行（自动解析 text）
curl -X POST http://localhost:8765/api/feishu/command \
  -H "Content-Type: application/json" \
  -d '{"text": "crawl weibo"}'

# 直接指定命令 + 参数
curl -X POST http://localhost:8765/api/feishu/command \
  -H "Content-Type: application/json" \
  -d '{"command": "crawl", "args": {"source": "weibo"}}'

# URL 验证（飞书事件订阅首次握手）
curl -X POST http://localhost:8765/api/feishu/event \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "xxx", "token": "yyy"}'
```

### 通过 MCP 调用

飞书集成**不直接通过 MCP**，但可结合 `manage_memory` 工具持久化群消息上下文：

```python
# 在 Claude Desktop 中：
# 1. 记忆存储飞书群 ID
result = await client.call_tool("manage_memory", {
    "action": "add",
    "title": "feishu_chat_id_main_group",
    "content": "oc_xxxxxxxxxxxxx"
})
# 2. 查询记忆
result = await client.call_tool("manage_memory", {
    "action": "get",
    "title": "feishu_chat_id_main_group"
})
```

## 飞书事件回调流程

```
飞书开放平台
  ↓ POST /api/feishu/event
  ↓
dashboard/feishu_handler.py
  ├─→ url_verification: 回 challenge
  └─→ im.message.receive_v1: 解析文本 → execute_command
                                  ↓
                            subprocess.run([spide, ...])
                                  ↓
                            返回 JSON 响应
```

## 支持的消息类型

| 类型 | 解析方式 |
|------|----------|
| `text` | 直接取 `content.text` |
| `post` | 提取 `title` + 所有 `line_blocks[].text` 拼接 |
| 其他 | 尝试取 `content.text`，失败则忽略 |

## 鉴权（可选）

```python
from dashboard.api import app
from dashboard.feishu_handler import set_feishu_config

set_feishu_config(
    app_id="cli_xxx",
    app_secret="xxx",
    verification_token="xxx",  # 用于 URL 验证
    encrypt_key="xxx",         # 用于消息解密
)
```

> 不配置时，所有请求**默认通过**（开发环境）。生产环境**强烈建议**配置。

## 前置条件

- 飞书企业自建应用：https://open.feishu.cn/app
- 应用权限：`im:message:receive_v1`（接收消息）
- 机器人能力：启用"接收消息"
- 事件订阅：填写 Request URL + 选择 `im.message.receive_v1`
- Dashboard 服务公网可访问（用 nginx 反代 + HTTPS）

## 注意事项

- 飞书事件回调**必须 HTTPS**（Let's Encrypt 免费证书）
- `subprocess.run` 超时：crawl=120s / analyze=180s / track=180s / batch=300s
- 单条消息长度限制：4000 字符（超长结果自动截断 + 提示）
- 群消息 @机器人 后才触发（私聊直接触发）
