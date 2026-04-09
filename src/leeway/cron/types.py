"""Cron job data models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Schedule specs ──────────────────────────────────────────────────

class CronScheduleSpec(BaseModel):
    """Standard cron expression schedule."""

    kind: Literal["cron"] = "cron"
    expression: str = Field(description="Cron expression (e.g. '*/5 * * * *')")


class IntervalSchedule(BaseModel):
    """Run every N seconds."""

    kind: Literal["interval"] = "interval"
    seconds: int = Field(gt=0, description="Interval in seconds")


class OneShotSchedule(BaseModel):
    """Run once at a specific time."""

    kind: Literal["once"] = "once"
    at: datetime


ScheduleSpec = Annotated[
    CronScheduleSpec | IntervalSchedule | OneShotSchedule,
    Field(discriminator="kind"),
]


# ── Actions ─────────────────────────────────────────────────────────

class WorkflowAction(BaseModel):
    """Execute a workflow."""

    kind: Literal["workflow"] = "workflow"
    workflow_name: str
    context: str = ""


class ShellAction(BaseModel):
    """Execute a shell command."""

    kind: Literal["shell"] = "shell"
    command: str
    cwd: str | None = None


class WebhookAction(BaseModel):
    """Send an HTTP request."""

    kind: Literal["webhook"] = "webhook"
    url: str
    method: str = "POST"
    body: dict[str, object] = Field(default_factory=dict)


CronAction = Annotated[
    WorkflowAction | ShellAction | WebhookAction,
    Field(discriminator="kind"),
]


# ── Job record ──────────────────────────────────────────────────────

class CronJob(BaseModel):
    """A scheduled job."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    schedule: ScheduleSpec
    action: CronAction
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0
    last_status: str | None = None
