"""Task creation tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class TaskCreateInput(BaseModel):
    """Input for creating a background task."""

    type: str = Field(description="Task type: 'shell' or 'workflow'")
    command: str | None = Field(default=None, description="Shell command (for type=shell)")
    workflow_name: str | None = Field(default=None, description="Workflow name (for type=workflow)")
    context: str | None = Field(default=None, description="Context/prompt for the workflow")
    description: str = Field(default="", description="Optional human-readable description")


class TaskCreateTool(BaseTool):
    """Create a background task (shell command or workflow execution)."""

    name = "task_create"
    description = (
        "Create a background task. Use type='shell' for a shell command, "
        "or type='workflow' for running a workflow."
    )
    input_model = TaskCreateInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, TaskCreateInput) else TaskCreateInput.model_validate(arguments)

        from agenttree.tasks.manager import BackgroundTaskManager

        manager: BackgroundTaskManager | None = context.metadata.get("task_manager")
        if manager is None:
            return ToolResult(output="Task manager not available.", is_error=True)

        cwd = str(context.cwd)

        if args.type == "shell":
            if not args.command:
                return ToolResult(output="'command' is required for shell tasks.", is_error=True)
            task = await manager.create_shell_task(
                command=args.command,
                cwd=cwd,
                description=args.description,
            )
        elif args.type == "workflow":
            if not args.workflow_name:
                return ToolResult(output="'workflow_name' is required for workflow tasks.", is_error=True)
            task = await manager.create_workflow_task(
                workflow_name=args.workflow_name,
                context=args.context or "",
                cwd=cwd,
                description=args.description,
            )
        else:
            return ToolResult(output=f"Unknown task type: '{args.type}'", is_error=True)

        return ToolResult(output=f"Task created: {task.id} ({task.type.value}, {task.state.value})")
