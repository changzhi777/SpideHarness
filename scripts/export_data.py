"""
导出 SQLite 数据为 Python 模块，用于 Vercel 部署。

用法：python scripts/export_data.py
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "spide_data.db"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "api" / "_data.py"

PLATFORM_MAP: dict[str, dict[str, str]] = {
    "weibo": {"label": "微博", "color": "#E6162D"},
    "baidu": {"label": "百度", "color": "#4E6EF2"},
    "douyin": {"label": "抖音", "color": "#FE2C55"},
    "zhihu": {"label": "知乎", "color": "#0066FF"},
    "bilibili": {"label": "B站", "color": "#00A1D6"},
    "kuaishou": {"label": "快手", "color": "#FF8C00"},
    "tieba": {"label": "贴吧", "color": "#4879BD"},
}


def pm(source: str) -> dict[str, str]:
    return PLATFORM_MAP.get(source, {"label": source, "color": "#40BE7A"})


def q(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        print(f"数据库不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        total = q(conn, "SELECT COUNT(*) AS cnt FROM hot_topics")[0]["cnt"]

        # 平台统计
        ps = q(
            conn,
            "SELECT source, COUNT(*) AS count FROM hot_topics GROUP BY source ORDER BY count DESC",
        )
        for p in ps:
            m = pm(p["source"])
            p["label"] = m["label"]
            p["color"] = m["color"]

        # Top 20
        tt = q(
            conn,
            "SELECT rank, title, source, hot_value, url, fetched_at "
            "FROM hot_topics WHERE rank IS NOT NULL ORDER BY hot_value DESC LIMIT 20",
        )
        for t in tt:
            m = pm(t["source"])
            t["source_label"] = m["label"]

        # 分类统计
        cs = q(
            conn,
            "SELECT category, COUNT(*) AS count FROM hot_topics "
            'WHERE category IS NOT NULL AND category != "" '
            "GROUP BY category ORDER BY count DESC",
        )

        # 平台 Top 5
        pr: dict[str, list[dict]] = {}
        for p in ps:
            s = p["source"]
            items = q(
                conn,
                "SELECT rank, title, url, hot_value FROM hot_topics "
                "WHERE source = ? ORDER BY hot_value DESC LIMIT 5",
                (s,),
            )
            pr[s] = items

        # 最新采集
        latest = q(conn, "SELECT MAX(fetched_at) AS latest FROM hot_topics")[0]["latest"]

        # 统计摘要
        avg_row = q(conn, "SELECT AVG(hot_value) AS a FROM hot_topics WHERE hot_value > 0")
        avg_hot = int(avg_row[0]["a"] or 0) if avg_row else 0
        today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
        today_count = q(
            conn,
            "SELECT COUNT(*) AS cnt FROM hot_topics WHERE fetched_at >= ?",
            (today_start,),
        )[0]["cnt"]

        data = {
            "total_count": total,
            "platform_stats": ps,
            "top_topics": tt,
            "category_stats": cs,
            "platform_ranks": pr,
            "latest_fetch": latest,
            "stats_summary": {
                "total": total,
                "platforms": len(ps),
                "today_count": today_count,
                "avg_hot_value": avg_hot,
            },
        }

        # 生成 Python 模块
        py_content = (
            '"""预生成的 Dashboard 数据（由 scripts/export_data.py 自动生成）。"""\n'
            "from __future__ import annotations\n\n"
            f"DATA: dict = {repr(data)}\n"
        )
        OUTPUT_PATH.write_text(py_content, encoding="utf-8")

        print(f"导出 {total} 条话题到 {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
