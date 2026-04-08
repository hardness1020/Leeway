"""Cron job creation tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult


class CronCreateInput(BaseModel):
    """Input for creating a cron job."""

    name: str = Field(description="Human-readable job name")
    schedule_type: str = Field(description="Schedule type: 'cron', 'interval', or 'once'")
    schedule_value: str = Field(
        description="Cron expression (e.g. '*/5 * * * *'), interval in seconds, or ISO datetime"
    )
    action_type: str = Field(description="Action type: 'shell', 'workflow', or 'webhook'")
    command: str | None = Field(default=None, description="Shell command (for action_type=shell)")
    workflow_name: str | None = Field(default=None, description="Workflow name (for action_type=workflow)")
    workflow_context: str | None = Field(default=None, description="Context for workflow")
    webhook_url: str | None = Field(default=None, description="URL (for action_type=webhook)")


class CronCreateTool(BaseTool):
    """Create a scheduled cron job."""

    name = "cron_create"
    description = (
        "Create a cron job that runs on a schedule. "
        "Supports cron expressions, intervals, or one-shot execution."
    )
    input_model = CronCreateInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, CronCreateInput) else CronCreateInput.model_validate(arguments)

        from agenttree.cron.store import CronStore
        from agenttree.cron.types import (
            CronJob,
            CronScheduleSpec,
            IntervalSchedule,
            OneShotSchedule,
            ShellAction,
            WebhookAction,
            WorkflowAction,
        )

        store: CronStore | None = context.metadata.get("cron_store")
        if store is None:
            return ToolResult(output="Cron store not available.", is_error=True)

        # Parse schedule
        if args.schedule_type == "cron":
            schedule = CronScheduleSpec(expression=args.schedule_value)
        elif args.schedule_type == "interval":
            try:
                schedule = IntervalSchedule(seconds=int(args.schedule_value))
            except ValueError:
                return ToolResult(output="interval schedule_value must be an integer (seconds)", is_error=True)
        elif args.schedule_type == "once":
            from datetime import datetime

            try:
                schedule = OneShotSchedule(at=datetime.fromisoformat(args.schedule_value))
            except ValueError:
                return ToolResult(output="once schedule_value must be an ISO datetime", is_error=True)
        else:
            return ToolResult(output=f"Unknown schedule_type: {args.schedule_type}", is_error=True)

        # Parse action
        if args.action_type == "shell":
            if not args.command:
                return ToolResult(output="'command' required for shell action", is_error=True)
            action = ShellAction(command=args.command)
        elif args.action_type == "workflow":
            if not args.workflow_name:
                return ToolResult(output="'workflow_name' required for workflow action", is_error=True)
            action = WorkflowAction(
                workflow_name=args.workflow_name,
                context=args.workflow_context or "",
            )
        elif args.action_type == "webhook":
            if not args.webhook_url:
                return ToolResult(output="'webhook_url' required for webhook action", is_error=True)
            action = WebhookAction(url=args.webhook_url)
        else:
            return ToolResult(output=f"Unknown action_type: {args.action_type}", is_error=True)

        from agenttree.cron.scheduler import compute_next_run

        job = CronJob(name=args.name, schedule=schedule, action=action)
        job.next_run = compute_next_run(job)
        store.save(job)

        return ToolResult(
            output=f"Cron job created: {job.id} ({job.name})\n"
            f"Schedule: {args.schedule_type} = {args.schedule_value}\n"
            f"Next run: {job.next_run or 'N/A'}"
        )
