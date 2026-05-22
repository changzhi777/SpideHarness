# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""MCP 工具定义 — 注册 Agent 可被外部调用的工具."""

from __future__ import annotations

# 工具定义（遵循 MCP Tool schema）
CRAWL_TOOL = {
    "name": "crawl_hot_topics",
    "description": "采集指定平台的热搜榜单数据。支持微博、百度、抖音、知乎、B站等平台。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "数据源平台：weibo, baidu, douyin, zhihu, bilibili",
                "enum": ["weibo", "baidu", "douyin", "zhihu", "bilibili"],
            },
            "save": {
                "type": "boolean",
                "description": "是否保存到数据库",
                "default": False,
            },
        },
        "required": ["source"],
    },
}

SEARCH_TOOL = {
    "name": "web_search",
    "description": "联网搜索 — 使用智谱 Web Search API 获取实时搜索结果。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "engine": {
                "type": "string",
                "description": "搜索引擎：search_std, search_pro, search_pro_sogou, search_pro_quark",
                "default": "search_pro",
            },
            "count": {
                "type": "integer",
                "description": "返回结果数量 (1-50)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}

MEMORY_TOOL = {
    "name": "manage_memory",
    "description": "管理 Agent 记忆 — 添加、删除或查询记忆条目。",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["add", "remove", "list", "get"],
            },
            "title": {
                "type": "string",
                "description": "记忆标题（add/remove/get 时必填）",
            },
            "content": {
                "type": "string",
                "description": "记忆内容（add 时必填）",
            },
        },
        "required": ["action"],
    },
}

HEALTH_TOOL = {
    "name": "health_check",
    "description": "检查 Agent 服务健康状态。",
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
}

DEEP_CRAWL_TOOL = {
    "name": "deep_crawl_hot_topics",
    "description": (
        "深度采集指定平台的内容数据（需要浏览器环境）。"
        "支持小红书(xhs)、抖音(dy)、快手(ks)、B站(bili)、微博(wb)、贴吧(tieba)、知乎(zhihu)。"
        "可搜索关键词、获取指定内容详情、获取创作者主页数据，含评论和子评论。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "目标平台",
                "enum": ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"],
            },
            "mode": {
                "type": "string",
                "description": "采集模式",
                "enum": ["search", "detail", "creator"],
                "default": "search",
            },
            "keywords": {
                "type": "string",
                "description": "搜索关键词（逗号分隔，search 模式必填）",
            },
            "content_ids": {
                "type": "string",
                "description": "内容 ID 或 URL（逗号分隔，detail 模式必填）",
            },
            "creator_ids": {
                "type": "string",
                "description": "创作者 ID（逗号分隔，creator 模式必填）",
            },
            "max_notes": {
                "type": "integer",
                "description": "最大采集数量",
                "default": 20,
            },
            "enable_comments": {
                "type": "boolean",
                "description": "是否采集评论",
                "default": True,
            },
        },
        "required": ["platform"],
    },
}

WEB_SEARCH_ENHANCED_TOOL = {
    "name": "web_search_enhanced",
    "description": (
        "增强联网搜索 — 多引擎搜索（DuckDuckGo/智谱），返回结构化结果（标题/URL/摘要）。"
        "适用于实时信息查询、新闻搜索、技术文档查找。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "engine": {
                "type": "string",
                "description": "搜索引擎：duckduckgo（免费，无需 Key）、zhipu（需 API Key）",
                "enum": ["duckduckgo", "zhipu"],
                "default": "duckduckgo",
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量 (1-50)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}

FETCH_WEB_PAGE_TOOL = {
    "name": "fetch_web_page",
    "description": (
        "抓取网页内容 — 获取指定 URL 的结构化文本内容。"
        "支持提取标题、正文、链接。适用于读取文章、文档、API 响应页面。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "目标网页 URL",
            },
            "extract_links": {
                "type": "boolean",
                "description": "是否提取页面中的链接",
                "default": False,
            },
        },
        "required": ["url"],
    },
}

FETCH_REPO_INFO_TOOL = {
    "name": "fetch_repo_info",
    "description": (
        "获取开源仓库信息 — GitHub 仓库元数据 + README 内容。"
        "支持获取仓库描述、Stars、语言、README 全文。"
        "适用于了解开源项目、技术选型调研。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "仓库路径（owner/repo），如 zhipu/zai-sdk-python",
            },
            "info_type": {
                "type": "string",
                "description": "信息类型",
                "enum": ["readme", "summary", "full"],
                "default": "summary",
            },
        },
        "required": ["repo"],
    },
}

# 所有工具集合
ALL_TOOLS = [
    CRAWL_TOOL,
    SEARCH_TOOL,
    WEB_SEARCH_ENHANCED_TOOL,
    FETCH_WEB_PAGE_TOOL,
    FETCH_REPO_INFO_TOOL,
    MEMORY_TOOL,
    HEALTH_TOOL,
    DEEP_CRAWL_TOOL,
]
