# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.integrations.video_pipeline 视频文章 pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.integrations.video_pipeline import (
    _build_markdown,
    _build_tags,
    _llm_summarize,
    extract_urls,
    process_urls,
)


class TestExtractUrls:
    """URL 提取（纯函数）."""

    def test_empty_text(self) -> None:
        """空文本应返回空列表."""
        assert extract_urls("") == []

    def test_no_url(self) -> None:
        """无 URL 文本应返回空列表."""
        assert extract_urls("纯文本，无链接") == []

    def test_single_url(self) -> None:
        """单个 URL 应正确提取."""
        urls = extract_urls("看 https://example.com")
        assert urls == ["https://example.com"]

    def test_multiple_urls(self) -> None:
        """多个 URL 应按顺序提取."""
        urls = extract_urls("A https://a.com B https://b.com")
        assert urls == ["https://a.com", "https://b.com"]

    def test_deduplication(self) -> None:
        """重复 URL 应去重."""
        urls = extract_urls("https://a.com 又 https://a.com")
        assert urls == ["https://a.com"]

    def test_max_urls_limit(self) -> None:
        """超过 max_urls 数量应被截断."""
        urls = extract_urls(
            "https://a.com https://b.com https://c.com https://d.com",
            max_urls=2,
        )
        assert len(urls) == 2
        assert urls == ["https://a.com", "https://b.com"]

    def test_trailing_punctuation_stripped(self) -> None:
        """尾随标点应被去除."""
        urls = extract_urls("看 https://x.com/foo. 末尾")
        assert urls == ["https://x.com/foo"]


class TestBuildTags:
    """标签构造."""

    def test_basic_tags(self) -> None:
        """基础标签应包含 video-article + auto-generated."""
        tags = _build_tags("", "")
        assert "video-article" in tags
        assert "auto-generated" in tags

    def test_site_name_added(self) -> None:
        """site_name 应被加入 tags."""
        tags = _build_tags("Bilibili", "")
        assert "Bilibili" in tags

    def test_user_id_added(self) -> None:
        """user_id 应被加 user: 前缀."""
        tags = _build_tags("", "user_abc")
        assert "user:user_abc" in tags


class TestBuildMarkdown:
    """Markdown 文章构造."""

    def test_basic_structure(self) -> None:
        """基本结构应含标题、摘要、元数据、署名."""
        meta = {
            "url": "https://x.com/a",
            "title": "T",
            "site_name": "X",
            "description": "D",
            "image": "",
        }
        md = _build_markdown("T", "S", meta)
        assert "# T" in md
        assert "## 摘要" in md
        assert "S" in md
        assert "https://x.com/a" in md
        assert "X" in md
        assert "spide" in md

    def test_image_included(self) -> None:
        """图片 URL 应在 Markdown 中渲染."""
        meta = {
            "url": "https://x.com/a",
            "title": "T",
            "site_name": "",
            "description": "",
            "image": "https://x.com/img.png",
        }
        md = _build_markdown("T", "S", meta)
        assert "https://x.com/img.png" in md


class TestLlmSummarize:
    """LLM 摘要（fallback 测试）."""

    @pytest.mark.asyncio
    async def test_fallback_on_error(self) -> None:
        """LLM 失败时应回退到 description 截断."""
        # LLMClient 在 _llm_summarize 内部 lazy import，patch 实际模块
        with patch(
            "spide.llm.LLMClient",
            side_effect=RuntimeError("API down"),
        ):
            result = await _llm_summarize(
                title="T",
                description="A" * 500,
                site_name="",
                url="https://x.com",
            )
        # 截断到 200 字符
        assert len(result) <= 200
        assert "A" in result


class TestProcessUrls:
    """process_urls 端到端（mock 全链路）."""

    @pytest.mark.asyncio
    async def test_no_urls_returns_zero(self) -> None:
        """无 URL 文本应直接返回 0."""
        count = await process_urls("纯文本", user_id="u1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_metadata_failure_skipped(self) -> None:
        """元数据抓取失败的 URL 应被跳过."""
        with patch(
            "spide.integrations.video_pipeline.fetch_metadata",
            AsyncMock(return_value={"url": "x", "error": "404"}),
        ):
            count = await process_urls(
                "看 https://x.com", user_id="u1"
            )
        assert count == 0

    @pytest.mark.asyncio
    async def test_thoth_missing_token_returns_zero(self) -> None:
        """Thoth token 缺失应返回 0（不抛异常）."""
        with (
            patch(
                "spide.integrations.video_pipeline.fetch_metadata",
                AsyncMock(
                    return_value={
                        "url": "https://x.com",
                        "title": "T",
                        "description": "D",
                        "site_name": "X",
                        "image": "",
                    }
                ),
            ),
            patch(
                "spide.integrations.video_pipeline.load_settings",
                return_value=MagicMock(
                    thoth=MagicMock(token="", default_room_id="r1")
                ),
            ),
        ):
            count = await process_urls("看 https://x.com", user_id="u1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_full_success_saves_note(self) -> None:
        """完整成功：1 URL → 元数据 → LLM → Thoth 写 1 篇."""
        with (
            patch(
                "spide.integrations.video_pipeline.fetch_metadata",
                AsyncMock(
                    return_value={
                        "url": "https://x.com",
                        "title": "T",
                        "description": "D",
                        "site_name": "X",
                        "image": "",
                    }
                ),
            ),
            patch(
                "spide.integrations.video_pipeline._llm_summarize",
                AsyncMock(return_value="S"),
            ),
            patch(
                "spide.integrations.video_pipeline.load_settings",
                return_value=MagicMock(
                    thoth=MagicMock(token="abc", default_room_id="r1")
                ),
            ),
            patch(
                "spide.integrations.video_pipeline.ThothClient"
            ) as MockClient,
        ):
            mock_instance = MagicMock()
            mock_instance.start = AsyncMock()
            mock_instance.stop = AsyncMock()
            mock_instance.create_note = AsyncMock(
                return_value={"id": "note_1"}
            )
            MockClient.return_value = mock_instance

            count = await process_urls("看 https://x.com", user_id="u1")

        assert count == 1
        mock_instance.create_note.assert_called_once()
        # 验证调用参数
        call_kwargs = mock_instance.create_note.call_args.kwargs
        assert call_kwargs["title"] == "T"
        assert call_kwargs["room_id"] == "r1"
        assert "video-article" in call_kwargs["tags"]

    @pytest.mark.asyncio
    async def test_thoth_error_does_not_propagate(self) -> None:
        """Thoth 抛异常时应被捕获，不影响其他 URL."""
        with (
            patch(
                "spide.integrations.video_pipeline.fetch_metadata",
                AsyncMock(
                    return_value={
                        "url": "https://x.com",
                        "title": "T",
                        "description": "D",
                        "site_name": "X",
                        "image": "",
                    }
                ),
            ),
            patch(
                "spide.integrations.video_pipeline._llm_summarize",
                AsyncMock(return_value="S"),
            ),
            patch(
                "spide.integrations.video_pipeline.load_settings",
                return_value=MagicMock(
                    thoth=MagicMock(token="abc", default_room_id="r1")
                ),
            ),
            patch(
                "spide.integrations.video_pipeline.ThothClient"
            ) as MockClient,
        ):
            mock_instance = MagicMock()
            mock_instance.start = AsyncMock()
            mock_instance.stop = AsyncMock()
            mock_instance.create_note = AsyncMock(
                side_effect=RuntimeError("Thoth down")
            )
            MockClient.return_value = mock_instance

            count = await process_urls("看 https://x.com", user_id="u1")

        assert count == 0  # 失败不计入
