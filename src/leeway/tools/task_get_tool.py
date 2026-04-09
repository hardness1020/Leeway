"""Task status/output tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class TaskGetInput(BaseModel):
    """Input for getting task details."""

    id: str = Field(description="Task ID")
    tail_lines: int = Field(default=50, description="Number of output lines to return")


class TaskGetTool(BaseTool):
    """Get a background task's status and recent output."""

    name = "task_get"
    description = "Get status and recent output of a background task by ID."
    input_model = TaskGetInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, TaskGetInput) else TaskGetInput.model_validate(arguments)

        from leeway.tasks.manager import BackgroundTaskManager

        manager: BackgroundTaskManager | None = context.metadata.get("task_manager")
        if manager is None:
            return ToolResult(output="Task manager not available.", is_error=True)

        task = manager.get_task(args.id)
        if task is None:
            return ToolResult(output=f"Task not found: {args.id}", is_error=True)

        lines = [
            f"ID: {task.id}",
            f"Type: {task.type.value}",
            f"State: {task.state.value}",
            f"Description: {task.description}",
            f"Created: {task.created_at.isoformat()}",
        ]
        if task.started_at:
            lines.append(f"Started: {task.started_at.isoformat()}")
        if task.completed_at:
            lines.append(f"Completed: {task.completed_at.isoformat()}")
        if task.exit_code is not None:
            lines.append(f"Exit code: {task.exit_code}")
        if task.error:
            lines.append(f"Error: {task.error}")

        output = manager.get_output(args.id, tail_lines=args.tail_lines)
        if output:
            lines.append(f"\n--- Output (last {args.tail_lines} lines) ---")
            lines.append(output)

        return ToolResult(output="\n".join(lines))
