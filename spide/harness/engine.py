# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Harness 调度引擎核心 — RuntimeBundle + 管道编排.

RuntimeBundle 封装单次运行所需的全部状态，
Engine 负责生命周期管理和管道编排。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from spide.config import Settings, load_settings
from spide.exceptions import SpideError
from spide.llm import LLMClient
from spide.logging import get_logger
from spide.prompts import build_system_prompt
from spide.session_storage import SessionStorage
from spide.spider.uapi_client import UAPIClient
from spide.storage.models import CrawlMode, HotTopic, Platform
from spide.workspace import get_workspace_root

logger = get_logger(__name__)


@dataclass
class RuntimeBundle:
    """运行时状态容器 — 封装单次 Agent 会话的全部依赖."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    settings: Settings = field(default_factory=load_settings)
    workspace: str = ""
    system_prompt: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    crawled_urls: list[str] = field(default_factory=list)
    progress: float = 0.0

    # 延迟初始化的组件
    llm: LLMClient | None = field(default=None, init=False)
    uapi: UAPIClient | None = field(default=None, init=False)
    session_storage: SessionStorage | None = field(default=None, init=False)


class Engine:
    """Harness 调度引擎 — 管理 RuntimeBundle 生命周期."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or load_settings()
        self._bundle: RuntimeBundle | None = None

    async def start(
        self,
        *,
        workspace: str | None = None,
        session_id: str | None = None,
    ) -> RuntimeBundle:
        """创建并初始化运行时环境.

        Args:
            workspace: 工作空间路径
            session_id: 会话 ID（默认自动生成）

        Returns:
            初始化完成的 RuntimeBundle
        """
        ws = workspace or str(get_workspace_root())
        system_prompt = build_system_prompt(workspace=ws)

        bundle = RuntimeBundle(
            session_id=session_id or uuid.uuid4().hex[:12],
            settings=self._settings,
            workspace=ws,
            system_prompt=system_prompt,
        )

        # 初始化 LLM 客户端
        bundle.llm = LLMClient(self._settings.llm)
        await bundle.llm.start()

        # 初始化 UAPI 客户端
        if self._settings.uapi.api_key:
            bundle.uapi = UAPIClient(self._settings.uapi)
            await bundle.uapi.start()

        # 初始化会话存储
        bundle.session_storage = SessionStorage(workspace=ws)

        self._bundle = bundle
        logger.debug(
            "engine_started",
            session_id=bundle.session_id,
            workspace=ws,
        )
        return bundle

    async def stop(self) -> None:
        """关闭运行时环境，保存会话."""
        if self._bundle is None:
            return

        bundle = self._bundle

        # 保存会话快照
        if bundle.session_storage:
            await bundle.session_storage.save_snapshot(
                session_id=bundle.session_id,
                session_key="spide:engine",
                model=bundle.settings.llm.text.model,
                system_prompt=bundle.system_prompt,
                messages=bundle.messages,
                crawled_urls=bundle.crawled_urls,
                progress=bundle.progress,
            )

        # 关闭组件
        if bundle.uapi:
            await bundle.uapi.stop()
        if bundle.llm:
            await bundle.llm.stop()

        self._bundle = None
        logger.debug("engine_stopped", session_id=bundle.session_id)

    @property
    def bundle(self) -> RuntimeBundle:
        """获取当前 RuntimeBundle."""
        if self._bundle is None:
            raise SpideError("引擎未启动，请先调用 start()")
        return self._bundle

    # -----------------------------------------------------------------------
    # 采集管道
    # -----------------------------------------------------------------------

    async def crawl(self, sources: list[str] | None = None) -> dict[str, list[HotTopic]]:
        """执行热搜采集.

        Args:
            sources: 平台列表 (weibo/baidu/douyin/zhihu/bilibili)
                     默认采集所有已配置的源

        Returns:
            平台标识 → 热搜话题列表
        """
        bundle = self.bundle
        if bundle.uapi is None:
            raise SpideError("UAPI 客户端未初始化（API Key 未配置）")

        if sources:
            results: dict[str, list[HotTopic]] = {}
            tasks = [bundle.uapi.fetch_hotboard(src) for src in sources]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for src, resp in zip(sources, responses, strict=False):
                if isinstance(resp, Exception):
                    logger.error("crawl_error", source=src, error=str(resp))
                    results[src] = []
                else:
                    results[src] = resp  # type: ignore[assignment]
            return results

        return await bundle.uapi.fetch_all()

    # -----------------------------------------------------------------------
    # 深度采集管道
    # -----------------------------------------------------------------------

    async def deep_crawl(
        self,
        platform: Platform | str,
        *,
        mode: CrawlMode | str = CrawlMode.SEARCH,
        keywords: list[str] | None = None,
        content_ids: list[str] | None = None,
        creator_ids: list[str] | None = None,
        max_notes: int = 20,
        enable_comments: bool = True,
        headless: bool = True,
    ) -> dict[str, list]:
        """执行深度采集（通过 MediaCrawler 适配器）.

        Args:
            platform: 目标平台 (xhs/dy/ks/bili/wb/tieba/zhihu)
            mode: 采集模式 (search/detail/creator)
            keywords: 搜索关键词
            content_ids: 内容 ID 列表
            creator_ids: 创作者 ID 列表
            max_notes: 最大采集数
            enable_comments: 是否采集评论
            headless: 无头浏览器

        Returns:
            {"contents": [...], "comments": [...], "creators": [...]}
        """
        from spide.spider.media_crawler_adapter import MediaCrawlerAdapter

        # 类型规范化
        if isinstance(platform, str):
            platform = Platform(platform)
        if isinstance(mode, str):
            mode = CrawlMode(mode)

        adapter = MediaCrawlerAdapter()
        result = await adapter.deep_crawl(
            platform=platform,
            mode=mode,
            keywords=keywords,
            content_ids=content_ids,
            creator_ids=creator_ids,
            max_notes=max_notes,
            enable_comments=enable_comments,
            headless=headless,
        )

        return {
            "contents": result.contents,
            "comments": result.comments,
            "creators": result.creators,
        }

    # -----------------------------------------------------------------------
    # LLM 对话
    # -----------------------------------------------------------------------

    async def chat(self, user_message: str) -> Any:
        """发送用户消息并获取 LLM 回复.

        自动维护消息历史。通过 to_thread 避免阻塞事件循环。
        """
        bundle = self.bundle
        if bundle.llm is None:
            raise SpideError("LLM 客户端未初始化")

        # 追加用户消息
        bundle.messages.append({"role": "user", "content": user_message})

        # 构建完整消息列表（system + 历史）
        full_messages = [
            {"role": "system", "content": bundle.system_prompt},
            *bundle.messages,
        ]

        # 在线程池中执行同步 LLM 调用，避免阻塞事件循环
        response = await asyncio.to_thread(bundle.llm.chat, messages=full_messages)

        # 提取助手回复
        assistant_content = response.choices[0].message.content
        bundle.messages.append({"role": "assistant", "content": assistant_content})

        logger.debug(
            "chat_completed",
            session_id=bundle.session_id,
            messages_count=len(bundle.messages),
        )
        return response

    def chat_stream(self, user_message: str) -> Any:
        """流式发送用户消息.

        返回同步 StreamResponse 迭代器（ZaiClient 限制）。
        流式场景下调用者负责处理迭代，不阻塞 await。
        """
        bundle = self.bundle
        if bundle.llm is None:
            raise SpideError("LLM 客户端未初始化")

        bundle.messages.append({"role": "user", "content": user_message})

        full_messages = [
            {"role": "system", "content": bundle.system_prompt},
            *bundle.messages,
        ]

        return bundle.llm.chat_stream(messages=full_messages)
