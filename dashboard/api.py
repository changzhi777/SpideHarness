"""
Dashboard Backend API - FastAPI 服务

从 SQLite 数据库读取热搜数据，提供给前端 Dashboard。
同时托管静态前端文件。

启动方式: uvicorn dashboard.api:app --reload --port 8765
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, JSONResponse

from dashboard.capability_registry import registry
from dashboard.feishu_handler import router as feishu_router
from dashboard.github_trending import GitHubTrendingService
from spide.logging import get_logger
from spide.mcp.tools import ALL_TOOLS as _MCP_TOOLS

logger = get_logger(__name__)

# Skills 自动扫描
_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# ── 常量 ──────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "spide_data.db"
STATIC_DIR = Path(__file__).resolve().parent

PLATFORM_MAP: dict[str, dict[str, str]] = {
    "weibo": {"label": "微博", "color": "#E6162D"},
    "baidu": {"label": "百度", "color": "#4E6EF2"},
    "douyin": {"label": "抖音", "color": "#FE2C55"},
    "zhihu": {"label": "知乎", "color": "#0066FF"},
    "bilibili": {"label": "B站", "color": "#00A1D6"},
    "kuaishou": {"label": "快手", "color": "#FF8C00"},
    "tieba": {"label": "贴吧", "color": "#4879BD"},
}

# ── 数据库工具 ────────────────────────────────────────────────────
Row = dict[str, Any]


@contextmanager
def _get_db():
    """获取 SQLite 连接（同步，适合小数据量场景）。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _query(sql: str, params: tuple = ()) -> list[Row]:
    with _get_db() as conn:
        cur = conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


# ── API 路由 ──────────────────────────────────────────────────────
app = FastAPI(title="SpideHarness Dashboard API", version="3.1.1")
app.include_router(feishu_router)


# ── 能力注册（MCP / HTTP / Skills） ────────────────────────────────

# MCP 工具（8 个）— 仅声明非默认值（auth/category）
_MCP_META = {
    "crawl_hot_topics": {"auth": "uapi_key", "category": "data_collection"},
    "web_search": {"auth": "llm_key", "category": "search"},
    "web_search_enhanced": {"category": "search"},
    "fetch_web_page": {"category": "web_fetch"},
    "fetch_repo_info": {"category": "web_fetch"},
    "manage_memory": {"category": "agent"},
    "health_check": {"category": "agent"},
    "deep_crawl_hot_topics": {"category": "data_collection"},
}
for _tool in _MCP_TOOLS:
    _meta = _MCP_META.get(_tool["name"], {})
    registry.register_mcp_tool(
        name=_tool["name"],
        description=_tool["description"],
        input_schema=_tool["inputSchema"],
        **_meta,
    )

# HTTP 端点（data-driven 列表）— (path, method, summary, kwargs)
_HTTP_ENDPOINTS = [
    (
        "/.well-known/agent.json", "GET",
        "AI Agent 自发现端点 — 返回所有 MCP / HTTP / Skills 能力清单",
        {"category": "discovery"},
    ),
    (
        "/api/dashboard", "GET", "获取 Dashboard 全量数据",
        {
            "response_schema": {"type": "object", "properties": {
                "total_count": {"type": "integer"},
                "platform_stats": {"type": "array"},
                "top_topics": {"type": "array"},
            }},
            "category": "dashboard",
        },
    ),
    (
        "/api/topics", "GET", "获取话题列表（支持分页/筛选）",
        {
            "response_schema": {"type": "object", "properties": {
                "total": {"type": "integer"},
                "items": {"type": "array"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            }},
            "category": "dashboard",
        },
    ),
    ("/api/sources", "GET", "获取所有数据源平台", {"category": "dashboard"}),
    (
        "/api/crawl", "POST", "触发全量热搜采集（同步执行 spide crawl --all --save，超时 120s）",
        {
            "response_schema": {"type": "object", "properties": {
                "status": {"type": "string"},
                "saved": {"type": "integer"},
                "output": {"type": "string"},
            }},
            "category": "data_collection",
        },
    ),
    (
        "/api/github/trending", "GET", "采集 GitHub AI/LLM/Agent/MCP/MLX 热门仓库",
        {"category": "data_collection"},
    ),
    (
        "/api/github/push", "POST", "采集 GitHub 热点并推送到飞书 Webhook",
        {"category": "integration"},
    ),
    (
        "/api/github/webhook", "POST", "动态设置飞书 Webhook URL",
        {
            "request_schema": {"type": "object", "required": ["url"], "properties": {
                "url": {"type": "string"},
            }},
            "category": "integration",
        },
    ),
    (
        "/api/feishu/event", "POST", "飞书事件回调（URL 验证 + 消息接收）",
        {"auth": "feishu_signature", "category": "integration"},
    ),
    (
        "/api/feishu/command", "POST", "通用命令执行接口（供飞书 Agent 或其他客户端调用）",
        {"category": "integration"},
    ),
]
for _path, _method, _summary, _kwargs in _HTTP_ENDPOINTS:
    registry.register_http_endpoint(_path, _method, _summary, **_kwargs)

# Skills（自动扫描 skills/ 目录）— category 从 SKILL.md frontmatter 读取
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
if _SKILLS_DIR.is_dir():
    for _skill_dir in sorted(_SKILLS_DIR.iterdir()):
        _skill_md = _skill_dir / "SKILL.md"
        if not _skill_md.is_file():
            continue
        try:
            _content = _skill_md.read_text(encoding="utf-8")
            _m = _FRONTMATTER_RE.match(_content)
            if not _m:
                continue
            _fm = _m.group(1)
            # 解析 frontmatter 字段
            _meta: dict[str, str] = {}
            for _line in _fm.splitlines():
                if ":" in _line and not _line.startswith((" ", "\t", "-")):
                    _k, _v = _line.split(":", 1)
                    _meta[_k.strip()] = _v.strip().strip(">")
            _name = _meta.get("name", "")
            if not _name:
                continue
            _desc = _meta.get("description", "")
            # 取首段非空 markdown 文本作为描述（若 frontmatter 无 description）
            if not _desc:
                for _line in _content[_m.end():].splitlines():
                    _line = _line.strip()
                    if _line and not _line.startswith("#"):
                        _desc = _line[:200]
                        break
            registry.register_skill(
                name=_name,
                description=_desc or f"Skill: {_name}",
                path=f"skills/{_skill_dir.name}/SKILL.md",
                category=_meta.get("category", "general"),
            )
        except Exception as exc:
            logger.debug("skill_scan_failed", skill_dir=_skill_dir.name, error=str(exc))
            continue


@app.get("/.well-known/agent.json", include_in_schema=False)
def agent_discovery() -> JSONResponse:
    """AI Agent 自发现端点 — 单一端点返回所有能力.

    符合 OpenAPI Discovery 风格扩展，AI Agent 可一次性发现：
    - MCP 工具清单（8 个，含完整 JSON Schema）
    - HTTP 端点清单（Dashboard / GitHub / 飞书）
    - Skills 清单（自动扫描 skills/ 目录）
    - 文档索引（INTEGRATION.md / mcp-api-reference.md 等）

    示例:
        curl http://localhost:8765/.well-known/agent.json
    """
    return JSONResponse(content=registry.to_agent_json())


@app.get("/api/dashboard", summary="获取 Dashboard 全量数据")
def get_dashboard() -> JSONResponse:
    """
    返回前端 Dashboard 所需的全部数据，结构与 window.__DASHBOARD_DATA__ 一致。

    包含：
    - total_count: 总话题数
    - platform_stats: 各平台话题统计
    - top_topics: Top 20 热搜排行
    - category_stats: 分类统计
    - platform_ranks: 各平台 Top 5
    - latest_fetch: 最近采集时间
    - stats_summary: 统计摘要
    """
    # 1. 总数
    total_row = _query("SELECT COUNT(*) AS cnt FROM hot_topics")
    total_count = total_row[0]["cnt"] if total_row else 0

    # 2. 各平台统计
    platform_stats = _query(
        "SELECT source, COUNT(*) AS count FROM hot_topics GROUP BY source ORDER BY count DESC"
    )
    for p in platform_stats:
        pm = PLATFORM_MAP.get(p["source"], {"label": p["source"], "color": "#40BE7A"})
        p["label"] = pm["label"]
        p["color"] = pm["color"]

    # 3. 全平台 Top 20（按热度降序）
    top_topics = _query(
        """
        SELECT rank, title, source, hot_value, url, fetched_at
        FROM hot_topics
        WHERE rank IS NOT NULL
        ORDER BY hot_value DESC
        LIMIT 20
        """
    )
    for t in top_topics:
        pm = PLATFORM_MAP.get(t["source"], {"label": t["source"], "color": "#40BE7A"})
        t["source_label"] = pm["label"]

    # 4. 分类统计
    category_stats = _query(
        "SELECT category, COUNT(*) AS count FROM hot_topics WHERE category IS NOT NULL AND category != '' GROUP BY category ORDER BY count DESC"
    )

    # 5. 各平台 Top 5
    platform_ranks: dict[str, list[Row]] = {}
    for ps in platform_stats:
        source = ps["source"]
        items = _query(
            """
            SELECT rank, title, url, hot_value
            FROM hot_topics
            WHERE source = ?
            ORDER BY hot_value DESC
            LIMIT 5
            """,
            (source,),
        )
        platform_ranks[source] = items

    # 6. 最近采集时间
    latest_row = _query("SELECT MAX(fetched_at) AS latest FROM hot_topics")
    latest_fetch = latest_row[0]["latest"] if latest_row else None

    # 7. 统计摘要
    avg_row = _query("SELECT AVG(hot_value) AS avg_hot FROM hot_topics WHERE hot_value > 0")
    avg_hot = int(avg_row[0]["avg_hot"]) if avg_row and avg_row[0]["avg_hot"] else 0

    today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
    today_row = _query(
        "SELECT COUNT(*) AS cnt FROM hot_topics WHERE fetched_at >= ?",
        (today_start,),
    )
    today_count = today_row[0]["cnt"] if today_row else 0

    payload = {
        "total_count": total_count,
        "platform_stats": platform_stats,
        "top_topics": top_topics,
        "category_stats": category_stats,
        "platform_ranks": platform_ranks,
        "latest_fetch": latest_fetch,
        "stats_summary": {
            "total": total_count,
            "platforms": len(platform_stats),
            "today_count": today_count,
            "avg_hot_value": avg_hot,
        },
    }
    return JSONResponse(content=payload)


@app.get("/api/topics", summary="获取话题列表（支持分页/筛选）")
def get_topics(
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    """按平台筛选话题，支持分页。"""
    if source:
        rows = _query(
            """
            SELECT id, title, source, hot_value, url, rank, category, fetched_at
            FROM hot_topics WHERE source = ?
            ORDER BY hot_value DESC
            LIMIT ? OFFSET ?
            """,
            (source, limit, offset),
        )
        count_row = _query("SELECT COUNT(*) AS cnt FROM hot_topics WHERE source = ?", (source,))
    else:
        rows = _query(
            """
            SELECT id, title, source, hot_value, url, rank, category, fetched_at
            FROM hot_topics
            ORDER BY hot_value DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        count_row = _query("SELECT COUNT(*) AS cnt FROM hot_topics")

    total = count_row[0]["cnt"] if count_row else 0
    return JSONResponse(content={"total": total, "items": rows, "limit": limit, "offset": offset})


@app.get("/api/sources", summary="获取所有数据源平台")
def get_sources() -> JSONResponse:
    """返回所有数据源平台及各自话题数量。"""
    rows = _query(
        "SELECT source, COUNT(*) AS count, MAX(fetched_at) AS latest_fetch FROM hot_topics GROUP BY source ORDER BY count DESC"
    )
    for r in rows:
        pm = PLATFORM_MAP.get(r["source"], {"label": r["source"], "color": "#40BE7A"})
        r["label"] = pm["label"]
        r["color"] = pm["color"]
    return JSONResponse(content={"sources": rows})


def _run_crawl_sync() -> dict:
    """同步执行 crawl 子进程（在线程池中调用）。"""
    import re as _re
    import subprocess
    import sys

    project_root = str(Path(__file__).resolve().parent.parent)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "spide", "crawl", "--all", "--save"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "crawl timeout (>120s)"}
    except Exception as exc:
        return {"status": "error", "message": f"subprocess error: {exc}"}

    raw_stdout = result.stdout
    raw_stderr = result.stderr
    stdout = raw_stdout.decode("utf-8", errors="replace") if raw_stdout else ""
    stderr = raw_stderr.decode("utf-8", errors="replace") if raw_stderr else ""

    if result.returncode != 0:
        return {"status": "error", "message": (stderr + stdout)[-500:] or f"rc={result.returncode}"}

    saved = 0
    for line in stdout.splitlines():
        if "已保存" in line and "条记录" in line:
            m = _re.search(r"已保存\s+(\d+)\s+条记录", line)
            if m:
                saved = int(m.group(1))

    return {"status": "ok", "saved": saved, "output": stdout[-800:]}


@app.post("/api/crawl", summary="触发全量热搜采集")
async def trigger_crawl() -> JSONResponse:
    """执行 spide crawl --all --save，返回采集结果摘要。"""
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _run_crawl_sync)
        return JSONResponse(content=result)
    except TimeoutError:
        return JSONResponse(status_code=504, content={"status": "error", "message": "crawl timeout (>120s)"})
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"status": "error", "message": f"{e}", "traceback": traceback.format_exc()})


# ── GitHub AI 热点 ────────────────────────────────────────────────

_feishu_webhook_url = ""


def set_feishu_webhook(url: str) -> None:
    global _feishu_webhook_url
    _feishu_webhook_url = url


@app.get("/api/github/trending", summary="获取 GitHub AI 热点仓库")
async def get_github_trending() -> JSONResponse:
    """采集 GitHub AI/LLM/Agent/MCP/MLX 热门仓库."""
    svc = GitHubTrendingService(feishu_webhook_url=_feishu_webhook_url)
    repos = await svc.collect()
    return JSONResponse(content={
        "total": len(repos),
        "repos": [r.to_dict() for r in repos[:30]],
    })


@app.post("/api/github/push", summary="采集 GitHub 热点并推送到飞书")
async def push_github_trending() -> JSONResponse:
    """一键采集 GitHub 热点并推送到飞书 Webhook."""
    svc = GitHubTrendingService(feishu_webhook_url=_feishu_webhook_url)
    result = await svc.run()
    return JSONResponse(content=result)


@app.post("/api/github/webhook", summary="设置飞书 Webhook URL")
async def set_webhook(body: dict[str, str] = Body(...)) -> JSONResponse:
    """动态设置飞书 Webhook URL.

    请求体: {"url": "https://open.feishu.cn/open-apis/bot/v2/hook/..."}
    """
    url = body.get("url", "")
    if not url:
        return JSONResponse(status_code=400, content={"error": "url is required"})
    set_feishu_webhook(url)
    return JSONResponse(content={"status": "ok", "url_set": True})


# ── 静态文件 & 前端路由 ──────────────────────────────────────────

# 根路径返回 dashboard 页面
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── 入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dashboard.api:app", host="0.0.0.0", port=8765, reload=True)
