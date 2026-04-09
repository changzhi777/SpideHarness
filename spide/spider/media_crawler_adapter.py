# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MediaCrawler 深度采集适配器 — 子进程桥接模式.

用法:
    from spide.spider.media_crawler_adapter import MediaCrawlerAdapter

    adapter = MediaCrawlerAdapter(media_crawler_root="MediaCrawler")
    results = await adapter.deep_crawl(
        platform="xhs",
        mode="search",
        keywords=["AI编程", "副业"],
    )

设计策略:
    MediaCrawler 是独立项目（依赖 Playwright、httpx 等重量级库），
    采用子进程调用 + JSON 文件交换的方式集成，避免依赖冲突。
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from spide.exceptions import SpiderError
from spide.logging import get_logger
from spide.storage.models import (
    CrawlMode,
    DeepComment,
    DeepContent,
    DeepCreator,
    Platform,
)

logger = get_logger(__name__)

# 平台映射: Spide Platform → MediaCrawler 平台标识
_PLATFORM_MAP: dict[Platform, str] = {
    Platform.XHS: "xhs",
    Platform.DOUYIN: "dy",
    Platform.KUAISHOU: "ks",
    Platform.BILIBILI: "bili",
    Platform.WEIBO: "wb",
    Platform.TIEBA: "tieba",
    Platform.ZHIHU: "zhihu",
}

# 爬取模式映射
_MODE_MAP: dict[CrawlMode, str] = {
    CrawlMode.SEARCH: "search",
    CrawlMode.DETAIL: "detail",
    CrawlMode.CREATOR: "creator",
}


class DeepCrawlResult:
    """深度采集结果容器."""

    __slots__ = ("comments", "contents", "creators")

    def __init__(self) -> None:
        self.contents: list[DeepContent] = []
        self.comments: list[DeepComment] = []
        self.creators: list[DeepCreator] = []


class MediaCrawlerAdapter:
    """MediaCrawler 深度采集适配器 — 子进程桥接.

    通过 uv run 调用 MediaCrawler 的 main.py，
    采集结果通过 JSON 文件回传，再解析为 Spide 数据模型。
    """

    def __init__(self, *, media_crawler_root: str = "MediaCrawler") -> None:
        self._root = Path(media_crawler_root).resolve()
        if not self._root.is_dir():
            raise SpiderError(f"MediaCrawler 目录不存在: {self._root}")

    async def deep_crawl(
        self,
        platform: Platform,
        mode: CrawlMode = CrawlMode.SEARCH,
        *,
        keywords: list[str] | None = None,
        content_ids: list[str] | None = None,
        creator_ids: list[str] | None = None,
        max_notes: int = 20,
        enable_comments: bool = True,
        enable_sub_comments: bool = False,
        save_format: str = "jsonl",
        headless: bool = True,
        timeout: int = 600,
    ) -> DeepCrawlResult:
        """执行深度采集.

        Args:
            platform: 目标平台
            mode: 采集模式 (search/detail/creator)
            keywords: 搜索关键词列表
            content_ids: 内容 ID 列表（detail 模式）
            creator_ids: 创作者 ID 列表（creator 模式）
            max_notes: 单次最大采集数
            enable_comments: 是否采集评论
            enable_sub_comments: 是否采集子评论
            save_format: 存储格式 (jsonl/json/csv)
            headless: 是否无头浏览器
            timeout: 超时秒数

        Returns:
            DeepCrawlResult 包含内容、评论、创作者列表
        """
        mc_platform = _PLATFORM_MAP.get(platform)
        if not mc_platform:
            raise SpiderError(f"不支持的平台: {platform}")

        mc_mode = _MODE_MAP.get(mode)
        if not mc_mode:
            raise SpiderError(f"不支持的采集模式: {mode}")

        # 准备输出目录
        output_dir = tempfile.mkdtemp(prefix="spide_deep_")

        # 构建子进程命令
        cmd = self._build_command(
            mc_platform=mc_platform,
            mc_mode=mc_mode,
            keywords=keywords,
            content_ids=content_ids,
            creator_ids=creator_ids,
            max_notes=max_notes,
            enable_comments=enable_comments,
            enable_sub_comments=enable_sub_comments,
            save_format=save_format,
            headless=headless,
            output_dir=output_dir,
        )

        logger.debug(
            "deep_crawl_starting",
            platform=mc_platform,
            mode=mc_mode,
            cmd=" ".join(cmd),
        )

        # 执行子进程
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._root),
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            raise SpiderError(f"深度采集超时 ({timeout}s): platform={mc_platform}") from None

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
            raise SpiderError(f"深度采集失败 [exit={process.returncode}]: {error_msg}")

        # 解析输出结果
        result = self._parse_output(platform, output_dir, save_format)

        logger.debug(
            "deep_crawl_completed",
            platform=mc_platform,
            contents=len(result.contents),
            comments=len(result.comments),
            creators=len(result.creators),
        )

        return result

    def _build_command(
        self,
        *,
        mc_platform: str,
        mc_mode: str,
        keywords: list[str] | None,
        content_ids: list[str] | None,
        creator_ids: list[str] | None,
        max_notes: int,
        enable_comments: bool,
        enable_sub_comments: bool,
        save_format: str,
        headless: bool,
        output_dir: str,
    ) -> list[str]:
        """构建 uv run 命令."""
        cmd = [
            sys.executable,
            "-m",
            "mediacrawler",
            "--platform",
            mc_platform,
            "--type",
            mc_mode,
            "--lt",
            "cookie",
            "--save",
            save_format,
        ]

        if keywords:
            cmd.extend(["--keywords", ",".join(keywords)])

        if content_ids:
            cmd.extend(["--urls", ",".join(content_ids)])

        if creator_ids:
            cmd.extend(["--creator", ",".join(creator_ids)])

        cmd.extend(["--max_notes", str(max_notes)])

        if headless:
            cmd.append("--headless")

        # 通过环境变量传递配置
        # MediaCrawler 使用 config 模块级变量 + 环境变量覆盖
        return cmd

    def _parse_output(
        self,
        platform: Platform,
        output_dir: str,
        save_format: str,
    ) -> DeepCrawlResult:
        """解析采集输出文件."""
        result = DeepCrawlResult()

        # MediaCrawler 默认输出到 data/ 目录
        data_dir = self._root / "data"
        if not data_dir.is_dir():
            # 尝试 output_dir
            data_dir = Path(output_dir)
            if not data_dir.is_dir():
                logger.warning("deep_crawl_no_output", path=str(data_dir))
                return result

        # 解析文件
        ext_map = {"jsonl": ".jsonl", "json": ".json", "csv": ".csv"}
        ext = ext_map.get(save_format, ".jsonl")

        for filepath in data_dir.glob(f"*{ext}"):
            try:
                if ext == ".jsonl":
                    items = self._read_jsonl(filepath)
                elif ext == ".json":
                    items = self._read_json(filepath)
                elif ext == ".csv":
                    items = self._read_csv(filepath)
                else:
                    continue
            except Exception as e:
                logger.warning("deep_crawl_parse_error", file=str(filepath), error=str(e))
                continue

            for item in items:
                mapped = self._map_raw_to_model(platform, item)
                if isinstance(mapped, DeepContent):
                    result.contents.append(mapped)
                elif isinstance(mapped, DeepComment):
                    result.comments.append(mapped)
                elif isinstance(mapped, DeepCreator):
                    result.creators.append(mapped)

        return result

    @staticmethod
    def _read_jsonl(filepath: Path) -> list[dict]:
        """读取 JSONL 文件."""
        items = []
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    @staticmethod
    def _read_json(filepath: Path) -> list[dict]:
        """读取 JSON 文件."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]

    @staticmethod
    def _read_csv(filepath: Path) -> list[dict]:
        """读取 CSV 文件."""
        import csv

        items = []
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(dict(row))
        return items

    @staticmethod
    def _map_raw_to_model(
        platform: Platform, raw: dict
    ) -> DeepContent | DeepComment | DeepCreator | None:
        """将 MediaCrawler 原始数据映射为 Spide 模型.

        根据文件名或字段特征自动判断类型（内容/评论/创作者），
        然后提取各平台共性字段。
        """
        # 判断数据类型
        if _is_creator(raw):
            return _map_creator(platform, raw)
        elif _is_comment(raw):
            return _map_comment(platform, raw)
        else:
            return _map_content(platform, raw)


# ---------------------------------------------------------------------------
# 内部映射函数
# ---------------------------------------------------------------------------


def _is_comment(raw: dict) -> bool:
    """判断是否为评论数据."""
    comment_keys = {"comment_id", "cid", "rpid"}
    return bool(comment_keys & raw.keys())


def _is_creator(raw: dict) -> bool:
    """判断是否为创作者数据."""
    creator_keys = {"fans", "follows", "user_id", "nickname"}
    # 创作者数据有粉丝/关注字段且无 content_id 类字段
    content_keys = {"note_id", "aweme_id", "video_id", "content_id"}
    return bool(creator_keys & raw.keys()) and not (content_keys & raw.keys())


def _safe_int(val: Any) -> int | None:
    """安全转整数."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> str:
    """安全转字符串."""
    if val is None:
        return ""
    return str(val)


def _map_content(platform: Platform, raw: dict) -> DeepContent:
    """映射内容数据 — 提取各平台共性字段."""
    # 平台特有的 ID 字段名
    id_fields = {
        Platform.XHS: "note_id",
        Platform.DOUYIN: "aweme_id",
        Platform.KUAISHOU: "photo_id",
        Platform.BILIBILI: "video_id",
        Platform.WEIBO: "note_id",
        Platform.TIEBA: "note_id",
        Platform.ZHIHU: "content_id",
    }

    # URL 字段名
    url_fields = {
        Platform.XHS: "note_url",
        Platform.DOUYIN: "aweme_url",
        Platform.KUAISHOU: "photo_url",
        Platform.BILIBILI: "video_url",
        Platform.WEIBO: "note_url",
        Platform.TIEBA: "note_url",
        Platform.ZHIHU: "content_url",
    }

    content_id = _safe_str(raw.get(id_fields.get(platform, "content_id"), ""))
    url = _safe_str(raw.get(url_fields.get(platform, "url"), raw.get("url", "")))

    # 提取媒体 URL
    media_urls: list[str] = []
    for field in ("image_list", "video_url", "cover_url", "video_cover_url"):
        val = raw.get(field, "")
        if isinstance(val, str) and val:
            media_urls.extend(u.strip() for u in val.split(",") if u.strip())
        elif isinstance(val, list):
            media_urls.extend(val)

    # 提取标签
    tags: list[str] = []
    tag_str = raw.get("tag_list", "")
    if isinstance(tag_str, str) and tag_str:
        tags = [t.strip() for t in tag_str.split(",") if t.strip()]

    return DeepContent(
        platform=platform,
        content_id=content_id,
        content_type=_safe_str(
            raw.get("type") or raw.get("content_type") or raw.get("video_type", "")
        ),
        title=_safe_str(raw.get("title", "")),
        content=_safe_str(raw.get("desc") or raw.get("content") or raw.get("content_text", "")),
        url=url,
        author_id=_safe_str(raw.get("user_id", "")),
        author_name=_safe_str(raw.get("nickname") or raw.get("user_nickname", "")),
        author_avatar=_safe_str(raw.get("avatar") or raw.get("user_avatar", "")),
        like_count=_safe_int(raw.get("liked_count") or raw.get("voteup_count")),
        comment_count=_safe_int(raw.get("comment_count") or raw.get("video_comment")),
        share_count=_safe_int(raw.get("share_count") or raw.get("video_share_count")),
        collect_count=_safe_int(raw.get("collected_count")),
        view_count=_safe_int(raw.get("view_count") or raw.get("video_play_count")),
        ip_location=_safe_str(raw.get("ip_location", "")),
        media_urls=media_urls,
        tags=tags,
        publish_time=_safe_int(
            raw.get("time")
            or raw.get("create_time")
            or raw.get("created_time")
            or raw.get("pubdate")
        ),
        source_keyword=_safe_str(raw.get("source_keyword", "")),
        extra={
            k: v
            for k, v in raw.items()
            if k
            not in {
                "note_id",
                "aweme_id",
                "video_id",
                "content_id",
                "photo_id",
                "type",
                "content_type",
                "video_type",
                "title",
                "desc",
                "content",
                "content_text",
                "note_url",
                "aweme_url",
                "video_url",
                "content_url",
                "photo_url",
                "url",
                "user_id",
                "nickname",
                "user_nickname",
                "avatar",
                "user_avatar",
                "liked_count",
                "voteup_count",
                "comment_count",
                "video_comment",
                "share_count",
                "video_share_count",
                "collected_count",
                "view_count",
                "video_play_count",
                "ip_location",
                "image_list",
                "cover_url",
                "video_cover_url",
                "tag_list",
                "time",
                "create_time",
                "created_time",
                "pubdate",
                "source_keyword",
                "last_modify_ts",
            }
        },
    )


def _map_comment(platform: Platform, raw: dict) -> DeepComment:
    """映射评论数据."""
    return DeepComment(
        platform=platform,
        comment_id=_safe_str(raw.get("comment_id") or raw.get("cid") or raw.get("rpid", "")),
        content_id=_safe_str(
            raw.get("note_id")
            or raw.get("aweme_id")
            or raw.get("video_id")
            or raw.get("content_id", "")
        ),
        parent_comment_id=_safe_str(
            raw.get("parent_comment_id") or raw.get("parent") or raw.get("reply_id", "")
        ),
        content=_safe_str(raw.get("content") or raw.get("text", "")),
        user_id=_safe_str(raw.get("user_id", "")),
        nickname=_safe_str(raw.get("nickname") or raw.get("user_nickname", "")),
        avatar=_safe_str(raw.get("avatar") or raw.get("user_avatar", "")),
        like_count=_safe_int(raw.get("like_count") or raw.get("digg_count")),
        sub_comment_count=_safe_int(
            raw.get("sub_comment_count") or raw.get("rcount") or raw.get("reply_comment_total")
        ),
        ip_location=_safe_str(raw.get("ip_location") or raw.get("ip_label", "")),
        publish_time=_safe_int(
            raw.get("create_time") or raw.get("ctime") or raw.get("publish_time")
        ),
        extra={
            k: v
            for k, v in raw.items()
            if k
            not in {
                "comment_id",
                "cid",
                "rpid",
                "note_id",
                "aweme_id",
                "video_id",
                "content_id",
                "parent_comment_id",
                "parent",
                "reply_id",
                "content",
                "text",
                "user_id",
                "nickname",
                "user_nickname",
                "avatar",
                "user_avatar",
                "like_count",
                "digg_count",
                "sub_comment_count",
                "rcount",
                "reply_comment_total",
                "ip_location",
                "ip_label",
                "create_time",
                "ctime",
                "publish_time",
                "last_modify_ts",
            }
        },
    )


def _map_creator(platform: Platform, raw: dict) -> DeepCreator:
    """映射创作者数据."""
    return DeepCreator(
        platform=platform,
        user_id=_safe_str(raw.get("user_id", "")),
        nickname=_safe_str(raw.get("nickname") or raw.get("user_nickname", "")),
        avatar=_safe_str(raw.get("avatar") or raw.get("user_avatar", "")),
        description=_safe_str(
            raw.get("desc") or raw.get("description") or raw.get("sign") or raw.get("signature", "")
        ),
        gender=_safe_str(raw.get("gender", "")),
        ip_location=_safe_str(raw.get("ip_location", "")),
        follows=_safe_int(raw.get("follows") or raw.get("follow_count")),
        fans=_safe_int(
            raw.get("fans") or raw.get("followers_count") or raw.get("max_follower_count")
        ),
        interaction=_safe_int(
            raw.get("interaction") or raw.get("total_favorited") or raw.get("get_voteup_count")
        ),
        extra={
            k: v
            for k, v in raw.items()
            if k
            not in {
                "user_id",
                "nickname",
                "user_nickname",
                "avatar",
                "user_avatar",
                "desc",
                "description",
                "sign",
                "signature",
                "gender",
                "ip_location",
                "follows",
                "follow_count",
                "fans",
                "followers_count",
                "max_follower_count",
                "interaction",
                "total_favorited",
                "get_voteup_count",
                "last_modify_ts",
            }
        },
    )
