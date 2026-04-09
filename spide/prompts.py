# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Prompt 层叠系统 — 分层组装 Agent 系统提示.

用法:
    from spide.prompts import build_system_prompt
    prompt = build_system_prompt(workspace="/path/to/.spide_agent")

组装顺序（逐层追加，空层自动跳过）：
    1. 基础系统指令 (Base)
    2. 灵魂文件 (Soul)
    3. 身份文件 (Identity)
    4. 用户画像 (User)
    5. 首次引导 (Bootstrap)
    6. 工作空间信息 (Workspace)
    7. 记忆索引 + 记忆文件 (Memory)
"""

from __future__ import annotations

from pathlib import Path

from spide.workspace import (
    get_bootstrap_path,
    get_identity_path,
    get_memory_dir,
    get_memory_index_path,
    get_soul_path,
    get_user_path,
    get_workspace_root,
)

# ---------------------------------------------------------------------------
# 基础系统指令
# ---------------------------------------------------------------------------

_BASE_SYSTEM_PROMPT = """\
你是 SpideHarness Agent，一个专业的热点新闻信息抓取与智能整理助手。

## 核心能力
- 热点新闻采集：从微博、百度、抖音、知乎、B站等平台抓取热搜数据
- 智能分析：使用 LLM 对新闻内容进行摘要、分类、关联分析
- 联网搜索：通过智谱 Web Search API 获取实时搜索结果
- 视觉理解：分析新闻配图、网页截图、视频内容
- 持续学习：记住网站结构、反爬规则、有效选择器

## 工作模式
1. 接收采集指令 → 确定数据源和采集策略
2. 执行采集 → 获取热搜/新闻数据
3. 智能整理 → 分类、摘要、关联分析
4. 输出结果 → 结构化展示采集成果

## 行为准则
- 数据采集遵守 robots.txt 和网站使用条款
- 对敏感信息脱敏处理
- 提供可溯源的新闻来源
- 优先使用高效的数据源 API，减少页面爬取
- 每次采集后自动保存会话快照
"""

_WORKSPACE_INFO_TEMPLATE = """\
## 工作空间
- 根目录：{workspace_root}
- 记忆目录：{memory_dir}
- 会话目录：{sessions_dir}
"""


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


def _read_file(path: Path) -> str | None:
    """读取文件内容，不存在或为空返回 None."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        return text if text else None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def build_system_prompt(
    workspace: str | Path | None = None,
    extra_prompt: str | None = None,
) -> str:
    """分层组装系统提示.

    Args:
        workspace: 工作空间路径，默认 ~/.spide_agent/
        extra_prompt: 额外追加的指令文本

    Returns:
        组装完成的系统提示字符串
    """
    root = get_workspace_root(workspace)
    sections: list[str] = []

    # 1. 基础系统指令
    sections.append(_BASE_SYSTEM_PROMPT)

    # 2. 额外指令
    if extra_prompt:
        sections.append(extra_prompt)

    # 3. 灵魂文件
    soul = _read_file(get_soul_path(root))
    if soul:
        sections.append(f"## 灵魂\n\n{soul}")

    # 4. 身份文件
    identity = _read_file(get_identity_path(root))
    if identity:
        sections.append(f"## 身份\n\n{identity}")

    # 5. 用户画像
    user = _read_file(get_user_path(root))
    if user:
        sections.append(f"## 用户画像\n\n{user}")

    # 6. 首次引导（仅当文件存在时）
    bootstrap = _read_file(get_bootstrap_path(root))
    if bootstrap:
        sections.append(f"## 首次引导\n\n{bootstrap}")

    # 7. 工作空间信息
    from spide.workspace import get_sessions_dir

    sections.append(
        _WORKSPACE_INFO_TEMPLATE.format(
            workspace_root=root,
            memory_dir=get_memory_dir(root),
            sessions_dir=get_sessions_dir(root),
        )
    )

    # 8. 记忆
    memory_prompt = _load_memory_prompt(root)
    if memory_prompt:
        sections.append(memory_prompt)

    return "\n\n".join(sections)


def _load_memory_prompt(
    root: Path, max_files: int = 5, max_chars_per_file: int = 4000
) -> str | None:
    """加载记忆目录中的文件作为 prompt 部分."""
    memory_dir = get_memory_dir(root)
    if not memory_dir.is_dir():
        return None

    # 加载记忆索引
    index_path = get_memory_index_path(root)
    index_text = _read_file(index_path)
    if not index_text:
        return None

    parts: list[str] = [f"## 记忆\n\n记忆目录：{memory_dir}\n"]
    parts.append(f"### 记忆索引\n\n{index_text}")

    # 加载记忆文件（排除 MEMORY.md 索引本身）
    memory_files = sorted(
        (f for f in memory_dir.glob("*.md") if f.name != "MEMORY.md"),
        key=lambda p: p.name,
    )[:max_files]

    for mf in memory_files:
        content = _read_file(mf)
        if content:
            truncated = content[:max_chars_per_file]
            parts.append(f"### {mf.stem}\n\n{truncated}")

    return "\n\n".join(parts)
