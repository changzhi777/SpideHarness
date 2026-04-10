#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Mcaclaw — macOS OpenClaw (小龙虾) 一键安装引导脚本
#
# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
#
# 用法:
#   bash install-mcaclaw.sh          # 交互式安装
#   bash install-mcaclaw.sh --skip   # 跳过确认，自动安装
#   bash install-mcaclaw.sh --help   # 查看帮助
#
# GitHub: https://github.com/openclaw/openclaw
# Docs:   https://docs.openclaw.ai
# ---------------------------------------------------------------------------
set -euo pipefail

# ============================== 版本信息 ====================================
readonly SCRIPT_NAME="Mcaclaw"
readonly SCRIPT_VERSION="1.0.0"
readonly OPENCLAW_MIN_NODE="22.12.0"

# ============================== 颜色定义 ====================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m' # No Color

# ============================== 工具函数 ====================================

print_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
print_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
print_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
print_step()    { echo -e "\n${BOLD}${CYAN}==>${NC} ${BOLD}$*${NC}"; }

print_banner() {
    echo -e "${CYAN}"
    cat << 'BANNER'
  __  __       _
 |  \/  | __ _| |_ ___ _ __
 | |\/| |/ _` | __/ _ \ '__|
 | |  | | (_| | ||  __/ |
 |_|  |_|\__,_|\__\___|_|
BANNER
    echo -e "${NC}"
    echo -e "  ${BOLD}macOS OpenClaw (小龙虾) 安装引导${NC} v${SCRIPT_VERSION}"
    echo -e "  ${DIM}GitHub: https://github.com/openclaw/openclaw${NC}"
    echo ""
}

# 检查命令是否存在
has_cmd() {
    command -v "$1" &>/dev/null
}

# 版本号比较: $1 >= $2
version_gte() {
    local v1="$1" v2="$2"
    # 将版本号转为可比较的整数
    local i1 i2
    IFS='.' read -r -a i1 <<< "$v1"
    IFS='.' read -r -a i2 <<< "$v2"
    for idx in 0 1 2; do
        local a="${i1[$idx]:-0}"
        local b="${i2[$idx]:-0}"
        if (( a > b )); then return 0; fi
        if (( a < b )); then return 1; fi
    done
    return 0
}

# 确认提示
confirm() {
    local prompt="${1:-是否继续?} [Y/n] "
    local default="${2:-Y}"
    if [[ "${AUTO_YES:-}" == "1" ]]; then
        echo -e "${prompt}y"
        return 0
    fi
    read -r -p "$(echo -e "$prompt")" answer
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[Yy] ]] || [[ -z "$answer" && "$default" == "Y" ]]
}

# 选择菜单
select_option() {
    local prompt="$1"
    shift
    local options=("$@")
    echo -e "\n${BOLD}${prompt}${NC}"
    for i in "${!options[@]}"; do
        echo -e "  ${GREEN}$((i+1)))${NC} ${options[$i]}"
    done
    read -r -p "$(echo -e "\n${CYAN}请选择 [1-${#options[@]}]:${NC} ")" choice
    # 默认选第一个
    choice="${choice:-1}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#options[@]} )); then
        SELECTED_INDEX=$((choice - 1))
        return 0
    fi
    SELECTED_INDEX=0
    return 0
}

# 多选菜单
multi_select() {
    local prompt="$1"
    shift
    local options=("$@")
    echo -e "\n${BOLD}${prompt}${NC}"
    for i in "${!options[@]}"; do
        echo -e "  ${GREEN}$((i+1)))${NC} ${options[$i]}"
    done
    echo -e "  ${YELLOW}输入编号，多个用空格分隔 (如: 1 3 5)，直接回车跳过${NC}"
    read -r -p "$(echo -e "\n${CYAN}请选择:${NC} ")" choices
    MULTI_SELECTED=()
    if [[ -n "$choices" ]]; then
        for c in $choices; do
            if [[ "$c" =~ ^[0-9]+$ ]] && (( c >= 1 && c <= ${#options[@]} )); then
                MULTI_SELECTED+=("$((c-1))")
            fi
        done
    fi
}

# ============================== 系统检查 ====================================

check_macos() {
    print_step "检查操作系统"
    if [[ "$(uname)" != "Darwin" ]]; then
        print_error "此脚本仅支持 macOS 系统。"
        print_info "Linux 用户请使用: curl -fsSL https://openclaw.ai/install.sh | bash"
        exit 1
    fi

    local macos_version
    macos_version="$(sw_vers -productVersion)"
    print_ok "macOS $macos_version"
}

check_arch() {
    print_step "检测芯片架构"
    local arch
    arch="$(uname -m)"
    case "$arch" in
        arm64)
            print_ok "Apple Silicon (M 系列芯片)"
            ARCH_TYPE="arm64"
            ;;
        x86_64)
            print_ok "Intel (x86_64)"
            ARCH_TYPE="x86_64"
            ;;
        *)
            print_warn "未知架构: $arch"
            ARCH_TYPE="$arch"
            ;;
    esac
}

check_xcode_cli() {
    print_step "检查 Xcode Command Line Tools"
    if xcode-select -p &>/dev/null; then
        print_ok "Xcode CLI 已安装"
    else
        print_warn "未检测到 Xcode Command Line Tools"
        if confirm "需要安装 Xcode CLI (git 等基础工具)。是否现在安装?"; then
            xcode-select --install 2>/dev/null || true
            print_info "请在弹出的安装窗口中完成安装后重新运行此脚本。"
            exit 0
        else
            print_error "Xcode CLI 是必需的。安装中止。"
            exit 1
        fi
    fi
}

# ============================== Node.js 安装 ================================

check_nodejs() {
    print_step "检查 Node.js 环境"
    if has_cmd node; then
        local node_version
        node_version="$(node -v | sed 's/^v//')"
        if version_gte "$node_version" "$OPENCLAW_MIN_NODE"; then
            print_ok "Node.js $node_version (>= $OPENCLAW_MIN_NODE)"
            return 0
        else
            print_warn "Node.js $node_version 版本过低，需要 >= $OPENCLAW_MIN_NODE"
        fi
    else
        print_warn "未检测到 Node.js"
    fi

    # 需要安装/升级 Node.js
    install_nodejs
}

install_nodejs() {
    echo ""
    echo -e "  ${BOLD}请选择 Node.js 安装方式:${NC}"
    echo -e "  ${GREEN}1)${NC} Homebrew (推荐，简单快捷)"
    echo -e "  ${GREEN}2)${NC} nvm (Node Version Manager，灵活管理多版本)"
    echo -e " ${GREEN} 3)${NC} fnm (Fast Node Manager，Rust 实现，速度最快)"
    echo -e "  ${GREEN}4)${NC} 官方安装包 (pkg，从 nodejs.org 下载)"
    echo -e "  ${GREEN}5)${NC} 跳过 (自行安装后重新运行)"

    read -r -p "$(echo -e "\n${CYAN}请选择 [1-5]:${NC} ")" choice
    choice="${choice:-1}"

    case "$choice" in
        1) install_node_brew ;;
        2) install_node_nvm ;;
        3) install_node_fnm ;;
        4) install_node_pkg ;;
        5)
            print_info "请手动安装 Node.js >= $OPENCLAW_MIN_NODE 后重新运行。"
            exit 0
            ;;
        *) install_node_brew ;;
    esac
}

install_node_brew() {
    print_step "通过 Homebrew 安装 Node.js"

    if ! has_cmd brew; then
        print_info "先安装 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Apple Silicon 需要配置 PATH
        if [[ "$ARCH_TYPE" == "arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
            if ! grep -q "brew shellenv" ~/.zprofile 2>/dev/null; then
                echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            fi
        fi
    fi

    brew install node@22
    brew link node@22 --overwrite --force 2>/dev/null || true

    # 验证
    local node_version
    node_version="$(node -v | sed 's/^v//')"
    print_ok "Node.js $node_version 安装成功"
}

install_node_nvm() {
    print_step "通过 nvm 安装 Node.js"

    if ! has_cmd nvm; then
        print_info "安装 nvm..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    nvm install 22
    nvm use 22
    nvm alias default 22

    local node_version
    node_version="$(node -v | sed 's/^v//')"
    print_ok "Node.js $node_version 安装成功"
}

install_node_fnm() {
    print_step "通过 fnm 安装 Node.js"

    if ! has_cmd fnm; then
        print_info "安装 fnm..."
        brew install fnm
        if ! grep -q "fnm env" ~/.zshrc 2>/dev/null; then
            echo 'eval "$(fnm env --use-on-cd --shell zsh)"' >> ~/.zshrc
        fi
        eval "$(fnm env --use-on-cd)"
    fi

    fnm install 22
    fnm use 22
    fnm default 22

    local node_version
    node_version="$(node -v | sed 's/^v//')"
    print_ok "Node.js $node_version 安装成功"
}

install_node_pkg() {
    print_step "通过官方安装包安装 Node.js"
    print_info "正在打开 Node.js 官方下载页面..."
    open "https://nodejs.org/en/download/prebuilt-installer"
    print_info "请下载并安装 Node.js 22.x LTS 后重新运行此脚本。"
    exit 0
}

# ============================== OpenClaw 安装 ===============================

fix_npm_permissions() {
    # 修复 npm 缓存目录权限（EACCES 常见问题）
    local npm_cache
    npm_cache="$(npm config get cache 2>/dev/null || echo "$HOME/.npm")"
    if [ ! -w "$npm_cache" ]; then
        print_warn "npm 缓存目录权限异常，自动修复..."
        sudo chown -R "$(id -u):$(id -g)" "$npm_cache"
        print_ok "npm 缓存权限已修复"
    fi
}

install_openclaw() {
    print_step "安装 OpenClaw (小龙虾)"

    # 修复 npm 缓存权限（常见 EACCES 问题）
    fix_npm_permissions

    # 默认使用 npm 全局安装（最简单可靠，不会接管 stdin）
    print_info "通过 npm 全局安装 OpenClaw..."
    if ! npm install -g openclaw 2>&1; then
        # npm 全局安装失败时回退到 sudo
        print_warn "普通权限安装失败，使用 sudo 重试..."
        sudo npm install -g openclaw
    fi

    # 验证安装
    if has_cmd openclaw; then
        local oc_version
        oc_version="$(openclaw --version 2>/dev/null || echo "unknown")"
        print_ok "OpenClaw $oc_version 安装成功"
    else
        print_warn "未在 PATH 中找到 openclaw 命令，可能需要重启终端。"
        print_info "手动安装方式:"
        print_info "  npm install -g openclaw          # npm 全局安装"
        print_info "  npx openclaw@latest onboard       # npx 免安装运行"
        print_info "  curl -fsSL https://openclaw.ai/install.sh | bash  # 官方脚本"
    fi
}

# ============================== AI 模型配置 =================================

config_ai_model() {
    print_step "配置 AI 模型"

    local models=(
        "OpenAI (GPT-4o / o3) — 需要 OPENAI_API_KEY"
        "Anthropic (Claude Opus/Sonnet) — 需要 ANTHROPIC_API_KEY"
        "Google (Gemini 2.5 Pro) — 需要 GEMINI_API_KEY"
        "OpenRouter (多模型聚合) — 需要 OPENROUTER_API_KEY"
        "智谱 AI (GLM-5.1) — 需要 ZAI_API_KEY"
        "Moonshot (Kimi K2.5，推荐) — 需要 MOONSHOT_API_KEY"
        "Deepseek — 需要 DEEPSEEK_API_KEY"
        "Ollama (本地模型) — 无需 API Key"
        "跳过，稍后配置"
    )

    select_option "选择主要 AI 模型提供商:" "${models[@]}"

    local env_file="$HOME/.openclaw/.env"
    mkdir -p "$HOME/.openclaw"

    # 如果 .env 不存在则创建
    touch "$env_file"

    case "$SELECTED_INDEX" in
        0) _config_api_key "OPENAI_API_KEY" "OpenAI" "$env_file" ;;
        1) _config_api_key "ANTHROPIC_API_KEY" "Anthropic" "$env_file" ;;
        2) _config_api_key "GEMINI_API_KEY" "Google Gemini" "$env_file" ;;
        3) _config_api_key "OPENROUTER_API_KEY" "OpenRouter" "$env_file" ;;
        4) _config_api_key "ZAI_API_KEY" "智谱 AI" "$env_file" ;;
        5) _config_api_key "MOONSHOT_API_KEY" "Moonshot" "$env_file" ;;
        6) _config_api_key "DEEPSEEK_API_KEY" "Deepseek" "$env_file" ;;
        7) _config_ollama "$env_file" ;;
        8) print_info "已跳过模型配置，稍后可通过编辑 ~/.openclaw/.env 配置。" ;;
    esac

    print_ok "AI 模型配置完成"
}

_config_api_key() {
    local var_name="$1"
    local provider="$2"
    local env_file="$3"

    echo ""
    echo -e "  ${BOLD}配置 $provider API Key${NC}"
    echo -e "  ${DIM}获取地址: https://platform.openclaw.ai/models${NC}"
    read -r -p "$(echo -e "  ${CYAN}请输入 ${var_name}:${NC} ")" api_key

    if [[ -n "$api_key" ]]; then
        # 移除旧的配置
        if grep -q "^${var_name}=" "$env_file" 2>/dev/null; then
            sed -i '' "s|^${var_name}=.*|${var_name}=${api_key}|" "$env_file"
        else
            echo "${var_name}=${api_key}" >> "$env_file"
        fi
        print_ok "$provider API Key 已保存"
    else
        print_warn "未输入 API Key，稍后请手动编辑 $env_file"
    fi
}

_config_ollama() {
    local env_file="$1"

    print_info "Ollama 使用本地模型，无需 API Key"
    if has_cmd ollama; then
        print_ok "Ollama 已安装"
    else
        if confirm "是否安装 Ollama?"; then
            brew install ollama
        fi
    fi

    # 设置 Ollama 基础 URL
    if ! grep -q "^OLLAMA_BASE_URL=" "$env_file" 2>/dev/null; then
        echo "OLLAMA_BASE_URL=http://localhost:11434" >> "$env_file"
    fi
}

# ============================== 消息通道配置 ================================

config_channels() {
    print_step "配置消息通道 (可选)"

    echo -e "  ${DIM}OpenClaw 支持 20+ 消息平台，可连接你的常用聊天工具。${NC}"
    echo -e "  ${DIM}也可以稍后通过 'openclaw onboard' 配置。${NC}"

    if ! confirm "是否现在配置消息通道?"; then
        print_info "已跳过通道配置。稍后运行 'openclaw onboard' 即可配置。"
        return 0
    fi

    local channels=(
        "Telegram Bot"
        "Discord Bot"
        "WhatsApp (扫码授权)"
        "Slack Bot"
        "飞书 (Lark)"
        "跳过，稍后配置"
    )

    multi_select "选择要配置的消息通道:" "${channels[@]}"

    local env_file="$HOME/.openclaw/.env"

    for idx in ${MULTI_SELECTED[@]+"${MULTI_SELECTED[@]}"}; do
        case "$idx" in
            0) _config_channel_token "TELEGRAM_BOT_TOKEN" "Telegram Bot" "$env_file" ;;
            1) _config_channel_token "DISCORD_BOT_TOKEN" "Discord Bot" "$env_file" ;;
            2) print_info "WhatsApp 需要扫码授权，请运行 'openclaw onboard' 选择 WhatsApp 进行配置。" ;;
            3)
                _config_channel_token "SLACK_BOT_TOKEN" "Slack Bot Token" "$env_file"
                _config_channel_token "SLACK_APP_TOKEN" "Slack App Token" "$env_file"
                ;;
            4) print_info "飞书配置请参考: https://docs.openclaw.ai/channels/feishu" ;;
        esac
    done

    print_ok "消息通道配置完成"
}

_config_channel_token() {
    local var_name="$1"
    local label="$2"
    local env_file="$3"

    echo ""
    read -r -p "$(echo -e "  ${CYAN}请输入 ${label}:${NC} ")" token

    if [[ -n "$token" ]]; then
        if grep -q "^${var_name}=" "$env_file" 2>/dev/null; then
            sed -i '' "s|^${var_name}=.*|${var_name}=${token}|" "$env_file"
        else
            echo "${var_name}=${token}" >> "$env_file"
        fi
        print_ok "$label 已保存"
    else
        print_warn "未输入 $label"
    fi
}

# ============================== 安装验证 ====================================

verify_installation() {
    print_step "验证安装"

    local all_ok=true

    # Node.js
    if has_cmd node; then
        print_ok "Node.js: $(node -v)"
    else
        print_error "Node.js: 未找到"
        all_ok=false
    fi

    # OpenClaw
    if has_cmd openclaw; then
        print_ok "OpenClaw: $(openclaw --version 2>/dev/null || echo 'installed')"
    else
        print_warn "OpenClaw: 未在 PATH 中找到 (可能需要重启终端)"
        all_ok=false
    fi

    # 配置文件
    if [[ -f "$HOME/.openclaw/.env" ]]; then
        print_ok "配置文件: ~/.openclaw/.env"
    else
        print_warn "配置文件: 未创建"
    fi

    # 运行 doctor
    if has_cmd openclaw; then
        echo ""
        print_info "运行 'openclaw doctor' 进行系统诊断..."
        if openclaw doctor 2>/dev/null; then
            print_ok "系统诊断通过"
        else
            print_warn "诊断发现问题，请查看上方输出"
        fi
    fi

    if [[ "$all_ok" == "true" ]]; then
        echo ""
        print_ok "所有检查通过！"
    fi
}

# ============================== 安装摘要 ====================================

print_summary() {
    print_step "安装完成"

    echo ""
    echo -e "  ${GREEN}${BOLD}========================================${NC}"
    echo -e "  ${GREEN}${BOLD}  Mcaclaw — 安装摘要${NC}"
    echo -e "  ${GREEN}${BOLD}========================================${NC}"
    echo ""
    echo -e "  系统:     macOS $(sw_vers -productVersion) ($ARCH_TYPE)"
    echo -e "  Node.js:  $(node -v 2>/dev/null || echo 'N/A')"
    echo -e "  OpenClaw: $(openclaw --version 2>/dev/null || echo 'N/A')"
    echo -e "  配置:     ~/.openclaw/"
    echo ""
    echo -e "  ${BOLD}后续步骤:${NC}"
    echo ""
    echo -e "  1. ${CYAN}启动 Gateway 服务:${NC}"
    echo -e "     openclaw gateway start"
    echo ""
    echo -e "  2. ${CYAN}运行 onboard 引导:${NC}"
    echo -e "     openclaw onboard"
    echo ""
    echo -e "  3. ${CYAN}健康检查:${NC}"
    echo -e "     openclaw doctor"
    echo ""
    echo -e "  4. ${CYAN}查看文档:${NC}"
    echo -e "     https://docs.openclaw.ai"
    echo ""
    echo -e "  ${BOLD}常用命令:${NC}"
    echo -e "     openclaw --help          查看帮助"
    echo -e "     openclaw models list     列出可用模型"
    echo -e "     openclaw health          查看服务状态"
    echo -e "     openclaw update          更新版本"
    echo -e "     openclaw uninstall       卸载"
    echo ""
    echo -e "  ${DIM}配置文件: ~/.openclaw/.env${NC}"
    echo -e "  ${DIM}配置文档: ~/.openclaw/openclaw.json${NC}"
    echo ""
    echo -e "  ${GREEN}${BOLD}祝使用愉快！${NC}"
    echo ""
}

# ============================== 卸载引导 ====================================

uninstall_openclaw() {
    print_step "卸载 OpenClaw"

    echo -e "  ${RED}${BOLD}警告: 此操作将移除 OpenClaw 及其所有配置！${NC}"
    echo ""
    if ! confirm "确认卸载? 这将删除 ~/.openclaw/ 目录和 OpenClaw CLI" "N"; then
        print_info "已取消卸载。"
        exit 0
    fi

    # 使用内置卸载
    if has_cmd openclaw; then
        openclaw uninstall --all --yes --non-interactive 2>/dev/null || {
            # 手动卸载
            _manual_uninstall
        }
    else
        _manual_uninstall
    fi

    print_ok "OpenClaw 已完全卸载"
}

_manual_uninstall() {
    print_info "执行手动卸载..."

    # 停止 Gateway
    if has_cmd openclaw; then
        openclaw gateway stop 2>/dev/null || true
        openclaw gateway uninstall 2>/dev/null || true
    fi

    # 移除 launchd 服务
    launchctl bootout "gui/$UID/ai.openclaw.gateway" 2>/dev/null || true
    rm -f ~/Library/LaunchAgents/ai.openclaw.gateway.plist 2>/dev/null || true

    # 删除状态目录
    rm -rf "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"

    # 卸载 CLI
    npm rm -g openclaw 2>/dev/null || true
    pnpm remove -g openclaw 2>/dev/null || true

    # 移除 App
    rm -rf /Applications/OpenClaw.app 2>/dev/null || true
}

# ============================== 帮助信息 ====================================

print_help() {
    cat << 'HELP'
Mcaclaw — macOS OpenClaw (小龙虾) 一键安装引导

用法:
  bash install-mcaclaw.sh [选项]

选项:
  --skip       跳过确认，自动安装（使用默认选项）
  --uninstall  卸载 OpenClaw 及其所有配置
  --help       显示此帮助信息
  --version    显示版本号

步骤:
  1. 系统检测 (macOS + 芯片架构)
  2. 环境检查 (Xcode CLI + Node.js)
  3. 安装 OpenClaw
  4. 配置 AI 模型 (API Key)
  5. 配置消息通道 (Telegram/Discord/WhatsApp 等)
  6. 验证安装

示例:
  bash install-mcaclaw.sh              # 交互式安装
  bash install-mcaclaw.sh --skip       # 自动安装
  bash install-mcaclaw.sh --uninstall  # 卸载

更多信息:
  GitHub: https://github.com/openclaw/openclaw
  文档:   https://docs.openclaw.ai
HELP
}

# ============================== 主流程 ====================================

main() {
    # 解析参数
    local skip_confirm=0
    local do_uninstall=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip|-y|--yes)
                skip_confirm=1
                export AUTO_YES="1"
                ;;
            --uninstall)
                do_uninstall=1
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            --version|-v)
                echo "Mcaclaw v${SCRIPT_VERSION}"
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                print_help
                exit 1
                ;;
        esac
        shift
    done

    # 卸载模式
    if (( do_uninstall )); then
        uninstall_openclaw
        exit 0
    fi

    # 欢迎横幅
    print_banner

    echo -e "  此脚本将引导你完成 OpenClaw 的安装和配置。"
    echo ""

    if (( ! skip_confirm )); then
        if ! confirm "开始安装?"; then
            print_info "已取消。"
            exit 0
        fi
    fi

    # Step 1: 系统检查
    check_macos
    check_arch

    # Step 2: 环境检查
    check_xcode_cli
    check_nodejs

    # Step 3: 安装 OpenClaw
    install_openclaw

    # Step 4: 配置 AI 模型
    config_ai_model

    # Step 5: 配置消息通道
    config_channels

    # Step 6: 验证安装
    verify_installation

    # Step 7: 安装摘要
    print_summary
}

# 运行主流程
main "$@"
