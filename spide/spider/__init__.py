# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Spider 引擎 — 热搜数据采集与处理."""

from spide.spider.fetcher import AsyncFetcher
from spide.spider.pipeline import deduplicate_items, parse_hot_items
from spide.spider.uapi_client import UAPIClient

__all__ = ["AsyncFetcher", "UAPIClient", "deduplicate_items", "parse_hot_items"]
