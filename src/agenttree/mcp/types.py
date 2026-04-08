"""MCP configuration types."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class McpServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    name: str
    transport: Literal["stdio", "sse"] = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
