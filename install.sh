#!/usr/bin/env bash
# install.sh — Spide Agent 一键安装脚本 (Linux/macOS)
#
# 用法:
#   ./install.sh                              # 默认安装到当前目录
#   ./install.sh --dir /opt/spide-agent       # 指定安装目录
#   ./install.sh --skip-skills                # 跳过 AI Skills 安装
#   ./install.sh --verify                     # 仅验证安装状态

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 颜色输出 ──────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

step()  { echo -e "\n${BLUE}${BOLD}[STEP $1]${NC} ${BOLD}$2${NC}"; }
info()  { echo -e "  ${BLUE}•${NC} $*"; }
ok()    { echo -e "  ${GREEN}✔${NC} $*"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $*"; }
error() { echo -e "  ${RED}✘${NC} $*"; }

# ── 默认参数 ──────────────────────────────────────────────────
SKIP_SKILLS="false"
VERIFY_ONLY="false"
INSTALL_DIR="$SCRIPT_DIR"

# ── 解析参数 ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --skip-skills)
            SKIP_SKILLS="true"
            shift
            ;;
        --verify)
            VERIFY_ONLY="true"
            shift
            ;;
        -h|--help)
            echo "Spide Agent 安装脚本"
            echo ""
            echo "用法: ./install.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --dir PATH        指定安装目录（默认: 当前目录）"
            echo "  --skip-skills     跳过 AI Skills 安装"
            echo "  --verify          仅验证安装状态"
            echo "  -h, --help        显示帮助"
            exit 0
            ;;
        *)
            error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ── 版本提取 ──────────────────────────────────────────────────
VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' spide/__init__.py 2>/dev/null || echo "unknown")

# ── Banner ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  Spide Agent ${VERSION} 安装程序${NC}"
echo -e "${BOLD}============================================${NC}"

# ── 验证模式 ──────────────────────────────────────────────────
if [[ "$VERIFY_ONLY" == "true" ]]; then
    echo ""
    info "验证安装状态..."
    echo ""

    ERRORS=0

    # Python
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 --version 2>&1)
        ok "Python: $PY_VER"
    elif command -v python &>/dev/null; then
        PY_VER=$(python --version 2>&1)
        ok "Python: $PY_VER"
    else
        error "Python: 未安装"
        ERRORS=$((ERRORS + 1))
    fi

    # uv
    if command -v uv &>/dev/null; then
        UV_VER=$(uv --version 2>&1)
        ok "uv: $UV_VER"
    else
        error "uv: 未安装"
        ERRORS=$((ERRORS + 1))
    fi

    # spide CLI
    if [[ -f ".venv/bin/spide" ]] || command -v spide &>/dev/null; then
        ok "spide CLI: 可用"
    else
        warn "spide CLI: 未找到（可能需要先运行安装）"
    fi

    # 配置文件
    for cfg in configs/llm.yaml configs/uapi.yaml; do
        if [[ -f "$cfg" ]]; then
            ok "配置: $cfg"
        else
            warn "配置: $cfg 不存在（需要填写 API Key）"
        fi
    done

    # Skills
    if [[ -d ".claude/skills" ]]; then
        SKILL_COUNT=$(ls .claude/skills/ 2>/dev/null | wc -l | tr -d ' ')
        ok "Skills: ${SKILL_COUNT} 个已安装"
    else
        warn "Skills: 未安装"
    fi

    echo ""
    if [[ $ERRORS -eq 0 ]]; then
        ok "验证通过"
    else
        error "发现 $ERRORS 个问题"
        exit 1
    fi
    exit 0
fi

# ── Step 1: 环境检查 ──────────────────────────────────────────
step 1 "环境检查"

# Python 3.12+
PY_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [[ "$PY_MAJOR" -gt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -ge 12 ]]; }; then
            PY_CMD="$cmd"
            ok "Python: $($cmd --version 2>&1)"
            break
        fi
    fi
done

if [[ -z "$PY_CMD" ]]; then
    error "需要 Python 3.12+"
    info "安装指南: https://www.python.org/downloads/"
    exit 1
fi

# uv
if command -v uv &>/dev/null; then
    ok "uv: $(uv --version 2>&1)"
else
    error "uv 未安装"
    info "安装指南: https://docs.astral.sh/uv/getting-started/installation/"
    echo ""
    info "快速安装:"
    info "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# ── Step 2: 安装依赖 ──────────────────────────────────────────
step 2 "安装 Python 依赖 (uv sync)"

cd "$INSTALL_DIR"

if [[ -d ".venv" ]]; then
    warn "检测到已有 .venv/，将重新同步依赖"
fi

uv sync 2>&1 | while IFS= read -r line; do
    echo "  $line"
done

if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
    error "uv sync 失败"
    info "请检查网络连接和 pyproject.toml 依赖配置"
    exit 1
fi

ok "依赖安装完成"

# ── Step 3: 生成配置模板 ──────────────────────────────────────
step 3 "生成配置模板"

mkdir -p configs

# llm.yaml
if [[ -f "configs/llm.yaml" ]]; then
    warn "configs/llm.yaml 已存在，跳过"
else
    cat > configs/llm.yaml << 'YAML'
# Spide Agent LLM 配置
# 请填写智谱 AI API Key（https://open.bigmodel.cn）
common:
  provider: "zhipuai"
  api_key: "YOUR_ZHIPUAI_API_KEY"    # <-- 替换为你的 API Key
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  sdk: "zai"

text:
  model: "glm-5.1"
  max_tokens: 4096
  temperature: 0.7
  thinking_type: "enabled"
  stream: true

vision:
  model: "glm-5v-turbo"
  max_tokens: 4096
  temperature: 0.7

web_search:
  engine: "search_pro"
  default_count: 15
  content_size: "high"
  recency_filter: "noLimit"
YAML
    ok "已生成 configs/llm.yaml（请填写 API Key）"
fi

# mqtt.yaml
if [[ -f "configs/mqtt.yaml" ]]; then
    warn "configs/mqtt.yaml 已存在，跳过"
else
    cat > configs/mqtt.yaml << 'YAML'
# Spide Agent MQTT 配置
# 如果不使用 MQTT 功能，可以保持默认值
host: "YOUR_MQTT_HOST"       # <-- 替换为 MQTT 服务器地址（可选）
port: 8883
username: ""
password: ""
use_tls: true
reconnect:
  max_retries: 5
  backoff_base: 1.0
  backoff_max: 30.0
YAML
    ok "已生成 configs/mqtt.yaml（MQTT 为可选功能）"
fi

# uapi.yaml
if [[ -f "configs/uapi.yaml" ]]; then
    warn "configs/uapi.yaml 已存在，跳过"
else
    cat > configs/uapi.yaml << 'YAML'
# Spide Agent UAPI 数据源配置
# 请填写 UAPI API Key（https://uapis.cn）
api_key: "YOUR_UAPI_API_KEY"  # <-- 替换为你的 API Key

hot_sources:
  - name: "weibo"
    alias: "微博热搜"
    refresh_interval: 300
  - name: "baidu"
    alias: "百度热搜"
    refresh_interval: 300
  - name: "douyin"
    alias: "抖音热点"
    refresh_interval: 180
  - name: "zhihu"
    alias: "知乎热榜"
    refresh_interval: 300
  - name: "bilibili"
    alias: "B站热搜"
    refresh_interval: 300

rate_limit:
  max_concurrent: 5
  requests_per_minute: 30

retry:
  max_retries: 3
  backoff_base: 1.0
  backoff_max: 30.0
YAML
    ok "已生成 configs/uapi.yaml（请填写 API Key）"
fi

# ── Step 4: 初始化工作空间 ─────────────────────────────────────
step 4 "初始化 Spide 工作空间"

uv run spide init 2>&1 | while IFS= read -r line; do
    echo "  $line"
done

if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
    ok "工作空间初始化完成"
else
    warn "工作空间初始化失败（可能需要手动运行 spide init）"
fi

# ── Step 5: 安装 AI Skills ─────────────────────────────────────
step 5 "安装 AI Agent Skills"

if [[ "$SKIP_SKILLS" == "true" ]]; then
    warn "已跳过 Skills 安装（--skip-skills）"
elif [[ -f "install-skills.sh" ]]; then
    bash install-skills.sh --claude 2>&1 | while IFS= read -r line; do
        echo "  $line"
    done
    ok "Skills 安装完成"
else
    warn "install-skills.sh 不存在，跳过 Skills 安装"
fi

# ── Step 6: MediaCrawler 检查 ──────────────────────────────────
step 6 "检查深度采集组件"

if [[ -d "MediaCrawler" ]]; then
    ok "MediaCrawler 已就绪（支持 7 平台深度采集）"
else
    warn "MediaCrawler 不存在（深度采集功能不可用）"
    info "深度采集为可选功能，基本的热搜采集不受影响"
    info "如需深度采集，请单独下载 MediaCrawler 到本项目根目录"
fi

# ── Step 7: 环境健康检查 ───────────────────────────────────────
step 7 "环境健康检查"

uv run spide doctor 2>&1 | while IFS= read -r line; do
    echo "  $line"
done

ok "健康检查完成"

# ── Step 8: 安装摘要 ──────────────────────────────────────────
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  安装完成!${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo -e "  安装目录: ${BOLD}$INSTALL_DIR${NC}"
echo -e "  版本:     ${BOLD}$VERSION${NC}"
echo ""
echo -e "${BOLD}  下一步:${NC}"
echo ""
echo "  1. 编辑配置文件，填写 API Key:"
echo "     ${BOLD}configs/llm.yaml${NC}   — 智谱 AI API Key"
echo "     ${BOLD}configs/uapi.yaml${NC}  — UAPI 数据源 Key"
echo ""
echo "  2. 验证环境:"
echo "     ${BOLD}uv run spide doctor${NC}"
echo ""
echo "  3. 开始使用:"
echo "     ${BOLD}uv run spide crawl -s weibo${NC}     # 采集微博热搜"
echo "     ${BOLD}uv run spide crawl --all${NC}         # 采集所有热搜源"
echo "     ${BOLD}uv run spide analyze -s baidu${NC}    # 分析百度热搜"
echo ""
echo -e "  文档: ${BOLD}README.md${NC} | ${BOLD}docs/skills-guide.md${NC}"
echo ""
