"""Task stop tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class TaskStopInput(BaseModel):
    """Input for stopping a background task."""

    id: str = Field(description="Task ID to stop")


class TaskStopTool(BaseTool):
    """Stop a running background task."""

    name = "task_stop"
    description = "Stop a running background task by ID."
    input_model = TaskStopInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, TaskStopInput) else TaskStopInput.model_validate(arguments)

        from leeway.tasks.manager import BackgroundTaskManager

        manager: BackgroundTaskManager | None = context.metadata.get("task_manager")
        if manager is None:
            return ToolResult(output="Task manager not available.", is_error=True)

        stopped = await manager.stop_task(args.id)
        if not stopped:
            return ToolResult(output=f"Could not stop task {args.id} (not running or not found).", is_error=True)

        return ToolResult(output=f"Task {args.id} stopped.")
