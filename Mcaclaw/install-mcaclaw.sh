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

# ============================== 国内镜像源 ===================================
# 默认使用国内镜像，GitHub 保持不变
readonly MIRROR_HOMEBREW="https://gitee.com/ineo6/homebrew-install/raw/master/install.sh"
readonly MIRROR_NVM="https://gitee.com/mirrors/nvm/raw/master/install.sh"
readonly MIRROR_NPM="https://registry.npmmirror.com"
readonly MIRROR_NPMJS="https://registry.npmjs.org"

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
    echo -e "  ${DIM}作者: 外星动物（常智） / IoTchange / 14455975@qq.com${NC}"
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

# 安全读取用户输入（防止 stdin 异常导致脚本退出）
safe_read() {
    local var_name="$1"
    local prompt="$2"
    if ! read -r -p "$(echo -e "$prompt")" "$var_name" 2>/dev/null; then
        # stdin 不可用（管道/非交互模式），使用默认值
        eval "$var_name=''"
        return 1
    fi
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
    local answer
    if ! safe_read answer "$prompt"; then
        answer="$default"
    fi
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
    local choice
    if ! safe_read choice "\n${CYAN}请选择 [1-${#options[@]}] (默认 1):${NC} "; then
        # stdin 不可用，使用默认值
        SELECTED_INDEX=0
        return 0
    fi
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
    local choices
    if ! safe_read choices "\n${CYAN}请选择:${NC} "; then
        MULTI_SELECTED=()
        return 0
    fi
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
        # 优先使用国内 gitee 镜像，失败回退官方源
        if curl -fsSL --connect-timeout 15 "$MIRROR_HOMEBREW" 2>/dev/null | /bin/bash; then
            : # 成功
        elif curl -fsSL --connect-timeout 15 "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh" 2>/dev/null | /bin/bash; then
            : # 官方源回退成功
        else
            print_error "Homebrew 安装失败，请手动安装: https://brew.sh"
            return 1
        fi

        # Apple Silicon 需要配置 PATH
        if [[ "$ARCH_TYPE" == "arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
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
        # 优先使用国内 gitee 镜像，失败回退官方源
        if curl -fsSL --connect-timeout 15 "$MIRROR_NVM" 2>/dev/null | bash; then
            : # 成功
        elif curl -fsSL --connect-timeout 15 "https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh" 2>/dev/null | bash; then
            : # 官方源回退成功
        else
            print_error "nvm 安装失败"
            return 1
        fi
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi

    # 设置 Node.js 二进制下载镜像（国内加速）
    export NVM_NODEJS_ORG_MIRROR="https://npmmirror.com/mirrors/node"
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

    # 设置 Node.js 二进制下载镜像（国内加速）
    export FNM_NODE_DIST_MIRROR="https://npmmirror.com/mirrors/node"
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
    # 修复 npm 缓存目录 + 全局模块目录权限（EACCES 常见问题）
    local npm_cache
    npm_cache="$(npm config get cache 2>/dev/null || echo "$HOME/.npm")"
    if [ ! -w "$npm_cache" ]; then
        print_warn "npm 缓存目录权限异常，自动修复..."
        sudo chown -R "$(id -u):$(id -g)" "$npm_cache"
        print_ok "npm 缓存权限已修复"
    fi

    # 修复全局 node_modules 目录权限（EACCES rename 错误根因）
    local npm_global
    npm_global="$(npm root -g 2>/dev/null || echo "/usr/local/lib/node_modules")"
    if [ -d "$npm_global" ] && [ ! -w "$npm_global" ]; then
        print_warn "npm 全局模块目录权限异常，自动修复..."
        sudo chown -R "$(id -u):$(id -g)" "$npm_global"
        # 同时修复 bin 目录
        local npm_bin
        npm_bin="$(npm bin -g 2>/dev/null || echo "/usr/local/bin")"
        if [ -d "$npm_bin" ] && [ ! -w "$npm_bin" ]; then
            sudo chown -R "$(id -u):$(id -g)" "$npm_bin"
        fi
        print_ok "npm 全局目录权限已修复"
    fi
}

install_openclaw() {
    print_step "安装 OpenClaw (小龙虾)"

    # 修复 npm 缓存权限（常见 EACCES 问题）
    fix_npm_permissions

    # 确保 npm 使用国内镜像
    local current_registry
    current_registry="$(npm config get registry 2>/dev/null || echo "")"
    if [[ "$current_registry" != "$MIRROR_NPM"* ]]; then
        print_info "切换 npm 到淘宝镜像..."
        npm config set registry "$MIRROR_NPM"
    fi

    # 默认使用 npm 全局安装（最简单可靠，不会接管 stdin）
    print_info "通过 npm 全局安装 OpenClaw (淘宝镜像)... "
    if npm install -g openclaw 2>&1; then
        : # 成功
    else
        # npm 全局安装失败时回退到 sudo
        print_warn "普通权限安装失败，使用 sudo 重试..."
        if ! sudo npm install -g openclaw 2>&1; then
            print_error "sudo npm install 也失败了，请手动执行: sudo npm install -g openclaw"
            return 1
        fi
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

    local env_file="$HOME/.openclaw/.env"
    mkdir -p "$HOME/.openclaw"
    touch "$env_file"

    echo ""
    echo -e "  ${BOLD}选择 AI 算力方案:${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Ollama 本地模型     ${DIM}(推荐，支持 Intel/Apple Silicon)${NC}"
    echo -e "  ${GREEN}2)${NC} MLX 本地模型         ${DIM}(Apple Silicon 专属，极限性能)${NC}"
    echo -e "  ${GREEN}3)${NC} 云端 API 模型        ${DIM}(OpenAI/Claude/Gemini/智谱等)${NC}"
    echo -e "  ${GREEN}4)${NC} 跳过，稍后配置"
    echo ""

    local model_choice
    safe_read model_choice "  ${CYAN}请选择 [1-4]:${NC} " || model_choice="1"

    case "$model_choice" in
        1) _config_ollama "$env_file" ;;
        2) _config_mlx "$env_file" ;;
        3) _config_cloud_model "$env_file" ;;
        *) print_info "已跳过 AI 模型配置" ;;
    esac

    print_ok "AI 模型配置完成"
}

_config_cloud_model() {
    local env_file="$1"

    local models=(
        "OpenAI (GPT-4o / o3) — 需要 OPENAI_API_KEY"
        "Anthropic (Claude Opus/Sonnet) — 需要 ANTHROPIC_API_KEY"
        "Google (Gemini 2.5 Pro) — 需要 GEMINI_API_KEY"
        "OpenRouter (多模型聚合) — 需要 OPENROUTER_API_KEY"
        "智谱 AI (GLM-5.1) — 需要 ZAI_API_KEY"
        "Moonshot (Kimi K2.5) — 需要 MOONSHOT_API_KEY"
        "Deepseek — 需要 DEEPSEEK_API_KEY"
        "返回，保持 Ollama"
    )

    select_option "选择云端 AI 模型提供商:" "${models[@]}"

    case "$SELECTED_INDEX" in
        0) _config_api_key "OPENAI_API_KEY" "OpenAI" "$env_file" ;;
        1) _config_api_key "ANTHROPIC_API_KEY" "Anthropic" "$env_file" ;;
        2) _config_api_key "GEMINI_API_KEY" "Google Gemini" "$env_file" ;;
        3) _config_api_key "OPENROUTER_API_KEY" "OpenRouter" "$env_file" ;;
        4) _config_api_key "ZAI_API_KEY" "智谱 AI" "$env_file" ;;
        5) _config_api_key "MOONSHOT_API_KEY" "Moonshot" "$env_file" ;;
        6) _config_api_key "DEEPSEEK_API_KEY" "Deepseek" "$env_file" ;;
        7) print_info "保持 Ollama 本地模型" ;;
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
    local api_key
    if ! safe_read api_key "  ${CYAN}请输入 ${var_name} (回车跳过):${NC} "; then
        print_warn "无法读取输入，跳过。稍后编辑 $env_file"
        return 0
    fi

    if [[ -n "$api_key" ]]; then
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

    print_info "Ollama — 本地大模型运行引擎，无需 API Key"

    # 1. 检查/安装 Ollama
    if has_cmd ollama; then
        local ollama_ver
        ollama_ver="$(ollama --version 2>/dev/null | head -1 || echo 'unknown')"
        print_ok "Ollama 已安装: $ollama_ver"
    else
        print_info "Ollama 未安装，开始安装..."
        if has_cmd brew; then
            brew install ollama
        else
            # 无 brew 时用官方脚本
            curl -fsSL https://ollama.com/install.sh | sh
        fi

        if has_cmd ollama; then
            print_ok "Ollama 安装成功"
        else
            print_error "Ollama 安装失败，请手动安装: https://ollama.com"
            return 1
        fi
    fi

    # 2. 启动 Ollama 服务
    print_info "检查 Ollama 服务状态..."
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_ok "Ollama 服务已运行"
    else
        print_info "启动 Ollama 服务..."
        ollama serve &>/dev/null &
        # 等待服务就绪
        local retry=0
        while (( retry < 10 )); do
            if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                print_ok "Ollama 服务已启动"
                break
            fi
            sleep 1
            ((retry++))
        done
        if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            print_warn "Ollama 服务启动超时，可稍后手动运行: ollama serve"
        fi
    fi

    # 3. 检查已安装的模型
    print_info "检查已安装的本地模型..."
    local installed_models
    installed_models="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v '^$' || true)"

    if [[ -n "$installed_models" ]]; then
        echo ""
        print_ok "已安装的模型:"
        echo "$installed_models" | while read -r m; do
            echo -e "    ${GREEN}*${NC} $m"
        done
    else
        print_info "尚未安装任何模型"
    fi

    # 4. 推荐拉取模型
    echo ""
    echo -e "  ${BOLD}推荐模型:${NC}"
    echo -e "    ${GREEN}g)${NC} gemma4:e4b          ${DIM}(Google Gemma 4, 4B, 多模态, 推荐)${NC}"
    echo -e "    ${GREEN}q)${NC} qwen3:8b            ${DIM}(通义千问 3, 8B, 通用对话)${NC}"
    echo -e "    ${GREEN}l)${NC} llama3.1:8b          ${DIM}(Meta Llama 3.1, 8B, 英文优秀)${NC}"
    echo -e "    ${GREEN}d)${NC} deepseek-r1:7b       ${DIM}(DeepSeek R1, 7B, 推理强)${NC}"
    echo -e "    ${GREEN}s)${NC} 跳过，稍后手动拉取"
    echo ""

    local pull_choice
    safe_read pull_choice "  ${CYAN}选择要拉取的模型 [g/q/l/d/s]:${NC} " || pull_choice="s"

    local model_name=""
    case "$pull_choice" in
        g|G) model_name="gemma4:e4b" ;;
        q|Q) model_name="qwen3:8b" ;;
        l|L) model_name="llama3.1:8b" ;;
        d|D) model_name="deepseek-r1:7b" ;;
        *) ;;
    esac

    if [[ -n "$model_name" ]]; then
        print_info "拉取并运行模型 $model_name (首次下载约 2-6GB，请耐心等待)..."
        print_info "ollama run 会自动下载模型并进入交互"
        echo ""
        if ollama run "$model_name"; then
            print_ok "模型 $model_name 就绪"
        else
            print_warn "模型拉取失败，可稍后手动运行: ollama run $model_name"
        fi
    fi

    # 5. 写入配置
    if ! grep -q "^OLLAMA_BASE_URL=" "$env_file" 2>/dev/null; then
        echo "OLLAMA_BASE_URL=http://localhost:11434" >> "$env_file"
    fi
}

# Apple Silicon MLX 本地推理 (视觉+语言多模态)
_config_mlx() {
    local env_file="$1"

    # 检查是否为 Apple Silicon
    if [[ "$ARCH_TYPE" != "arm64" ]]; then
        print_error "MLX 仅支持 Apple Silicon (M1/M2/M3/M4)，当前架构: $ARCH_TYPE"
        print_info "建议选择 Ollama 方案"
        return 1
    fi

    print_info "MLX-VLM — Apple Silicon 极限性能多模态推理 (视觉+语言)"
    echo ""
    echo -e "  ${DIM}mlx-vlm 是 Apple M 系列芯片优化的多模态视觉语言模型框架，${NC}"
    echo -e "  ${DIM}支持图像理解、视觉问答、图文生成等任务。${NC}"
    echo ""

    # 检查 Python
    if ! has_cmd python3; then
        print_error "需要 Python 3，请先通过 Homebrew 安装: brew install python3"
        return 1
    fi

    local python_ver
    python_ver="$(python3 --version 2>/dev/null || echo 'unknown')"
    print_ok "Python: $python_ver"

    # 检查 pip
    if ! python3 -m pip --version >/dev/null 2>&1; then
        print_info "安装 pip..."
        python3 -m ensurepip --upgrade 2>/dev/null || true
    fi

    # 检查/安装 mlx-vlm
    if python3 -c "import mlx_vlm" 2>/dev/null; then
        local mlx_ver
        mlx_ver="$(python3 -c 'import mlx_vlm; print(mlx_vlm.__version__)' 2>/dev/null || echo 'installed')"
        print_ok "mlx-vlm 已安装: $mlx_ver"
    else
        print_info "安装 mlx-vlm (Apple Silicon 多模态视觉推理引擎)..."
        pip3 install -U mlx-vlm 2>&1 || {
            print_error "mlx-vlm 安装失败，请手动安装: pip3 install -U mlx-vlm"
            return 1
        }
        print_ok "mlx-vlm 安装成功"
    fi

    # 检查/安装 git + git-lfs (模型下载需要)
    if ! has_cmd git; then
        print_info "安装 git..."
        if has_cmd brew; then
            brew install git
        else
            print_error "需要 git，请先安装 Xcode CLI: xcode-select --install"
            return 1
        fi
    fi

    if ! git lfs version >/dev/null 2>&1; then
        print_info "安装 git-lfs (大文件下载支持)..."
        if has_cmd brew; then
            brew install git-lfs
        else
            print_error "git-lfs 安装失败，请手动安装: brew install git-lfs"
            return 1
        fi
    fi
    git lfs install 2>/dev/null || true
    print_ok "git + git-lfs 就绪"

    # 推荐模型
    echo ""
    echo -e "  ${BOLD}MLX-VLM 推荐模型 (ModelScope 国内源):${NC}"
    echo -e "    ${GREEN}g)${NC} gemma-4-e4b-it-4bit  ${DIM}(Google Gemma 4, 4B, 多模态, 推荐)${NC}"
    echo -e "    ${GREEN}q)${NC} Qwen3-8B-6bit         ${DIM}(通义千问 3, 8B)${NC}"
    echo -e "    ${GREEN}l)${NC} Llama-3.1-8B-4bit     ${DIM}(Meta Llama 3.1, 8B)${NC}"
    echo -e "    ${GREEN}s)${NC} 跳过，稍后手动下载"
    echo ""

    local mlx_choice
    safe_read mlx_choice "  ${CYAN}选择模型 [g/q/l/s]:${NC} " || mlx_choice="s"

    # ModelScope 下载地址映射
    local mlx_model=""
    local mlx_local_path="$HOME/.openclaw/models"
    local modelscope_url=""
    case "$mlx_choice" in
        g|G)
            mlx_model="mlx-community/gemma-4-e4b-it-4bit"
            modelscope_url="https://www.modelscope.cn/mlx-community/gemma-4-e4b-it-4bit.git"
            ;;
        q|Q)
            mlx_model="mlx-community/Qwen3-8B-6bit"
            modelscope_url="https://www.modelscope.cn/mlx-community/Qwen3-8B-6bit.git"
            ;;
        l|L)
            mlx_model="mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
            modelscope_url="https://www.modelscope.cn/mlx-community/Meta-Llama-3.1-8B-Instruct-4bit.git"
            ;;
        *) ;;
    esac

    if [[ -n "$mlx_model" ]]; then
        mkdir -p "$mlx_local_path"
        local model_dir="$mlx_local_path/$(basename "$mlx_model")"

        if [[ -d "$model_dir" ]]; then
            print_ok "模型已存在: $model_dir"
        else
            print_info "从 ModelScope 下载模型 $mlx_model..."
            print_info "下载地址: $modelscope_url"
            print_info "模型较大 (2-6GB)，请耐心等待..."
            echo ""
            if git clone "$modelscope_url" "$model_dir"; then
                print_ok "模型下载完成: $model_dir"
            else
                print_warn "模型下载失败，可稍后手动下载:"
                echo -e "    ${CYAN}git lfs install${NC}"
                echo -e "    ${CYAN}git clone $modelscope_url $model_dir${NC}"
            fi
        fi

        # 写入本地模型路径
        echo ""
        echo -e "  ${BOLD}测试命令:${NC}"
        echo -e "    ${CYAN}python3 -m mlx_vlm.generate \\${NC}"
        echo -e "      ${CYAN}--model $model_dir \\${NC}"
        echo -e "      ${CYAN}--max-tokens 100 --temperature 0.0 \\${NC}"
        echo -e "      ${CYAN}--prompt \"Describe this image.\" --image <图片路径>${NC}"
    fi

    # 写入 MLX 配置
    if ! grep -q "^MLX_MODEL=" "$env_file" 2>/dev/null; then
        echo "MLX_MODEL=${mlx_model:-mlx-community/gemma-4-e4b-it-4bit}" >> "$env_file"
    fi
    if ! grep -q "^MLX_MODEL_PATH=" "$env_file" 2>/dev/null && [[ -n "$mlx_model" ]]; then
        echo "MLX_MODEL_PATH=$mlx_local_path/$(basename "$mlx_model")" >> "$env_file"
    fi
    if ! grep -q "^LOCAL_AI_ENGINE=" "$env_file" 2>/dev/null; then
        echo "LOCAL_AI_ENGINE=mlx-vlm" >> "$env_file"
    fi

    print_ok "MLX-VLM 配置完成"
}

# 本地 AI 算力状态检查
check_local_ai() {
    print_step "本地 AI 算力检查"
    echo ""

    local found_any=false

    # ---- Ollama ----
    echo -e "  ${BOLD}[Ollama]${NC}"
    if has_cmd ollama; then
        local ollama_ver
        ollama_ver="$(ollama --version 2>/dev/null | head -1 || echo 'unknown')"
        print_ok "已安装: $ollama_ver"

        # 服务状态
        if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
            print_ok "服务运行中 (localhost:11434)"

            # 列出已安装模型
            local models
            models="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v '^$' || true)"
            if [[ -n "$models" ]]; then
                local model_count
                model_count="$(echo "$models" | wc -l | tr -d ' ')"
                print_ok "已加载模型 ($model_count 个):"
                echo "$models" | while read -r m; do
                    echo -e "      ${GREEN}*${NC} $m"
                done
            else
                print_warn "无已安装模型，运行: ollama pull qwen3:8b"
            fi
        else
            print_warn "服务未运行，启动命令: ollama serve"
        fi
        found_any=true
    else
        print_warn "未安装 — 安装命令: brew install ollama"
    fi

    echo ""

    # ---- MLX-VLM (Apple Silicon only) ----
    echo -e "  ${BOLD}[MLX-VLM]${NC}  ${DIM}(Apple Silicon 专属, 多模态)${NC}"
    if [[ "$ARCH_TYPE" != "arm64" ]]; then
        print_warn "当前为 Intel 架构，MLX 不可用"
    elif has_cmd python3 && python3 -c "import mlx_vlm" 2>/dev/null; then
        local mlx_ver
        mlx_ver="$(python3 -c 'import mlx_vlm; print(mlx_vlm.__version__)' 2>/dev/null || echo 'installed')"
        print_ok "mlx-vlm 已安装: $mlx_ver"

        # 检查已下载模型
        local model_dir="$HOME/.openclaw/models"
        if [[ -d "$model_dir" ]]; then
            local downloaded
            downloaded="$(find "$model_dir" -maxdepth 1 -mindepth 1 -type d 2>/dev/null || true)"
            if [[ -n "$downloaded" ]]; then
                local dl_count
                dl_count="$(echo "$downloaded" | wc -l | tr -d ' ')"
                print_ok "已下载模型 ($dl_count 个):"
                echo "$downloaded" | while read -r d; do
                    echo -e "      ${GREEN}*${NC} $(basename "$d")"
                done
            else
                print_warn "无已下载模型"
            fi
        fi
        found_any=true
    else
        print_warn "未安装 — 安装命令: pip3 install -U mlx-vlm"
    fi

    echo ""

    # ---- 汇总 ----
    if [[ "$found_any" == "true" ]]; then
        print_ok "本地算力就绪"
    else
        print_warn "未检测到本地 AI 引擎"
        echo ""
        echo -e "  ${BOLD}安装建议:${NC}"
        echo -e "    Ollama (通用): ${CYAN}brew install ollama${NC}"
        if [[ "$ARCH_TYPE" == "arm64" ]]; then
            echo -e "    MLX-VLM (M芯片): ${CYAN}pip3 install -U mlx-vlm${NC}"
            echo -e "    然后下载模型:     ${CYAN}git lfs install && git clone https://www.modelscope.cn/mlx-community/gemma-4-e4b-it-4bit.git${NC}"
        fi
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

# ============================== 开机自启动 (launchd) =========================

setup_launchd() {
    local plist_name="ai.openclaw.gateway"
    local plist_path="$HOME/Library/LaunchAgents/${plist_name}.plist"
    local openclaw_bin
    openclaw_bin="$(command -v openclaw 2>/dev/null || echo '/usr/local/bin/openclaw')"

    if [[ -f "$plist_path" ]]; then
        print_info "开机自启动已配置，跳过"
        return 0
    fi

    mkdir -p "$HOME/Library/LaunchAgents"

    cat > "$plist_path" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${plist_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${openclaw_bin}</string>
        <string>gateway</string>
        <string>start</string>
        <string>--foreground</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.openclaw/logs/gateway.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.openclaw/logs/gateway.stderr.log</string>
    <key>WorkingDirectory</key>
    <string>$HOME/.openclaw</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/.nvm/versions/node/$(node -v 2>/dev/null || echo 'v22')/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
</dict>
</plist>
PLIST

    # 创建日志目录
    mkdir -p "$HOME/.openclaw/logs"

    # 加载服务
    launchctl bootout "gui/$UID/${plist_name}" 2>/dev/null || true
    launchctl bootstrap "gui/$UID" "$plist_path" 2>/dev/null || true

    print_ok "已配置开机自启动 (launchd)"
    print_info "管理命令:"
    print_info "  launchctl bootout   gui/$UID/${plist_name}   # 停止自启动"
    print_info "  launchctl bootstrap gui/$UID ${plist_path}  # 重新启用"
}

remove_launchd() {
    local plist_name="ai.openclaw.gateway"
    local plist_path="$HOME/Library/LaunchAgents/${plist_name}.plist"

    launchctl bootout "gui/$UID/${plist_name}" 2>/dev/null || true
    if [[ -f "$plist_path" ]]; then
        rm -f "$plist_path"
        print_ok "已移除开机自启动"
    fi
}

# ============================== 网络连通测试 ================================

# 检测并提示代理配置
detect_proxy() {
    # 检查常见代理环境变量
    local proxy_vars=("https_proxy" "HTTPS_PROXY" "http_proxy" "HTTP_PROXY" "all_proxy" "ALL_PROXY")
    for var in "${proxy_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            print_ok "检测到代理: ${var}=${!var}"
            return 0
        fi
    done
    return 1
}

# 尝试设置镜像加速（中国大陆用户）
suggest_mirrors() {
    echo ""
    echo -e "  ${YELLOW}${BOLD}网络访问受限，可尝试以下方案:${NC}"
    echo ""
    echo -e "  ${BOLD}方案 1: 配置代理${NC}"
    echo -e "    export https_proxy=http://127.0.0.1:7890"
    echo -e "    export http_proxy=http://127.0.0.1:7890"
    echo ""
    echo -e "  ${BOLD}方案 2: npm 淘宝镜像 (推荐)${NC}"
    echo -e "    npm config set registry $MIRROR_NPM"
    echo ""
    echo -e "  ${BOLD}方案 3: 设置 DNS (114.114.114.114 或 8.8.8.8)${NC}"
    echo -e "    网络设置 → DNS → 添加 114.114.114.114"
    echo ""
}

# 安全 curl：带重试和代理提示
safe_curl() {
    local url="$1"
    local max_retries="${2:-2}"

    for attempt in $(seq 1 $((max_retries + 1))); do
        if curl -fsSL --connect-timeout 15 --retry 1 --retry-delay 3 -o /dev/null "$url" 2>/dev/null; then
            return 0
        fi
        if (( attempt <= max_retries )); then
            print_warn "第 ${attempt} 次尝试失败，重试..."
            sleep 2
        fi
    done
    return 1
}

check_network() {
    print_step "Step 1/7: 测试网络连通性"

    local fail_count=0

    # 检测代理
    if detect_proxy; then
        print_info "将使用已有代理配置"
    fi

    # 测试 GitHub（保留，不修改）
    print_info "测试 GitHub 连通性..."
    if safe_curl "https://github.com" 1; then
        print_ok "GitHub 访问正常"
    else
        print_warn "GitHub 访问失败"
        ((fail_count++))
    fi

    # 测试 Homebrew/nvm 下载源（优先国内镜像）
    print_info "测试 Homebrew/nvm 下载源..."
    if safe_curl "$MIRROR_HOMEBREW" 1; then
        print_ok "国内镜像源 (gitee) 访问正常"
    else
        print_warn "国内镜像源访问失败"
        ((fail_count++))
    fi

    # 测试 npm registry（优先淘宝镜像）
    print_info "测试 npm 淘宝镜像连通性..."
    if safe_curl "$MIRROR_NPM" 1; then
        print_ok "npm 淘宝镜像访问正常"
        # 自动设置淘宝镜像
        npm config set registry "$MIRROR_NPM" 2>/dev/null || true
    else
        print_warn "npm 淘宝镜像访问失败，尝试官方源..."
        if safe_curl "$MIRROR_NPMJS" 1; then
            print_ok "npm 官方源访问正常"
        else
            print_warn "npm 所有源访问失败"
            ((fail_count++))
        fi
    fi

    # 测试 OpenClaw 官网（可选，不影响安装）
    print_info "测试 OpenClaw 官网连通性..."
    if safe_curl "https://openclaw.ai" 0; then
        print_ok "OpenClaw 官网访问正常"
    else
        print_warn "OpenClaw 官网访问失败（不影响安装）"
    fi

    # 结果汇总
    if (( fail_count == 0 )); then
        print_ok "网络连通性检查全部通过"
    else
        echo ""
        if (( fail_count >= 2 )); then
            suggest_mirrors
        fi
        if ! confirm "有 ${fail_count} 项网络检测失败，是否继续安装?"; then
            print_info "建议配置代理或镜像后重新运行脚本。"
            return 1
        fi
    fi
    return 0
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
    echo -e "  4. ${CYAN}配置开机自启动:${NC}"
    echo -e "     在安装后菜单中选择，或手动配置 launchd"
    echo ""
    echo -e "  5. ${CYAN}查看文档:${NC}"
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

    # 停止 Gateway + 移除 launchd 自启动
    remove_launchd 2>/dev/null || true
    if has_cmd openclaw; then
        openclaw gateway stop 2>/dev/null || true
        openclaw gateway uninstall 2>/dev/null || true
    fi

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

# 当前步骤编号
CURRENT_STEP=1
TOTAL_STEPS=7

# 步骤完成标记（bash 3.x 兼容，用普通变量）
STEP_DONE_1=0
STEP_DONE_2=0
STEP_DONE_3=0
STEP_DONE_4=0
STEP_DONE_5=0
STEP_DONE_6=0
STEP_DONE_7=0

# 获取步骤完成状态
_step_done() { eval "echo \${STEP_DONE_${1}:-0}"; }
_step_set()  { eval "STEP_DONE_${1}=1"; }

show_step_menu() {
    local step="$1"
    echo ""
    echo -e "  ${BOLD}${CYAN}─────────────────────────────────${NC}"
    echo -e "  ${BOLD}步骤 ${step}/${TOTAL_STEPS}${NC}  |  ${DIM}m=菜单  p=上一步  n=下一步  q=退出${NC}"
    echo -e "  ${BOLD}${CYAN}─────────────────────────────────${NC}"
}

ask_step_action() {
    local default_action="${1:-n}"  # n=next, p=prev, m=menu
    local action
    if [[ "${AUTO_YES:-}" == "1" ]]; then
        return 0
    fi
    safe_read action "\n  ${CYAN}操作 [n/p/m/q] (默认 n):${NC} " || action="$default_action"
    action="${action:-$default_action}"
    case "$action" in
        p|P|prev|back|b|B)
            return 2  # 上一步
            ;;
        m|M|menu)
            return 3  # 主菜单
            ;;
        q|Q|quit|exit)
            echo ""
            print_info "用户退出安装。可随时重新运行脚本继续。"
            exit 0
            ;;
        *)
            return 0  # 下一步
            ;;
    esac
}

run_step() {
    local step_num="$1"
    local step_func="$2"
    local step_name="$3"

    CURRENT_STEP="$step_num"

    # 检查是否已完成
    if [[ "$(_step_done "$step_num")" == "1" ]]; then
        print_ok "步骤 ${step_num}: ${step_name} (已完成)"
        return 0
    fi

    print_step "Step ${step_num}/${TOTAL_STEPS}: ${step_name}"

    # 执行步骤函数
    "$step_func"
    local rc=$?

    if (( rc == 0 )); then
        _step_set "$step_num"
    fi
    return $rc
}

show_main_menu() {
    echo ""
    echo -e "  ${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "  ${BOLD}${GREEN}║        Mcaclaw 安装主菜单                ║${NC}"
    echo -e "  ${BOLD}${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}1)${NC} 网络连通性测试     ${_done_1:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}2)${NC} 系统检测           ${_done_2:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}3)${NC} 环境检查 (Node.js) ${_done_3:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}4)${NC} 安装 OpenClaw      ${_done_4:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}5)${NC} 配置 AI 模型       ${_done_5:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}6)${NC} 配置消息通道       ${_done_6:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}7)${NC} 验证安装           ${_done_7:-${DIM}待执行${NC}}   ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${CYAN}工具与诊断:${NC}                            ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}l)${NC} 本地算力检查 (Ollama/MLX)         ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}g)${NC} 启动 Gateway 服务                 ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}o)${NC} 运行 onboard 引导                 ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}d)${NC} 健康检查 (doctor)                  ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}s)${NC} 配置开机自启动                     ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}a)${NC} 全部顺序执行                      ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}║${NC} ${GREEN}q)${NC} 退出                              ${BOLD}${GREEN}║${NC}"
    echo -e "  ${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
}

# Step 2 的组合函数
step_check_system() {
    check_macos
    check_arch
}

# Step 3 的组合函数
step_check_env() {
    check_xcode_cli
    check_nodejs
}

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

        # 交互模式：使用步骤导航
        interactive_install
    else
        # 自动模式：顺序执行全部步骤
        auto_install
    fi
}

interactive_install() {
    while true; do
        # 更新菜单中的完成状态
        local i
        for i in $(seq 1 $TOTAL_STEPS); do
            if _step_done "$i"; then
                eval "_done_${i}='${GREEN}✓ 已完成${NC}'"
            fi
        done

        show_main_menu

        local choice
        safe_read choice "\n  ${CYAN}请选择 [1-7/l/g/o/d/s/a/q]:${NC} " || choice="q"

        case "$choice" in
            1) run_step 1 check_network   "网络连通性测试" ;;
            2) run_step 2 step_check_system "系统检测" ;;
            3) run_step 3 step_check_env  "环境检查" ;;
            4) run_step 4 install_openclaw "安装 OpenClaw" ;;
            5) run_step 5 config_ai_model  "配置 AI 模型" ;;
            6) run_step 6 config_channels  "配置消息通道" ;;
            7)
                run_step 7 verify_installation "验证安装"
                if _step_done 7; then
                    print_summary
                fi
                ;;
            l|L)
                check_local_ai
                ;;
            g|G)
                if has_cmd openclaw; then
                    print_info "启动 Gateway 服务..."
                    openclaw gateway start 2>&1 || print_warn "Gateway 启动失败，可稍后手动运行: openclaw gateway start"
                else
                    print_error "openclaw 命令未找到，请先完成步骤 4"
                fi
                ;;
            o|O)
                if has_cmd openclaw; then
                    print_info "启动 onboard 引导..."
                    openclaw onboard || print_warn "onboard 已退出"
                else
                    print_error "openclaw 命令未找到，请先完成步骤 4"
                fi
                ;;
            d|D)
                if has_cmd openclaw; then
                    print_info "运行系统诊断..."
                    openclaw doctor || print_warn "诊断发现问题，请查看上方输出"
                else
                    print_error "openclaw 命令未找到，请先完成步骤 4"
                fi
                ;;
            s|S)
                if has_cmd openclaw; then
                    setup_launchd
                else
                    print_error "openclaw 命令未找到，请先完成步骤 4"
                fi
                ;;
            a|A|all)
                auto_install
                ;;
            q|Q|quit|exit)
                print_info "用户退出。可随时重新运行脚本继续。"
                exit 0
                ;;
            *)
                print_warn "无效选择"
                ;;
        esac
    done
}

auto_install() {
    print_info "自动模式：顺序执行全部步骤..."

    # Step 1: 网络测试
    run_step 1 check_network "网络连通性测试"
    if (( CURRENT_STEP == 1 )); then
        ask_step_action "n"
        case $? in
            2) return ;;
            3) return ;;
        esac
    fi

    # Step 2: 系统检测
    run_step 2 step_check_system "系统检测"

    # Step 3: 环境检查
    run_step 3 step_check_env "环境检查"

    # Step 4: 安装 OpenClaw
    run_step 4 install_openclaw "安装 OpenClaw"

    # Step 5: 配置 AI 模型
    run_step 5 config_ai_model "配置 AI 模型"

    # Step 6: 配置消息通道
    run_step 6 config_channels "配置消息通道"

    # Step 7: 验证安装
    run_step 7 verify_installation "验证安装"

    # 安装摘要 + 返回主菜单
    print_summary
    print_info "自动安装完成，返回主菜单..."
}

# 运行主流程
main "$@"
