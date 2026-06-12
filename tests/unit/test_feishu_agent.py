"""飞书智能体测试（ReAct 循环 + 多轮记忆 + LLM 降级）."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from dashboard.conversation_store import ConversationStore
from dashboard.feishu_agent import (
    AgentConfig,
    FeishuAgent,
    _friendly_action,
    _short_task_id,
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


async def test_agent_singleton(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """get_feishu_agent 返回单例。"""
    # 切到无 feishu.yaml 的目录,避免解析 ${ENV_VAR} 占位符
    monkeypatch.chdir(tmp_path)
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


# ── 辅助函数测试 ──────────────────────────────────────────────────


def test_short_task_id_from_call_id() -> None:
    """_short_task_id 取 call_id 后 3 位。"""
    assert _short_task_id("call_abc123def456", "any") == "456"
    assert _short_task_id("xyz", "any") == "xyz"
    assert _short_task_id("", "any") != "any"  # 空时回退到 tool_name hash


def test_short_task_id_fallback_to_hash() -> None:
    """空 call_id 时从 tool_name 生成稳定 hash 后 3 位。"""
    id1 = _short_task_id("", "crawl_hot_topics")
    id2 = _short_task_id("", "crawl_hot_topics")
    assert id1 == id2  # 稳定
    assert len(id1) == 3
    # 不同工具名不同
    assert _short_task_id("", "web_search") != id1


def test_friendly_action_success() -> None:
    """_friendly_action 成功时返回人类友好描述。"""
    assert "微博" in _friendly_action(
        "crawl_hot_topics", {"status": "ok", "source": "微博", "count": 10}
    )
    assert "10" in _friendly_action(
        "crawl_hot_topics", {"status": "ok", "source": "weibo", "count": 10}
    )
    assert _friendly_action("health_check", {"status": "ok"})  # 非空
    assert _friendly_action("unknown_tool", {"status": "ok"})  # 未知工具也有兜底


def test_friendly_action_error() -> None:
    """_friendly_action 错误时返回温和描述。"""
    msg = _friendly_action("crawl_hot_topics", {"status": "error", "message": "X"})
    assert "遇到问题" in msg or "尝试" in msg


async def test_agent_tool_trace_includes_short_id(tmp_db) -> None:
    """Agent 工具调用轨迹包含 task_id_short（UI 友好）。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    responses = [
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[ToolCall(name="health_check", arguments={}, call_id="call_full_xxx")],
        ),
        LLMResponse(content="运行正常", finish_reason="stop"),
    ]
    llm = make_llm_client(responses)
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    result = await agent.chat(user_message="检查", user_id="u1", chat_id="c1")
    assert len(result.tool_calls) == 1
    trace = result.tool_calls[0]
    # UI 字段
    assert "task_id_short" in trace
    assert trace["task_id_short"] == "xxx"  # call_id 后 3 位
    assert "friendly_action" in trace
    assert "友好" in trace["friendly_action"] or "完成" in trace["friendly_action"]


async def test_agent_persists_full_call_id(tmp_db) -> None:
    """数据库 chat_messages 仍保留完整 call_id（用于追踪）。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()

    full_id = "call_abc123def456789"
    responses = [
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[ToolCall(name="health_check", arguments={}, call_id=full_id)],
        ),
        LLMResponse(content="OK", finish_reason="stop"),
    ]
    llm = make_llm_client(responses)
    agent = FeishuAgent(llm_client=llm, store=store, config=AgentConfig())

    await agent.chat(user_message="check", user_id="u1", chat_id="c1")

    # 数据库中应保留完整 call_id
    session_id = store.make_session_id("u1", "c1")
    history = await store.get_history(session_id)
    # 找 assistant 消息（含 tool_calls）
    assistant_msgs = [m for m in history if m["role"] == "assistant" and m.get("tool_calls")]
    assert len(assistant_msgs) >= 1
    stored_id = assistant_msgs[0]["tool_calls"][0]["id"]
    assert stored_id == full_id  # 完整 ID 未截断
