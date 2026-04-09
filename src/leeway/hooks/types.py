"""Hook type definitions."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class HookEvent(str, Enum):
    BEFORE_TOOL_USE = "before_tool_use"
    AFTER_TOOL_USE = "after_tool_use"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"


class HookMatchSpec(BaseModel):
    """Conditions for when a hook should fire."""

    event: HookEvent
    tool_name: str | None = None
    workflow_name: str | None = None


class CommandHookDefinition(BaseModel):
    """A hook that runs a shell command."""

    type: Literal["command"] = "command"
    match: HookMatchSpec
    command: str
    timeout: int = 30


class HttpHookDefinition(BaseModel):
    """A hook that sends an HTTP request."""

    type: Literal["http"] = "http"
    match: HookMatchSpec
    url: str
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = 10


HookDefinition = Annotated[
    CommandHookDefinition | HttpHookDefinition,
    Field(discriminator="type"),
]
