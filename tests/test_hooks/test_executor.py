"""Tests for hook executor."""

import pytest

from agenttree.hooks.executor import HookExecutor
from agenttree.hooks.registry import HookRegistry
from agenttree.hooks.types import CommandHookDefinition, HookEvent, HookMatchSpec


@pytest.fixture
def registry_with_command_hook():
    registry = HookRegistry()
    registry.register(
        CommandHookDefinition(
            match=HookMatchSpec(event=HookEvent.BEFORE_TOOL_USE),
            command="echo hook_fired",
            timeout=5,
        )
    )
    return registry


@pytest.mark.asyncio
async def test_command_hook_fires(registry_with_command_hook):
    executor = HookExecutor(registry_with_command_hook)
    # Should not raise
    await executor.execute_hooks(
        HookEvent.BEFORE_TOOL_USE,
        {"tool_name": "bash"},
        tool_name="bash",
    )


@pytest.mark.asyncio
async def test_no_hooks_no_error():
    registry = HookRegistry()
    executor = HookExecutor(registry)
    await executor.execute_hooks(HookEvent.AFTER_TOOL_USE, {})


@pytest.mark.asyncio
async def test_hook_error_does_not_propagate():
    registry = HookRegistry()
    registry.register(
        CommandHookDefinition(
            match=HookMatchSpec(event=HookEvent.BEFORE_TOOL_USE),
            command="exit 1",  # will fail
            timeout=5,
        )
    )
    executor = HookExecutor(registry)
    # Should not raise even though the command fails
    await executor.execute_hooks(HookEvent.BEFORE_TOOL_USE, {})
