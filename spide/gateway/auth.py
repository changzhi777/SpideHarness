# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""API Key 鉴权 — 纯 stdlib，无外部依赖.

设计：
- 通过 `X-API-Key` 请求头传递
- 多个有效 Key 支持（环境变量 `SPIDE_GATEWAY_API_KEYS` 逗号分隔）
- 未配置 Key = **禁用鉴权**（开发模式，零配置启动）
- 鉴权失败返回 401 + `WWW-Authenticate` 头
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Header, HTTPException, status


def load_valid_keys() -> set[str]:
    """从环境变量加载有效 API Key 列表.

    Returns:
        有效 Key 集合；空集合表示禁用鉴权（开发模式）。
    """
    raw = os.environ.get("SPIDE_GATEWAY_API_KEYS", "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """FastAPI 依赖：验证请求头中的 API Key.

    行为：
    - 无 Key 配置（开发模式）→ 直接放行，返回 "anonymous"
    - 提供了 Key 但无效 → 抛 401
    - 提供了有效 Key → 返回该 Key（供日志/审计用）

    Usage:
        @app.get("/protected", dependencies=[Depends(require_api_key)])
    """
    valid_keys = load_valid_keys()
    # 开发模式：未配置 Key 直接放行
    if not valid_keys:
        return "anonymous"

    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


def is_auth_enabled() -> bool:
    """当前进程是否启用了鉴权（用于健康检查展示）."""
    return bool(load_valid_keys())
