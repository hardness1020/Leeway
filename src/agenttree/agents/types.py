"""Agent spec types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Specification for spawning a subagent."""

    task: str = Field(description="The task/prompt for the subagent")
    tools: list[str] = Field(default_factory=list, description="Tool whitelist for the subagent")
    workflow: str | None = Field(default=None, description="Optional workflow to follow")
    cwd: str | None = Field(default=None, description="Working directory")
    isolation: Literal["none", "worktree"] = "none"
