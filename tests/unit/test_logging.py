# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 日志系统."""

import logging
from pathlib import Path

import pytest
import structlog

from spide.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logging():
    """每个测试前重置 structlog 缓存."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


class TestGetLogger:
    """get_logger 测试."""

    def test_returns_logger(self):
        configure_logging()
        log = get_logger("test_module")
        assert log is not None

    def test_default_name(self):
        configure_logging()
        log = get_logger()
        assert log is not None

    def test_logger_can_log(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        configure_logging(log_file=str(log_file))
        log = get_logger("test_write")
        log.info("marker_hello")
        content = log_file.read_text()
        assert "marker_hello" in content


class TestConfigureLogging:
    """configure_logging 测试."""

    def test_default_level(self):
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_debug_level(self):
        configure_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_warning_level(self):
        configure_logging(level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_json_format(self):
        configure_logging(json_format=True)
        log = get_logger("test_json")
        assert log is not None

    def test_with_file(self, tmp_path: Path):
        log_file = tmp_path / "test.log"
        configure_logging(log_file=str(log_file))
        log = get_logger("test_file")
        log.info("log_test_marker")
        assert log_file.exists()
        content = log_file.read_text()
        assert "log_test_marker" in content

    def test_reconfigure_updates_level(self):
        configure_logging(level="DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        configure_logging(level="WARNING")
        assert logging.getLogger().level == logging.WARNING

    def test_stderr_handler_present(self):
        configure_logging()
        root = logging.getLogger()
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1
