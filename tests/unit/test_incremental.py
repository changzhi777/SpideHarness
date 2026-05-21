# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""单元测试 — 增量检测器."""

from spide.spider.incremental import IncrementalDetector
from spide.storage.models import (
    CrawlSnapshot,
    HotTopic,
    HotTopicChange,
    TopicSource,
    TopicStatus,
)


def _make_topic(title: str, hot_value: int = 1000, rank: int | None = None) -> HotTopic:
    return HotTopic(
        title=title,
        source=TopicSource.WEIBO,
        hot_value=hot_value,
        rank=rank,
    )


class TestDetectChanges:
    """detect_changes 测试."""

    def test_new_topics(self):
        detector = IncrementalDetector()
        current = [_make_topic("AI突破", 5000)]
        previous = []

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        assert len(changes) == 1
        assert changes[0].status == TopicStatus.NEW
        assert changes[0].title == "AI突破"

    def test_dropped_topics(self):
        detector = IncrementalDetector()
        current = []
        previous = [_make_topic("旧热搜", 3000)]

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        assert len(changes) == 1
        assert changes[0].status == TopicStatus.DROPPED

    def test_rising_topic(self):
        detector = IncrementalDetector()
        current = [_make_topic("热点", 5000)]
        previous = [_make_topic("热点", 3000)]

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        assert len(changes) == 1
        assert changes[0].status == TopicStatus.RISING
        assert changes[0].hot_value_change == 2000

    def test_falling_topic(self):
        detector = IncrementalDetector()
        current = [_make_topic("热点", 1000)]
        previous = [_make_topic("热点", 5000)]

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        assert len(changes) == 1
        assert changes[0].status == TopicStatus.FALLING

    def test_stable_topic(self):
        detector = IncrementalDetector()
        current = [_make_topic("热点", 1005)]
        previous = [_make_topic("热点", 1000)]

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        assert len(changes) == 1
        assert changes[0].status == TopicStatus.STABLE

    def test_mixed_changes(self):
        detector = IncrementalDetector()
        current = [
            _make_topic("新话题", 5000),
            _make_topic("继续", 1200),
            _make_topic("下跌", 500),
        ]
        previous = [
            _make_topic("继续", 1000),
            _make_topic("下跌", 2000),
            _make_topic("掉榜", 3000),
        ]

        changes = detector.detect_changes(current, previous, TopicSource.WEIBO)
        statuses = {c.title: c.status for c in changes}
        assert statuses["新话题"] == TopicStatus.NEW
        assert statuses["继续"] == TopicStatus.RISING
        assert statuses["下跌"] == TopicStatus.FALLING
        assert statuses["掉榜"] == TopicStatus.DROPPED

    def test_empty_both(self):
        detector = IncrementalDetector()
        changes = detector.detect_changes([], [], TopicSource.WEIBO)
        assert changes == []


class TestBuildSnapshot:
    """build_snapshot 测试."""

    def test_basic_snapshot(self):
        detector = IncrementalDetector()
        topics = [_make_topic("a"), _make_topic("b")]
        snapshot = detector.build_snapshot(topics, TopicSource.WEIBO)

        assert isinstance(snapshot, CrawlSnapshot)
        assert snapshot.total_topics == 2
        assert snapshot.source == TopicSource.WEIBO
        assert "weibo_" in snapshot.snapshot_key

    def test_snapshot_with_changes(self):
        detector = IncrementalDetector()
        changes = [
            HotTopicChange(title="a", source=TopicSource.WEIBO, status=TopicStatus.NEW),
            HotTopicChange(title="b", source=TopicSource.WEIBO, status=TopicStatus.RISING),
            HotTopicChange(title="c", source=TopicSource.WEIBO, status=TopicStatus.DROPPED),
        ]
        snapshot = detector.build_snapshot([_make_topic("a")], TopicSource.WEIBO, changes)
        assert snapshot.new_count == 1
        assert snapshot.rising_count == 1
        assert snapshot.dropped_count == 1


class TestGenerateDiffReport:
    """generate_diff_report 测试."""

    def test_report_structure(self):
        detector = IncrementalDetector()
        changes = [
            HotTopicChange(title="a", source=TopicSource.WEIBO, status=TopicStatus.NEW, current_hot_value=5000),
            HotTopicChange(title="b", source=TopicSource.WEIBO, status=TopicStatus.RISING, hot_value_change=1000),
            HotTopicChange(title="c", source=TopicSource.WEIBO, status=TopicStatus.STABLE),
        ]
        report = detector.generate_diff_report(changes)

        assert report["summary"]["total"] == 3
        assert report["summary"]["new"] == 1
        assert report["summary"]["rising"] == 1
        assert report["summary"]["stable"] == 1
        assert len(report["new"]) == 1
        assert report["new"][0]["title"] == "a"
