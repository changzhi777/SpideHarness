"""飞书事件回调处理 — 接收飞书 Bot 消息，解析为 Spide 命令并执行.

支持的指令格式（纯文本消息）:
    crawl <source>       — 采集指定平台热搜（如: crawl weibo），"crawl all" 采集全部
    analyze <source>     — AI 分析指定平台
    status               — 查看系统状态（话题数/平台数/最近采集时间）
    track <source> [N]   — 深度追踪 Top N 话题
    export <source>      — 导出数据
    help                 — 显示帮助信息

飞书事件订阅配置:
    请求地址: https://<host>/api/feishu/event
    事件: im.message.receive_v1
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

import logging

logger = logging.getLogger("spide.feishu")

router = APIRouter(prefix="/api/feishu", tags=["feishu"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 飞书事件验证 ──────────────────────────────────────────────────

# 从环境变量或配置读取，飞书开放平台获取
_FEISHU_APP_ID = ""
_FEISHU_APP_SECRET = ""
_FEISHU_VERIFICATION_TOKEN = ""
_FEISHU_ENCRYPT_KEY = ""


def set_feishu_config(
    app_id: str = "",
    app_secret: str = "",
    verification_token: str = "",
    encrypt_key: str = "",
) -> None:
    global _FEISHU_APP_ID, _FEISHU_APP_SECRET, _FEISHU_VERIFICATION_TOKEN, _FEISHU_ENCRYPT_KEY
    # 解析 ${ENV_VAR[:default]} 占位符(支持从环境变量注入密钥)
    from .secrets import resolve_secrets

    _FEISHU_APP_ID = resolve_secrets(app_id)
    _FEISHU_APP_SECRET = resolve_secrets(app_secret)
    _FEISHU_VERIFICATION_TOKEN = resolve_secrets(verification_token)
    _FEISHU_ENCRYPT_KEY = resolve_secrets(encrypt_key)


# ── 指令解析 ──────────────────────────────────────────────────────

_COMMAND_RE = re.compile(
    r"^(crawl|analyze|status|track|export|help|batch)\s*(.*)",
    re.IGNORECASE,
)


def parse_command(text: str) -> tuple[str, dict[str, Any]] | None:
    """从消息文本解析指令和参数."""
    text = text.strip()
    if not text:
        return None

    m = _COMMAND_RE.match(text)
    if not m:
        return None

    cmd = m.group(1).lower()
    raw_args = m.group(2).strip()

    if cmd == "help":
        return ("help", {})

    if cmd == "status":
        return ("status", {})

    if cmd == "crawl":
        source = raw_args if raw_args else "all"
        return ("crawl", {"source": source})

    if cmd == "analyze":
        source = raw_args if raw_args else "weibo"
        return ("analyze", {"source": source})

    if cmd == "track":
        parts = raw_args.split()
        source = parts[0] if parts else "weibo"
        top_n = int(parts[1]) if len(parts) > 1 else 10
        return ("track", {"source": source, "top_n": top_n})

    if cmd == "export":
        source = raw_args if raw_args else "weibo"
        return ("export", {"source": source})

    if cmd == "batch":
        platforms = [p.strip() for p in raw_args.split(",")] if raw_args else ["xhs", "dy"]
        return ("batch", {"platforms": platforms})

    return None


# ── 指令执行 ──────────────────────────────────────────────────────

def _run_spide_sync(args: list[str], timeout: int = 120) -> dict[str, Any]:
    """同步执行 spide CLI 命令."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "spide"] + args,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"命令执行超时 (>{timeout}s)"}
    except Exception as exc:
        return {"status": "error", "message": f"执行异常: {exc}"}

    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

    if result.returncode != 0:
        return {
            "status": "error",
            "message": (stderr + stdout)[-500:] or f"exit_code={result.returncode}",
        }

    return {"status": "ok", "output": stdout[-1500:]}


async def execute_command(cmd: str, args: dict[str, Any]) -> dict[str, Any]:
    """解析并执行指令，返回结果."""
    loop = asyncio.get_event_loop()

    if cmd == "help":
        return {
            "status": "ok",
            "message": (
                "SpideHarness 可用指令:\n"
                "• crawl <source|all> — 采集热搜\n"
                "• analyze <source> — AI 分析\n"
                "• track <source> [N] — 深度追踪 Top N\n"
                "• export <source> — 导出数据\n"
                "• batch <p1,p2> — 批量采集\n"
                "• status — 系统状态\n"
                "• help — 显示帮助"
            ),
        }

    if cmd == "status":
        return await loop.run_in_executor(None, _get_status)

    if cmd == "crawl":
        source = args.get("source", "all")
        cli_args = ["crawl"]
        if source == "all":
            cli_args.extend(["--all", "--save"])
        else:
            cli_args.extend(["-s", source, "--save"])
        return await loop.run_in_executor(None, _run_spide_sync, cli_args, 120)

    if cmd == "analyze":
        source = args.get("source", "weibo")
        return await loop.run_in_executor(
            None, _run_spide_sync, ["analyze", "-s", source], 180
        )

    if cmd == "track":
        source = args.get("source", "weibo")
        top_n = args.get("top_n", 10)
        return await loop.run_in_executor(
            None, _run_spide_sync, ["track", "-s", source, "--top", str(top_n)], 180
        )

    if cmd == "export":
        source = args.get("source", "weibo")
        return await loop.run_in_executor(
            None, _run_spide_sync, ["export", "-s", source, "-f", "excel"], 60
        )

    if cmd == "batch":
        platforms = args.get("platforms", ["xhs", "dy"])
        return await loop.run_in_executor(
            None,
            _run_spide_sync,
            ["batch-crawl", "-p", ",".join(platforms)],
            300,
        )

    return {"status": "error", "message": f"未知指令: {cmd}"}


def _get_status() -> dict[str, Any]:
    """获取系统状态."""
    import sqlite3

    db_path = PROJECT_ROOT / "spide_data.db"
    if not db_path.exists():
        return {"status": "ok", "message": "数据库未创建，请先执行 crawl"}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) AS cnt FROM hot_topics").fetchone()["cnt"]
        sources = conn.execute(
            "SELECT source, COUNT(*) AS cnt FROM hot_topics GROUP BY source ORDER BY cnt DESC"
        ).fetchall()
        latest = conn.execute("SELECT MAX(fetched_at) AS t FROM hot_topics").fetchone()["t"]
    finally:
        conn.close()

    platform_lines = "\n".join(f"  • {s['source']}: {s['cnt']} 条" for s in sources)
    return {
        "status": "ok",
        "message": (
            f"系统运行中\n"
            f"总话题数: {total}\n"
            f"各平台:\n{platform_lines}\n"
            f"最近采集: {latest or '从未采集'}"
        ),
    }


# ── API 端点 ──────────────────────────────────────────────────────


@router.post("/event", summary="飞书事件回调")
async def feishu_event(request: Request) -> JSONResponse:
    """处理飞书开放平台事件回调.

    支持:
    - URL 验证 (challenge)
    - 消息接收 (im.message.receive_v1)
    """
    body = await request.json()

    # 1. URL 验证（飞书配置事件订阅时发送）
    if body.get("type") == "url_verification":
        challenge = body.get("challenge", "")
        token = body.get("token", "")
        if _FEISHU_VERIFICATION_TOKEN and token != _FEISHU_VERIFICATION_TOKEN:
            return JSONResponse(status_code=403, content={"error": "invalid token"})
        logger.info("feishu_url_verification_ok")
        return JSONResponse(content={"challenge": challenge})

    # 2. 事件回调（需要验证签名）
    schema = body.get("schema", "")
    header = body.get("header", {})
    event_type = header.get("event_type", "")

    # 3. 处理消息事件
    if event_type == "im.message.receive_v1" or "im.message.receive" in schema:
        event = body.get("event", {}) or body.get("payload", {}).get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})

        msg_type = message.get("message_type", "")
        content_str = message.get("content", "{}")

        # 解析消息文本
        text = _extract_text(content_str, msg_type)
        if not text:
            return JSONResponse(content={"status": "ignored", "reason": "empty text"})

        logger.info(
            "feishu_message_received",
            sender=sender.get("sender_id", {}).get("open_id", "unknown"),
            text=text[:100],
        )

        # 解析指令
        parsed = parse_command(text)
        if not parsed:
            # 非指令消息 → 路由到 Agent（自然语言对话）
            from .feishu_agent import get_feishu_agent
            from .feishu_card import agent_response_card

            agent = get_feishu_agent()
            try:
                await agent.init()
            except Exception as exc:
                logger.warning("agent_init_failed", error=str(exc))

            sender_open_id = sender.get("sender_id", {}).get("open_id", "unknown")
            chat_id = message.get("chat_id", "")
            try:
                agent_result = await agent.chat(
                    user_message=text, user_id=sender_open_id, chat_id=chat_id
                )
                card = agent_response_card(
                    answer=agent_result.answer,
                    tool_calls=agent_result.tool_calls,
                    iterations=agent_result.iterations,
                )
                return JSONResponse(content=card)
            except Exception as exc:
                logger.error("agent_chat_failed", error=str(exc))
                return JSONResponse(
                    content={
                        "status": "error",
                        "message": f"Agent 处理失败: {exc}",
                        "hint": "可尝试指令: 'crawl weibo' / 'analyze weibo' / 'status'",
                    }
                )

        cmd, args = parsed
        result = await execute_command(cmd, args)

        return JSONResponse(content=result)

    return JSONResponse(content={"status": "ignored", "event_type": event_type})


@router.post("/command", summary="通用命令执行接口（供飞书 Agent 或其他客户端调用）")
async def feishu_command(body: dict[str, Any] = Body(...)) -> JSONResponse:
    """直接执行命令，无需飞书事件格式.

    请求体:
        {"command": "crawl", "args": {"source": "weibo"}}
        {"command": "status"}
        {"text": "crawl weibo"}  — 自动解析
    """
    # 支持两种格式：直接指定 command，或传入 text 自动解析
    if "text" in body:
        parsed = parse_command(body["text"])
        if not parsed:
            return JSONResponse(
                content={"status": "error", "message": "无法解析指令，发送 'help' 查看帮助"}
            )
        cmd, args = parsed
    elif "command" in body:
        cmd = body["command"]
        args = body.get("args", {})
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "需要 'text' 或 'command' 字段"},
        )

    result = await execute_command(cmd, args)
    return JSONResponse(content=result)


def _extract_text(content_str: str, msg_type: str) -> str:
    """从飞书消息 content 中提取纯文本."""
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except json.JSONDecodeError:
        return content_str

    if msg_type == "text":
        return content.get("text", "").strip()

    if msg_type == "post":
        # 富文本消息
        title = content.get("title", "")
        lines = []
        for lang_content in content.values():
            if isinstance(lang_content, list):
                for line_blocks in lang_content:
                    if isinstance(line_blocks, list):
                        line_text = "".join(
                            block.get("text", "") for block in line_blocks if isinstance(block, dict)
                        )
                        if line_text:
                            lines.append(line_text)
        return (title + " " + " ".join(lines)).strip()

    # 其他类型尝试提取 text
    return content.get("text", "").strip()
