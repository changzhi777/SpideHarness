# OpenClaw Skills

## 概述

本技能提供对 OpenClaw 工具的完整访问能力，包括浏览器控制、会话管理、技能和渠道管理。

## 技能列表

### openclaw-browser

浏览器自动化控制技能。

**可用工具:**
- `openclaw_browser_navigate` - 导航到指定 URL
- `openclaw_browser_click` - 点击页面元素
- `openclaw_browser_type` - 输入文本
- `openclaw_browser_screenshot` - 截取截图
- `openclaw_browser_content` - 获取页面内容

**使用示例:**
```
使用 openclaw-browser 导航到 https://github.com 并获取页面标题
```

---

### openclaw-sessions

会话管理技能。

**可用工具:**
- `openclaw_sessions_list` - 列出所有活动会话
- `openclaw_sessions_history` - 获取会话历史
- `openclaw_sessions_send` - 发送消息
- `openclaw_sessions_spawn` - 创建新会话

**使用示例:**
```
使用 openclaw-sessions 列出所有活动会话
```

---

### openclaw-skills

技能管理技能。

**可用工具:**
- `openclaw_skills_list` - 列出所有可用技能
- `openclaw_skills_run` - 运行指定技能
- `openclaw_skills_install` - 从 ClawHub 安装技能

**使用示例:**
```
使用 openclaw-skills 运行 "github-readme" 技能
```

---

### openclaw-channels

渠道管理技能。

**可用工具:**
- `openclaw_channels_list` - 列出所有已配置渠道
- `openclaw_channels_status` - 检查渠道连接状态
- `openclaw_gateway_status` - 检查 Gateway 状态

**使用示例:**
```
使用 openclaw-channels 检查 Telegram 渠道状态
```

---

## 支持的渠道

OpenClaw 支持 25+ 消息渠道：

| 渠道 | 说明 |
|------|------|
| whatsapp | WhatsApp |
| telegram | Telegram |
| slack | Slack |
| discord | Discord |
| google_chat | Google Chat |
| signal | Signal |
| imessage | iMessage |
| bluebubbles | BlueBubbles |
| irc | IRC |
| microsoft_teams | Microsoft Teams |
| matrix | Matrix |
| feishu | 飞书 |
| line | LINE |
| mattermost | Mattermost |
| nextcloud_talk | Nextcloud Talk |
| nostr | Nostr |
| synology_chat | Synology Chat |
| twitch | Twitch |
| zalo | Zalo |
| wechat | 微信 |
| qq | QQ |
| webchat | WebChat |
| macos | macOS |
| ios | iOS |
| android | Android |

---

## 连接方式

### HTTP 模式

```bash
# 启动 OpenClaw Gateway
openclaw gateway --port 18789 --verbose

# 在 Spide Agent 中连接
spide mcp-connect --target openclaw --url http://localhost:18789/mcp --action list
```

### stdio 模式

```bash
# 直接调用
spide mcp-serve --transport stdio
```

---

## 安全提示

- 默认情况下，工具在主机上运行，Agent 具有完全访问权限
- 暴露到远程时，务必配置沙箱模式
- 详情请参阅 OpenClaw 安全文档
