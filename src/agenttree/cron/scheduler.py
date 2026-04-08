"""Cron scheduler — checks jobs and fires them when due."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from agenttree.cron.store import CronStore
from agenttree.cron.types import (
    CronJob,
    CronScheduleSpec,
    IntervalSchedule,
    OneShotSchedule,
    ShellAction,
    WebhookAction,
    WorkflowAction,
)
from agenttree.tasks.manager import BackgroundTaskManager

logger = logging.getLogger(__name__)


def compute_next_run(job: CronJob) -> datetime | None:
    """Compute the next run time for a job based on its schedule."""
    now = datetime.now(timezone.utc)
    schedule = job.schedule

    if isinstance(schedule, OneShotSchedule):
        if job.run_count > 0:
            return None  # Already ran
        at = schedule.at
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return at if at > now else None

    if isinstance(schedule, IntervalSchedule):
        if job.last_run is None:
            return now
        return job.last_run.replace(tzinfo=timezone.utc) + __import__("datetime").timedelta(
            seconds=schedule.seconds
        )

    if isinstance(schedule, CronScheduleSpec):
        try:
            from croniter import croniter

            base = job.last_run or now
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            cron = croniter(schedule.expression, base)
            return cron.get_next(datetime).replace(tzinfo=timezone.utc)
        except Exception:
            logger.warning("Invalid cron expression: %s", schedule.expression)
            return None

    return None


class CronScheduler:
    """Periodically checks cron jobs and fires them when due."""

    def __init__(
        self,
        store: CronStore,
        task_manager: BackgroundTaskManager,
        check_interval: float = 30.0,
    ) -> None:
        self._store = store
        self._task_manager = task_manager
        self._check_interval = check_interval
        self._running = False

    async def run(self) -> None:
        """Main scheduler loop — runs until stopped."""
        self._running = True
        logger.info("Cron scheduler started (check every %.0fs)", self._check_interval)
        while self._running:
            await self._tick()
            await asyncio.sleep(self._check_interval)

    def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        """Check all enabled jobs and fire those that are due."""
        now = datetime.now(timezone.utc)
        for job in self._store.list(enabled_only=True):
            next_run = job.next_run
            if next_run is None:
                next_run = compute_next_run(job)
                if next_run is None:
                    continue
                job.next_run = next_run
                self._store.save(job)

            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            if next_run <= now:
                await self._fire_job(job)

    async def _fire_job(self, job: CronJob) -> None:
        """Execute a job's action."""
        logger.info("Firing cron job: %s (%s)", job.name, job.id)
        action = job.action
        try:
            if isinstance(action, ShellAction):
                await self._task_manager.create_shell_task(
                    command=action.command,
                    cwd=action.cwd,
                    description=f"cron:{job.name}",
                )
            elif isinstance(action, WorkflowAction):
                await self._task_manager.create_workflow_task(
                    workflow_name=action.workflow_name,
                    context=action.context,
                    description=f"cron:{job.name}",
                )
            elif isinstance(action, WebhookAction):
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.request(
                        method=action.method,
                        url=action.url,
                        json=action.body,
                    )
            job.last_status = "ok"
        except Exception as exc:
            logger.warning("Cron job %s failed: %s", job.name, exc)
            job.last_status = f"error: {exc}"

        job.last_run = datetime.now(timezone.utc)
        job.run_count += 1
        job.next_run = compute_next_run(job)
        self._store.save(job)
