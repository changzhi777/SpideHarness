"""Vercel Serverless Function — Dashboard API (Supabase 实时数据)

直接查询 Supabase PostgreSQL，无需本地数据库或预生成数据。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

PLATFORM_MAP: dict[str, dict[str, str]] = {
    "weibo": {"label": "微博", "color": "#E6162D"},
    "baidu": {"label": "百度", "color": "#4E6EF2"},
    "douyin": {"label": "抖音", "color": "#FE2C55"},
    "zhihu": {"label": "知乎", "color": "#0066FF"},
    "bilibili": {"label": "B站", "color": "#00A1D6"},
    "kuaishou": {"label": "快手", "color": "#FF8C00"},
    "tieba": {"label": "贴吧", "color": "#4879BD"},
}


def _pm(source: str) -> dict[str, str]:
    return PLATFORM_MAP.get(source, {"label": source, "color": "#40BE7A"})


def _get_sb() -> Any:
    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


app = FastAPI(title="SpideHarness Dashboard API", version="3.1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/dashboard", summary="获取 Dashboard 全量数据")
def get_dashboard() -> JSONResponse:
    """返回前端 Dashboard 所需的全部数据。"""
    sb = _get_sb()

    resp = sb.table("hot_topics").select("*", count="exact").execute()
    all_rows = resp.data
    total_count = resp.count or 0

    if total_count == 0:
        return JSONResponse(content={
            "total_count": 0, "platform_stats": [], "top_topics": [],
            "category_stats": [], "platform_ranks": {}, "latest_fetch": None,
            "stats_summary": {"total": 0, "platforms": 0, "today_count": 0, "avg_hot_value": 0},
        })

    # 平台统计
    source_count: dict[str, int] = {}
    for r in all_rows:
        s = r.get("source", "")
        source_count[s] = source_count.get(s, 0) + 1
    platform_stats = [
        {"source": s, "count": c, **_pm(s)}
        for s, c in sorted(source_count.items(), key=lambda x: -x[1])
    ]

    # Top 20 — 序号 = 列表索引 + 1
    sorted_rows = sorted(all_rows, key=lambda r: r.get("hot_value") or 0, reverse=True)
    top_topics = []
    for i, r in enumerate(sorted_rows[:20]):
        m = _pm(r.get("source", ""))
        top_topics.append({
            "rank": i + 1,
            "title": r.get("title", ""),
            "source": r.get("source", ""),
            "source_label": m["label"],
            "hot_value": r.get("hot_value", 0),
            "url": r.get("url", ""),
            "fetched_at": r.get("fetched_at"),
        })

    # 分类统计
    cat_count: dict[str, int] = {}
    for r in all_rows:
        c = r.get("category")
        if c:
            cat_count[c] = cat_count.get(c, 0) + 1
    category_stats = [
        {"category": c, "count": n}
        for c, n in sorted(cat_count.items(), key=lambda x: -x[1])
    ]

    # 各平台 Top 5
    platform_ranks: dict[str, list[dict]] = {}
    for s in source_count:
        items = sorted(
            [r for r in all_rows if r.get("source") == s],
            key=lambda r: r.get("hot_value") or 0,
            reverse=True,
        )[:5]
        platform_ranks[s] = [
            {"rank": i + 1, "title": r.get("title", ""), "url": r.get("url", ""), "hot_value": r.get("hot_value")}
            for i, r in enumerate(items)
        ]

    # 最新采集时间
    fetch_times = [r["fetched_at"] for r in all_rows if r.get("fetched_at")]
    latest_fetch = max(fetch_times) if fetch_times else None

    # 统计摘要
    hot_values = [r["hot_value"] for r in all_rows if r.get("hot_value")]
    avg_hot = int(sum(hot_values) / len(hot_values)) if hot_values else 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(
        1 for r in all_rows
        if r.get("fetched_at") and r["fetched_at"].startswith(today_str)
    )

    return JSONResponse(content={
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
    })


@app.get("/api/sources", summary="获取所有数据源平台")
def get_sources() -> JSONResponse:
    """返回所有数据源平台及各自话题数量。"""
    sb = _get_sb()
    resp = sb.table("hot_topics").select("source").execute()
    source_count: dict[str, int] = {}
    for r in resp.data:
        s = r.get("source", "")
        source_count[s] = source_count.get(s, 0) + 1
    sources = [
        {"source": s, "count": c, **_pm(s)}
        for s, c in sorted(source_count.items(), key=lambda x: -x[1])
    ]
    return JSONResponse(content={"sources": sources})


@app.post("/api/crawl", summary="触发采集（不可用）")
def trigger_crawl() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={"status": "error", "message": "请在本地运行 spide crawl --all --save"},
    )
