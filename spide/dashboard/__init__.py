# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Dashboard 看板模块 — 数据可视化看板生成.

用法:
    from spide.dashboard import collect_dashboard_data, render_dashboard

    data = await collect_dashboard_data(db_path="spide_data.db")
    html = render_dashboard(data)
    # 写入文件后用浏览器打开
"""

from spide.dashboard.collector import collect_dashboard_data
from spide.dashboard.renderer import render_dashboard

__all__ = ["collect_dashboard_data", "render_dashboard"]
