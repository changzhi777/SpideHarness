"""敏感信息占位符解析器.

支持在 YAML / 配置文件中使用 ``${ENV_VAR}`` 或 ``${ENV_VAR:default}`` 形式的占位符,
加载时从环境变量注入真实值,避免密钥硬编码到仓库.

典型用法:

.. code-block:: yaml

    feishu:
      app_id: cli_xxxxxxxxxxxx
      app_secret: ${SPIDE_FEISHU__APP_SECRET}    # 必填,无默认值
      encrypt_key: ${SPIDE_FEISHU__ENCRYPT_KEY:}  # 选填,默认空字符串

约定:
- ``${X}``  : 必填,缺失时抛出 :class:`SecretError`.
- ``${X:}`` 或 ``${X:default}`` : 选填,缺失时使用 default.
- 字符串内若不含 ``${`` 则原样返回(零开销).
"""

from __future__ import annotations

import os
import re
from typing import Final

_PLACEHOLDER_RE: Final[re.Pattern[str]] = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")


class SecretError(RuntimeError):
    """敏感信息占位符解析失败."""


def resolve_secrets(value: str) -> str:
    """解析字符串中的 ``${ENV_VAR[:default]}`` 占位符.

    Args:
        value: 待解析字符串(来自 YAML / JSON / 环境)

    Returns:
        替换后的字符串

    Raises:
        SecretError: 占位符引用的环境变量未设置且无默认值
    """
    if not isinstance(value, str) or "${" not in value:
        return value

    def _replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)
        env_val = os.environ.get(var_name)
        if env_val is not None and env_val != "":
            return env_val
        if default is not None:
            return default
        raise SecretError(
            f"必需的环境变量未设置: {var_name} (可在 YAML 中使用 ${{{var_name}:<default>}} 提供默认值)"
        )

    return _PLACEHOLDER_RE.sub(_replace, value)


def resolve_secrets_in_obj(obj: object) -> object:
    """递归解析 dict / list / str 中的占位符.

    Args:
        obj: 任意 Python 对象(YAML 加载后的结构)

    Returns:
        解析后的新对象(不修改入参)
    """
    if isinstance(obj, str):
        return resolve_secrets(obj)
    if isinstance(obj, dict):
        return {k: resolve_secrets_in_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_secrets_in_obj(v) for v in obj]
    return obj


def required_env(name: str) -> str:
    """获取必需的环境变量,缺失时抛出 :class:`SecretError`."""
    val = os.environ.get(name)
    if not val:
        raise SecretError(f"必需的环境变量未设置: {name}")
    return val
