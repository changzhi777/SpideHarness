# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Thoth 知识库 HTTP 客户端 — 最小可用实现.

服务地址: http://10.10.10.15:8765 (FastAPI v1.0.32, 已部署)
认证: Authorization: Bearer <token>
核心端点: /api/notes (CRUD + search)

Usage:
    from spide.config import load_settings
    from spide.integrations import ThothClient

    settings = load_settings()
    client = ThothClient(settings.thoth)
    if await client.health_check():
        note = await client.create_note(
            title="GPT-5 综述",
            content="# GPT-5\\n\\n核心要点...",
            tags="AI,LLM",
            room_id="room_video_2026",
        )

Note:
    当前 (2026-06-14) Thoth PG sslmode 限制未解，register/login 暂不可用。
    需手动从 Thoth Web UI DevTools 拿 token 填入 configs/thoth.yaml。
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from spide.config import ThothConfig
from spide.exceptions import (
    ThothAuthError,
    ThothError,
    ThothNotFoundError,
    ThothServerError,
)
from spide.logging import get_logger

logger = get_logger(__name__)

# 业务错误不重试的状态码
_NON_RETRYABLE_STATUS = {400, 401, 403, 404, 422}


class ThothClient:
    """Thoth 知识库异步 HTTP 客户端.

    特性:
    - 网络错误重试 3 次（指数退避 0.5/1/2s）
    - 业务错误（4xx）不重试
    - 5xx 抛 ThothServerError（让上层决定重试）
    - 401/403 抛 ThothAuthError（提示 token 失效）
    - 404 抛 ThothNotFoundError
    """

    def __init__(self, config: ThothConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """初始化 HTTP session（幂等 — 重复调用安全）."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self) -> None:
        """关闭 HTTP session（幂等 — 重复调用安全）."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            await self.start()
        assert self._session is not None
        return self._session

    def _headers(self) -> dict[str, str]:
        """构造请求头（含 Bearer token）."""
        h = {"Content-Type": "application/json"}
        if self._config.token:
            h["Authorization"] = f"Bearer {self._config.token}"
        return h

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """通用 HTTP 请求方法（含重试 + 异常映射）."""
        session = await self._ensure_session()
        url = f"{self._config.base_url.rstrip('/')}{path}"
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                async with session.request(
                    method, url, json=json, headers=self._headers()
                ) as resp:
                    # 业务错误（4xx）不重试，直接抛
                    if 400 <= resp.status < 500:
                        await self._raise_for_status(resp, json)
                    # 5xx 重试
                    if resp.status >= 500:
                        last_exc = ThothServerError(
                            f"Thoth {resp.status}", status_code=resp.status
                        )
                        logger.warning(
                            "thoth_5xx",
                            method=method,
                            path=path,
                            status=resp.status,
                            attempt=attempt + 1,
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.5 * (2**attempt))
                            continue
                        raise last_exc
                    # 2xx 成功
                    if resp.content_length == 0:
                        return {}
                    return await resp.json()

            except aiohttp.ClientError as e:
                # 网络错误 — 重试
                last_exc = e
                logger.warning(
                    "thoth_request_error",
                    method=method,
                    path=path,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise ThothError(
                    f"Thoth 请求失败: {e}", detail=str(e)
                ) from e

        # 不应到达此处
        raise ThothError("Thoth 请求重试耗尽") from last_exc

    async def _raise_for_status(
        self, resp: aiohttp.ClientResponse, json_body: dict | None
    ) -> None:
        """根据 HTTP 状态码抛对应异常."""
        status = resp.status
        try:
            detail = (await resp.json()).get("detail", resp.reason)
        except Exception:
            detail = resp.reason
        if status in (401, 403):
            raise ThothAuthError(
                f"Thoth 认证失败: {detail}", status_code=status
            )
        if status == 404:
            raise ThothNotFoundError(
                f"Thoth 资源不存在: {detail}", status_code=status
            )
        raise ThothError(
            f"Thoth 业务错误 {status}: {detail}", status_code=status
        )

    # ── 公开 API ──────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """检查 Thoth 服务可用性（公开端点 /api/status）."""
        try:
            session = await self._ensure_session()
            async with session.get(
                f"{self._config.base_url.rstrip('/')}/api/status"
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning("thoth_health_check_failed", error=str(e))
            return False

    async def create_note(
        self,
        *,
        title: str,
        content: str = "",
        tags: str = "",
        room_id: str | None = None,
        folder_path: str = "/",
    ) -> dict[str, Any]:
        """创建知识库笔记.

        Args:
            title: 笔记标题（必填，空字符串会被 Thoth 拒绝）
            content: Markdown 文章正文
            tags: 逗号分隔的标签字符串
            room_id: 房间 ID（默认从配置读取）
            folder_path: 文件夹路径（默认 "/"）

        Returns:
            创建后的完整 note dict（含 id, created_at 等）
        """
        return await self._request(
            "POST",
            "/api/notes",
            json={
                "title": title,
                "content": content,
                "tags": tags,
                "room_id": room_id or self._config.default_room_id,
                "folder_path": folder_path,
            },
        )

    async def get_note(self, note_id: str) -> dict[str, Any]:
        """获取单个笔记."""
        return await self._request("GET", f"/api/notes/{note_id}")

    async def search_notes(
        self,
        query: str,
        *,
        room_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """搜索笔记（POST /api/notes/search）.

        Returns:
            笔记列表
        """
        body: dict[str, Any] = {"query": query}
        if room_id:
            body["room_id"] = room_id
        result = await self._request("POST", "/api/notes/search", json=body)
        # Thoth 返回结构待定，容错处理
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return []

    async def update_note(
        self, note_id: str, **fields: Any
    ) -> dict[str, Any]:
        """更新笔记（PUT /api/notes/{id}）.

        fields 允许: title, content, tags, folder_path, is_pinned
        """
        return await self._request(
            "PUT", f"/api/notes/{note_id}", json=fields
        )

    async def delete_note(self, note_id: str) -> None:
        """删除笔记（DELETE /api/notes/{id}）."""
        await self._request("DELETE", f"/api/notes/{note_id}")
