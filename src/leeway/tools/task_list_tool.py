"""Task listing tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class TaskListInput(BaseModel):
    """Input for listing background tasks."""

    state: str | None = Field(
        default=None,
        description="Filter by state: pending, running, completed, failed, killed",
    )


class TaskListTool(BaseTool):
    """List background tasks."""

    name = "task_list"
    description = "List background tasks, optionally filtered by state."
    input_model = TaskListInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, TaskListInput) else TaskListInput.model_validate(arguments)

        from leeway.tasks.manager import BackgroundTaskManager

        manager: BackgroundTaskManager | None = context.metadata.get("task_manager")
        if manager is None:
            return ToolResult(output="Task manager not available.", is_error=True)

        tasks = manager.list_tasks(state=args.state)
        if not tasks:
            return ToolResult(output="No tasks found.")

        lines = [f"{'ID':<14} {'Type':<10} {'State':<12} {'Description'}"]
        lines.append("-" * 60)
        for t in tasks[:20]:
            lines.append(f"{t.id:<14} {t.type.value:<10} {t.state.value:<12} {t.description[:40]}")

        return ToolResult(output="\n".join(lines))
