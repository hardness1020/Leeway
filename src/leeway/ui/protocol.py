"""Structured protocol models for the React TUI backend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from leeway.state.app_state import AppState


class FrontendRequest(BaseModel):
    """One request sent from the React frontend to the Python backend."""

    type: Literal["submit_line", "permission_response", "question_response", "cancel", "shutdown"]
    line: str | None = None
    request_id: str | None = None
    allowed: bool | None = None
    answer: str | None = None


class TranscriptItem(BaseModel):
    """One transcript row rendered by the frontend."""

    role: Literal["system", "user", "assistant", "tool", "tool_result", "log"]
    text: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    is_error: bool | None = None


class BackendEvent(BaseModel):
    """One event sent from the Python backend to the React frontend."""

    type: Literal[
        "ready",
        "state_snapshot",
        "transcript_item",
        "assistant_delta",
        "assistant_complete",
        "line_complete",
        "tool_started",
        "tool_completed",
        "clear_transcript",
        "modal_request",
        "select_request",
        "error",
        "shutdown",
    ]
    message: str | None = None
    item: TranscriptItem | None = None
    state: dict[str, Any] | None = None
    commands: list[str] | None = None
    modal: dict[str, Any] | None = None
    select_options: list[dict[str, Any]] | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    output: str | None = None
    is_error: bool | None = None

    @classmethod
    def ready(cls, state: AppState, commands: list[str] | None = None) -> "BackendEvent":
        return cls(
            type="ready",
            state=_state_payload(state),
            commands=commands or [],
        )

    @classmethod
    def state_snapshot(cls, state: AppState) -> "BackendEvent":
        return cls(type="state_snapshot", state=_state_payload(state))

    @classmethod
    def status_snapshot(cls, *, state: AppState) -> "BackendEvent":
        return cls(
            type="state_snapshot",
            state=_state_payload(state),
        )


def _state_payload(state: AppState) -> dict[str, Any]:
    return {
        "model": state.model,
        "cwd": state.cwd,
        "provider": state.provider,
        "auth_status": state.auth_status,
        "base_url": state.base_url,
        "permission_mode": _format_permission_mode(state.permission_mode),
        "theme": state.theme,
        "fast_mode": state.fast_mode,
        "effort": state.effort,
        "passes": state.passes,
        "input_tokens": state.input_tokens,
        "output_tokens": state.output_tokens,
        "session_start_ms": state.session_start_ms,
        "workflow_name": state.workflow_name,
        "workflow_node": state.workflow_node,
        "workflow_parallel_branches": state.workflow_parallel_branches,
    }


_MODE_LABELS = {
    "default": "Default",
    "plan": "Plan Mode",
    "full_auto": "Auto",
    "PermissionMode.DEFAULT": "Default",
    "PermissionMode.PLAN": "Plan Mode",
    "PermissionMode.FULL_AUTO": "Auto",
}


def _format_permission_mode(raw: str) -> str:
    return _MODE_LABELS.get(raw, raw)


__all__ = [
    "BackendEvent",
    "FrontendRequest",
    "TranscriptItem",
]
