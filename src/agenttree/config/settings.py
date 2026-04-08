"""Settings model and loading logic for AgentTree.

Settings are resolved with the following precedence (highest first):
1. CLI arguments
2. Environment variables (ANTHROPIC_API_KEY, AGENTTREE_MODEL, etc.)
3. Config file (~/.agenttree/settings.json)
4. Defaults
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agenttree.permissions.modes import PermissionMode


class PathRuleConfig(BaseModel):
    """A glob-pattern path permission rule."""

    pattern: str
    allow: bool = True


class PermissionSettings(BaseModel):
    """Permission mode configuration."""

    mode: PermissionMode = PermissionMode.DEFAULT
    allowed_tools: list[str] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    path_rules: list[PathRuleConfig] = Field(default_factory=list)
    denied_commands: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    """Main settings model for AgentTree."""

    # API configuration
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 16384
    base_url: str | None = None
    api_format: str = "anthropic"  # "anthropic" or "openai"

    # Behavior
    system_prompt: str | None = None
    permission: PermissionSettings = Field(default_factory=PermissionSettings)

    # Hooks — list of hook definition dicts (parsed at runtime)
    hooks: list[dict[str, Any]] = Field(default_factory=list)

    # MCP servers — list of server config dicts
    mcp_servers: list[dict[str, Any]] = Field(default_factory=list)

    # UI
    theme: str = "default"
    fast_mode: bool = False
    effort: str = "medium"
    passes: int = 1
    verbose: bool = False

    def resolve_api_key(self) -> str:
        """Resolve API key with precedence: instance value > env var > empty.

        Returns the API key string. Raises ValueError if no key is found.
        """
        if self.api_key:
            return self.api_key

        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key:
            return env_key

        # Also check OPENAI_API_KEY for openai-format providers
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            return openai_key

        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY (or OPENAI_API_KEY for openai-format "
            "providers) environment variable, or configure api_key in "
            "~/.agenttree/settings.json"
        )

    def merge_cli_overrides(self, **overrides: Any) -> Settings:
        """Return a new Settings with CLI overrides applied (non-None values only)."""
        updates = {k: v for k, v in overrides.items() if v is not None}
        return self.model_copy(update=updates)


def _apply_env_overrides(settings: Settings) -> Settings:
    """Apply supported environment variable overrides over loaded settings."""
    updates: dict[str, Any] = {}
    model = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("AGENTTREE_MODEL")
    if model:
        updates["model"] = model

    base_url = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("AGENTTREE_BASE_URL")
    if base_url:
        updates["base_url"] = base_url

    max_tokens = os.environ.get("AGENTTREE_MAX_TOKENS")
    if max_tokens:
        updates["max_tokens"] = int(max_tokens)

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        updates["api_key"] = api_key

    api_format = os.environ.get("AGENTTREE_API_FORMAT")
    if api_format:
        updates["api_format"] = api_format

    if not updates:
        return settings
    return settings.model_copy(update=updates)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from config file, merging with defaults."""
    if config_path is None:
        from agenttree.config.paths import get_config_file_path

        config_path = get_config_file_path()

    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return _apply_env_overrides(Settings.model_validate(raw))

    return _apply_env_overrides(Settings())


def save_settings(settings: Settings, config_path: Path | None = None) -> None:
    """Persist settings to the config file."""
    if config_path is None:
        from agenttree.config.paths import get_config_file_path

        config_path = get_config_file_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        settings.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
