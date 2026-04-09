# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Harness 调度引擎 — 运行时状态管理 + 管道编排.

用法:
    from spide.harness import Engine
    from spide.config import load_settings

    engine = Engine(load_settings())
    await engine.start()

    # 采集热搜
    results = await engine.crawl(sources=["weibo", "baidu"])

    # 与 LLM 对话
    response = engine.chat("分析今日微博热搜趋势")

    await engine.stop()
"""

from spide.harness.engine import Engine, RuntimeBundle

__all__ = ["Engine", "RuntimeBundle"]
