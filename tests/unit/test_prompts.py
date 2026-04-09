# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — Prompt 层叠系统."""

from pathlib import Path


class TestBuildPrompt:
    """Prompt 组装."""

    def test_base_always_present(self, tmp_workspace: Path):
        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(workspace=str(tmp_workspace))
        assert "Spide Agent" in prompt
        assert "热点新闻" in prompt

    def test_extra_prompt(self, tmp_workspace: Path):
        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(
            workspace=str(tmp_workspace),
            extra_prompt="自定义：只采科技新闻",
        )
        assert "只采科技新闻" in prompt

    def test_soul_file_included(self, tmp_workspace: Path):
        from spide.workspace import get_soul_path

        soul = get_soul_path(tmp_workspace)
        soul.write_text("我的灵魂：抓取一切热点", encoding="utf-8")

        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(workspace=str(tmp_workspace))
        assert "我的灵魂" in prompt

    def test_no_soul_file(self, tmp_workspace: Path):
        from spide.workspace import get_soul_path

        soul = get_soul_path(tmp_workspace)
        soul.unlink()

        from spide.prompts import build_system_prompt

        prompt = build_system_prompt(workspace=str(tmp_workspace))
        assert "热点新闻" in prompt  # 基础指令仍在
