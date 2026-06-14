# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""视频文章 pipeline — 飞书消息 URL → 元数据 → LLM 摘要 → Thoth 笔记.

任务 2-A 阶段实现（V3.1.5+）：
- 飞书消息文本中提取 URL
- 每个 URL 抓 OG 元数据
- GLM-5.1 生成 200 字摘要
- ThothClient.create_note 保存

Usage:
    from spide.integrations.video_pipeline import process_urls

    count = await process_urls(
        text="看这个视频 https://example.com/article/123",
        user_id="user_abc",
        max_urls=3,
    )
    # → count = 1（已保存到 Thoth）
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from spide.config import ThothConfig, load_settings
from spide.integrations.thoth_client import ThothClient
from spide.integrations.url_metadata import fetch as fetch_metadata
from spide.logging import get_logger

logger = get_logger(__name__)

# URL 正则（http/https，常见边界字符）
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\\)\]【】]+",
    re.IGNORECASE,
)
_DEFAULT_MAX_URLS = 3
_LLM_PROMPT_TEMPLATE = """你是一个专业的内容摘要助手。请基于以下网页元数据生成 200 字以内的中文摘要。

标题: {title}
来源: {site_name}
URL: {url}
描述: {description}

要求：
- 直接输出摘要，不要前缀
- 提炼核心信息，删除营销废话
- 100-200 字
"""


def extract_urls(text: str, *, max_urls: int = _DEFAULT_MAX_URLS) -> list[str]:
    """从文本中提取最多 max_urls 个 HTTP/HTTPS URL.

    去重 + 保留出现顺序。
    """
    if not text:
        return []
    # 尾随标点（含中英文括号 + 引号）
    _TRAILING_PUNCT = ".,;:!?()）]】」』'\" "
    seen: set[str] = set()
    result: list[str] = []
    for m in _URL_PATTERN.finditer(text):
        url = m.group(0).rstrip(_TRAILING_PUNCT)
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)
        if len(result) >= max_urls:
            break
    return result


async def process_urls(
    text: str,
    user_id: str = "",
    *,
    max_urls: int = _DEFAULT_MAX_URLS,
) -> int:
    """处理文本中的 URL 列表：抓元数据 → LLM 摘要 → 存 Thoth.

    Args:
        text: 飞书消息文本（可能含 URL）
        user_id: 飞书用户 ID（用于日志）
        max_urls: 最多处理的 URL 数（防 LLM 过载）

    Returns:
        成功保存的笔记数（失败 URL 不计入）
    """
    urls = extract_urls(text, max_urls=max_urls)
    if not urls:
        return 0

    logger.info("video_pipeline_start", user_id=user_id, url_count=len(urls))

    # 一次性加载配置（避免 per-URL 重复 IO）
    thoth_config = _load_thoth_config()
    if not thoth_config.token:
        logger.warning(
            "video_pipeline_thoth_token_missing_global", url_count=len(urls)
        )
        return 0

    saved = 0
    for url in urls:
        try:
            ok = await _process_single_url(
                url, user_id, thoth_config, thoth_config.default_room_id
            )
            if ok:
                saved += 1
        except Exception as e:
            logger.warning(
                "video_pipeline_url_failed", url=url, error=str(e)
            )
            # per-URL 失败不影响其他

    logger.info("video_pipeline_done", user_id=user_id, saved=saved, total=len(urls))
    return saved


async def _process_single_url(
    url: str, user_id: str, thoth_config: ThothConfig, room_id: str
) -> bool:
    """处理单个 URL：抓元数据 → LLM 摘要 → 存 Thoth.

    失败时返回 False（不抛异常），由 caller 决定是否继续。
    """
    # 1. 抓元数据
    meta = await fetch_metadata(url)
    if "error" in meta:
        logger.warning("video_pipeline_metadata_failed", url=url, error=meta["error"])
        return False

    title = meta.get("title", "").strip() or url
    description = meta.get("description", "").strip()
    site_name = meta.get("site_name", "").strip()

    # 2. LLM 摘要
    summary = await _llm_summarize(
        title=title,
        description=description,
        site_name=site_name,
        url=url,
    )

    # 3. 拼 Markdown 内容
    content = _build_markdown(title, summary, meta)

    # 4. 存 Thoth（复用 caller 传入的 config）
    client = ThothClient(thoth_config)
    await client.start()
    try:
        note = await client.create_note(
            title=title,
            content=content,
            tags=_build_tags(site_name, user_id),
            room_id=room_id,
        )
        logger.info(
            "video_pipeline_note_saved",
            url=url,
            note_id=note.get("id"),
            user_id=user_id,
        )
        return True
    finally:
        await client.stop()


def _load_thoth_config() -> ThothConfig:
    """加载 Thoth 配置（轻量封装，便于测试 mock）."""
    return load_settings().thoth


async def _llm_summarize(
    *, title: str, description: str, site_name: str, url: str
) -> str:
    """调用 GLM-5.1 生成摘要.

    失败时回退到 description 截断（不阻塞 pipeline）。
    """
    try:
        from spide.llm import LLMClient

        settings = load_settings()
        client = LLMClient(settings.llm)
        await client.start()
        try:
            prompt = _LLM_PROMPT_TEMPLATE.format(
                title=title,
                site_name=site_name or "(未知)",
                url=url,
                description=description or "(无)",
            )
            response = await asyncio.to_thread(
                client.chat,
                messages=[
                    {"role": "system", "content": "你是专业的内容摘要助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            return (response.choices[0].message.content or "").strip()
        finally:
            await client.stop()
    except Exception as e:
        logger.warning("video_pipeline_llm_failed", error=str(e))
        # 回退：description 截断 200 字
        return (description or title)[:200]


def _build_markdown(
    title: str, summary: str, meta: dict[str, Any]
) -> str:
    """拼接 Markdown 文章内容."""
    parts = [
        f"# {title}",
        "",
        "## 摘要",
        "",
        summary,
        "",
        "## 元数据",
        "",
        f"- **URL**: {meta.get('url', '')}",
        f"- **来源**: {meta.get('site_name', '') or '(未知)'}",
    ]
    image = meta.get("image", "")
    if image:
        parts.append(f"- **缩略图**: ![]({image})")
    parts.extend(["", "---", "", "*由 spide video-pipeline 自动生成*"])
    return "\n".join(parts)


def _build_tags(site_name: str, user_id: str) -> str:
    """构造 Thoth tags 字符串."""
    tags = ["video-article", "auto-generated"]
    if site_name:
        # tag 不能含逗号
        clean = site_name.replace(",", "").strip()
        if clean:
            tags.append(clean)
    if user_id:
        tags.append(f"user:{user_id}")
    return ",".join(tags)
