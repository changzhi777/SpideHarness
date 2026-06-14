# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — spide.integrations.url_metadata URL 元数据抓取."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spide.integrations.url_metadata import _parse_html, fetch


def _make_response(
    status: int = 200,
    body: bytes = b"<html></html>",
    content_type: str = "text/html; charset=utf-8",
) -> MagicMock:
    """构造 aiohttp 响应 mock."""
    resp = MagicMock()
    resp.status = status
    resp.headers = {"Content-Type": content_type}
    resp.content = MagicMock()
    resp.content.read = AsyncMock(return_value=body)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


class TestUrlValidation:
    """URL 合法性校验."""

    @pytest.mark.asyncio
    async def test_non_http_url_returns_error(self) -> None:
        """非 http(s) URL 应返回 error."""
        result = await fetch("not-a-url")
        assert "error" in result
        assert "http" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self) -> None:
        """空 URL 应返回 error."""
        result = await fetch("")
        assert "error" in result


class TestFetchHttp:
    """HTTP 抓取流程."""

    @pytest.mark.asyncio
    async def test_success_returns_metadata(self) -> None:
        """成功响应应返回解析后的 metadata."""
        html = b"""
        <html>
        <head>
        <meta property="og:title" content="Test Title">
        <meta property="og:description" content="Test Desc">
        <meta property="og:image" content="https://x.com/img.png">
        <meta property="og:site_name" content="X Site">
        </head>
        </html>
        """
        with patch("spide.integrations.url_metadata.aiohttp.ClientSession") as MockSession:
            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = _make_response(200, html)
            mock_session_instance.close = AsyncMock()
            MockSession.return_value = mock_session_instance
            result = await fetch("https://x.com/article")
        assert result["title"] == "Test Title"
        assert result["description"] == "Test Desc"
        assert result["image"] == "https://x.com/img.png"
        assert result["site_name"] == "X Site"

    @pytest.mark.asyncio
    async def test_404_returns_error(self) -> None:
        """404 应返回 error."""
        with patch("spide.integrations.url_metadata.aiohttp.ClientSession") as MockSession:
            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = _make_response(404)
            mock_session_instance.close = AsyncMock()
            MockSession.return_value = mock_session_instance
            result = await fetch("https://x.com/missing")
        assert "error" in result
        assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_non_html_returns_error(self) -> None:
        """非 HTML 内容（图片/二进制）应返回 error."""
        with patch("spide.integrations.url_metadata.aiohttp.ClientSession") as MockSession:
            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = _make_response(
                200, b"binary", "image/png"
            )
            mock_session_instance.close = AsyncMock()
            MockSession.return_value = mock_session_instance
            result = await fetch("https://x.com/img.png")
        assert "error" in result
        assert "html" in result["error"].lower()


class TestParseHtml:
    """HTML 解析（纯函数测试）."""

    def test_og_meta_extraction(self) -> None:
        """og: meta 应被提取."""
        html = b"""
        <html><head>
        <meta property="og:title" content="OG Title">
        <meta property="og:description" content="OG Desc">
        </head></html>
        """
        result = _parse_html(html, "https://x.com")
        assert result["title"] == "OG Title"
        assert result["description"] == "OG Desc"

    def test_twitter_card_fallback(self) -> None:
        """无 og: 时应回退到 twitter: meta."""
        html = b"""
        <html><head>
        <meta name="twitter:title" content="Twitter Title">
        <meta name="twitter:description" content="Twitter Desc">
        </head></html>
        """
        result = _parse_html(html, "https://x.com")
        assert result["title"] == "Twitter Title"

    def test_fallback_to_html_title(self) -> None:
        """无 OG/Twitter 时应回退到 <title>."""
        html = b"<html><head><title>Plain Title</title></head></html>"
        result = _parse_html(html, "https://x.com")
        assert result["title"] == "Plain Title"

    def test_relative_image_url_made_absolute(self) -> None:
        """相对路径图片 URL 应转为绝对."""
        html = b"""
        <html><head>
        <meta property="og:image" content="/img.png">
        </head></html>
        """
        result = _parse_html(html, "https://x.com")
        assert result["image"] == "https://x.com/img.png"

    def test_empty_html_returns_empty(self) -> None:
        """空 HTML 应返回空字段."""
        html = b"<html><head></head><body></body></html>"
        result = _parse_html(html, "https://x.com")
        assert result["title"] == ""
        assert result["url"] == "https://x.com"
