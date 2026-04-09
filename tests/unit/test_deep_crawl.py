# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — MediaCrawler 深度采集适配器."""


import pytest

from spide.spider.media_crawler_adapter import (
    MediaCrawlerAdapter,
    _map_comment,
    _map_content,
    _map_creator,
    _safe_int,
    _safe_str,
)
from spide.storage.models import DeepComment, DeepContent, DeepCreator, Platform


class TestHelperFunctions:
    """工具函数."""

    def test_safe_int(self):
        assert _safe_int(42) == 42
        assert _safe_int("100") == 100
        assert _safe_int(None) is None
        assert _safe_int("abc") is None

    def test_safe_str(self):
        assert _safe_str("hello") == "hello"
        assert _safe_str(42) == "42"
        assert _safe_str(None) == ""


class TestContentMapping:
    """内容数据映射."""

    def test_xhs_content(self):
        raw = {
            "note_id": "abc123",
            "title": "测试笔记",
            "desc": "这是描述",
            "user_id": "u001",
            "nickname": "测试用户",
            "liked_count": 100,
            "comment_count": 20,
            "note_url": "https://www.xiaohongshu.com/explore/abc123",
            "ip_location": "北京",
            "source_keyword": "AI",
        }
        result = _map_content(Platform.XHS, raw)
        assert isinstance(result, DeepContent)
        assert result.content_id == "abc123"
        assert result.title == "测试笔记"
        assert result.author_name == "测试用户"
        assert result.like_count == 100
        assert result.platform == Platform.XHS

    def test_douyin_content(self):
        raw = {
            "aweme_id": "dy001",
            "desc": "抖音视频描述",
            "user_id": "u002",
            "nickname": "抖音用户",
            "liked_count": 500,
            "comment_count": 30,
            "aweme_url": "https://www.douyin.com/video/dy001",
        }
        result = _map_content(Platform.DOUYIN, raw)
        assert result.content_id == "dy001"
        assert result.url == "https://www.douyin.com/video/dy001"

    def test_bilibili_content(self):
        raw = {
            "video_id": "bv123",
            "title": "B站视频",
            "desc": "视频描述",
            "user_id": "u003",
            "nickname": "UP主",
            "liked_count": 200,
            "video_comment": 50,
            "video_url": "https://www.bilibili.com/video/avbv123",
        }
        result = _map_content(Platform.BILIBILI, raw)
        assert result.content_id == "bv123"
        assert result.comment_count == 50

    def test_zhihu_content(self):
        raw = {
            "content_id": "zh001",
            "content_type": "answer",
            "title": "知乎回答",
            "content_text": "回答正文",
            "user_id": "u004",
            "user_nickname": "知乎用户",
            "voteup_count": 1000,
            "content_url": "https://www.zhihu.com/question/123/answer/zh001",
        }
        result = _map_content(Platform.ZHIHU, raw)
        assert result.content_id == "zh001"
        assert result.content_type == "answer"
        assert result.like_count == 1000
        assert result.author_name == "知乎用户"

    def test_extra_fields_preserved(self):
        raw = {
            "note_id": "x1",
            "title": "标题",
            "user_id": "u1",
            "platform_specific_field": "特殊值",
        }
        result = _map_content(Platform.XHS, raw)
        assert result.extra["platform_specific_field"] == "特殊值"

    def test_media_urls_from_image_list(self):
        raw = {
            "note_id": "x2",
            "title": "图文",
            "image_list": "https://img1.jpg,https://img2.jpg",
        }
        result = _map_content(Platform.XHS, raw)
        assert len(result.media_urls) == 2


class TestCommentMapping:
    """评论数据映射."""

    def test_xhs_comment(self):
        raw = {
            "comment_id": "c001",
            "note_id": "note001",
            "content": "很好的笔记",
            "user_id": "u001",
            "nickname": "评论者",
            "like_count": 5,
            "sub_comment_count": 2,
            "parent_comment_id": "0",
        }
        result = _map_comment(Platform.XHS, raw)
        assert isinstance(result, DeepComment)
        assert result.comment_id == "c001"
        assert result.content_id == "note001"
        assert result.content == "很好的笔记"

    def test_douyin_comment(self):
        raw = {
            "cid": "dc001",
            "aweme_id": "dy001",
            "text": "不错",
            "user_id": "u002",
            "nickname": "抖音评论者",
            "digg_count": 10,
            "reply_id": "0",
        }
        result = _map_comment(Platform.DOUYIN, raw)
        assert result.comment_id == "dc001"
        assert result.like_count == 10

    def test_bilibili_comment(self):
        raw = {
            "rpid": "bc001",
            "video_id": "bv001",
            "content": {"message": "B站评论"},
            "member": {"mid": "u003", "uname": "B站用户"},
            "like": 8,
            "parent": 0,
        }
        result = _map_comment(Platform.BILIBILI, raw)
        # rpid should be captured
        assert result.comment_id == "bc001"


class TestCreatorMapping:
    """创作者数据映射."""

    def test_basic_creator(self):
        raw = {
            "user_id": "u001",
            "nickname": "创作者",
            "avatar": "https://avatar.jpg",
            "desc": "简介",
            "fans": 1000,
            "follows": 100,
            "gender": "Male",
        }
        result = _map_creator(Platform.XHS, raw)
        assert isinstance(result, DeepCreator)
        assert result.user_id == "u001"
        assert result.fans == 1000
        assert result.platform == Platform.XHS

    def test_zhihu_creator(self):
        raw = {
            "user_id": "zh001",
            "user_nickname": "知乎大V",
            "user_avatar": "https://pic.jpg",
            "followers_count": 5000,
            "get_voteup_count": 100000,
        }
        result = _map_creator(Platform.ZHIHU, raw)
        assert result.nickname == "知乎大V"
        assert result.fans == 5000
        assert result.interaction == 100000


class TestAdapterInit:
    """适配器初始化."""

    def test_valid_root(self, tmp_path):
        # 创建一个有效的 MediaCrawler 目录结构
        mc_root = tmp_path / "MediaCrawler"
        mc_root.mkdir()
        (mc_root / "main.py").write_text("# mock")

        adapter = MediaCrawlerAdapter(media_crawler_root=str(mc_root))
        assert adapter._root == mc_root.resolve()

    def test_invalid_root(self):
        with pytest.raises(Exception, match="不存在"):
            MediaCrawlerAdapter(media_crawler_root="/nonexistent/path")


class TestDeepCrawlTool:
    """MCP 深度采集工具定义."""

    def test_deep_crawl_tool_schema(self):
        from spide.mcp.tools import DEEP_CRAWL_TOOL

        props = DEEP_CRAWL_TOOL["inputSchema"]["properties"]
        assert "platform" in props
        assert "mode" in props
        assert "keywords" in props
        assert props["platform"]["enum"] == ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]

    def test_deep_crawl_tool_required(self):
        from spide.mcp.tools import DEEP_CRAWL_TOOL

        assert "platform" in DEEP_CRAWL_TOOL["inputSchema"]["required"]


class TestNewModels:
    """新增数据模型."""

    def test_deep_content_roundtrip(self):
        content = DeepContent(
            platform=Platform.XHS,
            content_id="test001",
            title="测试内容",
            author_name="用户A",
            like_count=100,
            extra={"platform_field": "value"},
        )
        data = content.model_dump(mode="json")
        restored = DeepContent(**data)
        assert restored.platform == Platform.XHS
        assert restored.like_count == 100
        assert restored.extra["platform_field"] == "value"

    def test_deep_comment_roundtrip(self):
        comment = DeepComment(
            platform=Platform.DOUYIN,
            comment_id="c001",
            content="评论内容",
            like_count=5,
        )
        data = comment.model_dump(mode="json")
        restored = DeepComment(**data)
        assert restored.platform == Platform.DOUYIN
        assert restored.content == "评论内容"

    def test_deep_creator_roundtrip(self):
        creator = DeepCreator(
            platform=Platform.BILIBILI,
            user_id="up001",
            nickname="UP主",
            fans=10000,
        )
        data = creator.model_dump(mode="json")
        restored = DeepCreator(**data)
        assert restored.platform == Platform.BILIBILI
        assert restored.fans == 10000

    def test_platform_enum_values(self):
        assert Platform.XHS.value == "xhs"
        assert Platform.DOUYIN.value == "dy"
        assert Platform.BILIBILI.value == "bili"
        assert Platform.ZHIHU.value == "zhihu"

    def test_crawl_mode_enum_values(self):
        from spide.storage.models import CrawlMode
        assert CrawlMode.SEARCH.value == "search"
        assert CrawlMode.DETAIL.value == "detail"
        assert CrawlMode.CREATOR.value == "creator"
