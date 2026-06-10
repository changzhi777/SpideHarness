"""占位符解析器测试."""

from __future__ import annotations

import pytest

from dashboard.secrets import (
    SecretError,
    required_env,
    resolve_secrets,
    resolve_secrets_in_obj,
)


def test_resolve_passthrough_no_placeholder() -> None:
    """无占位符的字符串原样返回."""
    assert resolve_secrets("hello world") == "hello world"
    assert resolve_secrets("") == ""
    assert resolve_secrets("no placeholder here") == "no placeholder here"


def test_resolve_simple_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    """${ENV_VAR} 基础替换."""
    monkeypatch.setenv("MY_TEST_VAR", "secret_value_123")
    assert resolve_secrets("prefix-${MY_TEST_VAR}-suffix") == "prefix-secret_value_123-suffix"


def test_resolve_placeholder_missing_required() -> None:
    """必填占位符缺失时抛错."""
    import os

    os.environ.pop("SPIDE_REQUIRED_VAR", None)
    with pytest.raises(SecretError, match="SPIDE_REQUIRED_VAR"):
        resolve_secrets("${SPIDE_REQUIRED_VAR}")


def test_resolve_placeholder_with_default_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """${ENV_VAR:} 选填,默认空字符串."""
    import os

    os.environ.pop("SPIDE_OPTIONAL_VAR", None)
    assert resolve_secrets("${SPIDE_OPTIONAL_VAR:}") == ""


def test_resolve_placeholder_with_default_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """${ENV_VAR:default} 选填,使用默认值."""
    import os

    os.environ.pop("SPIDE_OPTIONAL_VAR", None)
    assert resolve_secrets("${SPIDE_OPTIONAL_VAR:fallback}") == "fallback"


def test_resolve_placeholder_with_default_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量已设置时,默认值被覆盖."""
    monkeypatch.setenv("SPIDE_OPTIONAL_VAR", "real_value")
    assert resolve_secrets("${SPIDE_OPTIONAL_VAR:fallback}") == "real_value"


def test_resolve_placeholder_treats_empty_as_missing() -> None:
    """环境变量为空字符串时,视为未设置(使用默认值)."""
    import os

    os.environ["SPIDE_EMPTY_VAR"] = ""
    assert resolve_secrets("${SPIDE_EMPTY_VAR:default}") == "default"


def test_resolve_multiple_placeholders(monkeypatch: pytest.MonkeyPatch) -> None:
    """多个占位符同时替换."""
    monkeypatch.setenv("VAR_A", "alpha")
    monkeypatch.setenv("VAR_B", "beta")
    assert resolve_secrets("${VAR_A}-${VAR_B}") == "alpha-beta"


def test_resolve_placeholder_without_closing_brace() -> None:
    """没有结束符 } 的占位符原样保留(非标准格式,容错)."""
    # ${X 没有 },正则不会匹配,原样返回
    result = resolve_secrets("prefix-${UNCLOSED suffix")
    assert result == "prefix-${UNCLOSED suffix"


def test_resolve_in_obj_dict() -> None:
    """字典递归解析."""
    import os

    os.environ["API_KEY"] = "secret123"
    data = {
        "app_id": "cli_xxx",
        "app_secret": "${API_KEY}",
        "nested": {"token": "${API_KEY:default}"},
    }
    result = resolve_secrets_in_obj(data)
    assert result == {
        "app_id": "cli_xxx",
        "app_secret": "secret123",
        "nested": {"token": "secret123"},
    }


def test_resolve_in_obj_list() -> None:
    """列表递归解析."""
    import os

    os.environ["ID"] = "42"
    data = ["static", "${ID}", {"key": "${ID:99}"}]
    result = resolve_secrets_in_obj(data)
    assert result == ["static", "42", {"key": "42"}]


def test_resolve_in_obj_preserves_non_strings() -> None:
    """非字符串原样保留(int / float / bool / None)."""
    data = {"port": 8765, "tls": True, "ratio": 0.5, "desc": None}
    assert resolve_secrets_in_obj(data) == data


def test_resolve_in_obj_yaml_realistic(monkeypatch: pytest.MonkeyPatch) -> None:
    """真实 YAML 结构(模拟 feishu.yaml)."""
    monkeypatch.setenv("SPIDE_FEISHU__APP_SECRET", "real_secret_abc")
    monkeypatch.setenv("SPIDE_FEISHU__ENCRYPT_KEY", "ek_123")

    data = {
        "feishu": {
            "app_id": "cli_976c6aaaa7adcbb",
            "app_secret": "${SPIDE_FEISHU__APP_SECRET}",
            "verification_token": "${SPIDE_FEISHU__VERIFICATION_TOKEN:}",
            "encrypt_key": "${SPIDE_FEISHU__ENCRYPT_KEY:}",
            "default_chat_id": "",
        },
        "llm": {
            "base_url": "http://localhost:8001",
            "api_key": "${SPIDE_LLM__LOCAL_API_KEY:EMPTY}",
        },
    }
    result = resolve_secrets_in_obj(data)
    assert result["feishu"]["app_secret"] == "real_secret_abc"
    assert result["feishu"]["verification_token"] == ""
    assert result["feishu"]["encrypt_key"] == "ek_123"
    assert result["llm"]["api_key"] == "EMPTY"


def test_required_env_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """required_env 正常返回."""
    monkeypatch.setenv("MY_REQ", "value")
    assert required_env("MY_REQ") == "value"


def test_required_env_missing() -> None:
    """required_env 缺失抛错."""
    import os

    os.environ.pop("MY_MISSING", None)
    with pytest.raises(SecretError, match="MY_MISSING"):
        required_env("MY_MISSING")
