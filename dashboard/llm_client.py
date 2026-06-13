"""OpenAI 兼容 LLM 客户端（本地 Gemma 3 4B / vLLM / Ollama）。

支持：
- Chat Completion（流式 + 非流式）
- Function Calling（tools 参数）
- JSON Action 兜底（弱模型不支持 tools 时降级为提示词工程）
- 启动健康检查 + 自动降级
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置。"""

    base_url: str = "http://localhost:8001"
    model: str = "google/gemma-3-4b-it"
    api_key: str = "EMPTY"  # 本地服务通常不需要
    timeout: int = 60
    max_tokens: int = 2048
    temperature: float = 0.7
    supports_function_calling: bool = False  # Gemma 3 4B 弱，默认关


@dataclass
class ToolCall:
    """LLM 返回的工具调用。"""

    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class LLMResponse:
    """统一 LLM 响应结构。"""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """OpenAI 兼容客户端（异步）。"""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._healthy: bool | None = None

    async def health_check(self) -> bool:
        """检查 LLM 服务是否可用。"""
        url = f"{self.config.base_url.rstrip('/')}/v1/models"
        headers = {"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {}
        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
                session.get(url, headers=headers) as resp,
            ):
                self._healthy = resp.status == 200
                if self._healthy:
                    logger.info(
                        "llm_healthy",
                        base_url=self.config.base_url,
                        model=self.config.model,
                    )
                else:
                    logger.warning("llm_unhealthy", status=resp.status)
                return self._healthy
        except Exception as exc:
            self._healthy = False
            logger.warning("llm_unreachable", error=str(exc))
            return False

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """调用 chat completion。

        Args:
            messages: OpenAI 格式消息列表
            tools: 可选 tools（function calling schema）
            temperature: 覆盖默认温度

        Returns:
            LLMResponse: 统一响应
        """
        url = f"{self.config.base_url.rstrip('/')}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if tools and self.config.supports_function_calling:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as session,
                session.post(url, json=payload, headers=headers) as resp,
            ):
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("llm_http_error", status=resp.status, body=text[:500])
                    return LLMResponse(content=f"[LLM 错误 {resp.status}]", finish_reason="error")
                data = await resp.json()
                return self._parse_response(data)
        except Exception as exc:
            logger.error("llm_request_failed", error=str(exc))
            return LLMResponse(content=f"[LLM 请求失败: {exc}]", finish_reason="error")

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """解析 OpenAI 兼容响应。"""
        choices = data.get("choices") or []
        if not choices:
            return LLMResponse(raw=data, finish_reason="empty")

        choice = choices[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args_raw = fn.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    name=fn.get("name", ""),
                    arguments=args,
                    call_id=tc.get("id", ""),
                )
            )

        # JSON Action 兜底：解析 content 中的 ```json ... ``` 块
        if not tool_calls and content:
            tool_calls = self._extract_json_action(content)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            raw=data,
        )

    @staticmethod
    def _extract_json_action(content: str) -> list[ToolCall]:
        """从文本中提取 JSON Action（兜底）。

        识别格式：
        ```json
        {"action": "tool_name", "arguments": {...}}
        ```
        """
        import re

        pattern = r"```json\s*(\{.*?\})\s*```"
        matches = re.findall(pattern, content, re.DOTALL)
        tool_calls: list[ToolCall] = []
        for raw in matches:
            try:
                obj = json.loads(raw)
                action = obj.get("action") or obj.get("tool") or obj.get("name")
                args = obj.get("arguments") or obj.get("args") or obj.get("params") or {}
                if action:
                    tool_calls.append(ToolCall(name=action, arguments=args))
            except json.JSONDecodeError:
                continue
        return tool_calls


_client: LLMClient | None = None


def load_llm_config_from_yaml(config_path: str = "configs/feishu.yaml") -> LLMConfig | None:
    """从 configs/feishu.yaml 加载 LLM 配置（llm 节）。

    Returns:
        LLMConfig 实例;文件不存在或 llm 节缺失时返回 None
    """
    from pathlib import Path

    import yaml

    path = Path(config_path)
    if not path.exists():
        return None

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 解析 ${ENV_VAR[:default]} 占位符
    from .secrets import resolve_secrets_in_obj

    data = cast(dict[str, Any], resolve_secrets_in_obj(data))
    llm_data = data.get("llm")
    if not llm_data or not isinstance(llm_data, dict):
        return None

    # 映射 feishu.yaml 的 llm 节 → LLMConfig
    return LLMConfig(
        base_url=llm_data.get("base_url", "http://localhost:8001"),
        model=llm_data.get("model", "google/gemma-3-4b-it"),
        api_key=llm_data.get("api_key", "EMPTY"),
        timeout=int(llm_data.get("timeout", 60)),
        max_tokens=int(llm_data.get("max_tokens", 2048)),
        temperature=float(llm_data.get("temperature", 0.7)),
        supports_function_calling=bool(llm_data.get("supports_function_calling", False)),
    )


def get_llm_client(config: LLMConfig | None = None) -> LLMClient:
    """获取全局 LLM 客户端单例。

    优先级:
    1. 显式传入的 config
    2. configs/feishu.yaml 中的 llm 节
    3. 默认 LLMConfig()
    """
    global _client
    if _client is None:
        if config is None:
            config = load_llm_config_from_yaml() or LLMConfig()
        _client = LLMClient(config)
    return _client


def reset_llm_client() -> None:
    """重置客户端（测试用）。"""
    global _client
    _client = None
