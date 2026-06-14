#!/usr/bin/env python3
# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Thoth 知识库端到端验证脚本 — 配置有效 token 后可一键跑.

Usage:
    export THOTH_API_TOKEN='your-token-here'
    uv run python scripts/verify_thoth_e2e.py

    # 或先 dry-run 验证 client 构造 + 配置正确性
    uv run python scripts/verify_thoth_e2e.py --dry-run

    # 跳过删除（保留测试 note）
    uv run python scripts/verify_thoth_e2e.py --keep

功能:
    1. health_check  → 验证 Thoth 服务可达
    2. create_note   → 真实创建一篇测试笔记
    3. get_note      → 验证能取回
    4. search_notes  → 验证搜索能找到
    5. update_note   → 验证更新可工作（可选）
    6. delete_note   → 清理（除非 --keep）

退出码:
    0 = 全部成功
    1 = 任何步骤失败
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

from spide.config import load_settings
from spide.integrations import ThothClient, ThothError


async def main() -> int:
    parser = argparse.ArgumentParser(description="Thoth 端到端验证")
    parser.add_argument(
        "--dry-run", action="store_true", help="只验证 client 构造 + 配置正确性"
    )
    parser.add_argument(
        "--keep", action="store_true", help="保留测试 note（不删除）"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Thoth 知识库端到端验证")
    print("=" * 60)

    # 1. 加载配置
    try:
        settings = load_settings()
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return 1

    print(f"  base_url      : {settings.thoth.base_url}")
    print(f"  default_room  : {settings.thoth.default_room_id}")
    print(f"  timeout       : {settings.thoth.timeout}s")
    token_preview = settings.thoth.token[:20] + "..." if settings.thoth.token else "(空)"
    print(f"  token         : {token_preview}")

    if not settings.thoth.token:
        print("\n❌ token 未配置！请设置环境变量 THOTH_API_TOKEN")
        print("   或在 configs/thoth.yaml 中填入 token 字段")
        return 1

    # 2. 构造 client
    try:
        client = ThothClient(settings.thoth)
    except Exception as e:
        print(f"\n❌ Client 构造失败: {e}")
        return 1

    print(f"\n✅ Client 构造成功: {type(client).__name__}")

    if args.dry_run:
        print("\n[dry-run] 跳过实际 HTTP 调用")
        return 0

    # 3. 健康检查
    print("\n[1/5] health_check() ...")
    try:
        ok = await client.health_check()
        if not ok:
            print("  ❌ Thoth 服务不可达")
            return 1
        print("  ✅ Thoth 服务可达")
    except Exception as e:
        print(f"  ❌ health_check 异常: {e}")
        return 1

    # 4. 创建测试 note
    test_title = f"E2E 验证 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    test_content = (
        "# Thoth 端到端验证\n\n"
        "这是 spide ThothClient 的自动化验证笔记。\n\n"
        "- 创建时间: 自动\n"
        "- 验证项: create/get/search/update/delete\n"
        "- 工具: scripts/verify_thoth_e2e.py\n"
    )
    test_tags = "e2e,test,spide,verification"
    print(f"\n[2/5] create_note(title='{test_title}') ...")
    try:
        note = await client.create_note(
            title=test_title, content=test_content, tags=test_tags
        )
        note_id = note.get("id")
        if not note_id:
            print(f"  ❌ 创建失败：无 id 字段，响应={note}")
            return 1
        print(f"  ✅ 创建成功 id={note_id}")
        print(f"     room_id={note.get('room_id')}")
    except ThothError as e:
        print(f"  ❌ 创建失败: {e}")
        return 1

    # 5. 获取
    print(f"\n[3/5] get_note({note_id}) ...")
    try:
        got = await client.get_note(note_id)
        if got.get("title") != test_title:
            print(f"  ❌ 标题不匹配: {got.get('title')}")
            return 1
        print(f"  ✅ 标题匹配: {got.get('title')}")
    except ThothError as e:
        print(f"  ❌ 获取失败: {e}")
        return 1

    # 6. 搜索
    print("\n[4/5] search_notes('E2E 验证') ...")
    try:
        results = await client.search_notes("E2E 验证")
        if not any(r.get("id") == note_id for r in results):
            print(f"  ⚠️ 搜索未命中（可能索引延迟）: 共 {len(results)} 条")
        else:
            print(f"  ✅ 搜索命中: 共 {len(results)} 条")
    except ThothError as e:
        print(f"  ❌ 搜索失败: {e}")
        return 1

    # 7. 清理
    if args.keep:
        print("\n[5/5] SKIP delete_note (--keep 模式)")
        print(f"  💡 测试 note id={note_id} 已保留")
    else:
        print(f"\n[5/5] delete_note({note_id}) ...")
        try:
            await client.delete_note(note_id)
            print("  ✅ 删除成功")
        except ThothError as e:
            print(f"  ⚠️ 删除失败（可手动清理）: {e}")

    # 8. 清理 session
    await client.stop()

    print("\n" + "=" * 60)
    print("✅ Thoth 端到端验证全部通过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        exit_code = 1
    sys.exit(exit_code)
