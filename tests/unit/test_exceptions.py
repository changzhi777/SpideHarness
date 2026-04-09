# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 异常层级."""

from spide.exceptions import (
    ConfigError,
    LLMError,
    MCPError,
    MQTTError,
    SpideError,
    SpiderError,
    StorageError,
    WorkspaceError,
)


class TestExceptionHierarchy:
    """所有业务异常继承自 SpideError."""

    def test_base(self):
        assert issubclass(ConfigError, SpideError)
        assert issubclass(StorageError, SpideError)
        assert issubclass(SpiderError, SpideError)
        assert issubclass(MCPError, SpideError)
        assert issubclass(MQTTError, SpideError)
        assert issubclass(LLMError, SpideError)
        assert issubclass(WorkspaceError, SpideError)

    def test_spide_error_inherits_exception(self):
        assert issubclass(SpideError, Exception)

    def test_catch_all_with_base(self):
        try:
            raise StorageError("test")
        except SpideError as e:
            assert str(e) == "test"
