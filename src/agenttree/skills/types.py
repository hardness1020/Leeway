"""Skill definition model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """A skill loaded from a markdown file with YAML frontmatter."""

    name: str
    description: str = ""
    content: str
    source: Literal["bundled", "user", "project", "plugin"] = "project"
    path: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
