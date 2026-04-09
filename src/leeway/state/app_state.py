"""Minimal application state model."""

from __future__ import annotations

from dataclasses import dataclass, field


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

    # Token usage (updated after each turn)
    input_tokens: int = 0
    output_tokens: int = 0

    # Session timing (epoch ms, set once at startup)
    session_start_ms: float = 0.0

    # Active workflow state
    workflow_name: str = ""
    workflow_node: str = ""
    workflow_parallel_branches: list[str] = field(default_factory=list)
