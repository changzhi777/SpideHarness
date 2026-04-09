# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — Memory 管理."""

from pathlib import Path


class TestMemoryCRUD:
    """记忆增删查."""

    def test_add_creates_file(self, tmp_workspace: Path):
        from spide.memory import add_memory, list_memory_files

        add_memory(str(tmp_workspace), title="微博规则", content="每5分钟采集")
        files = list_memory_files(str(tmp_workspace))
        assert len(files) == 1

    def test_add_updates_index(self, tmp_workspace: Path):
        from spide.memory import add_memory
        from spide.workspace import get_memory_index_path

        add_memory(str(tmp_workspace), title="测试条目", content="内容")
        index = get_memory_index_path(tmp_workspace).read_text(encoding="utf-8")
        assert "测试条目" in index

    def test_remove(self, tmp_workspace: Path):
        from spide.memory import add_memory, list_memory_files, remove_memory

        add_memory(str(tmp_workspace), title="要删除的", content="内容")
        assert len(list_memory_files(str(tmp_workspace))) == 1

        assert remove_memory(str(tmp_workspace), name="要删除的") is True
        assert len(list_memory_files(str(tmp_workspace))) == 0

    def test_remove_nonexistent(self, tmp_workspace: Path):
        from spide.memory import remove_memory

        assert remove_memory(str(tmp_workspace), name="不存在") is False

    def test_append_mode(self, tmp_workspace: Path):
        from spide.memory import add_memory, get_memory_content

        add_memory(str(tmp_workspace), title="追加测试", content="第一段")
        add_memory(str(tmp_workspace), title="追加测试", content="第二段")

        content = get_memory_content(str(tmp_workspace), name="追加测试")
        assert "第一段" in content
        assert "第二段" in content

    def test_slug_generation(self, tmp_workspace: Path):
        from spide.memory import add_memory, list_memory_files

        add_memory(str(tmp_workspace), title="特殊@#字符!测试", content="内容")
        files = list_memory_files(str(tmp_workspace))
        assert len(files) == 1
        # slug 应只含合法字符
        assert files[0].suffix == ".md"

    def test_get_content_nonexistent(self, tmp_workspace: Path):
        from spide.memory import get_memory_content

        assert get_memory_content(str(tmp_workspace), name="不存在") is None
