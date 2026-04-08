"""Workflow signal tool -- the bridge between LLM cognition and deterministic control."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class WorkflowSignalInput(BaseModel):
    """Input for the workflow_signal tool."""

    decision: str = Field(description="The decision or outcome label for the current workflow step")
    summary: str = Field(
        default="",
        description="Brief summary of findings or reasoning to carry forward",
    )
    data: dict = Field(
        default_factory=dict,
        description="Structured data to pass to downstream nodes",
    )


class WorkflowSignalTool(BaseTool):
    """Signal a decision to the workflow controller.

    Injected into every workflow node's tool registry.  When the LLM
    calls this tool the engine captures the signal and uses it for
    deterministic transition evaluation.
    """

    name = "workflow_signal"
    description = (
        "Signal your decision for the current workflow step. "
        "You MUST call this exactly once when you have finished "
        "the work described in your instructions."
    )
    input_model = WorkflowSignalInput

    def __init__(self, valid_decisions: list[str] | None = None) -> None:
        self._valid_decisions = valid_decisions
        self._captured: WorkflowSignalInput | None = None

    @property
    def captured(self) -> WorkflowSignalInput | None:
        """Return the most recent signal, or ``None``."""
        return self._captured

    def reset(self) -> None:
        """Clear the captured signal (used between nodes)."""
        self._captured = None

    def is_read_only(self, arguments: BaseModel) -> bool:  # noqa: ARG002
        return True

    async def execute(
        self, arguments: WorkflowSignalInput, context: ToolExecutionContext
    ) -> ToolResult:
        if self._valid_decisions and arguments.decision not in self._valid_decisions:
            return ToolResult(
                output=(
                    f"Invalid decision '{arguments.decision}'. "
                    f"Must be one of: {self._valid_decisions}"
                ),
                is_error=True,
            )
        self._captured = arguments
        return ToolResult(output=f"Signal received: decision='{arguments.decision}'")
