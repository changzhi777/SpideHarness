#!/usr/bin/env bash
# pack.sh — 将 Spide Agent 打包为发布压缩包
#
# 用法:
#   scripts/pack.sh                           # 默认：不含 MediaCrawler
#   scripts/pack.sh --with-media-crawler      # 包含 MediaCrawler（约 54MB）
#   scripts/pack.sh --output-dir /tmp/dist    # 自定义输出目录
#
# 输出:
#   dist/spide-agent-{version}.tar.gz         # 发布压缩包
#   dist/spide-agent-{version}.tar.gz.sha256  # 校验和

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ── 颜色输出 ──────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── 默认参数 ──────────────────────────────────────────────────
OUTPUT_DIR="$PROJECT_ROOT/dist"
INCLUDE_MC="false"
CUSTOM_VERSION=""

# ── 解析参数 ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-media-crawler)
            INCLUDE_MC="true"
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --version)
            CUSTOM_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            head -10 "$0" | tail -8
            exit 0
            ;;
        *)
            error "未知选项: $1"
            exit 1
            ;;
    esac
done

# ── 版本提取 ──────────────────────────────────────────────────
if [[ -n "$CUSTOM_VERSION" ]]; then
    VERSION="$CUSTOM_VERSION"
else
    VERSION=$(grep -oP '__version__\s*=\s*"\K[^"]+' spide/__init__.py 2>/dev/null || true)
    if [[ -z "$VERSION" ]]; then
        error "无法从 spide/__init__.py 提取版本号"
        exit 1
    fi
fi

ARCHIVE_NAME="spide-agent-${VERSION}"
ARCHIVE_FILE="${ARCHIVE_NAME}.tar.gz"
SUFFIX=""
if [[ "$INCLUDE_MC" == "true" ]]; then
    SUFFIX="-full"
    ARCHIVE_FILE="${ARCHIVE_NAME}-full.tar.gz"
fi

# ── 前置检查 ──────────────────────────────────────────────────
if [[ ! -f "spide/__init__.py" ]]; then
    error "请在项目根目录运行此脚本"
    exit 1
fi

if [[ ! -f "install.sh" ]]; then
    error "install.sh 不存在，请先创建安装脚本"
    exit 1
fi

if [[ ! -f "install.ps1" ]]; then
    error "install.ps1 不存在，请先创建安装脚本"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# ── 构建排除列表 ──────────────────────────────────────────────
EXCLUDES=(
    --exclude='.git'
    --exclude='.venv'
    --exclude='venv'
    --exclude='env'
    --exclude='__pycache__'
    --exclude='.mypy_cache'
    --exclude='.pytest_cache'
    --exclude='.ruff_cache'
    --exclude='.claude'
    --exclude='.zcf'
    --exclude='.spec-workflow'
    --exclude='.DS_Store'
    --exclude='Thumbs.db'
    --exclude='OpenHarness'
    --exclude='dist'
    --exclude='build'
    --exclude='*.egg-info'
    --exclude='*.log'
    --exclude='configs/llm.yaml'
    --exclude='configs/mqtt.yaml'
    --exclude='configs/uapi.yaml'
    --exclude='CA'
    --exclude='CLAUDE.md'
    --exclude='.gitignore'
    --exclude='scripts'
)

if [[ "$INCLUDE_MC" != "true" ]]; then
    EXCLUDES+=(--exclude='MediaCrawler')
fi

# ── 打包 ──────────────────────────────────────────────────────
echo ""
echo "Spide Agent — 发布打包"
echo "========================"
echo ""
info "版本: $VERSION"
info "输出: $OUTPUT_DIR/$ARCHIVE_FILE"
info "MediaCrawler: $(if [[ "$INCLUDE_MC" == "true" ]]; then echo "包含"; else echo "不包含"; fi)"
echo ""

# 包含的文件列表
INCLUDE_FILES=(
    install.sh
    install.ps1
    spide/
    tests/
    skills/
    configs/
    docs/
    pyproject.toml
    uv.lock
    README.md
    install-skills.sh
)

info "正在打包..."

tar czf "$OUTPUT_DIR/$ARCHIVE_FILE" \
    --transform "s,^,$ARCHIVE_NAME/," \
    "${EXCLUDES[@]}" \
    "${INCLUDE_FILES[@]}"

if [[ $? -ne 0 ]]; then
    error "打包失败"
    exit 1
fi

ok "压缩包已生成: $OUTPUT_DIR/$ARCHIVE_FILE"

# ── 校验和 ────────────────────────────────────────────────────
info "生成校验和..."

# 兼容 macOS (shasum) 和 Linux (sha256sum)
if command -v sha256sum &>/dev/null; then
    sha256sum "$OUTPUT_DIR/$ARCHIVE_FILE" > "$OUTPUT_DIR/$ARCHIVE_FILE.sha256"
elif command -v shasum &>/dev/null; then
    shasum -a 256 "$OUTPUT_DIR/$ARCHIVE_FILE" > "$OUTPUT_DIR/$ARCHIVE_FILE.sha256"
else
    warn "未找到 sha256sum/shasum，跳过校验和生成"
fi

# ── 文件大小 ──────────────────────────────────────────────────
FILE_SIZE=$(du -h "$OUTPUT_DIR/$ARCHIVE_FILE" | cut -f1 | tr -d ' ')

echo ""
echo "========================"
ok "打包完成!"
echo ""
echo "  文件: $OUTPUT_DIR/$ARCHIVE_FILE"
echo "  大小: $FILE_SIZE"
echo "  校验: $OUTPUT_DIR/$ARCHIVE_FILE.sha256"
echo ""
echo "  安装方式:"
echo "    tar xzf $ARCHIVE_FILE"
echo "    cd $ARCHIVE_NAME"
echo "    ./install.sh          # Linux/macOS"
echo "    .\\install.ps1         # Windows"
echo ""
