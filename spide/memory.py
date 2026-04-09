# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Memory 管理 — 文件系统知识记忆 CRUD.

用法:
    from spide.memory import add_memory, remove_memory, list_memory_files

    add_memory(workspace="~/.spide_agent", title="微博采集规则", content="...")
    files = list_memory_files(workspace="~/.spide_agent")
"""

from __future__ import annotations

import re
from pathlib import Path

from spide.logging import get_logger
from spide.workspace import get_memory_dir, get_memory_index_path, get_workspace_root

logger = get_logger(__name__)


def list_memory_files(workspace: str | Path | None = None) -> list[Path]:
    """列出所有记忆文件（排除 MEMORY.md 索引本身）."""
    mem_dir = get_memory_dir(get_workspace_root(workspace))
    if not mem_dir.is_dir():
        return []
    return sorted(
        (f for f in mem_dir.glob("*.md") if f.name != "MEMORY.md"),
        key=lambda p: p.name,
    )


def add_memory(
    workspace: str | Path | None = None,
    *,
    title: str,
    content: str,
) -> Path:
    """添加一条记忆.

    创建 {slug}.md 文件，并更新 MEMORY.md 索引。

    Args:
        workspace: 工作空间路径
        title: 记忆标题（用于生成文件名和索引条目）
        content: 记忆内容（Markdown 格式）

    Returns:
        创建的记忆文件路径
    """
    root = get_workspace_root(workspace)
    mem_dir = get_memory_dir(root)
    mem_dir.mkdir(parents=True, exist_ok=True)

    slug = _title_to_slug(title)
    memory_file = mem_dir / f"{slug}.md"

    # 写入记忆文件（如果已存在则追加）
    if memory_file.exists():
        existing = memory_file.read_text(encoding="utf-8")
        content = f"{existing}\n\n---\n\n{content}"

    memory_file.write_text(content, encoding="utf-8")

    # 更新索引
    _update_memory_index(root, title, f"{slug}.md")

    logger.debug("memory_added", title=title, file=str(memory_file))
    return memory_file


def remove_memory(
    workspace: str | Path | None = None,
    *,
    name: str,
) -> bool:
    """移除一条记忆.

    Args:
        name: 记忆文件名（不含路径，可含或不含 .md 后缀）

    Returns:
        是否成功移除
    """
    root = get_workspace_root(workspace)
    mem_dir = get_memory_dir(root)

    if not name.endswith(".md"):
        name = f"{name}.md"

    memory_file = mem_dir / name
    if not memory_file.exists():
        return False

    memory_file.unlink()

    # 从索引中移除
    _remove_from_memory_index(root, name)

    logger.debug("memory_removed", name=name)
    return True


def get_memory_content(
    workspace: str | Path | None = None,
    *,
    name: str,
) -> str | None:
    """读取一条记忆的内容."""
    root = get_workspace_root(workspace)
    mem_dir = get_memory_dir(root)

    if not name.endswith(".md"):
        name = f"{name}.md"

    memory_file = mem_dir / name
    if not memory_file.exists():
        return None

    return memory_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _title_to_slug(title: str) -> str:
    """将标题转换为 URL-safe 文件名 slug."""
    # 保留中文、字母、数字、连字符
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", title.strip())
    slug = slug.strip("_")
    return slug[:64] if slug else "untitled"


def _update_memory_index(root: Path, title: str, filename: str) -> None:
    """在 MEMORY.md 索引中添加条目（去重）."""
    index_path = get_memory_index_path(root)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"- [{title}]({filename})"

    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        # 检查是否已存在
        if filename in content:
            return
        # 追加到末尾
        if not content.endswith("\n"):
            content += "\n"
        content += f"{entry}\n"
    else:
        content = f"# Spide Agent 知识记忆\n\n{entry}\n"

    index_path.write_text(content, encoding="utf-8")


def _remove_from_memory_index(root: Path, filename: str) -> None:
    """从 MEMORY.md 索引中移除条目."""
    index_path = get_memory_index_path(root)
    if not index_path.exists():
        return

    lines = index_path.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [line for line in lines if filename not in line]
    index_path.write_text("".join(filtered), encoding="utf-8")
