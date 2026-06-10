"""飞书智能体核心 — ReAct 循环 Agent。

工作流程：
1. 加载会话历史
2. 拼接 system_prompt + history + user_message
3. 调用 LLM（带 tools 或 JSON Action 兜底）
4. 若返回 tool_calls：执行工具 → 追加结果 → 回 LLM（最多 max_iterations 次）
5. 返回最终文本 + 工具调用轨迹

特点：
- 多轮上下文记忆（SQLite 持久化）
- 工具调用超时保护
- 单次迭代防死循环
- LLM 不可用时降级为关键词匹配
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from .conversation_store import ChatMessage, ConversationStore, get_conversation_store
from .llm_client import LLMClient, LLMConfig, get_llm_client
from .tool_router import call_tool, format_tool_result, get_tool_schemas

logger = structlog.get_logger(__name__)


def _short_task_id(call_id: str, tool_name: str) -> str:
    """生成 3 位短任务标识（UI 友好，DB 保留完整 ID）。

    优先取 call_id 后 3 位；空 call_id 时从 tool_name 生成稳定 hash 后 3 位。
    """
    import hashlib

    if call_id:
        return call_id[-3:]
    h = hashlib.md5(tool_name.encode("utf-8")).hexdigest()
    return h[-3:]


def _friendly_action(tool_name: str, result: dict[str, Any]) -> str:
    """生成人类友好的动作描述（用于 UI 显示）。"""
    if result.get("status") == "error":
        return f"尝试获取 {tool_name} 时遇到问题"

    count = result.get("count")
    source = result.get("source", "")

    actions: dict[str, str] = {
        "crawl_hot_topics": f"已为您采集{source or ''}热搜{count or ''}条".rstrip("已为您采集"),
        "web_search": f"为您检索了 {count or '相关'} 条结果",
        "web_search_enhanced": f"为您检索了 {count or '相关'} 条结果",
        "fetch_web_page": "已获取网页内容",
        "fetch_repo_info": "已获取仓库信息",
        "manage_memory": "已更新记忆",
        "health_check": "已完成健康检查",
        "deep_crawl_hot_topics": f"已为您深度采集{count or ''}条内容".rstrip("已为您深度采集"),
    }
    return actions.get(tool_name, "处理完成")


DEFAULT_SYSTEM_PROMPT = """你是 SpideHarness 飞书智能助手。

你的能力：
- 采集热搜（微博/百度/抖音/知乎/B站）
- 联网搜索（智谱/DuckDuckGo）
- 抓取网页 / GitHub 仓库信息
- 深度采集（小红书/抖音/快手/B站/微博/贴吧/知乎）
- 管理记忆、检查健康状态

工具调用规则：
- 若需要执行操作，输出 JSON Action：```json
{"action": "工具名", "arguments": {...}}
```
- 若只需回答，直接输出文本
- 同一轮最多调用 1 个工具

回答风格：像一位专业、亲切的同事，自然流畅、中文表达。"""


@dataclass
class AgentConfig:
    """Agent 配置。"""

    max_iterations: int = 5
    max_history: int = 20
    step_timeout: int = 30
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


@dataclass
class AgentResult:
    """Agent 执行结果。"""

    answer: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    status: str = "ok"  # ok / error / max_iter / llm_down
    error: str | None = None


class FeishuAgent:
    """ReAct 循环 Agent。"""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        store: ConversationStore | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.llm = llm_client or get_llm_client()
        self.store = store or get_conversation_store()
        self.config = config or AgentConfig()

    async def init(self) -> None:
        """初始化会话存储 + 检查 LLM 可用性。"""
        await self.store.init()
        await self.llm.health_check()

    async def chat(
        self,
        user_message: str,
        user_id: str,
        chat_id: str,
    ) -> AgentResult:
        """处理用户消息（一次完整 ReAct 循环）。"""
        # LLM 不可用：降级为关键词匹配
        if self.llm._healthy is False:
            return await self._fallback_keyword(user_message)

        session_id = await self.store.get_or_create_session(user_id, chat_id)
        await self.store.append_message(
            session_id, ChatMessage(role="user", content=user_message)
        )

        history = await self.store.get_history(session_id, limit=self.config.max_history)
        messages = self._build_messages(history)

        tool_trace: list[dict[str, Any]] = []
        final_answer = ""

        for iteration in range(1, self.config.max_iterations + 1):
            tools = (
                get_tool_schemas() if self.llm.config.supports_function_calling else None
            )
            response = await self.llm.chat(messages=messages, tools=tools)

            if response.finish_reason == "error":
                logger.error("agent_llm_error", iteration=iteration)
                return AgentResult(
                    answer=response.content or "LLM 调用失败",
                    status="error",
                    error=response.content,
                    iterations=iteration,
                )

            # 无工具调用：返回最终答案
            if not response.tool_calls:
                final_answer = response.content or "（无响应）"
                await self.store.append_message(
                    session_id, ChatMessage(role="assistant", content=final_answer)
                )
                return AgentResult(
                    answer=final_answer,
                    tool_calls=tool_trace,
                    iterations=iteration,
                    status="ok",
                )

            # 执行工具调用（最多 1 个/轮）
            tc = response.tool_calls[0]
            logger.info("agent_tool_call", iteration=iteration, tool=tc.name)

            tool_result = await call_tool(tc.name, tc.arguments, timeout=self.config.step_timeout)
            result_text = format_tool_result(tc.name, tool_result)

            tool_trace.append(
                {
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "summary": tool_result.get("status", "?")
                    + ": "
                    + (
                        tool_result.get("message")
                        or f"count={tool_result.get('count', '?')}"
                    ),
                    "task_id_short": _short_task_id(tc.call_id, tc.name),
                    "friendly_action": _friendly_action(tc.name, tool_result),
                }
            )

            # 追加 assistant + tool 消息到上下文 + 持久化
            assistant_content = response.content or f"调用工具 {tc.name}"
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": f"[工具 {tc.name} 返回]\n{result_text}"})

            await self.store.append_message(
                session_id,
                ChatMessage(
                    role="assistant",
                    content=assistant_content,
                    tool_calls=[
                        {"name": tc.name, "arguments": tc.arguments, "id": tc.call_id}
                    ],
                ),
            )
            await self.store.append_message(
                session_id,
                ChatMessage(
                    role="tool",
                    content=result_text,
                    tool_call_id=tc.call_id,
                    name=tc.name,
                ),
            )

        # 超过最大迭代次数
        logger.warning("agent_max_iterations", iterations=self.config.max_iterations)
        return AgentResult(
            answer=final_answer or "已达最大迭代次数，未能给出最终答案",
            tool_calls=tool_trace,
            iterations=self.config.max_iterations,
            status="max_iter",
        )

    def _build_messages(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """构建 OpenAI 格式消息列表（system + history）。"""
        return [{"role": "system", "content": self.config.system_prompt}, *history]

    async def _fallback_keyword(self, text: str) -> AgentResult:
        """LLM 不可用时的降级：关键词匹配 → 直接调用工具。"""
        from .feishu_handler import execute_command, parse_command

        logger.info("agent_fallback_keyword", text=text[:50])
        parsed = parse_command(text)
        if not parsed:
            return AgentResult(
                answer=(
                    "⚠️ LLM 服务不可用，已降级为关键词模式。\n"
                    "请使用指令：`crawl <平台>` / `analyze <平台>` / `status` / `help`"
                ),
                status="llm_down",
            )

        cmd, args = parsed
        result = await execute_command(cmd, args)
        return AgentResult(
            answer=result.get("output") or result.get("message", ""),
            status="llm_down",
            tool_calls=[{"name": cmd, "arguments": args, "summary": result.get("status", "?")}],
        )

    async def clear_session(self, user_id: str, chat_id: str) -> int:
        """清空会话历史。"""
        session_id = self.store.make_session_id(user_id, chat_id)
        return await self.store.clear_session(session_id)


_agent: FeishuAgent | None = None


def get_feishu_agent(
    llm_config: LLMConfig | None = None,
    agent_config: AgentConfig | None = None,
) -> FeishuAgent:
    """获取全局 Agent 单例。"""
    global _agent
    if _agent is None:
        llm = get_llm_client(llm_config)
        _agent = FeishuAgent(llm_client=llm, config=agent_config)
    return _agent


def reset_feishu_agent() -> None:
    """重置 Agent（测试用）。"""
    global _agent
    _agent = None
