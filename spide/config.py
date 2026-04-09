# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""配置加载模块 — Pydantic 模型 + YAML + 环境变量覆盖.

用法:
    from spide.config import load_settings
    settings = load_settings()
    settings.llm.text.model  # "glm-5.1"
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from spide.exceptions import ConfigError

# ---------------------------------------------------------------------------
# Pydantic 模型定义
# ---------------------------------------------------------------------------


class LLMTextConfig(BaseModel):
    """GLM-5.1 文本模型配置."""

    model: str = "glm-5.1"
    max_tokens: int = 65536
    temperature: float = 1.0
    thinking_type: str = Field("enabled", alias="thinking_type")
    stream: bool = True


class LLMVisionConfig(BaseModel):
    """GLM-5V-Turbo 视觉模型配置."""

    model: str = "glm-5v-turbo"
    max_tokens: int = 65536
    temperature: float = 1.0
    thinking_type: str = "enabled"
    stream: bool = True


class LLMCommonConfig(BaseModel):
    """LLM 共用配置."""

    provider: str = "zhipuai"
    api_key: str = ""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    sdk: str = "zai-sdk"


class WebSearchConfig(BaseModel):
    """联网搜索配置."""

    engine: str = "search_pro"
    default_count: int = 15
    content_size: str = "high"
    recency_filter: str = "noLimit"


class LLMConfig(BaseModel):
    """LLM 总配置."""

    common: LLMCommonConfig = LLMCommonConfig()
    text: LLMTextConfig = LLMTextConfig()  # type: ignore[call-arg]
    vision: LLMVisionConfig = LLMVisionConfig()
    web_search: WebSearchConfig = WebSearchConfig()


class MQTTReconnectConfig(BaseModel):
    """MQTT 重连策略."""

    max_retries: int = 10
    backoff_base: float = 2.0
    backoff_max: float = 60.0


class MQTTConfig(BaseModel):
    """MQTT 云服务配置."""

    host: str = ""
    port: int = 8883
    ws_port: int = 8084
    username: str = ""
    password: str = ""
    use_tls: bool = True
    ca_cert: str = "CA/emqxsl-ca.crt"
    keepalive: int = 60
    clean_session: bool = True
    reconnect: MQTTReconnectConfig = MQTTReconnectConfig()


class UAPIHotSourceConfig(BaseModel):
    """单个热搜数据源配置."""

    name: str = ""
    endpoint: str = ""
    interval: int = 300


class UAPIRateLimitConfig(BaseModel):
    """UAPI 请求控制."""

    max_concurrent: int = 5
    requests_per_minute: int = 30


class UAPIRetryConfig(BaseModel):
    """UAPI 重试策略."""

    max_retries: int = 3
    backoff_base: float = 1.0


class UAPIConfig(BaseModel):
    """UAPI 数据源配置."""

    base_url: str = "https://uapis.cn/api"
    api_key: str = ""
    sdk: str = "uapi-sdk-python"
    timeout: int = 30
    hot_sources: list[UAPIHotSourceConfig] = []
    rate_limit: UAPIRateLimitConfig = UAPIRateLimitConfig()
    retry: UAPIRetryConfig = UAPIRetryConfig()


class StorageConfig(BaseModel):
    """存储配置."""

    sqlite_path: str = "spide_data.db"
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "spide:"


class Settings(BaseModel):
    """全局配置根模型."""

    llm: LLMConfig = LLMConfig()
    mqtt: MQTTConfig = MQTTConfig()
    uapi: UAPIConfig = UAPIConfig()
    storage: StorageConfig = StorageConfig()


# ---------------------------------------------------------------------------
# 配置加载逻辑
# ---------------------------------------------------------------------------

_DEFAULT_CONFIGS_DIR = Path("configs")


def _map_yaml_to_settings(filename: str, data: dict) -> dict:
    """将 YAML 文件的扁平结构映射到 Settings 层级.

    YAML 文件中的 key 直接对应 Settings 的子模型:
    - llm.yaml: common/text/vision/web_search → llm.*
    - mqtt.yaml: host/port/... 或 mqtt.host/... → mqtt.*
    - uapi.yaml: base_url/api_key/... 或 uapi.base_url/... → uapi.*
    - default.yaml: storage/... → storage.*

    自动检测：如果顶层已有 section key 则不重复包裹。
    """
    section_map = {
        "llm.yaml": "llm",
        "mqtt.yaml": "mqtt",
        "uapi.yaml": "uapi",
        "default.yaml": None,
    }

    section = section_map.get(filename)
    if section is None:
        return data

    # 如果顶层已有 section key，直接返回
    if section in data:
        return data

    return {section: data}


def _load_yaml(path: Path) -> dict:
    """加载单个 YAML 文件."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _merge_dicts(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def load_settings(
    *,
    configs_dir: Path | None = None,
    project_root: Path | None = None,
) -> Settings:
    """加载并合并所有配置文件.

    加载优先级:
    1. configs/default.yaml — 默认配置
    2. configs/llm.yaml — LLM 配置（敏感）
    3. configs/mqtt.yaml — MQTT 配置（敏感）
    4. configs/uapi.yaml — UAPI 配置（敏感）
    5. 环境变量覆盖（SPIDE_ 前缀）

    Args:
        configs_dir: 配置文件目录路径，默认为 project_root/configs
        project_root: 项目根目录，默认为当前工作目录

    Returns:
        合并后的 Settings 实例

    Raises:
        ConfigError: 配置校验失败
    """
    root = project_root or Path.cwd()
    cfg_dir = configs_dir or root / _DEFAULT_CONFIGS_DIR

    merged: dict = {}

    # 按优先级依次加载并合并
    for filename in ("default.yaml", "llm.yaml", "mqtt.yaml", "uapi.yaml"):
        file_data = _load_yaml(cfg_dir / filename)
        if file_data:
            # YAML 文件的顶层 key 需要映射到 Settings 对应的 section
            mapped = _map_yaml_to_settings(filename, file_data)
            merged = _merge_dicts(merged, mapped)

    # 环境变量覆盖
    env_overrides = _collect_env_overrides()
    if env_overrides:
        merged = _merge_dicts(merged, env_overrides)

    try:
        return Settings(**merged)
    except Exception as e:
        raise ConfigError(f"配置校验失败: {e}", detail=str(e)) from e


def _collect_env_overrides() -> dict:
    """收集 SPIDE_ 前缀的环境变量作为配置覆盖.

    格式: SPIDE_SECTION__KEY=value
    示例: SPIDE_LLM__COMMON__API_KEY=xxx → {llm: {common: {api_key: "xxx"}}}
    """
    result: dict = {}
    prefix = "SPIDE_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        # SPIDE_LLM__COMMON__API_KEY → ["LLM", "COMMON", "API_KEY"]
        parts = key[len(prefix) :].lower().split("__")
        d = result
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = value
    return result
