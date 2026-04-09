# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 配置加载模块."""



from spide.config import (
    Settings,
    UAPIConfig,
    _map_yaml_to_settings,
    _merge_dicts,
    load_settings,
)


class TestConfigModels:
    """配置模型默认值."""

    def test_settings_defaults(self):
        s = Settings()
        assert s.llm.text.model == "glm-5.1"
        assert s.llm.vision.model == "glm-5v-turbo"
        assert s.mqtt.port == 8883
        assert s.storage.sqlite_path == "spide_data.db"

    def test_uapi_config_defaults(self):
        c = UAPIConfig()
        assert c.timeout == 30
        assert c.rate_limit.max_concurrent == 5
        assert c.retry.max_retries == 3


class TestYamlMapping:
    """YAML 文件到 Settings 层级映射."""

    def test_llm_yaml_wrapping(self):
        data = {"common": {"api_key": "test"}, "text": {"model": "glm-5.1"}}
        result = _map_yaml_to_settings("llm.yaml", data)
        assert "llm" in result
        assert result["llm"]["common"]["api_key"] == "test"

    def test_llm_yaml_already_wrapped(self):
        data = {"llm": {"common": {"api_key": "test"}}}
        result = _map_yaml_to_settings("llm.yaml", data)
        # 不应双重包裹
        assert "llm" in result
        assert "common" in result["llm"]

    def test_mqtt_yaml_wrapping(self):
        data = {"mqtt": {"host": "test.local"}}
        result = _map_yaml_to_settings("mqtt.yaml", data)
        assert "mqtt" in result

    def test_default_yaml_passthrough(self):
        data = {"storage": {"sqlite_path": "test.db"}}
        result = _map_yaml_to_settings("default.yaml", data)
        assert result == data


class TestMergeDicts:
    """深度合并字典."""

    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _merge_dicts(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge(self):
        base = {"llm": {"common": {"api_key": "old"}, "text": {"model": "glm-5.1"}}}
        override = {"llm": {"common": {"api_key": "new"}}}
        result = _merge_dicts(base, override)
        assert result["llm"]["common"]["api_key"] == "new"
        assert result["llm"]["text"]["model"] == "glm-5.1"


class TestEnvOverrides:
    """环境变量覆盖."""

    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SPIDE_LLM__COMMON__API_KEY", "env-test-key")
        # 创建空配置目录避免加载真实配置
        cfg_dir = tmp_path / "configs"
        cfg_dir.mkdir()
        settings = load_settings(configs_dir=cfg_dir)
        assert settings.llm.common.api_key == "env-test-key"
