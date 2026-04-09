# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""Spide Agent 统一异常体系."""


class SpideError(Exception):
    """Spide Agent 基础异常."""

    def __init__(self, message: str = "", *, detail: str = "") -> None:
        self.detail = detail
        super().__init__(message)


class ConfigError(SpideError):
    """配置加载或校验错误."""


class StorageError(SpideError):
    """数据存储操作错误."""


class SpiderError(SpideError):
    """爬虫引擎执行错误."""


class MCPError(SpideError):
    """MCP 协议通讯错误."""


class MQTTError(SpideError):
    """MQTT 通讯错误."""


class LLMError(SpideError):
    """LLM 模型调用错误."""


class WorkspaceError(SpideError):
    """工作空间管理错误."""


class AnalysisError(SpideError):
    """AI 分析模块错误."""
