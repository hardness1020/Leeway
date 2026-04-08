"""Cron job enable/disable tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronToggleInput(BaseModel):
    """Input for toggling a cron job."""

    id: str = Field(description="Cron job ID")
    enabled: bool = Field(description="True to enable, False to disable")


class CronToggleTool(BaseTool):
    """Enable or disable a cron job."""

    name = "cron_toggle"
    description = "Enable or disable a scheduled cron job."
    input_model = CronToggleInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, CronToggleInput) else CronToggleInput.model_validate(arguments)

        from agenttree.cron.store import CronStore

        store: CronStore | None = context.metadata.get("cron_store")
        if store is None:
            return ToolResult(output="Cron store not available.", is_error=True)

        job = store.get(args.id)
        if job is None:
            return ToolResult(output=f"Cron job not found: {args.id}", is_error=True)

        job.enabled = args.enabled
        store.save(job)
        state = "enabled" if args.enabled else "disabled"
        return ToolResult(output=f"Cron job '{job.name}' ({job.id}) {state}.")
