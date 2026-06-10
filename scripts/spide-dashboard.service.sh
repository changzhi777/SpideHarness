#!/bin/bash
# SpideHarness Dashboard 启动脚本（CT107 部署）
# 用法：
#   ./spide-dashboard.service.sh start    # 后台启动
#   ./spide-dashboard.service.sh stop     # 停止
#   ./spide-dashboard.service.sh status   # 查看状态
#   ./spide-dashboard.service.sh restart  # 重启
#   ./spide-dashboard.service.sh logs     # 实时日志
#
# 环境变量从 /root/.spide/env.sh 加载（包含 SPIDE_FEISHU__APP_SECRET / SPIDE_LLM__LOCAL_API_KEY）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/opt/Spide_agent"
PID_FILE="/var/run/spide/dashboard.pid"
LOG_FILE="/var/log/spide/dashboard.log"
PORT="${SPIDE_DASHBOARD_PORT:-8765}"
HOST="${SPIDE_DASHBOARD_HOST:-0.0.0.0}"

# 加载环境变量
if [ -f "/root/.spide/env.sh" ]; then
    # shellcheck disable=SC1091
    source /root/.spide/env.sh
fi

# 验证关键依赖
check_requirements() {
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        echo "[ERROR] $PROJECT_ROOT/.venv 不存在，请先 uv sync"
        exit 1
    fi
    if [ -z "${SPIDE_FEISHU__APP_SECRET:-}" ]; then
        echo "[WARN] SPIDE_FEISHU__APP_SECRET 未设置，主动推送将禁用"
    fi
    if [ -z "${SPIDE_LLM__LOCAL_API_KEY:-}" ]; then
        echo "[WARN] SPIDE_LLM__LOCAL_API_KEY 未设置，LLM 走降级模式"
    fi
}

ensure_dirs() {
    mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"
}

is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start() {
    check_requirements
    ensure_dirs
    if is_running; then
        echo "[INFO] Dashboard 已在运行 (PID $(cat "$PID_FILE"))"
        return 0
    fi
    echo "[INFO] 启动 Dashboard @ $HOST:$PORT ..."
    cd "$PROJECT_ROOT"
    nohup .venv/bin/uvicorn dashboard.api:app \
        --host "$HOST" --port "$PORT" \
        --no-access-log \
        --log-level info \
        > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    if is_running; then
        echo "[OK] Dashboard 已启动 (PID $(cat "$PID_FILE"))"
        echo "     日志: $LOG_FILE"
        echo "     端点: http://$HOST:$PORT/api/dashboard"
    else
        echo "[ERROR] 启动失败，查看日志：tail -f $LOG_FILE"
        return 1
    fi
}

stop() {
    if ! is_running; then
        echo "[INFO] Dashboard 未运行"
        rm -f "$PID_FILE"
        return 0
    fi
    local pid
    pid=$(cat "$PID_FILE")
    echo "[INFO] 停止 Dashboard (PID $pid) ..."
    kill -TERM "$pid" 2>/dev/null || true
    for _ in {1..10}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    kill -KILL "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "[OK] Dashboard 已停止"
}

status() {
    if is_running; then
        echo "[OK] Dashboard 运行中 (PID $(cat "$PID_FILE"))"
        echo "     端点: http://$HOST:$PORT/"
        return 0
    else
        echo "[INFO] Dashboard 未运行"
        return 1
    fi
}

case "${1:-status}" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status) status ;;
    logs) tail -f "$LOG_FILE" ;;
    *) echo "Usage: $0 {start|stop|restart|status|logs}"; exit 1 ;;
esac
