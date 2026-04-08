"""Hook registry — stores and matches hook definitions."""

from __future__ import annotations

from agenttree.hooks.types import (
    CommandHookDefinition,
    HookEvent,
    HttpHookDefinition,
)


HookDef = CommandHookDefinition | HttpHookDefinition


class HookRegistry:
    """Stores hook definitions and finds matching hooks for events."""

    def __init__(self) -> None:
        self._hooks: list[HookDef] = []

    def register(self, hook: HookDef) -> None:
        self._hooks.append(hook)

    def get_matching(
        self,
        event: HookEvent,
        *,
        tool_name: str | None = None,
        workflow_name: str | None = None,
    ) -> list[HookDef]:
        """Return all hooks whose match spec matches the given event context."""
        matched: list[HookDef] = []
        for hook in self._hooks:
            m = hook.match
            if m.event != event:
                continue
            if m.tool_name is not None and m.tool_name != tool_name:
                continue
            if m.workflow_name is not None and m.workflow_name != workflow_name:
                continue
            matched.append(hook)
        return matched
