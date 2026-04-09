#!/usr/bin/env bash
# install-skills.sh — OpenClaw / Claude Code 一键安装 SpideHarness Agent Skills
#
# 用法:
#   ./install-skills.sh              # 安装到 OpenClaw + Claude Code
#   ./install-skills.sh --openclaw   # 仅安装到 OpenClaw
#   ./install-skills.sh --claude     # 仅安装到 Claude Code
#   ./install-skills.sh --uninstall  # 卸载所有已安装的 Skills
#
# 安装位置:
#   OpenClaw:   ~/.openclaw/skills/spide-*/
#   Claude Code: <project>/.claude/skills/spide-*/

set -uo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
SKILL_NAMES=(spide-crawl spide-deep-crawl spide-analyze spide-export spide-wordcloud spide-batch spide-schedule)

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── OpenClaw 安装 ──────────────────────────────────────────────
install_openclaw() {
    local target_dir="$HOME/.openclaw/skills"
    info "安装 Skills 到 OpenClaw: $target_dir"

    mkdir -p "$target_dir"

    local count=0
    for skill in "${SKILL_NAMES[@]}"; do
        local src="$SKILLS_DIR/$skill"
        local dst="$target_dir/$skill"

        if [[ ! -d "$src" ]]; then
            warn "跳过 $skill（源目录不存在）"
            continue
        fi

        # 使用符号链接，方便更新
        if [[ -L "$dst" ]]; then
            rm "$dst"
        elif [[ -d "$dst" ]]; then
            rm -rf "$dst"
        fi

        ln -s "$src" "$dst"
        ok "$skill → $dst"
        ((count++))
    done

    echo ""
    ok "OpenClaw: 已安装 $count/${#SKILL_NAMES[@]} 个 Skills"
}

# ── Claude Code 安装 ───────────────────────────────────────────
install_claude() {
    # 查找项目根目录（包含 pyproject.toml 的目录）
    local project_root
    project_root="$(cd "$(dirname "$0")" && pwd)"
    local target_dir="$project_root/.claude/skills"

    info "安装 Skills 到 Claude Code: $target_dir"

    mkdir -p "$target_dir"

    local count=0
    for skill in "${SKILL_NAMES[@]}"; do
        local src="$SKILLS_DIR/$skill"
        local dst="$target_dir/$skill"

        if [[ ! -d "$src" ]]; then
            warn "跳过 $skill（源目录不存在）"
            continue
        fi

        if [[ -L "$dst" ]]; then
            rm "$dst"
        elif [[ -d "$dst" ]]; then
            rm -rf "$dst"
        fi

        # Claude Code 使用相对路径的符号链接
        ln -s "../../skills/$skill" "$dst"
        ok "$skill → $dst"
        ((count++))
    done

    # 确保 .claude/settings.json 存在并注册 skills
    local settings="$project_root/.claude/settings.json"
    if [[ ! -f "$settings" ]]; then
        echo '{}' > "$settings"
    fi

    echo ""
    ok "Claude Code: 已安装 $count/${#SKILL_NAMES[@]} 个 Skills"
    info "Skills 将在 Claude Code 中作为斜杠命令可用"
}

# ── 卸载 ──────────────────────────────────────────────────────
uninstall() {
    info "卸载所有 SpideHarness Agent Skills..."

    # OpenClaw
    local openclaw_dir="$HOME/.openclaw/skills"
    for skill in "${SKILL_NAMES[@]}"; do
        local dst="$openclaw_dir/$skill"
        if [[ -L "$dst" ]] || [[ -d "$dst" ]]; then
            rm -rf "$dst"
            ok "已移除 OpenClaw: $skill"
        fi
    done

    # Claude Code
    local project_root
    project_root="$(cd "$(dirname "$0")" && pwd)"
    local claude_dir="$project_root/.claude/skills"
    for skill in "${SKILL_NAMES[@]}"; do
        local dst="$claude_dir/$skill"
        if [[ -L "$dst" ]] || [[ -d "$dst" ]]; then
            rm -rf "$dst"
            ok "已移除 Claude Code: $skill"
        fi
    done

    echo ""
    ok "卸载完成"
}

# ── 验证 ──────────────────────────────────────────────────────
verify() {
    echo ""
    info "验证安装..."
    echo ""

    local all_ok=true

    # 检查源文件
    for skill in "${SKILL_NAMES[@]}"; do
        local skill_file="$SKILLS_DIR/$skill/SKILL.md"
        if [[ -f "$skill_file" ]]; then
            ok "源文件: $skill/SKILL.md"
        else
            error "缺失: $skill/SKILL.md"
            all_ok=false
        fi
    done

    echo ""

    # 检查 OpenClaw
    local openclaw_dir="$HOME/.openclaw/skills"
    for skill in "${SKILL_NAMES[@]}"; do
        local dst="$openclaw_dir/$skill"
        if [[ -f "$dst/SKILL.md" ]]; then
            ok "OpenClaw: $skill"
        else
            warn "OpenClaw: $skill 未安装"
        fi
    done

    echo ""

    # 检查 Claude Code
    local project_root
    project_root="$(cd "$(dirname "$0")" && pwd)"
    local claude_dir="$project_root/.claude/skills"
    for skill in "${SKILL_NAMES[@]}"; do
        local dst="$claude_dir/$skill"
        if [[ -f "$dst/SKILL.md" ]]; then
            ok "Claude Code: $skill"
        else
            warn "Claude Code: $skill 未安装"
        fi
    done

    echo ""
    if $all_ok; then
        ok "所有源文件验证通过"
    else
        error "部分源文件缺失，请检查 skills/ 目录"
    fi
}

# ── 帮助 ──────────────────────────────────────────────────────
usage() {
    cat << 'EOF'
SpideHarness Agent Skills 安装器

用法:
  ./install-skills.sh [选项]

选项:
  (无)          安装到 OpenClaw + Claude Code
  --openclaw    仅安装到 OpenClaw (~/.openclaw/skills/)
  --claude      仅安装到 Claude Code (<project>/.claude/skills/)
  --uninstall   卸载所有已安装的 Skills
  --verify      验证安装状态
  -h, --help    显示帮助信息

Skills 列表:
  spide-crawl       热搜采集
  spide-deep-crawl  深度采集
  spide-analyze     AI 分析
  spide-export      数据导出
  spide-wordcloud   词云生成
  spide-batch       批量并行采集
  spide-schedule    定时调度
EOF
}

# ── 主入口 ────────────────────────────────────────────────────
main() {
    echo ""
    echo "🦞 SpideHarness Agent Skills — 一键安装"
    echo "================================="
    echo ""

    # 检查 skills 源目录
    if [[ ! -d "$SKILLS_DIR" ]]; then
        error "skills/ 目录不存在: $SKILLS_DIR"
        exit 1
    fi

    local mode="${1:-all}"

    case "$mode" in
        --openclaw)
            install_openclaw
            verify
            ;;
        --claude)
            install_claude
            verify
            ;;
        --uninstall)
            uninstall
            ;;
        --verify)
            verify
            ;;
        -h|--help)
            usage
            ;;
        all|"")
            install_openclaw
            echo ""
            install_claude
            verify
            ;;
        *)
            error "未知选项: $mode"
            usage
            exit 1
            ;;
    esac

    echo ""
    ok "完成！使用 /spide-crawl 等斜杠命令调用 Skills"
}

main "$@"
