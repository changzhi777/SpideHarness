# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""工作空间管理 — ~/.spide_agent/ 统一状态目录.

用法:
    from spide.workspace import get_workspace_root, initialize_workspace, workspace_health
    root = initialize_workspace()  # 创建 ~/.spide_agent/ 及模板文件
    health = workspace_health()    # 检查各关键资产是否存在
"""

from __future__ import annotations

import os
from pathlib import Path

from spide.exceptions import WorkspaceError

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

WORKSPACE_DIRNAME = ".spide_agent"
DEFAULT_WORKSPACE_ROOT = Path.home() / WORKSPACE_DIRNAME

# ---------------------------------------------------------------------------
# 模板内容
# ---------------------------------------------------------------------------

SOUL_TEMPLATE = """\
# SpideHarness Agent 灵魂

你是 SpideHarness Agent，一个专业的热点新闻信息抓取与智能整理助手。

## 核心能力
- 热点新闻采集：从微博、百度、抖音、知乎、B站等平台抓取热搜数据
- 智能分析：使用 LLM 对新闻内容进行摘要、分类、关联分析
- 视觉理解：分析新闻配图、网页截图、视频内容
- 持续学习：记住网站结构、反爬规则、有效选择器

## 行为准则
- 数据采集遵守 robots.txt 和网站使用条款
- 对敏感信息脱敏处理
- 提供可溯源的新闻来源
- 优先使用高效的数据源 API，减少页面爬取
"""

USER_TEMPLATE = """\
# 用户画像

<!-- 在此记录你的偏好，帮助 Agent 提供更好的服务 -->
<!-- 示例:
- 关注领域：科技、财经、国际新闻
- 语言偏好：中文
- 输出格式：简洁摘要
- 排除关键词：广告、推广
-->
"""

IDENTITY_TEMPLATE = """\
# SpideHarness Agent 身份

- 名称：SpideHarness Agent
- 版本：0.1.0
- 类型：热点新闻抓取 Agent CLI
- 架构：Harness Engineering
"""

MEMORY_INDEX_TEMPLATE = """\
# SpideHarness Agent 知识记忆

此文件是记忆索引，Agent 会自动维护。
下方列表中的记忆文件会被加载到上下文中。

<!-- 示例:
- [网站规则](weibo-rules.md) — 微博热搜采集规则
- [反爬策略](anti-detect.md) — 常见反爬应对方案
-->
"""

BOOTSTRAP_TEMPLATE = """\
# 快速开始

欢迎使用 SpideHarness Agent！首次使用建议：

1. 运行 `spide config` 配置 API Key 和数据源
2. 运行 `spide doctor` 检查环境
3. 运行 `spide crawl --source weibo` 开始采集

完成后可以删除此文件。
"""


# ---------------------------------------------------------------------------
# 路径获取函数
# ---------------------------------------------------------------------------


def get_workspace_root(workspace: str | Path | None = None) -> Path:
    """解析工作空间根目录.

    优先级: 显式参数 > SPIDE_WORKSPACE 环境变量 > ~/.spide_agent/
    """
    if workspace:
        return Path(workspace).expanduser().resolve()
    env = os.environ.get("SPIDE_WORKSPACE")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_WORKSPACE_ROOT


def get_soul_path(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "soul.md"


def get_user_path(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "user.md"


def get_identity_path(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "identity.md"


def get_bootstrap_path(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "BOOTSTRAP.md"


def get_memory_dir(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "memory"


def get_memory_index_path(workspace: str | Path | None = None) -> Path:
    return get_memory_dir(workspace) / "MEMORY.md"


def get_sessions_dir(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "sessions"


def get_plugins_dir(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "plugins"


def get_logs_dir(workspace: str | Path | None = None) -> Path:
    return get_workspace_root(workspace) / "logs"


# ---------------------------------------------------------------------------
# 工作空间操作
# ---------------------------------------------------------------------------


def _seed_file(path: Path, content: str) -> bool:
    """写入模板文件（仅当文件不存在时）.

    Returns:
        True 表示新创建了文件
    """
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def ensure_workspace(workspace: str | Path | None = None) -> Path:
    """确保工作空间目录结构存在."""
    root = get_workspace_root(workspace)
    root.mkdir(parents=True, exist_ok=True)

    for dir_fn in (get_memory_dir, get_sessions_dir, get_plugins_dir, get_logs_dir):
        dir_fn(root).mkdir(parents=True, exist_ok=True)

    return root


def initialize_workspace(workspace: str | Path | None = None) -> Path:
    """初始化工作空间：创建目录 + 种子模板文件.

    Returns:
        工作空间根路径
    """
    root = ensure_workspace(workspace)

    # 种子模板文件（仅当不存在时写入）
    templates: list[tuple[Path, str]] = [
        (get_soul_path(root), SOUL_TEMPLATE),
        (get_user_path(root), USER_TEMPLATE),
        (get_identity_path(root), IDENTITY_TEMPLATE),
        (get_bootstrap_path(root), BOOTSTRAP_TEMPLATE),
        (get_memory_index_path(root), MEMORY_INDEX_TEMPLATE),
    ]

    for path, content in templates:
        try:
            _seed_file(path, content)
        except OSError as e:
            raise WorkspaceError(
                f"无法创建模板文件 {path}: {e}", detail=str(e)
            ) from e

    return root


def workspace_health(workspace: str | Path | None = None) -> dict[str, bool]:
    """检查工作空间各关键资产是否存在.

    Returns:
        资产名 → 是否存在的映射
    """
    root = get_workspace_root(workspace)

    checks: dict[str, bool] = {
        "workspace_root": root.is_dir(),
        "soul": get_soul_path(root).exists(),
        "user": get_user_path(root).exists(),
        "identity": get_identity_path(root).exists(),
        "memory_dir": get_memory_dir(root).is_dir(),
        "memory_index": get_memory_index_path(root).exists(),
        "sessions_dir": get_sessions_dir(root).is_dir(),
        "plugins_dir": get_plugins_dir(root).is_dir(),
        "logs_dir": get_logs_dir(root).is_dir(),
    }
    return checks
