# Claude Desktop / Cursor / Cline — 一键集成 SpideHarness Agent

> 版本: V3.1.1 | 更新: 2026-06-09 | 受众: 终端用户 + 桌面 AI 客户端集成方

本文档说明如何将 **SpideHarness Agent** 集成到主流 AI 桌面客户端（Claude Desktop / Cursor / Cline / Continue 等支持 MCP 协议的客户端）。

---

## 1. 集成流程（5 分钟）

```
┌────────────────┐    1. 准备项目    ┌────────────────────────┐
│  Spide_agent   │ ──────────────►  │  克隆 + uv sync        │
│  仓库          │                  │  复制 configs/ 模板    │
└────────────────┘                  └────────────────────────┘
                                            │
                                            ▼
┌────────────────┐    2. 验证 CLI   ┌────────────────────────┐
│  终端          │ ◄──────────────  │  spide doctor          │
└────────────────┘    看到 OK       │  spide config          │
                                   └────────────────────────┘
                                            │
                                            ▼
┌────────────────┐    3. 改配置     ┌────────────────────────┐
│  客户端        │ ◄──────────────  │  mcpServers.spide-agent│
│  (Claude 等)   │                  │  command: spide        │
└────────────────┘    重启客户端    │  args: [mcp-serve]     │
                                   └────────────────────────┘
                                            │
                                            ▼
┌────────────────┐    4. 验证       ┌────────────────────────┐
│  对话框        │ ──────────────►  │  "采集微博热搜"        │
└────────────────┘                  │  → 应触发工具调用      │
                                   └────────────────────────┘
```

---

## 2. 前置准备

### 2.1 系统要求

| 项 | 要求 |
|---|---|
| OS | macOS 12+ / Ubuntu 20.04+ / Windows 10+ (WSL2 推荐) |
| Python | 3.12+ |
| 包管理 | [uv](https://github.com/astral-sh/uv)（推荐）或 pip |
| 磁盘 | ≥ 500 MB（包含 Playwright Chromium） |

### 2.2 克隆与安装

```bash
# 1. 克隆仓库
git clone https://gitea.example.com/iotchange/Spide_agent.git
cd Spide_agent

# 2. 安装依赖（使用 uv，推荐）
uv sync

# 或使用 pip
pip install -e .

# 3. 验证安装
spide --version
# 应输出: SpideHarness Agent 1.1.1
```

### 2.3 初始化工作空间

```bash
spide init
# 按提示创建 ~/.spide_agent/ 工作空间
```

### 2.4 配置文件

复制并编辑 `configs/` 下的 YAML 文件：

```bash
cd configs
cp default.yaml.example default.yaml
cp uapi.yaml.example uapi.yaml
cp llm.yaml.example llm.yaml
# 编辑 uapi.yaml 填入 API Key
# 编辑 llm.yaml 填入智谱 API Key
```

**最小配置（仅使用免费工具）**：
- `uapi.yaml` 必填（`crawl_hot_topics` 需要）
- `llm.yaml` 必填（`web_search` 需要；`web_search_enhanced` 用 duckduckgo 时可选）

### 2.5 验证环境

```bash
spide doctor
```

**预期输出**（关键字段）：
```
✓ Python 3.12.0
✓ spide 命令可用
✓ 配置文件加载成功
✓ UAPI Key 已配置
✓ LLM API Key 已配置
✓ MCP Server 启动正常
```

> 若有 ✗ 项，请按提示修复后再继续。

---

## 3. Claude Desktop 集成

### 3.1 配置文件位置

| OS | 路径 |
|----|------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

### 3.2 配置文件内容

#### 方式 A：使用系统 PATH 中的 `spide` 命令

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"]
    }
  }
}
```

#### 方式 B：使用绝对路径（推荐，避免 PATH 问题）

**macOS/Linux**：
```bash
# 查找 spide 绝对路径
which spide
# 例: /Users/mac/.local/bin/spide
```

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "/Users/mac/.local/bin/spide",
      "args": ["mcp-serve"]
    }
  }
}
```

**Windows**：
```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "C:\\Users\\YourName\\.local\\bin\\spide.exe",
      "args": ["mcp-serve"]
    }
  }
}
```

#### 方式 C：直接通过 `python -m spide`（最稳定）

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/Spide_agent",
        "run", "python", "-m", "spide", "mcp-serve"
      ]
    }
  }
}
```

> 替换 `/absolute/path/to/Spide_agent` 为实际克隆路径。

### 3.3 重启 Claude Desktop

**完全退出**（不是关闭窗口）：
- **macOS**: `⌘ + Q` 或菜单 Claude → Quit Claude
- **Windows**: 右键任务栏 → 关闭窗口
- **Linux**: 窗口菜单 → Quit

### 3.4 验证集成

1. 打开 Claude Desktop
2. 点击左下角 🔌 插件图标（Plugins/Tools）
3. 应看到 "spide-agent" 及 8 个工具：
   - `crawl_hot_topics` / `web_search` / `web_search_enhanced`
   - `fetch_web_page` / `fetch_repo_info`
   - `manage_memory` / `health_check` / `deep_crawl_hot_topics`

4. 在对话中测试：
   ```
   请用 spide-agent 工具采集微博热搜
   ```
   应看到 Claude 调用 `crawl_hot_topics` 工具并返回结果。

---

## 4. Cursor 集成

### 4.1 配置文件位置

| OS | 路径 |
|----|------|
| **macOS** | `~/.cursor/mcp.json` |
| **Windows** | `%APPDATA%\Cursor\User\mcp.json` |
| **Linux** | `~/.config/Cursor/mcp.json` |

### 4.2 配置文件内容

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Spide_agent"
      }
    }
  }
}
```

### 4.3 重启 Cursor

完全退出后重新打开（`⌘ + Q` / 文件 → Exit）。

### 4.4 验证集成

1. 打开 Cursor
2. 按 `⌘ + L` 打开 Composer
3. 输入：
   ```
   使用 spide-agent 工具搜索 Python asyncio 教程
   ```
4. 应自动调用 `web_search_enhanced` 工具。

---

## 5. Cline (VS Code) 集成

### 5.1 安装 Cline 扩展

VS Code → Extensions → 搜索 "Cline" → Install。

### 5.2 配置 MCP Servers

1. Cline 侧边栏 → ⚙️ Settings → MCP Servers
2. 或编辑 `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

### 5.3 配置内容

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "disabled": false
    }
  }
}
```

### 5.4 验证

VS Code → Cline 面板 → "Approved Tools" 应列出 8 个 spide-agent 工具。

---

## 6. 环境变量注入（高级）

如需在 MCP 启动时覆盖 API Key（无需修改 `configs/*.yaml`）：

```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {
        "SPIDE_LLM__COMMON__API_KEY": "your.zhipu.api.key",
        "SPIDE_UAPI__COMMON__API_KEY": "your.uapi.key",
        "GITHUB_TOKEN": "ghp_optional_for_higher_rate_limit"
      }
    }
  }
}
```

**环境变量命名规则**：`SPIDE_<SECTION>__<KEY>`，双下划线分隔嵌套层级。

| YAML 路径 | 环境变量 |
|-----------|----------|
| `llm.common.api_key` | `SPIDE_LLM__COMMON__API_KEY` |
| `uapi.common.api_key` | `SPIDE_UAPI__COMMON__API_KEY` |
| `mqtt.broker.host` | `SPIDE_MQTT__BROKER__HOST` |

> 环境变量优先级**高于** `configs/*.yaml`。

---

## 7. 一键安装脚本

为简化集成，提供 shell 脚本（macOS/Linux）：

```bash
#!/bin/bash
# install-claude-mcp.sh
# 用法: ./install-claude-mcp.sh /path/to/Spide_agent

set -e
SPIDE_ROOT="${1:-$HOME/Spide_agent}"
CONFIG_PATH="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# 1. 验证项目目录
if [ ! -d "$SPIDE_ROOT" ]; then
  echo "❌ 项目目录不存在: $SPIDE_ROOT"
  exit 1
fi

# 2. 安装依赖
cd "$SPIDE_ROOT"
uv sync

# 3. 验证 CLI
if ! command -v spide &> /dev/null; then
  echo "❌ spide 命令未找到，请运行 'uv sync' 后重试"
  exit 1
fi

# 4. 备份现有配置
if [ -f "$CONFIG_PATH" ]; then
  cp "$CONFIG_PATH" "${CONFIG_PATH}.bak.$(date +%s)"
  echo "✓ 备份现有配置到 ${CONFIG_PATH}.bak.*"
fi

# 5. 合并 MCP 配置
mkdir -p "$(dirname "$CONFIG_PATH")"
if [ ! -f "$CONFIG_PATH" ]; then
  echo '{"mcpServers": {}}' > "$CONFIG_PATH"
fi

python3 -c "
import json
from pathlib import Path
p = Path('$CONFIG_PATH')
cfg = json.loads(p.read_text())
cfg.setdefault('mcpServers', {})
cfg['mcpServers']['spide-agent'] = {
    'command': 'spide',
    'args': ['mcp-serve']
}
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('✓ Claude Desktop 配置已更新')
"

# 6. 提示用户
echo ""
echo "✅ 安装完成！请执行以下步骤："
echo "  1. 关闭 Claude Desktop (⌘ + Q)"
echo "  2. 重新打开 Claude Desktop"
echo "  3. 在对话中输入: 采集微博热搜"
echo ""
```

**用法**：
```bash
chmod +x install-claude-mcp.sh
./install-claude-mcp.sh ~/Spide_agent
```

---

## 8. 故障排除

### 8.1 工具列表为空

**症状**：Claude Desktop 看到 `spide-agent` 服务器但工具数为 0。

**排查**：
1. 查看 Claude 日志：
   - macOS: `tail -f ~/Library/Logs/Claude/mcp*.log`
   - Windows: `type %APPDATA%\Claude\Logs\mcp*.log`

2. 手动测试 MCP Server 启动：
   ```bash
   spide mcp-serve
   # 应保持运行不退出，等待 stdin 输入
   # Ctrl+C 退出
   ```

3. 检查 mcp-sdk 版本：
   ```bash
   uv pip show mcp | grep Version
   # 应 >= 1.27.0
   ```

### 8.2 工具调用失败 `Tool result missing due to internal error`

**症状**：Claude 提示"工具调用失败"但无具体错误。

**排查**：
1. 启用详细日志：
   ```json
   {"mcpServers": {"spide-agent": {"command": "spide", "args": ["mcp-serve", "--verbose"]}}}
   ```
   （如 CLI 支持 `--verbose`）

2. 直接在终端运行：
   ```bash
   spide crawl -s weibo
   # 查看具体错误
   ```

3. 检查 `spide_data.log`（项目根目录）

### 8.3 `command not found: spide`

**原因**：`spide` 不在 Claude Desktop 进程的 PATH 中（GUI 应用 PATH 可能与 shell 不同）。

**解决**：使用**绝对路径**（见 §3.2 方式 B）。

**查找绝对路径**：
```bash
which spide                      # macOS/Linux
where spide                      # Windows
uv run which spide               # 通过 uv 安装
```

### 8.4 `Permission denied` 启动错误

**原因**：`spide` 脚本无执行权限。

**解决**：
```bash
chmod +x $(which spide)
# 或重新安装
uv sync --reinstall
```

### 8.5 `ModuleNotFoundError: No module named 'spide'`

**原因**：Python 环境隔离 — Claude Desktop 使用了不同的 Python。

**解决**：使用方式 C（`uv --directory`）指定项目根目录：
```json
{
  "mcpServers": {
    "spide-agent": {
      "command": "uv",
      "args": ["--directory", "/path/to/Spide_agent", "run", "python", "-m", "spide", "mcp-serve"]
    }
  }
}
```

### 8.6 工具调用超时

**症状**：Claude 显示 "Tool execution timed out"。

**解决**：
- `web_search_enhanced` (duckduckgo) 默认 15s 超时
- `deep_crawl_hot_topics` 需要 30s+（Playwright 启动）
- 复杂任务（`analyze` / `track`）需要 60-180s
- Claude Desktop MCP 超时默认 60s，建议长任务用 `batch` 模式

### 8.7 API Key 相关错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `UAPI Key not configured` | `configs/uapi.yaml` 缺 Key | 编辑 yaml 或用 ENV 注入 |
| `LLM API 401` | 智谱 Key 无效/过期 | 检查 `configs/llm.yaml` |
| `GitHub API 403` | 未认证 60/h 限额 | 配置 `GITHUB_TOKEN` |

---

## 9. 验证清单

集成完成后，运行以下验证：

- [ ] `spide --version` 输出 `1.1.1`
- [ ] `spide doctor` 所有项 ✓
- [ ] Claude Desktop 显示 8 个 spide-agent 工具
- [ ] 测试对话：采集微博热搜 → 返回 20 条话题
- [ ] 测试对话：搜索 Python 教程 → 返回搜索结果
- [ ] 测试对话：分析百度热搜 → 返回趋势报告
- [ ] 错误处理：故意传错参数 → 返回友好错误提示

---

## 10. 进阶

### 10.1 多实例配置

可在同一客户端配置多个 SpideHarness 实例（不同项目目录/不同配置）：

```json
{
  "mcpServers": {
    "spide-prod": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {"SPIDE_WORKSPACE": "~/.spide_agent_prod"}
    },
    "spide-dev": {
      "command": "spide",
      "args": ["mcp-serve"],
      "env": {"SPIDE_WORKSPACE": "~/.spide_agent_dev"}
    }
  }
}
```

### 10.2 与 HTTP REST API 协同

如已启动 FastAPI Dashboard（端口 8765），可同时使用 HTTP + MCP 两种方式：

```bash
# 终端 1: Dashboard Web 服务
uvicorn dashboard.api:app --port 8765

# 终端 2: MCP Server（通过 Claude Desktop）
spide mcp-serve
```

两者共享 SQLite 数据库（`spide_data.db`），MCP 采集的数据立即在 Dashboard 可见。

### 10.3 升级 SpideHarness

升级后需重启 Claude Desktop 加载新版工具：

```bash
cd /path/to/Spide_agent
git pull
uv sync
# 退出 Claude Desktop (⌘Q)
# 重新打开
```

---

## 11. 相关文档

- [INTEGRATION.md](./INTEGRATION.md) — 三视角综合集成（开发者 + 终端用户 + AI Agent）
- [mcp-api-reference.md](../mcp-api-reference.md) — MCP 协议对接文档
- [http-api-reference.md](../http-api-reference.md) — HTTP REST API 文档
- [CLAUDE.md](../../CLAUDE.md) — 项目主文档
- [dashboard/CLAUDE.md](../../dashboard/CLAUDE.md) — Dashboard 模块文档

---

*Copyright (C) 2026 IoTchange - All Rights Reserved*
