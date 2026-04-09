"""Cron job deletion tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronDeleteInput(BaseModel):
    """Input for deleting a cron job."""

    id: str = Field(description="Cron job ID to delete")


class CronDeleteTool(BaseTool):
    """Delete a cron job by ID."""

    name = "cron_delete"
    description = "Delete a scheduled cron job by its ID."
    input_model = CronDeleteInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, CronDeleteInput) else CronDeleteInput.model_validate(arguments)

        from leeway.cron.store import CronStore

        store: CronStore | None = context.metadata.get("cron_store")
        if store is None:
            return ToolResult(output="Cron store not available.", is_error=True)

        if store.delete(args.id):
            return ToolResult(output=f"Cron job {args.id} deleted.")
        return ToolResult(output=f"Cron job not found: {args.id}", is_error=True)
