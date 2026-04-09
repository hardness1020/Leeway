"""Parallel execution models for workflow branches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from agenttree.workflow.types import ConditionSpec


class BranchSpec(BaseModel):
    """One branch in a parallel node — like NodeSpec but no edges, plus a condition."""

    when: ConditionSpec | Literal["always"] = "always"
    prompt: str
    tools: list[str] = Field(default_factory=list)
    max_turns: int = 50
    skills: list[str] = Field(default_factory=list)
    hooks: list[dict[str, Any]] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    requires_approval: bool = Field(False, description="Gate: ask user before executing")

    @model_validator(mode="after")
    def _normalise_always(self) -> BranchSpec:
        if self.when == "always":
            object.__setattr__(self, "when", ConditionSpec(always=True))
        return self

    @property
    def condition(self) -> ConditionSpec:
        assert isinstance(self.when, ConditionSpec)
        return self.when


class ParallelSpec(BaseModel):
    """Parallel execution specification within a node."""

    branches: dict[str, BranchSpec]
    timeout: int = Field(600, description="Seconds to wait for all triggered branches")

    @model_validator(mode="after")
    def _validate_branches(self) -> ParallelSpec:
        if not self.branches:
            raise ValueError("Parallel spec must have at least one branch")
        return self


@dataclass
class BranchResult:
    """Outcome of one parallel branch execution."""

    branch_name: str
    triggered: bool = True
    approved: bool = True
    final_text: str = ""
    tools_called: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    turns_used: int = 0
