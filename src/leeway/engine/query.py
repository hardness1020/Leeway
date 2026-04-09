"""Core tool-aware query loop."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Awaitable, Callable

from leeway.api.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
    SupportsStreamingMessages,
)
from leeway.api.usage import UsageSnapshot
from leeway.engine.messages import ConversationMessage, ToolResultBlock
from leeway.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    StreamEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)
from leeway.permissions.checker import PermissionChecker
from leeway.tools.base import ToolExecutionContext
from leeway.tools.base import ToolRegistry


PermissionPrompt = Callable[[str, str], Awaitable[bool]]
AskUserPrompt = Callable[[str], Awaitable[str]]


@dataclass
class QueryContext:
    """Context shared across a query run."""

    api_client: SupportsStreamingMessages
    tool_registry: ToolRegistry
    permission_checker: PermissionChecker
    cwd: Path
    model: str
    system_prompt: str
    max_tokens: int
    permission_prompt: PermissionPrompt | None = None
    ask_user_prompt: AskUserPrompt | None = None
    max_turns: int = 200
    tool_metadata: dict[str, object] | None = None
    turn_budget_warning: str | None = None
    """If set, inject this message as a user reminder when 2 turns remain."""


async def run_query(
    context: QueryContext,
    messages: list[ConversationMessage],
) -> AsyncIterator[tuple[StreamEvent, UsageSnapshot | None]]:
    """Run the conversation loop until the model stops requesting tools."""
    from leeway.services.compact import (
        AutoCompactState,
        auto_compact_if_needed,
    )

    compact_state = AutoCompactState()
    _budget_warned = False

    for turn_idx in range(context.max_turns):
        # --- turn budget warning ---
        if (
            not _budget_warned
            and context.turn_budget_warning
            and turn_idx >= context.max_turns - 2
        ):
            _budget_warned = True
            messages.append(
                ConversationMessage.from_user_text(context.turn_budget_warning)
            )
        # --- auto-compact check before calling the model ---------------
        messages, was_compacted = await auto_compact_if_needed(
            messages,
            api_client=context.api_client,
            model=context.model,
            system_prompt=context.system_prompt,
            state=compact_state,
        )
        # ---------------------------------------------------------------

        final_message: ConversationMessage | None = None
        usage = UsageSnapshot()

        async for event in context.api_client.stream_message(
            ApiMessageRequest(
                model=context.model,
                messages=messages,
                system_prompt=context.system_prompt,
                max_tokens=context.max_tokens,
                tools=context.tool_registry.to_api_schema(),
            )
        ):
            if isinstance(event, ApiTextDeltaEvent):
                yield AssistantTextDelta(text=event.text), None
                continue

            if isinstance(event, ApiMessageCompleteEvent):
                final_message = event.message
                usage = event.usage

        if final_message is None:
            raise RuntimeError("Model stream finished without a final message")

        messages.append(final_message)
        yield AssistantTurnComplete(message=final_message, usage=usage), usage

        if not final_message.tool_uses:
            return

        tool_calls = final_message.tool_uses

        if len(tool_calls) == 1:
            tc = tool_calls[0]
            yield ToolExecutionStarted(tool_name=tc.name, tool_input=tc.input), None
            result = await _execute_tool_call(context, tc.name, tc.id, tc.input)
            yield ToolExecutionCompleted(
                tool_name=tc.name,
                output=result.content,
                is_error=result.is_error,
            ), None
            tool_results = [result]
        else:
            for tc in tool_calls:
                yield ToolExecutionStarted(tool_name=tc.name, tool_input=tc.input), None

            async def _run(tc):
                return await _execute_tool_call(context, tc.name, tc.id, tc.input)

            results = await asyncio.gather(*[_run(tc) for tc in tool_calls])
            tool_results = list(results)

            for tc, result in zip(tool_calls, tool_results):
                yield ToolExecutionCompleted(
                    tool_name=tc.name,
                    output=result.content,
                    is_error=result.is_error,
                ), None

        messages.append(ConversationMessage(role="user", content=tool_results))

    raise RuntimeError(f"Exceeded maximum turn limit ({context.max_turns})")


async def _execute_tool_call(
    context: QueryContext,
    tool_name: str,
    tool_use_id: str,
    tool_input: dict[str, object],
) -> ToolResultBlock:
    tool = context.tool_registry.get(tool_name)
    if tool is None:
        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=f"Unknown tool: {tool_name}",
            is_error=True,
        )

    try:
        parsed_input = tool.input_model.model_validate(tool_input)
    except Exception as exc:
        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=f"Invalid input for {tool_name}: {exc}",
            is_error=True,
        )

    # Extract file_path and command for path-level permission checks
    _file_path = str(tool_input.get("file_path", "")) or None
    _command = str(tool_input.get("command", "")) or None
    decision = context.permission_checker.evaluate(
        tool_name,
        is_read_only=tool.is_read_only(parsed_input),
        file_path=_file_path,
        command=_command,
    )
    if not decision.allowed:
        if decision.requires_confirmation and context.permission_prompt is not None:
            confirmed = await context.permission_prompt(tool_name, decision.reason)
            if not confirmed:
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=f"Permission denied for {tool_name}",
                    is_error=True,
                )
        else:
            return ToolResultBlock(
                tool_use_id=tool_use_id,
                content=decision.reason or f"Permission denied for {tool_name}",
                is_error=True,
            )

    metadata = {
        "tool_registry": context.tool_registry,
        "ask_user_prompt": context.ask_user_prompt,
        **(context.tool_metadata or {}),
    }

    # Fire before-tool hooks
    hook_executor = metadata.get("hook_executor")
    if hook_executor is not None:
        from leeway.hooks.types import HookEvent

        await hook_executor.execute_hooks(
            HookEvent.BEFORE_TOOL_USE,
            {"tool_name": tool_name, "tool_input": tool_input},
            tool_name=tool_name,
        )

    result = await tool.execute(
        parsed_input,
        ToolExecutionContext(cwd=context.cwd, metadata=metadata),
    )

    # Fire after-tool hooks
    if hook_executor is not None:
        await hook_executor.execute_hooks(
            HookEvent.AFTER_TOOL_USE,
            {"tool_name": tool_name, "output": result.output[:500], "is_error": result.is_error},
            tool_name=tool_name,
        )

    return ToolResultBlock(
        tool_use_id=tool_use_id,
        content=result.output,
        is_error=result.is_error,
    )
