# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""外部系统集成层 — Thoth 知识库等."""

from spide.exceptions import (
    ThothAuthError,
    ThothError,
    ThothNotFoundError,
    ThothServerError,
)
from spide.integrations.thoth_client import ThothClient
from spide.integrations.url_metadata import fetch as fetch_url_metadata
from spide.integrations.video_pipeline import (
    extract_urls,
    process_urls,
)

__all__ = [
    "ThothAuthError",
    "ThothClient",
    "ThothError",
    "ThothNotFoundError",
    "ThothServerError",
    "extract_urls",
    "fetch_url_metadata",
    "process_urls",
]
