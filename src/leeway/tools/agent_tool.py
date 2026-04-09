"""Agent spawning tool."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class AgentToolInput(BaseModel):
    """Input for spawning a subagent."""

    task: str = Field(description="Task/prompt for the subagent")
    workflow: str | None = Field(default=None, description="Optional workflow to follow")
    isolation: Literal["none", "worktree"] = Field(
        default="none",
        description="Isolation mode: 'none' (shared) or 'worktree' (git worktree)",
    )


class AgentTool(BaseTool):
    """Spawn a subagent to work on a task in the background."""

    name = "agent"
    description = (
        "Spawn a subagent to work on a task independently. "
        "The agent runs in the background; check status via task_get."
    )
    input_model = AgentToolInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, AgentToolInput) else AgentToolInput.model_validate(arguments)

        from leeway.agents.spawner import AgentSpawner
        from leeway.agents.types import AgentSpec

        spawner: AgentSpawner | None = context.metadata.get("agent_spawner")
        if spawner is None:
            return ToolResult(output="Agent spawner not available.", is_error=True)

        spec = AgentSpec(
            task=args.task,
            workflow=args.workflow,
            cwd=str(context.cwd),
            isolation=args.isolation,
        )

        task = await spawner.spawn(spec)
        return ToolResult(
            output=(
                f"Agent spawned: task_id={task.id}\n"
                f"Task: {args.task[:100]}\n"
                f"Isolation: {args.isolation}\n"
                f"Use task_get with id={task.id} to check progress."
            )
        )
