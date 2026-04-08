"""Minimal application state model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppState:
    """Shared mutable UI/session state."""

    model: str
    permission_mode: str
    theme: str
    cwd: str = "."
    provider: str = "unknown"
    auth_status: str = "missing"
    base_url: str = ""
    fast_mode: bool = False
    effort: str = "medium"
    passes: int = 1
