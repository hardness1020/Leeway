"""Cron job listing tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronListInput(BaseModel):
    """Input for listing cron jobs."""

    enabled_only: bool = Field(default=False, description="Only show enabled jobs")


class CronListTool(BaseTool):
    """List scheduled cron jobs."""

    name = "cron_list"
    description = "List all scheduled cron jobs."
    input_model = CronListInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        return True

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, CronListInput) else CronListInput.model_validate(arguments)

        from leeway.cron.store import CronStore

        store: CronStore | None = context.metadata.get("cron_store")
        if store is None:
            return ToolResult(output="Cron store not available.", is_error=True)

        jobs = store.list(enabled_only=args.enabled_only)
        if not jobs:
            return ToolResult(output="No cron jobs found.")

        lines = [f"{'ID':<14} {'Name':<20} {'Enabled':<9} {'Runs':<6} {'Last Status'}"]
        lines.append("-" * 70)
        for j in jobs:
            status = j.last_status or "-"
            lines.append(
                f"{j.id:<14} {j.name[:18]:<20} {'yes' if j.enabled else 'no':<9} "
                f"{j.run_count:<6} {status[:20]}"
            )
        return ToolResult(output="\n".join(lines))
