"""飞书富文本卡片模板（Interactive Message Card v2）。

参考：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/feishu-cards/
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def text_card(title: str, content: str, template: str = "blue") -> dict[str, Any]:
    """纯文本卡片。"""
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                _footer_element(),
            ],
        },
    }


def error_card(title: str, error: str) -> dict[str, Any]:
    """错误提示卡片。"""
    return text_card(title=f"❌ {title}", content=f"**错误**：{error}", template="red")


def topics_list_card(
    title: str,
    source: str,
    items: list[dict[str, Any]],
    show_rank: bool = True,
) -> dict[str, Any]:
    """热搜列表卡片。

    Args:
        title: 卡片标题
        source: 平台标识
        items: 话题列表 [{rank, title, hot_value, url?}, ...]
        show_rank: 是否显示排名前缀
    """
    if not items:
        return text_card(title=title, content="*暂无数据*", template="grey")

    lines: list[str] = [f"**平台**: `{source}` | **数量**: {len(items)}", ""]
    for i, t in enumerate(items[:20], 1):
        rank = t.get("rank", i)
        topic = str(t.get("title", "")).replace("\n", " ")[:80]
        hot = t.get("hot_value", 0)
        url = t.get("url", "")
        prefix = f"**{rank}.**" if show_rank else "•"
        hot_str = f" 🔥{_fmt_hot(hot)}" if hot else ""
        if url:
            lines.append(f"{prefix} [{topic}]({url}){hot_str}")
        else:
            lines.append(f"{prefix} {topic}{hot_str}")

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
                _footer_element(),
            ],
        },
    }


def agent_response_card(
    answer: str,
    tool_calls: list[dict[str, Any]] | None = None,
    iterations: int = 0,
) -> dict[str, Any]:
    """Agent 响应卡片（拟人化风格）。

    UI 隐藏 call_id / 迭代次数等机械标识。
    仅以温和的方式提示每一步的处理进度 + 任务短码（#xxx）。
    数据库（chat_messages.tool_calls）保留完整 call_id 用于追踪。
    """
    elements: list[dict[str, Any]] = [
        {"tag": "div", "text": {"tag": "lark_md", "content": answer or "我这边暂时没有合适的回答，稍后再试？😊"}},
    ]

    if tool_calls:
        progress_lines = ["**处理进度**"]
        for tc in tool_calls:
            short_id = tc.get("task_id_short", "000")
            friendly = tc.get("friendly_action") or "已为您处理"
            progress_lines.append(f"- {friendly} · 任务 #{short_id}")
        elements.append({"tag": "hr"})
        elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(progress_lines)}}
        )

    elements.append(_footer_element())

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "青沐信息官"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def daily_brief_card(
    title: str,
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    """每日简报卡片。

    Args:
        sections: [{title, content, color?}, ...]
    """
    elements: list[dict[str, Any]] = []
    for i, sec in enumerate(sections):
        if i > 0:
            elements.append({"tag": "hr"})
        sec_title = sec.get("title", "")
        sec_content = sec.get("content", "")
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{sec_title}**\n\n{sec_content}",
                },
            }
        )
    elements.append(_footer_element())

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def _footer_element() -> dict[str, Any]:
    """卡片底部脚注。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"青沐信息官 · SpideHarness V3.1.1 | {ts}",
            }
        ],
    }


def _fmt_hot(value: Any) -> str:
    """格式化热度值（千分位 / 万 / 亿）。"""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    if n >= 1e8:
        return f"{n / 1e8:.1f}亿"
    if n >= 1e4:
        return f"{n / 1e4:.1f}万"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return f"{int(n)}"
