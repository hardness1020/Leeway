"""Memory entry types."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A persistent memory entry stored as a markdown file."""

    name: str
    description: str = ""
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    path: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
