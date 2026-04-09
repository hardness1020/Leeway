"""Tests for hook registry."""

from leeway.hooks.registry import HookRegistry
from leeway.hooks.types import CommandHookDefinition, HookEvent, HookMatchSpec, HttpHookDefinition


def test_match_by_event():
    registry = HookRegistry()
    hook = CommandHookDefinition(
        match=HookMatchSpec(event=HookEvent.BEFORE_TOOL_USE),
        command="echo before",
    )
    registry.register(hook)

    matched = registry.get_matching(HookEvent.BEFORE_TOOL_USE)
    assert len(matched) == 1
    assert matched[0].command == "echo before"

    assert registry.get_matching(HookEvent.AFTER_TOOL_USE) == []


def test_match_by_tool_name():
    registry = HookRegistry()
    hook = CommandHookDefinition(
        match=HookMatchSpec(event=HookEvent.AFTER_TOOL_USE, tool_name="bash"),
        command="echo after-bash",
    )
    registry.register(hook)

    assert len(registry.get_matching(HookEvent.AFTER_TOOL_USE, tool_name="bash")) == 1
    assert len(registry.get_matching(HookEvent.AFTER_TOOL_USE, tool_name="grep")) == 0


def test_match_by_workflow_name():
    registry = HookRegistry()
    hook = HttpHookDefinition(
        match=HookMatchSpec(event=HookEvent.WORKFLOW_START, workflow_name="deploy"),
        url="https://example.com/hook",
    )
    registry.register(hook)

    assert len(registry.get_matching(HookEvent.WORKFLOW_START, workflow_name="deploy")) == 1
    assert len(registry.get_matching(HookEvent.WORKFLOW_START, workflow_name="test")) == 0


def test_multiple_hooks():
    registry = HookRegistry()
    registry.register(
        CommandHookDefinition(
            match=HookMatchSpec(event=HookEvent.BEFORE_TOOL_USE),
            command="echo 1",
        )
    )
    registry.register(
        CommandHookDefinition(
            match=HookMatchSpec(event=HookEvent.BEFORE_TOOL_USE),
            command="echo 2",
        )
    )
    assert len(registry.get_matching(HookEvent.BEFORE_TOOL_USE)) == 2
