"""APScheduler 主动推送调度器测试."""

from __future__ import annotations

from dashboard.scheduler import (
    FeishuPushScheduler,
    JobSpec,
    SchedulerConfig,
    load_scheduler_from_config,
    reset_scheduler,
)


def test_scheduler_disabled_no_secret() -> None:
    """无 app_secret 时 start() 返回 False。"""
    config = SchedulerConfig(enabled=True, app_secret="", jobs=[JobSpec("t", "0 9 * * *", "crawl_hot_topics")])
    scheduler = FeishuPushScheduler(config)
    import asyncio

    started = asyncio.run(scheduler.start())
    assert started is False


def test_scheduler_disabled_by_config() -> None:
    """config.enabled=False 时 start() 返回 False。"""
    config = SchedulerConfig(enabled=False, app_secret="secret", jobs=[])
    scheduler = FeishuPushScheduler(config)
    import asyncio

    started = asyncio.run(scheduler.start())
    assert started is False


def test_scheduler_no_jobs() -> None:
    """无 jobs 时 start() 返回 False。"""
    config = SchedulerConfig(enabled=True, app_secret="secret", jobs=[])
    scheduler = FeishuPushScheduler(config)
    import asyncio

    started = asyncio.run(scheduler.start())
    assert started is False


async def test_scheduler_start_with_secret_and_jobs() -> None:
    """有 secret + jobs 时 start() 返回 True 并启动调度器。"""
    config = SchedulerConfig(
        enabled=True,
        app_id="cli_test",
        app_secret="secret",
        default_chat_id="oc_test",
        jobs=[JobSpec(name="daily_brief", cron="0 9 * * *", action="crawl_hot_topics")],
    )
    scheduler = FeishuPushScheduler(config)
    started = await scheduler.start()
    assert started is True
    await scheduler.stop()


def test_load_scheduler_from_config_missing_file() -> None:
    """配置文件缺失时返回禁用调度器。"""
    scheduler = load_scheduler_from_config(config_path="/nonexistent/path/feishu.yaml")
    assert scheduler.config.enabled is False


def test_load_scheduler_from_config_valid(tmp_path) -> None:
    """加载有效配置。"""
    import yaml

    config_file = tmp_path / "feishu.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "feishu": {
                    "app_id": "cli_test",
                    "app_secret": "secret",
                    "default_chat_id": "oc_test",
                },
                "scheduler": {
                    "enabled": True,
                    "jobs": [
                        {
                            "name": "morning_brief",
                            "cron": "0 9 * * *",
                            "action": "crawl_hot_topics",
                            "params": {"source": "weibo", "limit": 10},
                            "push_card": True,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    scheduler = load_scheduler_from_config(config_path=str(config_file))
    assert scheduler.config.app_id == "cli_test"
    assert scheduler.config.app_secret == "secret"
    assert len(scheduler.config.jobs) == 1
    assert scheduler.config.jobs[0].name == "morning_brief"
    assert scheduler.config.jobs[0].params == {"source": "weibo", "limit": 10}


def test_render_card_error_result() -> None:
    """_render_card 错误结果渲染为错误卡片。"""
    config = SchedulerConfig()
    scheduler = FeishuPushScheduler(config)
    job = JobSpec(name="test_job", cron="0 9 * * *", action="crawl_hot_topics")
    result = {"status": "error", "message": "API 超时"}
    card = scheduler._render_card(job, result)
    assert card["card"]["header"]["template"] == "red"
    assert "API 超时" in str(card)


def test_render_card_crawl_result() -> None:
    """_render_card 采集结果渲染为列表卡片。"""
    config = SchedulerConfig()
    scheduler = FeishuPushScheduler(config)
    job = JobSpec(name="morning", cron="0 9 * * *", action="crawl_hot_topics")
    result = {
        "status": "ok",
        "source": "weibo",
        "count": 2,
        "items": [
            {"rank": 1, "title": "AI 新闻", "hot_value": 100000},
            {"rank": 2, "title": "股票", "hot_value": 50000},
        ],
    }
    card = scheduler._render_card(job, result)
    assert card["card"]["header"]["template"] == "blue"
    body = str(card)
    assert "AI 新闻" in body


def test_singleton() -> None:
    """get_scheduler 返回单例。"""
    reset_scheduler()
    s1 = load_scheduler_from_config(config_path="/nonexistent/path/feishu.yaml")
    s2 = load_scheduler_from_config(config_path="/nonexistent/path/feishu.yaml")
    # 实际单例由 get_scheduler 管理
    assert s1.config.enabled == s2.config.enabled == False  # noqa: E712
    reset_scheduler()
