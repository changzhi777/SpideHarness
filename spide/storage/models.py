# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""数据模型 — Pydantic v2 定义.

核心实体:
- HotTopic: 热搜话题（来自 UAPI 各平台）
- NewsArticle: 新闻文章（抓取后结构化）
- DeepContent: 深度采集内容（来自 MediaCrawler 适配器）
- DeepComment: 深度采集评论
- DeepCreator: 深度采集创作者
- CrawlTask: 爬取任务
- CrawlSession: 爬取会话快照
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class TopicSource(str, Enum):
    """热搜数据源平台."""

    WEIBO = "weibo"
    BAIDU = "baidu"
    DOUYIN = "douyin"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    KUAISHOU = "kuaishou"
    TIEBA = "tieba"
    WEB_SEARCH = "web_search"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """任务状态."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArticleCategory(str, Enum):
    """新闻分类."""

    SOCIETY = "society"
    TECH = "tech"
    FINANCE = "finance"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    INTERNATIONAL = "international"
    SCIENCE = "science"
    HEALTH = "health"
    OTHER = "other"


# ---------------------------------------------------------------------------
# 核心实体
# ---------------------------------------------------------------------------


class HotTopic(BaseModel):
    """热搜话题."""

    id: int | None = None
    title: str
    source: TopicSource
    hot_value: int | None = None  # 热度值
    url: str | None = None
    rank: int | None = None  # 排名
    category: ArticleCategory | None = None
    summary: str | None = None
    fetched_at: datetime = Field(default_factory=datetime.now)
    extra: dict = Field(default_factory=dict)


class NewsArticle(BaseModel):
    """新闻文章."""

    id: int | None = None
    title: str
    url: str
    source: TopicSource
    author: str | None = None
    published_at: datetime | None = None
    content: str | None = None
    summary: str | None = None  # LLM 生成摘要
    category: ArticleCategory | None = None
    keywords: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.now)
    extra: dict = Field(default_factory=dict)


class CrawlTask(BaseModel):
    """爬取任务."""

    id: int | None = None
    name: str
    source: TopicSource
    status: TaskStatus = TaskStatus.PENDING
    params: dict = Field(default_factory=dict)
    result_count: int = 0
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CrawlSession(BaseModel):
    """爬取会话快照."""

    session_id: str
    session_key: str | None = None
    cwd: str = ""
    model: str = "glm-5.1"
    system_prompt: str | None = None
    messages: list[dict] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    summary: str | None = None
    # 爬虫特有字段
    crawled_urls: list[str] = Field(default_factory=list)
    task_ids: list[int] = Field(default_factory=list)
    progress: float = 0.0  # 0.0 ~ 1.0


class Platform(str, Enum):
    """深度采集支持的平台（对应 MediaCrawler）."""

    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class CrawlMode(str, Enum):
    """深度采集模式."""

    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"


class DeepContent(BaseModel):
    """深度采集内容 — 来自 MediaCrawler 各平台.

    统一 7 个平台的内容数据模型，字段为各平台共性字段。
    平台特有字段通过 extra dict 存储。
    """

    id: int | None = None
    platform: Platform
    content_id: str = ""  # 平台内容 ID
    content_type: str = ""  # 内容类型（video/image/article/answer 等）
    title: str = ""
    content: str = ""  # 正文 / 描述
    url: str = ""  # 内容落地页 URL
    author_id: str = ""
    author_name: str = ""
    author_avatar: str = ""
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    collect_count: int | None = None
    view_count: int | None = None
    ip_location: str = ""
    media_urls: list[str] = Field(default_factory=list)  # 图片/视频/封面 URL
    tags: list[str] = Field(default_factory=list)
    publish_time: int | None = None  # Unix 时间戳
    source_keyword: str = ""
    fetched_at: datetime = Field(default_factory=datetime.now)
    extra: dict = Field(default_factory=dict)  # 平台特有字段


class DeepComment(BaseModel):
    """深度采集评论."""

    id: int | None = None
    platform: Platform
    comment_id: str = ""
    content_id: str = ""  # 所属内容的 ID
    parent_comment_id: str = ""
    content: str = ""
    user_id: str = ""
    nickname: str = ""
    avatar: str = ""
    like_count: int | None = None
    sub_comment_count: int | None = None
    ip_location: str = ""
    publish_time: int | None = None  # Unix 时间戳
    fetched_at: datetime = Field(default_factory=datetime.now)
    extra: dict = Field(default_factory=dict)


class DeepCreator(BaseModel):
    """深度采集创作者."""

    id: int | None = None
    platform: Platform
    user_id: str = ""
    nickname: str = ""
    avatar: str = ""
    description: str = ""  # 简介
    gender: str = ""
    ip_location: str = ""
    follows: int | None = None
    fans: int | None = None
    interaction: int | None = None  # 获赞/互动总数
    fetched_at: datetime = Field(default_factory=datetime.now)
    extra: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 增量采集 & 告警 & 追踪 & 聚类
# ---------------------------------------------------------------------------


class TopicStatus(str, Enum):
    """话题状态变化."""

    NEW = "new"
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    DROPPED = "dropped"


class HotTopicChange(BaseModel):
    """话题变化记录."""

    id: int | None = None
    title: str
    source: TopicSource
    status: TopicStatus
    previous_rank: int | None = None
    current_rank: int | None = None
    previous_hot_value: int | None = None
    current_hot_value: int | None = None
    hot_value_change: int | None = None
    detected_at: datetime = Field(default_factory=datetime.now)


class CrawlSnapshot(BaseModel):
    """采集快照 — 记录一轮采集的完整结果."""

    id: int | None = None
    snapshot_key: str
    source: TopicSource
    total_topics: int = 0
    new_count: int = 0
    rising_count: int = 0
    falling_count: int = 0
    dropped_count: int = 0
    changes: list[HotTopicChange] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class AlertRule(BaseModel):
    """告警规则."""

    id: int | None = None
    name: str
    keywords: list[str] = Field(default_factory=list)
    sources: list[TopicSource] = Field(default_factory=list)
    hot_value_threshold: int = 0
    status_trigger: list[TopicStatus] = Field(default_factory=lambda: [TopicStatus.NEW])
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class AlertRecord(BaseModel):
    """告警记录."""

    id: int | None = None
    rule_id: int
    rule_name: str
    topic_title: str
    topic_source: TopicSource
    topic_hot_value: int | None = None
    alert_type: str = ""
    notification_sent: bool = False
    notification_channels: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class TopicDeepTrack(BaseModel):
    """话题深度追踪."""

    id: int | None = None
    topic_title: str
    topic_source: TopicSource
    topic_hot_value: int | None = None
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    sentiment: str = ""
    related_articles: list[dict] = Field(default_factory=list)
    deep_content_ids: list[int] = Field(default_factory=list)
    analysis_status: str = "pending"
    analyzed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class TopicCluster(BaseModel):
    """话题聚类."""

    id: int | None = None
    cluster_name: str
    cluster_keywords: list[str] = Field(default_factory=list)
    platform_sources: list[str] = Field(default_factory=list)
    topic_titles: list[str] = Field(default_factory=list)
    total_hot_value: int = 0
    cross_platform: bool = False
    analysis: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
