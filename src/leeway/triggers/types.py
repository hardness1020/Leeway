"""Trigger type definitions."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from leeway.cron.types import CronAction


class TriggerDefinition(BaseModel):
    """A webhook trigger that fires an action when called."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    secret: str = Field(default_factory=lambda: secrets.token_urlsafe(24))
    action: CronAction
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: datetime | None = None
    trigger_count: int = 0
