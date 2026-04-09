"""Task data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class TaskType(str, Enum):
    SHELL = "shell"
    WORKFLOW = "workflow"


class TaskRecord(BaseModel):
    """A background task record."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    type: TaskType
    state: TaskState = TaskState.PENDING
    description: str = ""

    # Shell task fields
    command: str | None = None
    cwd: str | None = None

    # Workflow task fields
    workflow_name: str | None = None
    workflow_context: str | None = None

    # Lifecycle
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None

    # Output
    output_path: Path | None = None
