"""飞书富文本卡片模板测试."""

from __future__ import annotations

from dashboard.feishu_card import (
    agent_response_card,
    daily_brief_card,
    error_card,
    text_card,
    topics_list_card,
)


def test_text_card_basic() -> None:
    """text_card 包含 header + content。"""
    card = text_card(title="标题", content="内容")
    assert card["msg_type"] == "interactive"
    assert card["card"]["header"]["title"]["content"] == "标题"
    assert card["card"]["elements"][0]["text"]["content"] == "内容"
    assert "footer" in str(card) or "SpideHarness" in str(card)


def test_text_card_template_red() -> None:
    """text_card 红色模板（用于告警）。"""
    card = text_card(title="紧急", content="服务降级", template="red")
    assert card["card"]["header"]["template"] == "red"


def test_error_card() -> None:
    """error_card 红色 + 错误前缀。"""
    card = error_card(title="采集失败", error="UAPI 超时")
    assert card["card"]["header"]["template"] == "red"
    assert "❌" in card["card"]["header"]["title"]["content"]
    assert "UAPI 超时" in card["card"]["elements"][0]["text"]["content"]


def test_topics_list_card_with_data() -> None:
    """topics_list_card 渲染话题列表。"""
    items = [
        {"rank": 1, "title": "AI 革命", "hot_value": 100000, "url": "https://example.com/1"},
        {"rank": 2, "title": "中美关系", "hot_value": 50000},
    ]
    card = topics_list_card(title="今日热搜", source="weibo", items=items)
    body = card["card"]["elements"][0]["text"]["content"]
    assert "AI 革命" in body
    assert "中美关系" in body
    assert "weibo" in body
    assert "1." in body
    assert "2." in body


def test_topics_list_card_empty() -> None:
    """topics_list_card 空数据降级。"""
    card = topics_list_card(title="今日热搜", source="weibo", items=[])
    body = card["card"]["elements"][0]["text"]["content"]
    assert "暂无数据" in body


def test_topics_list_card_truncate_long_title() -> None:
    """topics_list_card 截断超长标题。"""
    long_title = "A" * 200
    items = [{"rank": 1, "title": long_title, "hot_value": 100}]
    card = topics_list_card(title="test", source="weibo", items=items)
    body = card["card"]["elements"][0]["text"]["content"]
    # 80 字符截断
    assert "A" * 80 in body
    assert "A" * 81 not in body


def test_agent_response_card_with_trace() -> None:
    """agent_response_card 含工具调用轨迹。"""
    tool_calls = [
        {"name": "crawl_hot_topics", "arguments": {"source": "weibo"}, "summary": "ok: count=20"},
    ]
    card = agent_response_card(answer="已采集微博热搜", tool_calls=tool_calls, iterations=2)
    body = str(card)
    assert "已采集微博热搜" in body
    assert "crawl_hot_topics" in body
    assert "迭代 2" in body


def test_agent_response_card_no_trace() -> None:
    """agent_response_card 无工具调用时不含轨迹。"""
    card = agent_response_card(answer="你好")
    body = str(card)
    assert "工具调用轨迹" not in body
    assert "你好" in body


def test_daily_brief_card() -> None:
    """daily_brief_card 多分区。"""
    sections = [
        {"title": "AI 话题", "content": "AI Agent 关注度上升"},
        {"title": "财经话题", "content": "股市震荡"},
    ]
    card = daily_brief_card(title="今日简报", sections=sections)
    body = str(card)
    assert "AI 话题" in body
    assert "财经话题" in body
    assert "今日简报" in body
