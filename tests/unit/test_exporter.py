# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 多格式数据导出器."""

import json
from pathlib import Path

import pytest

from spide.exceptions import StorageError
from spide.storage.exporter import DataExporter
from spide.storage.models import HotTopic


def _make_topics(n: int = 3) -> list[HotTopic]:
    """构造测试用 HotTopic 列表."""
    topics = []
    for i in range(n):
        topics.append(
            HotTopic(
                title=f"测试话题 {i}",
                hot_value=1000 * (n - i),
                rank=i + 1,
                source="weibo",
                url=f"https://weibo.com/{i}",
            )
        )
    return topics


class TestDataExporter:
    """多格式导出器."""

    async def test_export_json(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export_json(topics, filename="test")

        assert filepath.exists()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert len(data) == 3
        assert data[0]["title"] == "测试话题 0"

    async def test_export_jsonl(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export_jsonl(topics, filename="test")

        assert filepath.exists()
        lines = filepath.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        parsed = json.loads(lines[0])
        assert "title" in parsed

    async def test_export_csv(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export_csv(topics, filename="test")

        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8-sig")
        lines = [line for line in content.strip().splitlines() if line]
        assert len(lines) == 4  # header + 3 data rows

    async def test_export_csv_empty(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        with pytest.raises(StorageError):
            await exporter.export_csv([], filename="test")

    async def test_export_excel(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export_excel(topics, filename="test")

        assert filepath.exists()
        assert filepath.suffix == ".xlsx"
        assert filepath.stat().st_size > 0

    async def test_export_excel_empty(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        with pytest.raises(StorageError):
            await exporter.export_excel([], filename="test")

    async def test_export_unified_json(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export(topics, filename="test", fmt="json")
        assert filepath.suffix == ".json"

    async def test_export_unified_csv(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export(topics, filename="test", fmt="csv")
        assert filepath.suffix == ".csv"

    async def test_export_unified_xlsx_alias(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        filepath = await exporter.export(topics, filename="test", fmt="xlsx")
        assert filepath.suffix == ".xlsx"

    async def test_export_unsupported_format(self, tmp_path: Path):
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        topics = _make_topics()
        with pytest.raises(Exception, match="不支持的导出格式"):
            await exporter.export(topics, filename="test", fmt="xml")

    async def test_export_creates_directory(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c"
        exporter = DataExporter(output_dir=str(nested))
        topics = _make_topics()
        filepath = await exporter.export_json(topics, filename="test")
        assert nested.exists()
        assert filepath.exists()

    async def test_export_json_with_extra_field(self, tmp_path: Path):
        """导出包含 extra dict 字段的数据."""
        topic = HotTopic(
            title="测试",
            hot_value=999,
            source="weibo",
            extra={"note": "complex", "tags": ["AI"]},
        )
        exporter = DataExporter(output_dir=str(tmp_path / "out"))
        filepath = await exporter.export_json([topic], filename="test")

        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["title"] == "测试"
        assert data[0]["extra"]["note"] == "complex"
