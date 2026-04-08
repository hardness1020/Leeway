"""Workflow engine -- drives a decision tree by calling run_query() per node."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agenttree.api.client import SupportsStreamingMessages

# Optional async callback for workflow progress events
ProgressCallback = Callable[[str], Awaitable[None]]
from agenttree.engine.messages import ConversationMessage
from agenttree.engine.query import QueryContext, run_query
from agenttree.engine.stream_events import (
    AssistantTurnComplete,
    ToolExecutionCompleted,
)
from agenttree.permissions.checker import PermissionChecker
from agenttree.tools.base import ToolRegistry

from agenttree.workflow.audit import NodeExecution, WorkflowAuditTrail
from agenttree.workflow.evaluator import NodeResult, evaluate_transitions
from agenttree.workflow.signal_tool import WorkflowSignalTool
from agenttree.workflow.types import ConditionType, WorkflowDefinition

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Outcome of a complete workflow execution."""

    audit: WorkflowAuditTrail
    final_output: str = ""
    success: bool = True
    error: str | None = None

    def format_output(self) -> str:
        """Format for returning to the main agent via ToolResult."""
        parts = [self.audit.to_summary()]
        if self.final_output:
            parts.append(f"\n--- Final Output ---\n{self.final_output}")
        if self.error:
            parts.append(f"\n--- Error ---\n{self.error}")
        return "\n".join(parts)


@dataclass
class WorkflowEngine:
    """Execute a workflow definition by driving ``run_query`` per node."""

    workflow: WorkflowDefinition
    api_client: SupportsStreamingMessages
    full_tool_registry: ToolRegistry
    permission_checker: PermissionChecker
    cwd: Path
    model: str
    max_tokens: int = 16384
    tool_metadata: dict[str, Any] | None = None
    on_progress: ProgressCallback | None = None

    # runtime state
    _audit: WorkflowAuditTrail = field(init=False)

    def __post_init__(self) -> None:
        self._audit = WorkflowAuditTrail(workflow_name=self.workflow.name)

    async def _emit_progress(self, message: str) -> None:
        """Send a progress message via the callback, if set."""
        if self.on_progress is not None:
            await self.on_progress(message)

    async def execute(self, user_context: str) -> WorkflowResult:
        """Run the full workflow from ``start_node`` to a terminal node."""
        current_name: str | None = self.workflow.start_node
        carry_forward = user_context

        await self._emit_progress(
            f"▶ Starting workflow '{self.workflow.name}' at node '{current_name}'"
        )

        try:
            while current_name is not None:
                node = self.workflow.nodes[current_name]
                logger.info("Workflow '%s': entering node '%s'", self.workflow.name, current_name)

                is_terminal = self.workflow.is_terminal(current_name)
                tag = " (terminal)" if is_terminal else ""
                await self._emit_progress(
                    f"  ● Node '{current_name}'{tag} — {len(node.tools)} tools, max {node.max_turns} turns"
                )

                valid_signals = self.workflow.signal_decisions_for_node(current_name)
                signal_tool = WorkflowSignalTool(valid_decisions=valid_signals or None)
                scoped_registry = self._build_scoped_registry(current_name, signal_tool)
                system_prompt = self._build_node_prompt(current_name, carry_forward)

                context = QueryContext(
                    api_client=self.api_client,
                    tool_registry=scoped_registry,
                    permission_checker=self.permission_checker,
                    cwd=self.cwd,
                    model=self.model,
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                    max_turns=node.max_turns,
                    tool_metadata=self.tool_metadata,
                )

                messages: list[ConversationMessage] = [
                    ConversationMessage.from_user_text(carry_forward),
                ]

                tools_called: list[str] = []
                final_text = ""
                turns = 0

                async for event, _usage in run_query(context, messages):
                    if isinstance(event, ToolExecutionCompleted):
                        tools_called.append(event.tool_name)
                    if isinstance(event, AssistantTurnComplete):
                        final_text = event.message.text
                        turns += 1

                node_result = NodeResult(
                    signal=signal_tool.captured,
                    tools_called=tools_called,
                    final_text=final_text,
                )
                next_name = evaluate_transitions(node, node_result)

                self._audit.node_executions.append(
                    NodeExecution(
                        node_name=current_name,
                        signal_decision=(
                            signal_tool.captured.decision if signal_tool.captured else None
                        ),
                        signal_summary=(
                            signal_tool.captured.summary if signal_tool.captured else ""
                        ),
                        tools_called=tools_called,
                        next_node=next_name,
                        turns_used=turns,
                    )
                )

                # Emit transition progress
                if signal_tool.captured:
                    decision = signal_tool.captured.decision
                    if next_name:
                        await self._emit_progress(
                            f"  ⇢ Signal '{decision}' → moving to '{next_name}'"
                        )
                    else:
                        await self._emit_progress(
                            f"  ⇢ Signal '{decision}' — no matching transition"
                        )
                elif next_name:
                    await self._emit_progress(f"  ⇢ Transition → '{next_name}'")

                if signal_tool.captured and signal_tool.captured.summary:
                    carry_forward = signal_tool.captured.summary
                elif final_text:
                    carry_forward = final_text

                current_name = next_name

        except Exception as exc:
            logger.error("Workflow '%s' failed: %s", self.workflow.name, exc)
            self._audit.mark_complete()
            return WorkflowResult(
                audit=self._audit,
                final_output=carry_forward,
                success=False,
                error=str(exc),
            )

        self._audit.final_output = carry_forward
        self._audit.mark_complete()
        path = " → ".join(self._audit.path_taken)
        await self._emit_progress(
            f"✓ Workflow '{self.workflow.name}' complete. Path: {path}"
        )
        return WorkflowResult(audit=self._audit, final_output=carry_forward)

    def _build_scoped_registry(
        self, node_name: str, signal_tool: WorkflowSignalTool
    ) -> ToolRegistry:
        node = self.workflow.nodes[node_name]
        allowed = set(node.tools) | set(self.workflow.global_tools)

        registry = ToolRegistry()
        for tool in self.full_tool_registry.list_tools():
            if allowed and tool.name in allowed:
                registry.register(tool)

        if not self.workflow.is_terminal(node_name):
            registry.register(signal_tool)
        return registry

    def _build_node_prompt(self, node_name: str, carry_forward: str) -> str:
        node = self.workflow.nodes[node_name]
        parts: list[str] = []

        parts.append(f"# Workflow Step: {node_name}")
        parts.append(f"You are executing step '{node_name}' of the '{self.workflow.name}' workflow.")
        parts.append("")
        parts.append("## Your Task")
        parts.append(node.prompt)

        valid_signals = self.workflow.signal_decisions_for_node(node_name)
        if valid_signals:
            parts.append("")
            parts.append("## Required Action")
            parts.append(
                "When you have completed this step, you MUST call the `workflow_signal` tool "
                "with one of the following decisions:"
            )
            for sig in valid_signals:
                parts.append(f"- `{sig}`")
            parts.append("")
            parts.append(
                "Do NOT proceed beyond the scope of this step. "
                "Do NOT invent steps outside this workflow."
            )
        elif self.workflow.is_terminal(node_name):
            parts.append("")
            parts.append(
                "This is the final step. Complete your task and provide the final output."
            )

        if node.carry_context and carry_forward:
            parts.append("")
            parts.append("## Context From Prior Steps")
            parts.append(carry_forward)

        return "\n".join(parts)
