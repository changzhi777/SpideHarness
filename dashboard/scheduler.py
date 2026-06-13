"""APScheduler 主动推送调度器。

功能：
- 加载 configs/feishu.yaml 中的 cron jobs
- 定时执行工具（采集 / 分析）→ 渲染卡片 → 推送到飞书群
- 需要 app_secret 才能启用（获取 tenant_access_token）

无 app_secret 时：调度器禁用，日志提示。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, cast

import aiohttp
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .feishu_card import daily_brief_card, error_card, topics_list_card
from .secrets import resolve_secrets_in_obj
from .tool_router import call_tool

logger = structlog.get_logger(__name__)

_FEISHU_API = "https://open.feishu.cn/open-apis"


@dataclass
class JobSpec:
    """调度任务定义。"""

    name: str
    cron: str  # "0 9 * * *"
    action: str  # 工具名
    params: dict[str, Any] = field(default_factory=dict)
    push_card: bool = True
    target_chat_id: str = ""


@dataclass
class SchedulerConfig:
    """调度器配置。"""

    enabled: bool = True
    app_id: str = ""
    app_secret: str = ""
    default_chat_id: str = ""
    jobs: list[JobSpec] = field(default_factory=list)


class FeishuPushScheduler:
    """APScheduler 包装器 + 飞书推送。"""

    def __init__(self, config: SchedulerConfig) -> None:
        self.config = config
        self.scheduler: AsyncIOScheduler | None = None
        self._token: str = ""
        self._token_expires_at: float = 0.0

    async def start(self) -> bool:
        """启动调度器。返回是否成功启动。"""
        if not self.config.enabled:
            logger.info("scheduler_disabled")
            return False
        if not self.config.app_secret:
            logger.warning("scheduler_no_secret", reason="app_secret 缺失，主动推送禁用")
            return False
        if not self.config.jobs:
            logger.info("scheduler_no_jobs")
            return False

        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        for job in self.config.jobs:
            try:
                trigger = CronTrigger.from_crontab(job.cron, timezone="Asia/Shanghai")
                self.scheduler.add_job(
                    self._execute_job,
                    trigger=trigger,
                    args=[job],
                    id=job.name,
                    name=job.name,
                    replace_existing=True,
                )
                logger.info("scheduler_job_added", name=job.name, cron=job.cron)
            except Exception as exc:
                logger.error("scheduler_job_failed", name=job.name, error=str(exc))

        self.scheduler.start()
        logger.info("scheduler_started", jobs=len(self.scheduler.get_jobs()))
        return True

    async def stop(self) -> None:
        """停止调度器。"""
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            logger.info("scheduler_stopped")

    async def _execute_job(self, job: JobSpec) -> None:
        """执行单个 Job：工具调用 + 推送卡片。"""
        logger.info("job_triggered", name=job.name, action=job.action)
        try:
            result = await call_tool(job.action, job.params, timeout=120)

            if not job.push_card:
                logger.info("job_completed_no_push", name=job.name)
                return

            target = job.target_chat_id or self.config.default_chat_id
            if not target:
                logger.warning("job_no_target", name=job.name)
                return

            card = self._render_card(job, result)
            await self.push_card(target, card)
            logger.info("job_pushed", name=job.name, target=target)
        except Exception as exc:
            logger.error("job_failed", name=job.name, error=str(exc))

    def _render_card(self, job: JobSpec, result: dict[str, Any]) -> dict[str, Any]:
        """根据工具结果渲染卡片。"""
        if result.get("status") == "error":
            return error_card(
                title=f"任务失败：{job.name}", error=result.get("message", "未知错误")
            )

        if job.action == "crawl_hot_topics":
            return topics_list_card(
                title=f"📊 {job.name} | 热搜采集",
                source=result.get("source", "?"),
                items=result.get("items", []),
            )

        return daily_brief_card(
            title=f"📋 {job.name}",
            sections=[
                {"title": "执行状态", "content": f"`{result.get('status', '?')}`"},
                {"title": "数据", "content": str(result)[:500]},
            ],
        )

    async def _ensure_token(self) -> str:
        """获取 tenant_access_token（带缓存，提前 5 分钟过期）。"""
        now = time.time()
        if self._token and now < self._token_expires_at - 300:
            return self._token

        url = f"{_FEISHU_API}/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}

        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
            session.post(url, json=payload) as resp,
        ):
            data = await resp.json()

        if data.get("code") != 0:
            logger.error("feishu_token_failed", data=data)
            raise RuntimeError(f"获取 tenant_access_token 失败: {data}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = now + int(data.get("expire", 7200))
        logger.info("feishu_token_refreshed", expires_in=int(data.get("expire", 7200)))
        return self._token

    async def push_card(self, chat_id: str, card: dict[str, Any]) -> dict[str, Any]:
        """推送卡片到指定 chat_id。"""
        token = await self._ensure_token()
        url = f"{_FEISHU_API}/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {
            "receive_id": chat_id,
            "msg_type": card.get("msg_type", "interactive"),
            "content": _json_dumps(card.get("card", card)),
        }

        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session,
            session.post(url, json=payload, headers=headers) as resp,
        ):
            data = await resp.json()

        if data.get("code") != 0:
            logger.error("feishu_push_failed", data=data)
        return data


def _json_dumps(obj: Any) -> str:
    """JSON 序列化（飞书要求 content 是字符串）。"""
    import json

    return json.dumps(obj, ensure_ascii=False)


def load_scheduler_from_config(config_path: str = "configs/feishu.yaml") -> FeishuPushScheduler:
    """从 YAML 加载配置并构建调度器。"""
    from pathlib import Path

    import yaml

    path = Path(config_path)
    if not path.exists():
        logger.warning("scheduler_config_missing", path=str(path))
        return FeishuPushScheduler(SchedulerConfig(enabled=False))

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 解析 ${ENV_VAR[:default]} 占位符（app_secret 等敏感字段）
    data = cast(dict[str, Any], resolve_secrets_in_obj(data))

    feishu = data.get("feishu", {})
    sched = data.get("scheduler", {})

    jobs = [
        JobSpec(
            name=j.get("name", ""),
            cron=j.get("cron", "0 9 * * *"),
            action=j.get("action", ""),
            params=j.get("params") or {},
            push_card=bool(j.get("push_card", True)),
            target_chat_id=j.get("target_chat_id", ""),
        )
        for j in sched.get("jobs", [])
    ]

    config = SchedulerConfig(
        enabled=bool(sched.get("enabled", True)),
        app_id=feishu.get("app_id", ""),
        app_secret=feishu.get("app_secret", ""),
        default_chat_id=feishu.get("default_chat_id", ""),
        jobs=jobs,
    )
    return FeishuPushScheduler(config)


_scheduler: FeishuPushScheduler | None = None


def get_scheduler(config_path: str = "configs/feishu.yaml") -> FeishuPushScheduler:
    """获取全局调度器单例。"""
    global _scheduler
    if _scheduler is None:
        _scheduler = load_scheduler_from_config(config_path)
    return _scheduler


def reset_scheduler() -> None:
    """重置调度器（测试用）。"""
    global _scheduler
    _scheduler = None


async def main_loop() -> None:
    """独立运行入口（用于测试）。"""
    scheduler = get_scheduler()
    started = await scheduler.start()
    if not started:
        logger.warning("scheduler_not_started")
        return
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await scheduler.stop()
