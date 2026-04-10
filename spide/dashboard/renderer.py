# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""看板渲染器 — 合并模板与数据生成完整 HTML.

用法:
    from spide.dashboard.renderer import render_dashboard

    html = render_dashboard(data)
    Path("dashboard.html").write_text(html, encoding="utf-8")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spide.dashboard.template import DASHBOARD_TEMPLATE
from spide.logging import get_logger

logger = get_logger(__name__)


def render_dashboard(data: dict[str, Any]) -> str:
    """将看板数据注入模板，返回完整 HTML 字符串.

    Args:
        data: collect_dashboard_data() 返回的聚合数据字典

    Returns:
        完整的 HTML 字符串
    """
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    html = DASHBOARD_TEMPLATE.replace("{{JSON_DATA}}", json_str)
    return html


def write_dashboard(html: str, output_path: str | Path) -> Path:
    """将 HTML 写入文件.

    Args:
        html: render_dashboard() 返回的 HTML 字符串
        output_path: 输出文件路径

    Returns:
        写入的文件 Path
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    logger.debug("dashboard_written", path=str(path), size_kb=round(path.stat().st_size / 1024, 1))
    return path
