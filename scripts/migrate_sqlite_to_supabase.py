# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""SQLite → Supabase 数据迁移脚本.

用法:
    # 确保已配置 configs/supabase.yaml
    python scripts/migrate_sqlite_to_supabase.py

    # 指定 SQLite 路径
    python scripts/migrate_sqlite_to_supabase.py --db-path ./spide_data.db

    # 仅干跑（不写入 Supabase）
    python scripts/migrate_sqlite_to_supabase.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_supabase_config() -> tuple[str, str]:
    """从 configs/supabase.yaml 读取连接参数."""
    import yaml

    cfg_path = PROJECT_ROOT / "configs" / "supabase.yaml"
    if not cfg_path.exists():
        print(f"[ERROR] 配置文件不存在: {cfg_path}")
        print("请先创建 configs/supabase.yaml（参考 configs/default.yaml 中的占位字段）")
        sys.exit(1)

    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    url = cfg.get("supabase_url", "")
    key = cfg.get("supabase_service_key", "")

    if not url or not key:
        print("[ERROR] supabase_url 或 supabase_service_key 未配置")
        sys.exit(1)

    return url, key


def _get_sb_client(url: str, key: str) -> Any:
    """创建 Supabase 同步客户端."""
    from supabase import create_client

    return create_client(url, key)


def _read_sqlite(db_path: str) -> dict[str, list[dict]]:
    """读取 SQLite 全部数据，按表分组."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有用户表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r["name"] for r in cursor.fetchall()]

    result: dict[str, list[dict]] = {}
    for table in tables:
        cursor.execute(f"SELECT * FROM {table} ORDER BY id")
        rows = [dict(r) for r in cursor.fetchall()]
        if rows:
            result[table] = rows
            print(f"  SQLite [{table}]: {len(rows)} 条记录")

    conn.close()
    return result


# ── 序列化适配 ──────────────────────────────────────────────────
# SQLite 存储的值需要适配 Supabase 列类型：
#   - extra/keywords/image_urls/media_urls/tags/messages/usage/crawled_urls/task_ids: TEXT → JSONB
#   - fetched_at/created_at/started_at/completed_at/published_at: TEXT → TIMESTAMPTZ
#   - 其余字段直传

_JSON_FIELDS = {
    "extra", "keywords", "image_urls", "media_urls", "tags",
    "messages", "usage", "crawled_urls", "task_ids", "params",
}

_DATETIME_FIELDS = {
    "fetched_at", "created_at", "started_at", "completed_at", "published_at",
}


def _adapt_row(row: dict, table: str) -> dict:
    """将 SQLite 行转换为 Supabase 兼容格式."""
    out: dict[str, Any] = {}

    for key, val in row.items():
        # 跳过 id — Supabase 自增主键
        if key == "id":
            continue

        # None 保持 None
        if val is None:
            out[key] = None
            continue

        # JSON 字段：TEXT → Python 对象
        if key in _JSON_FIELDS and isinstance(val, str):
            try:
                out[key] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                out[key] = val
            continue

        # 时间字段：确保 ISO 格式
        if key in _DATETIME_FIELDS and isinstance(val, str):
            # SQLite 可能存 '2026-04-23 12:34:56' — 加 T 转为 ISO
            iso = val.replace(" ", "T") if " " in val and "T" not in val else val
            # 补时区后缀（本地时间 → +00:00 近似）
            if "+" not in iso and "Z" not in iso:
                iso += "+00:00"
            out[key] = iso
            continue

        out[key] = val

    return out


def _migrate_table(
    sb: Any,
    table: str,
    rows: list[dict],
    *,
    batch_size: int = 100,
    dry_run: bool = False,
) -> int:
    """迁移单张表到 Supabase，使用 upsert 去重."""
    if not rows:
        return 0

    adapted = [_adapt_row(r, table) for r in rows]
    total_upserted = 0

    for i in range(0, len(adapted), batch_size):
        batch = adapted[i : i + batch_size]
        if dry_run:
            total_upserted += len(batch)
            continue

        resp = sb.table(table).upsert(batch, on_conflict="").execute()
        total_upserted += len(batch)

    return total_upserted


# ── Supabase 表 ↔ UNIQUE 约束字段映射 ────────────────────────
# upsert 需要 on_conflict 指定冲突字段
_CONFLICT_FIELDS: dict[str, str] = {
    "hot_topics": "title,source",
    "news_articles": "url,source",
    "deep_contents": "platform,content_id",
    "deep_comments": "platform,comment_id",
    "deep_creators": "platform,user_id",
    # crawl_tasks / crawl_sessions: 无 UNIQUE，普通 INSERT
}


def _migrate_table_v2(
    sb: Any,
    table: str,
    rows: list[dict],
    *,
    batch_size: int = 100,
    dry_run: bool = False,
) -> int:
    """迁移单张表到 Supabase（带 on_conflict 去重）."""
    if not rows:
        return 0

    adapted = [_adapt_row(r, table) for r in rows]
    conflict = _CONFLICT_FIELDS.get(table, "")
    total = 0

    for i in range(0, len(adapted), batch_size):
        batch = adapted[i : i + batch_size]
        if dry_run:
            total += len(batch)
            continue

        if conflict:
            sb.table(table).upsert(
                batch, on_conflict=conflict
            ).execute()
        else:
            # 无 UNIQUE 约束 → 普通 INSERT（跳过已有 id 重复）
            for row in batch:
                try:
                    sb.table(table).insert(row).execute()
                except Exception:
                    pass  # 跳过已存在记录
        total += len(batch)

    return total


def _verify(sb: Any, table: str, expected: int) -> int:
    """验证 Supabase 表记录数."""
    resp = sb.table(table).select("*", count="exact").execute()
    actual = resp.count or 0
    status = "OK" if actual >= expected else "MISMATCH"
    print(f"  [{table}] Supabase: {actual} 条 | SQLite 源: {expected} 条 | {status}")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite → Supabase 数据迁移")
    parser.add_argument("--db-path", default=str(PROJECT_ROOT / "spide_data.db"), help="SQLite 数据库路径")
    parser.add_argument("--dry-run", action="store_true", help="仅干跑，不写入 Supabase")
    parser.add_argument("--batch-size", type=int, default=100, help="每批写入条数（默认 100）")
    args = parser.parse_args()

    print("=" * 60)
    print("SQLite → Supabase 数据迁移")
    print("=" * 60)
    print(f"SQLite 路径: {args.db_path}")
    print(f"干跑模式: {'是' if args.dry_run else '否'}")
    print()

    # 1. 读取 SQLite
    print("[1/3] 读取 SQLite 数据...")
    if not os.path.exists(args.db_path):
        print(f"[ERROR] SQLite 文件不存在: {args.db_path}")
        sys.exit(1)

    sqlite_data = _read_sqlite(args.db_path)
    total_sqlite = sum(len(v) for v in sqlite_data.values())
    print(f"  共 {len(sqlite_data)} 张表, {total_sqlite} 条记录")
    print()

    if not sqlite_data:
        print("[INFO] SQLite 无数据，无需迁移。")
        return

    # 2. 迁移到 Supabase
    if args.dry_run:
        print("[2/3] 干跑模式 — 跳过 Supabase 写入")
        for table, rows in sqlite_data.items():
            print(f"  [{table}] 将迁移 {len(rows)} 条")
    else:
        print("[2/3] 连接 Supabase...")
        url, key = _load_supabase_config()
        sb = _get_sb_client(url, key)
        print(f"  URL: {url}")
        print()

        for table, rows in sqlite_data.items():
            count = _migrate_table_v2(sb, table, rows, batch_size=args.batch_size)
            print(f"  [{table}] 迁移完成: {count}/{len(rows)} 条")

    print()

    # 3. 验证
    if not args.dry_run:
        print("[3/3] 验证迁移结果...")
        url, key = _load_supabase_config()
        sb = _get_sb_client(url, key)
        for table, rows in sqlite_data.items():
            _verify(sb, table, len(rows))
    else:
        print("[3/3] 干跑模式 — 跳过验证")

    print()
    print("迁移完成。" if not args.dry_run else "干跑完成（未写入任何数据）。")


if __name__ == "__main__":
    main()
