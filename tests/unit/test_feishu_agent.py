"""飞书智能体测试（ReAct 循环 + 多轮记忆 + LLM 降级）."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from dashboard.conversation_store import ConversationStore
from dashboard.feishu_agent import (
    AgentConfig,
    FeishuAgent,
    get_feishu_agent,
    reset_feishu_agent,
)
from dashboard.llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall


def make_llm_client(responses: list[LLMResponse]) -> MagicMock:
    """构造 mock LLM 客户端（按顺序返回响应）。"""
    mock = MagicMock(spec=LLMClient)
    mock.config = LLMConfig()
    mock._healthy = True
    mock.chat = AsyncMock(side_effect=responses)
    mock.health_check = AsyncMock(return_value=True)
    return mock


async def test_agent_no_tool_call_returns_text(tmp_db) -> None:
    """LLM 直接返回文本（无工具调用）时直接返回。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    llm = make_llm_client([LLMResponse(content="你好！有什么可以帮您？", finish_reason="stop")])
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    result = await agent.chat(user_message="你好", user_id="u1", chat_id="c1")
    assert result.status == "ok"
    assert "你好" in result.answer
    assert result.iterations == 1
    assert result.tool_calls == []


async def test_agent_with_tool_call(tmp_db) -> None:
    """LLM 返回工具调用 → 执行工具 → LLM 生成最终回复。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    responses = [
        LLMResponse(
            content="",
            finish_reason="tool_calls",
            tool_calls=[ToolCall(name="health_check", arguments={}, call_id="call_1")],
        ),
        LLMResponse(content="服务运行正常。", finish_reason="stop"),
    ]
    llm = make_llm_client(responses)
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    result = await agent.chat(user_message="健康检查", user_id="u1", chat_id="c1")
    assert result.status == "ok"
    assert "正常" in result.answer
    assert result.iterations == 2
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "health_check"


async def test_agent_max_iterations(tmp_db) -> None:
    """持续工具调用达到 max_iterations 时停止。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    responses = [
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[ToolCall(name="health_check", arguments={}, call_id=f"call_{i}")],
        )
        for i in range(10)
    ]
    llm = make_llm_client(responses)
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig(max_iterations=3))

    result = await agent.chat(user_message="测试", user_id="u1", chat_id="c1")
    assert result.status == "max_iter"
    assert result.iterations == 3
    assert len(result.tool_calls) == 3


async def test_agent_fallback_when_llm_down(tmp_db) -> None:
    """LLM 不可用时降级为关键词匹配。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    llm = MagicMock(spec=LLMClient)
    llm.config = LLMConfig()
    llm._healthy = False
    llm.health_check = AsyncMock(return_value=False)

    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())
    result = await agent.chat(user_message="help", user_id="u1", chat_id="c1")
    assert result.status == "llm_down"
    assert "指令" in result.answer


async def test_agent_fallback_unknown_message(tmp_db) -> None:
    """LLM 不可用 + 非指令消息 → 返回降级提示。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    llm = MagicMock(spec=LLMClient)
    llm.config = LLMConfig()
    llm._healthy = False
    llm.health_check = AsyncMock(return_value=False)

    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())
    result = await agent.chat(user_message="请问今天天气如何？", user_id="u1", chat_id="c1")
    assert result.status == "llm_down"
    assert "降级" in result.answer


async def test_agent_clear_session(tmp_db) -> None:
    """清空会话历史。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    llm = make_llm_client([LLMResponse(content="ok", finish_reason="stop")])
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    await agent.chat(user_message="test", user_id="u1", chat_id="c1")
    deleted = await agent.clear_session("u1", "c1")
    assert deleted >= 1  # user + assistant 至少 1 条
    history = await store.get_history(store.make_session_id("u1", "c1"))
    assert history == []


async def test_agent_singleton() -> None:
    """get_feishu_agent 返回单例。"""
    reset_feishu_agent()
    a1 = get_feishu_agent()
    a2 = get_feishu_agent()
    assert a1 is a2
    reset_feishu_agent()


async def test_agent_llm_error_response(tmp_db) -> None:
    """LLM 响应 finish_reason=error 时返回错误。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    responses = [LLMResponse(content="服务异常", finish_reason="error")]
    llm = make_llm_client(responses)
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    result = await agent.chat(user_message="test", user_id="u1", chat_id="c1")
    assert result.status == "error"
    assert "异常" in result.answer
