"""Plugin manifest types."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """A plugin manifest loaded from plugin.json."""

    name: str
    version: str = "0.0.0"
    description: str = ""
    skills: list[str] = Field(default_factory=list)  # relative paths to .md files
    hooks: list[dict[str, Any]] = Field(default_factory=list)  # hook definitions
    mcp_servers: list[dict[str, Any]] = Field(default_factory=list)  # server configs
