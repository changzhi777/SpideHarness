# Mcaclaw — macOS OpenClaw (小龙虾) 一键安装引导

> 作者: 外星动物（常智） / IoTchange / 14455975@qq.com
>
> OpenClaw 是一个开源的个人 AI 助手，支持 40+ AI 模型和 20+ 消息平台。
> Mcaclaw 为 macOS 用户提供一键式安装引导，自动配置环境和模块。

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 12+ (Monterey 及以上) |
| 芯片 | Apple Silicon (M1/M2/M3/M4) 或 Intel |
| Xcode CLI | 需要 (git 等基础工具) |
| Node.js | >= 22.12.0 (脚本可自动安装) |

## 一键安装

```bash
# 一键安装（推荐）
curl -fsSL https://raw.githubusercontent.com/changzhi777/SpideHarness/main/Mcaclaw/install-mcaclaw.sh | bash

# 或者先下载再运行
curl -fsSL -o install-mcaclaw.sh https://raw.githubusercontent.com/changzhi777/SpideHarness/main/Mcaclaw/install-mcaclaw.sh
bash install-mcaclaw.sh

# 或者克隆后运行
git clone https://github.com/changzhi777/SpideHarness.git
cd SpideHarness/Mcaclaw
bash install-mcaclaw.sh
```

## 安装选项

```bash
bash install-mcaclaw.sh              # 交互式安装 (推荐)
bash install-mcaclaw.sh --skip       # 自动安装 (使用默认选项)
bash install-mcaclaw.sh --uninstall  # 卸载 OpenClaw
bash install-mcaclaw.sh --help       # 查看帮助
bash install-mcaclaw.sh --version    # 查看版本
```

## 安装流程

脚本将引导完成以下 6 个步骤：

```
1. 系统检测 → 验证 macOS + 芯片架构
2. 环境检查 → Xcode CLI + Node.js (缺失则自动安装)
3. 安装 OpenClaw → 一键脚本 / npx / npm 三种方式
4. 配置 AI 模型 → 选择提供商 + 输入 API Key
5. 配置消息通道 → Telegram / Discord / WhatsApp 等
6. 验证安装 → 运行 openclaw doctor
```

## 支持的 AI 模型

| 提供商 | 模型 | API Key 变量 |
|--------|------|-------------|
| OpenAI | GPT-4o, o3 | `OPENAI_API_KEY` |
| Anthropic | Claude Opus, Sonnet | `ANTHROPIC_API_KEY` |
| Google | Gemini 2.5 Pro | `GEMINI_API_KEY` |
| OpenRouter | 多模型聚合 | `OPENROUTER_API_KEY` |
| 智谱 AI | GLM-5.1 | `ZAI_API_KEY` |
| Moonshot | Kimi K2.5 | `MOONSHOT_API_KEY` |
| Deepseek | Deepseek V3 | `DEEPSEEK_API_KEY` |
| Ollama | 本地模型 (无需 Key) | - |

## 支持的消息通道

| 通道 | 配置方式 |
|------|---------|
| Telegram Bot | Bot Token |
| Discord Bot | Bot Token |
| WhatsApp | 扫码授权 |
| Slack Bot | Bot Token + App Token |
| 飞书 (Lark) | 配置面板 |
| 更多 | 通过 `openclaw onboard` 配置 |

## Node.js 安装方式

脚本支持 4 种 Node.js 安装方式：

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| Homebrew | `brew install node@22` | 推荐，简单快捷 |
| nvm | `nvm install 22` | 需要多版本管理 |
| fnm | `fnm install 22` | 追求速度，Rust 实现 |
| 官方 pkg | nodejs.org 下载 | 不想用包管理器 |

## 配置文件

安装完成后，配置文件位于：

```
~/.openclaw/
├── .env                  # API Key 和 Token
├── openclaw.json         # 主配置文件
└── workspace/            # 工作区数据
```

## 常用命令

```bash
openclaw onboard          # 运行交互式配置向导
openclaw --help           # 查看帮助
openclaw models list      # 列出可用模型
openclaw health           # 查看服务状态
openclaw doctor           # 系统诊断
openclaw update           # 更新版本
openclaw gateway start    # 启动 Gateway 服务
openclaw uninstall        # 卸载
```

## 卸载

```bash
# 方式一：通过脚本卸载
bash install-mcaclaw.sh --uninstall

# 方式二：使用 OpenClaw 内置卸载
openclaw uninstall --all --yes

# 方式三：手动卸载
openclaw gateway stop
openclaw gateway uninstall
rm -rf ~/.openclaw
npm rm -g openclaw
```

## 常见问题

### Q: 提示 "Node.js 版本过低"
A: 脚本会引导安装 Node.js 22.x，也可以手动安装：
```bash
brew install node@22
brew link node@22 --overwrite --force
```

### Q: 安装后找不到 `openclaw` 命令
A: 需要重启终端或执行 `source ~/.zshrc` 刷新 PATH。

### Q: 如何配置多个 AI 模型?
A: 编辑 `~/.openclaw/.env`，添加多个 API Key：
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

### Q: 如何更新 OpenClaw?
```bash
openclaw update
# 或
npm update -g openclaw
```

### Q: Apple Silicon (M 系列芯片) 有什么特殊配置?
A: 无需特殊配置，脚本会自动检测架构并选择正确的安装方式。Homebrew 会安装到 `/opt/homebrew`。

## 相关链接

- **Mcaclaw 仓库**: https://github.com/changzhi777/SpideHarness/tree/main/Mcaclaw
- **OpenClaw GitHub**: https://github.com/openclaw/openclaw
- **OpenClaw 官方文档**: https://docs.openclaw.ai
- **OpenClaw 官网**: https://openclaw.ai

## 版权

- **Mcaclaw 脚本**: Copyright (C) 2026 IoTchange - All Rights Reserved
- **OpenClaw**: MIT License (https://github.com/openclaw/openclaw)
