"""Tool for executing deterministic workflow subagents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agenttree.tools.base import BaseTool, ToolExecutionContext, ToolResult

logger = logging.getLogger(__name__)


class WorkflowToolInput(BaseModel):
    """Arguments for the workflow tool."""

    name: str = Field(description="Name of the workflow to execute")
    context: str = Field(
        description="Context and instructions for the workflow (what to work on)",
    )


class WorkflowTool(BaseTool):
    """Execute a deterministic decision-tree workflow.

    The main agent calls this tool to delegate work to a predefined
    workflow.  The workflow constrains the LLM to follow a strict graph
    of steps, each with scoped tools and a scoped prompt.
    """

    name = "workflow"
    description = (
        "Execute a deterministic workflow (decision tree). "
        "The workflow constrains the AI to follow predefined steps with "
        "scoped tools at each step. Use this when a task matches an "
        "available workflow for reliable, auditable execution."
    )
    input_model = WorkflowToolInput

    def __init__(
        self,
        *,
        workflow_registry: Any,
        api_client: Any,
        permission_checker: Any,
        model: str = "",
        max_tokens: int = 16384,
        on_progress: Any = None,
    ) -> None:
        self._registry = workflow_registry
        self._api_client = api_client
        self._permission_checker = permission_checker
        self._model = model
        self._max_tokens = max_tokens
        self._on_progress = on_progress

    async def execute(
        self, arguments: WorkflowToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        from agenttree.workflow.engine import WorkflowEngine
        from agenttree.workflow.registry import WorkflowRegistry

        registry: WorkflowRegistry = self._registry
        defn = registry.get(arguments.name)
        if defn is None:
            available = [w.name for w in registry.list_workflows()]
            return ToolResult(
                output=(
                    f"Unknown workflow '{arguments.name}'. "
                    f"Available workflows: {available or '(none)'}"
                ),
                is_error=True,
            )

        full_tool_registry = context.metadata.get("tool_registry")
        if full_tool_registry is None:
            return ToolResult(
                output="Workflow tool requires tool_registry in execution context",
                is_error=True,
            )

        # Pull progress callback from metadata if available
        on_progress = self._on_progress or context.metadata.get("workflow_progress")

        engine = WorkflowEngine(
            workflow=defn,
            api_client=self._api_client,
            full_tool_registry=full_tool_registry,
            permission_checker=self._permission_checker,
            cwd=Path(context.cwd),
            model=self._model,
            max_tokens=self._max_tokens,
            tool_metadata=context.metadata,
            on_progress=on_progress,
        )

        result = await engine.execute(user_context=arguments.context)

        if not result.success:
            return ToolResult(output=result.format_output(), is_error=True)
        return ToolResult(output=result.format_output())
