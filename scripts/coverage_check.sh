#!/usr/bin/env bash
# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
#
# 本地覆盖率检查脚本 — 模拟 CI 行为
#
# 用法:
#   ./scripts/coverage_check.sh           # 全量测试 + 覆盖率
#   ./scripts/coverage_check.sh --unit    # 仅单元测试
#
# 退出码:
#   0 = 覆盖率达标（默认 50%）
#   1 = 覆盖率不达标
#   非 pytest 错误 = 透传

set -euo pipefail

cd "$(dirname "$0")/.."

TARGET="50"
PYTEST_TARGETS=()

# 解析参数：仅 --unit 改变测试范围（其他透传给 pytest）
while [[ $# -gt 0 ]]; do
    case "$1" in
        --unit)
            PYTEST_TARGETS=("tests/unit/")
            shift
            ;;
        *)
            break
            ;;
    esac
done

echo "=== 覆盖率检查（目标 ${TARGET}%）==="
echo ""

uv run pytest "${PYTEST_TARGETS[@]}" \
    --cov=spide \
    --cov=dashboard \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-fail-under="${TARGET}" \
    --tb=short \
    "$@"

echo ""
echo "✅ 覆盖率检查通过"
