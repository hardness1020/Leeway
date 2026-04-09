"""Remote trigger management tool."""

from __future__ import annotations

from pydantic import BaseModel, Field

from leeway.tools.base import BaseTool, ToolExecutionContext, ToolResult


class RemoteTriggerInput(BaseModel):
    """Input for creating or listing triggers."""

    action: str = Field(description="Action: 'create', 'list', or 'delete'")
    name: str | None = Field(default=None, description="Trigger name (for create)")
    action_type: str | None = Field(default=None, description="'shell', 'workflow', or 'webhook'")
    command: str | None = Field(default=None, description="Shell command (for shell action)")
    workflow_name: str | None = Field(default=None, description="Workflow name (for workflow action)")
    workflow_context: str | None = Field(default=None, description="Context for workflow")
    trigger_id: str | None = Field(default=None, description="Trigger ID (for delete)")


class RemoteTriggerTool(BaseTool):
    """Create, list, or delete webhook triggers."""

    name = "remote_trigger"
    description = (
        "Manage webhook triggers. Create triggers that fire actions "
        "when called via HTTP POST."
    )
    input_model = RemoteTriggerInput

    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        args = arguments if isinstance(arguments, RemoteTriggerInput) else RemoteTriggerInput.model_validate(arguments)

        from leeway.triggers.registry import TriggerRegistry

        registry: TriggerRegistry | None = context.metadata.get("trigger_registry")
        if registry is None:
            return ToolResult(output="Trigger registry not available.", is_error=True)

        if args.action == "list":
            triggers = registry.list()
            if not triggers:
                return ToolResult(output="No triggers defined.")
            lines = [f"{'ID':<14} {'Name':<20} {'Enabled':<9} {'Fires'}"]
            lines.append("-" * 55)
            for t in triggers:
                lines.append(f"{t.id:<14} {t.name[:18]:<20} {'yes' if t.enabled else 'no':<9} {t.trigger_count}")
            return ToolResult(output="\n".join(lines))

        if args.action == "delete":
            if not args.trigger_id:
                return ToolResult(output="'trigger_id' required for delete.", is_error=True)
            if registry.delete(args.trigger_id):
                return ToolResult(output=f"Trigger {args.trigger_id} deleted.")
            return ToolResult(output=f"Trigger not found: {args.trigger_id}", is_error=True)

        if args.action == "create":
            if not args.name:
                return ToolResult(output="'name' required for create.", is_error=True)

            from leeway.cron.types import ShellAction, WorkflowAction
            from leeway.triggers.types import TriggerDefinition

            if args.action_type == "shell":
                if not args.command:
                    return ToolResult(output="'command' required for shell trigger.", is_error=True)
                cron_action = ShellAction(command=args.command)
            elif args.action_type == "workflow":
                if not args.workflow_name:
                    return ToolResult(output="'workflow_name' required for workflow trigger.", is_error=True)
                cron_action = WorkflowAction(
                    workflow_name=args.workflow_name,
                    context=args.workflow_context or "",
                )
            else:
                return ToolResult(output=f"Unsupported action_type: {args.action_type}", is_error=True)

            trigger = TriggerDefinition(name=args.name, action=cron_action)
            registry.save(trigger)

            return ToolResult(
                output=(
                    f"Trigger created: {trigger.id} ({trigger.name})\n"
                    f"Secret: {trigger.secret}\n"
                    f"URL: POST /trigger/{trigger.id}\n"
                    f"Header: X-Trigger-Secret: {trigger.secret}"
                )
            )

        return ToolResult(output=f"Unknown action: {args.action}", is_error=True)
