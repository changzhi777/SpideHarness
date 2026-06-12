"""会话存储测试（SQLite 多轮记忆）."""

from __future__ import annotations

from dashboard.conversation_store import (
    ChatMessage,
    ConversationStore,
    get_conversation_store,
    reset_conversation_store,
)


async def test_init_creates_tables(tmp_db) -> None:
    """init() 创建 chat_sessions + chat_messages 表。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    import aiosqlite

    async with aiosqlite.connect(str(tmp_db)) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cur:
            rows = await cur.fetchall()
        table_names = {r[0] for r in rows}
    assert "chat_sessions" in table_names
    assert "chat_messages" in table_names


def test_make_session_id_stable() -> None:
    """同一 user/chat 生成稳定的 session_id。"""
    sid1 = ConversationStore.make_session_id("u1", "c1")
    sid2 = ConversationStore.make_session_id("u1", "c1")
    assert sid1 == sid2
    assert sid1 == "c1:u1"


def test_make_session_id_different() -> None:
    """不同 user/chat 生成不同 session_id。"""
    assert ConversationStore.make_session_id("u1", "c1") != ConversationStore.make_session_id(
        "u2", "c1"
    )
    assert ConversationStore.make_session_id("u1", "c1") != ConversationStore.make_session_id(
        "u1", "c2"
    )


async def test_get_or_create_session_new(tmp_db) -> None:
    """新会话：创建并返回 session_id。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    sid = await store.get_or_create_session("u1", "c1")
    assert sid == "c1:u1"
    # 二次调用应返回相同 id（不创建新行）
    sid2 = await store.get_or_create_session("u1", "c1")
    assert sid == sid2


async def test_append_message(tmp_db) -> None:
    """追加消息到会话。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    sid = await store.get_or_create_session("u1", "c1")
    await store.append_message(sid, ChatMessage(role="user", content="你好"))
    await store.append_message(sid, ChatMessage(role="assistant", content="你好！有什么可以帮您？"))
    history = await store.get_history(sid)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


async def test_get_history_limit(tmp_db) -> None:
    """limit 参数限制返回数量。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    sid = await store.get_or_create_session("u1", "c1")
    for i in range(10):
        await store.append_message(sid, ChatMessage(role="user", content=f"msg{i}"))
    history = await store.get_history(sid, limit=3)
    assert len(history) == 3
    # 按时间正序，最新 3 条
    assert history[-1]["content"] == "msg9"


async def test_get_history_with_tool_calls(tmp_db) -> None:
    """含 tool_calls 的消息完整序列化。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    sid = await store.get_or_create_session("u1", "c1")
    await store.append_message(
        sid,
        ChatMessage(
            role="assistant",
            content="",
            tool_calls=[
                {"name": "crawl_hot_topics", "arguments": {"source": "weibo"}, "id": "call_1"}
            ],
        ),
    )
    history = await store.get_history(sid)
    assert history[0]["tool_calls"][0]["name"] == "crawl_hot_topics"


async def test_clear_session(tmp_db) -> None:
    """清空会话历史但保留 session 元信息。"""
    store = ConversationStore(db_path=tmp_db)
    await store.init()
    sid = await store.get_or_create_session("u1", "c1")
    await store.append_message(sid, ChatMessage(role="user", content="test"))
    deleted = await store.clear_session(sid)
    assert deleted == 1
    history = await store.get_history(sid)
    assert history == []
    # 重新插入应仍可用
    await store.append_message(sid, ChatMessage(role="user", content="new"))
    assert len(await store.get_history(sid)) == 1


async def test_singleton(tmp_db) -> None:
    """get_conversation_store 返回单例。"""
    reset_conversation_store()
    s1 = get_conversation_store(db_path=tmp_db)
    s2 = get_conversation_store(db_path=tmp_db)
    assert s1 is s2
    reset_conversation_store()
