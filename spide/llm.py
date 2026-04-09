# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""LLM 集成层 — ZaiClient 封装，chat completions + web search 统一接口.

用法:
    from spide.llm import LLMClient
    from spide.config import load_settings

    settings = load_settings()
    client = LLMClient(settings.llm)
    await client.start()

    # 文本对话
    response = await client.chat(messages=[{"role": "user", "content": "你好"}])

    # 流式对话
    async for chunk in client.chat_stream(messages=[...]):
        print(chunk, end="")

    # 联网搜索
    results = await client.web_search(query="今日微博热搜")

    await client.stop()
"""

from __future__ import annotations

from typing import Any

from zai import ZaiClient

from spide.config import LLMConfig
from spide.exceptions import LLMError
from spide.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """LLM 统一客户端 — 封装 ZaiClient."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client: ZaiClient | None = None

    async def start(self) -> None:
        """初始化 ZaiClient."""
        api_key = self._config.common.api_key
        if not api_key:
            raise LLMError("LLM API Key 未配置")

        self._client = ZaiClient(
            api_key=api_key,
            base_url=self._config.common.base_url,
        )
        logger.debug("llm_client_initialized", model=self._config.text.model)

    async def stop(self) -> None:
        """关闭客户端."""
        if self._client:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> ZaiClient:
        """检查客户端状态."""
        if self._client is None:
            raise LLMError("LLM 客户端未初始化，请先调用 start()")
        return self._client

    # -----------------------------------------------------------------------
    # 文本对话
    # -----------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Any:
        """同步文本对话（非流式返回完整响应）."""
        client = self._ensure_client()
        try:
            params = self._build_chat_params(
                messages, model, temperature, max_tokens, tools, **kwargs
            )
            return client.chat.completions.create(**params)
        except Exception as e:
            raise LLMError(f"LLM 请求失败: {e}") from e

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Any:
        """流式文本对话（返回 StreamResponse 迭代器）."""
        client = self._ensure_client()
        try:
            params = self._build_chat_params(
                messages, model, temperature, max_tokens, tools, stream=True, **kwargs
            )
            return client.chat.completions.create(**params)
        except Exception as e:
            raise LLMError(f"LLM 流式请求失败: {e}") from e

    # -----------------------------------------------------------------------
    # 联网搜索
    # -----------------------------------------------------------------------

    def web_search(
        self,
        query: str,
        *,
        search_engine: str | None = None,
        count: int | None = None,
        content_size: str | None = None,
        search_recency_filter: str | None = None,
    ) -> Any:
        """联网搜索 — 智谱 Web Search API."""
        client = self._ensure_client()
        ws_config = self._config.web_search
        try:
            result = client.web_search.web_search(
                search_query=query,
                search_engine=search_engine or ws_config.engine,
                count=count or ws_config.default_count,
                content_size=content_size or ws_config.content_size,
                search_recency_filter=search_recency_filter or ws_config.recency_filter,
            )
            logger.debug("web_search_done", query=query)
            return result
        except Exception as e:
            raise LLMError(f"联网搜索失败: {e}") from e

    # -----------------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------------

    def _build_chat_params(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """构建 chat completions 请求参数."""
        text_config = self._config.text
        params: dict[str, Any] = {
            "model": model or text_config.model,
            "messages": messages,
            "stream": stream,
        }

        if temperature is not None:
            params["temperature"] = temperature
        elif text_config.temperature != 1.0:
            params["temperature"] = text_config.temperature

        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        elif text_config.max_tokens != 65536:
            params["max_tokens"] = text_config.max_tokens

        if tools:
            params["tools"] = tools

        # 思考模式
        if text_config.thinking_type:
            params["thinking"] = {"type": text_config.thinking_type}

        params.update(kwargs)
        return params
