"""Workflow engine -- drives a decision tree by calling run_query() per node."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from leeway.api.client import SupportsStreamingMessages

# Optional async callback for workflow progress events
ProgressCallback = Callable[[str], Awaitable[None]]
from leeway.engine.messages import ConversationMessage
from leeway.engine.query import QueryContext, run_query
from leeway.engine.stream_events import (
    AssistantTurnComplete,
    ToolExecutionCompleted,
)
from leeway.permissions.checker import PermissionChecker
from leeway.tools.base import ToolRegistry

from leeway.hooks import HookExecutor, HookRegistry
from leeway.hooks.types import CommandHookDefinition, HttpHookDefinition
from leeway.skills.registry import SkillRegistry
from leeway.workflow.audit import NodeExecution, WorkflowAuditTrail
from leeway.workflow.evaluator import NodeResult, _matches, evaluate_transitions
from leeway.workflow.parallel import BranchResult, BranchSpec, ParallelSpec
from leeway.workflow.signal_tool import WorkflowSignalTool
from leeway.workflow.types import ConditionType, NodeSpec, WorkflowDefinition

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Outcome of a complete workflow execution."""

    audit: WorkflowAuditTrail
    final_output: str = ""
    success: bool = True
    error: str | None = None

    def format_output(self) -> str:
        """Format for returning to the main agent via ToolResult."""
        parts = [self.audit.to_summary()]
        if self.final_output:
            parts.append(f"\n--- Final Output ---\n{self.final_output}")
        if self.error:
            parts.append(f"\n--- Error ---\n{self.error}")
        return "\n".join(parts)


PermissionPromptFn = Callable[[str, str], Awaitable[bool]]
AskUserPromptFn = Callable[[str], Awaitable[str]]


@dataclass
class WorkflowEngine:
    """Execute a workflow definition by driving ``run_query`` per node."""

    workflow: WorkflowDefinition
    api_client: SupportsStreamingMessages
    full_tool_registry: ToolRegistry
    permission_checker: PermissionChecker
    cwd: Path
    model: str
    max_tokens: int = 16384
    tool_metadata: dict[str, Any] | None = None
    on_progress: ProgressCallback | None = None
    permission_prompt: PermissionPromptFn | None = None
    ask_user_prompt: AskUserPromptFn | None = None

    # runtime state
    _audit: WorkflowAuditTrail = field(init=False)

    def __post_init__(self) -> None:
        self._audit = WorkflowAuditTrail(workflow_name=self.workflow.name)

    async def _emit_progress(self, message: str) -> None:
        """Send a progress message via the callback, if set."""
        if self.on_progress is not None:
            await self.on_progress(message)

    def validate_resources(self) -> list[str]:
        """Check all referenced skills, MCP servers, tools, and hooks exist.

        Returns a list of warning messages (empty = all valid).
        Called before execution to surface configuration issues early.
        """
        warnings: list[str] = []
        meta = self.tool_metadata or {}
        global_skill_reg: SkillRegistry | None = meta.get("skill_registry")
        available_skills = {s.name for s in global_skill_reg.list_skills()} if global_skill_reg else set()
        available_tools = {t.name for t in self.full_tool_registry.list_tools()}
        available_mcp_servers = {
            t.name.split("_")[1]
            for t in self.full_tool_registry.list_tools()
            if t.name.startswith("mcp_") and t.name.count("_") >= 2
        }

        def _check_node(node: NodeSpec, label: str) -> None:
            # Check tools
            for tool_name in node.tools:
                if tool_name not in available_tools:
                    warnings.append(f"{label}: tool '{tool_name}' not found in registry")
            # Check skills
            for skill_name in node.skills:
                if available_skills and skill_name not in available_skills:
                    warnings.append(f"{label}: skill '{skill_name}' not found")
                elif not global_skill_reg and node.skills:
                    warnings.append(f"{label}: skills referenced but no skill registry available")
                    break
            # Check MCP servers
            for server in node.mcp_servers:
                if server not in available_mcp_servers:
                    warnings.append(f"{label}: MCP server '{server}' has no registered tools")
            # Check hooks parse correctly
            for i, hook_def in enumerate(node.hooks):
                hook_type = hook_def.get("type")
                if hook_type not in ("command", "http"):
                    warnings.append(f"{label}: hook[{i}] has unknown type '{hook_type}'")
                else:
                    try:
                        if hook_type == "command":
                            CommandHookDefinition.model_validate(hook_def)
                        else:
                            HttpHookDefinition.model_validate(hook_def)
                    except Exception as exc:
                        warnings.append(f"{label}: hook[{i}] invalid — {exc}")

        # Check workflow-level globals
        for skill_name in self.workflow.global_skills:
            if available_skills and skill_name not in available_skills:
                warnings.append(f"global_skills: skill '{skill_name}' not found")
        for server in self.workflow.global_mcp_servers:
            if server not in available_mcp_servers:
                warnings.append(f"global_mcp_servers: MCP server '{server}' has no registered tools")
        for i, hook_def in enumerate(self.workflow.global_hooks):
            hook_type = hook_def.get("type")
            if hook_type not in ("command", "http"):
                warnings.append(f"global_hooks[{i}]: unknown type '{hook_type}'")
            else:
                try:
                    if hook_type == "command":
                        CommandHookDefinition.model_validate(hook_def)
                    else:
                        HttpHookDefinition.model_validate(hook_def)
                except Exception as exc:
                    warnings.append(f"global_hooks[{i}]: invalid — {exc}")

        # Check each node
        for node_name, node in self.workflow.nodes.items():
            _check_node(node, f"node '{node_name}'")
            # Check parallel branches
            parallel_spec = node.get_parallel_spec()
            if parallel_spec is not None:
                for branch_name, branch in parallel_spec.branches.items():
                    branch_node = NodeSpec(
                        prompt=branch.prompt,
                        tools=branch.tools,
                        skills=branch.skills,
                        hooks=branch.hooks,
                        mcp_servers=branch.mcp_servers,
                    )
                    _check_node(branch_node, f"node '{node_name}' branch '{branch_name}'")

        return warnings

    async def execute(self, user_context: str) -> WorkflowResult:
        """Run the full workflow from ``start_node`` to a terminal node."""
        # Validate resources before starting
        resource_warnings = self.validate_resources()
        if resource_warnings:
            for w in resource_warnings:
                logger.warning("Workflow '%s': %s", self.workflow.name, w)
                await self._emit_progress(f"  ⚠ {w}")

        current_name: str | None = self.workflow.start_node
        carry_forward = user_context
        prev_node_result: NodeResult | None = None

        await self._emit_progress(
            f"▶ Starting workflow '{self.workflow.name}' at node '{current_name}'"
        )

        try:
            while current_name is not None:
                node = self.workflow.nodes[current_name]
                logger.info("Workflow '%s': entering node '%s'", self.workflow.name, current_name)

                is_terminal = self.workflow.is_terminal(current_name)

                # --- Parallel node path ---
                parallel_spec = node.get_parallel_spec()
                if parallel_spec is not None:
                    branch_count = len(parallel_spec.branches)
                    await self._emit_progress(
                        f"  || Parallel node '{current_name}' — {branch_count} branches"
                    )
                    node_result, branch_results, carry_forward = (
                        await self._execute_parallel_node(
                            current_name, node, parallel_spec, carry_forward, prev_node_result,
                        )
                    )
                    next_name = evaluate_transitions(node, node_result)

                    self._audit.node_executions.append(
                        NodeExecution(
                            node_name=current_name,
                            tools_called=node_result.tools_called,
                            next_node=next_name,
                            parallel_results={
                                name: _branch_result_to_dict(br)
                                for name, br in branch_results.items()
                            },
                        )
                    )
                    if next_name:
                        await self._emit_progress(
                            f"  || All branches complete → '{next_name}'"
                        )
                    prev_node_result = node_result
                    current_name = next_name
                    continue

                # --- Sequential node path ---
                tag = " (terminal)" if is_terminal else ""
                await self._emit_progress(
                    f"  ● Node '{current_name}'{tag} — {len(node.tools)} tools, max {node.max_turns} turns"
                )

                valid_signals = self.workflow.signal_decisions_for_node(current_name)
                signal_tool = WorkflowSignalTool(valid_decisions=valid_signals or None)
                scoped_registry, scoped_metadata = self._build_node_context(
                    node, current_name, signal_tool, is_terminal=is_terminal,
                )
                system_prompt = self._build_node_prompt(current_name, carry_forward)

                # interactive: false → suppress user interaction
                node_ask = self.ask_user_prompt if node.interactive else None
                node_perm = self.permission_prompt if node.interactive else None

                context = QueryContext(
                    api_client=self.api_client,
                    tool_registry=scoped_registry,
                    permission_checker=self.permission_checker,
                    cwd=self.cwd,
                    model=self.model,
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                    max_turns=node.max_turns,
                    tool_metadata=scoped_metadata,
                    permission_prompt=node_perm,
                    ask_user_prompt=node_ask,
                )

                messages: list[ConversationMessage] = [
                    ConversationMessage.from_user_text(carry_forward),
                ]

                tools_called: list[str] = []
                final_text = ""
                turns = 0

                async for event, _usage in run_query(context, messages):
                    if isinstance(event, ToolExecutionCompleted):
                        tools_called.append(event.tool_name)
                    if isinstance(event, AssistantTurnComplete):
                        final_text = event.message.text
                        turns += 1

                node_result = NodeResult(
                    signal=signal_tool.captured,
                    tools_called=tools_called,
                    final_text=final_text,
                )
                next_name = evaluate_transitions(node, node_result)

                self._audit.node_executions.append(
                    NodeExecution(
                        node_name=current_name,
                        signal_decision=(
                            signal_tool.captured.decision if signal_tool.captured else None
                        ),
                        signal_summary=(
                            signal_tool.captured.summary if signal_tool.captured else ""
                        ),
                        tools_called=tools_called,
                        next_node=next_name,
                        turns_used=turns,
                    )
                )

                # Emit transition progress
                if signal_tool.captured:
                    decision = signal_tool.captured.decision
                    if next_name:
                        await self._emit_progress(
                            f"  ⇢ Signal '{decision}' → moving to '{next_name}'"
                        )
                    else:
                        await self._emit_progress(
                            f"  ⇢ Signal '{decision}' — no matching transition"
                        )
                elif next_name:
                    await self._emit_progress(f"  ⇢ Transition → '{next_name}'")

                if signal_tool.captured and signal_tool.captured.summary:
                    carry_forward = signal_tool.captured.summary
                elif final_text:
                    carry_forward = final_text

                prev_node_result = node_result
                current_name = next_name

        except Exception as exc:
            logger.error("Workflow '%s' failed: %s", self.workflow.name, exc)
            self._audit.mark_complete()
            return WorkflowResult(
                audit=self._audit,
                final_output=carry_forward,
                success=False,
                error=str(exc),
            )

        self._audit.final_output = carry_forward
        self._audit.mark_complete()
        path = " → ".join(self._audit.path_taken)
        await self._emit_progress(
            f"✓ Workflow '{self.workflow.name}' complete. Path: {path}"
        )
        return WorkflowResult(audit=self._audit, final_output=carry_forward)

    def _build_node_context(
        self,
        node: NodeSpec,
        node_name: str,
        signal_tool: WorkflowSignalTool | None,
        is_terminal: bool = False,
    ) -> tuple[ToolRegistry, dict[str, Any]]:
        """Build scoped tool registry and scoped tool_metadata for a node.

        Scopes tools, skills, hooks, and MCP servers based on the node's
        fields merged with the workflow's global fields.
        """
        # --- Tool + MCP scoping ---
        allowed_tools = set(node.tools) | set(self.workflow.global_tools)
        allowed_mcp = set(node.mcp_servers) | set(self.workflow.global_mcp_servers)

        registry = ToolRegistry()
        for tool in self.full_tool_registry.list_tools():
            # Skip the global SkillTool — we'll add a scoped one if needed
            if tool.name == "skill":
                continue
            if allowed_tools and tool.name in allowed_tools:
                registry.register(tool)
            elif allowed_mcp and tool.name.startswith("mcp_"):
                # Check if tool belongs to an allowed MCP server
                for server in allowed_mcp:
                    if tool.name.startswith(f"mcp_{server}_"):
                        registry.register(tool)
                        break
            elif not allowed_tools and not allowed_mcp:
                # No scoping declared — include everything
                registry.register(tool)

        if signal_tool is not None and not is_terminal:
            registry.register(signal_tool)

        # Warn about missing tools/MCP servers
        if allowed_tools:
            registered_names = {t.name for t in registry.list_tools()}
            for tool_name in allowed_tools:
                if tool_name not in registered_names and tool_name != "workflow_signal":
                    logger.warning("Node '%s': tool '%s' not found in registry", node_name, tool_name)
        if allowed_mcp:
            found_servers = set()
            for tool in registry.list_tools():
                if tool.name.startswith("mcp_"):
                    parts = tool.name.split("_", 2)
                    if len(parts) >= 2:
                        found_servers.add(parts[1])
            for server in allowed_mcp:
                if server not in found_servers:
                    logger.warning("Node '%s': MCP server '%s' has no registered tools", node_name, server)

        # --- Skill scoping ---
        allowed_skills = set(node.skills) | set(self.workflow.global_skills)
        global_skill_reg: SkillRegistry | None = (self.tool_metadata or {}).get("skill_registry")

        if global_skill_reg is not None:
            if allowed_skills:
                scoped_skill_reg = SkillRegistry()
                for skill in global_skill_reg.list_skills():
                    if skill.name in allowed_skills:
                        scoped_skill_reg.register(skill)
                # Warn about missing skills
                found = {s.name for s in scoped_skill_reg.list_skills()}
                missing = allowed_skills - found
                for name in missing:
                    logger.warning("Node '%s': skill '%s' not found", node_name, name)
            else:
                scoped_skill_reg = global_skill_reg

            if scoped_skill_reg.list_skills():
                from leeway.tools.skill_tool import SkillTool
                registry.register(SkillTool(skill_registry=scoped_skill_reg))
        elif allowed_skills:
            logger.warning("Node '%s': skills referenced but no skill registry available", node_name)

        # --- Hook scoping ---
        scoped_metadata = dict(self.tool_metadata or {})
        node_hooks = self.workflow.global_hooks + node.hooks
        if node_hooks:
            scoped_hook_registry = HookRegistry()
            # Copy global hooks from the session-level hook registry
            global_hook_reg: HookRegistry | None = (self.tool_metadata or {}).get("hook_registry")
            if global_hook_reg is not None:
                for hook in global_hook_reg._hooks:
                    scoped_hook_registry.register(hook)
            # Add workflow-level and node-level hooks
            for hook_def in node_hooks:
                hook_type = hook_def.get("type")
                try:
                    if hook_type == "command":
                        scoped_hook_registry.register(CommandHookDefinition.model_validate(hook_def))
                    elif hook_type == "http":
                        scoped_hook_registry.register(HttpHookDefinition.model_validate(hook_def))
                except Exception:
                    logger.warning("Invalid hook in node '%s': %s", node_name, hook_def)
            scoped_metadata["hook_executor"] = HookExecutor(scoped_hook_registry)

        return registry, scoped_metadata

    def _build_node_prompt(self, node_name: str, carry_forward: str) -> str:
        node = self.workflow.nodes[node_name]
        parts: list[str] = []

        parts.append(f"# Workflow Step: {node_name}")
        parts.append(f"You are executing step '{node_name}' of the '{self.workflow.name}' workflow.")
        parts.append("")
        parts.append("## Your Task")
        parts.append(node.prompt)

        valid_signals = self.workflow.signal_decisions_for_node(node_name)
        if valid_signals:
            parts.append("")
            parts.append("## Required Action")
            parts.append(
                "When you have completed this step, you MUST call the `workflow_signal` tool "
                "with one of the following decisions:"
            )
            for sig in valid_signals:
                parts.append(f"- `{sig}`")
            parts.append("")
            parts.append(
                "Do NOT proceed beyond the scope of this step. "
                "Do NOT invent steps outside this workflow."
            )
        elif self.workflow.is_terminal(node_name):
            parts.append("")
            parts.append(
                "This is the final step. Complete your task and provide the final output."
            )

        if node.carry_context and carry_forward:
            parts.append("")
            parts.append("## Context From Prior Steps")
            parts.append(carry_forward)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parallel node execution
    # ------------------------------------------------------------------

    async def _execute_parallel_node(
        self,
        node_name: str,
        node: NodeSpec,
        spec: ParallelSpec,
        carry_forward: str,
        prev_result: NodeResult | None,
    ) -> tuple[NodeResult, dict[str, BranchResult], str]:
        """Execute a parallel node. Returns (merged NodeResult, branch results, carry_forward)."""
        from leeway.workflow.hitl import HitlBroker

        # Determine which branches trigger based on conditions
        triggered: dict[str, BranchSpec] = {}
        skipped: dict[str, BranchResult] = {}

        for branch_name, branch in spec.branches.items():
            if prev_result is not None:
                if _matches(branch.condition, prev_result):
                    triggered[branch_name] = branch
                else:
                    skipped[branch_name] = BranchResult(
                        branch_name=branch_name, triggered=False,
                    )
            else:
                # No previous result (first node) — only trigger 'always' branches
                if branch.condition.type == ConditionType.ALWAYS:
                    triggered[branch_name] = branch
                else:
                    skipped[branch_name] = BranchResult(
                        branch_name=branch_name, triggered=False,
                    )

        if not triggered:
            await self._emit_progress(
                f"  || No branches triggered in '{node_name}'"
            )
            return (
                NodeResult(final_text="No branches triggered."),
                skipped,
                "No branches triggered.",
            )

        # HITL broker — suppressed when interactive: false
        upstream_ask = self.ask_user_prompt if node.interactive else None
        broker = HitlBroker(upstream_ask=upstream_ask)

        # Check approval gates
        results: dict[str, BranchResult] = dict(skipped)
        branches_to_run: dict[str, BranchSpec] = {}

        for branch_name, branch in triggered.items():
            if branch.requires_approval:
                approved = await broker.request_approval(branch_name)
                if not approved:
                    await self._emit_progress(
                        f"  |  Branch '{branch_name}': denied"
                    )
                    results[branch_name] = BranchResult(
                        branch_name=branch_name, approved=False,
                    )
                    continue
                await self._emit_progress(
                    f"  |  Branch '{branch_name}': approved"
                )
            branches_to_run[branch_name] = branch

        if not branches_to_run:
            merged = self._merge_branch_results(results)
            return NodeResult(final_text=merged), results, merged

        # Spawn branches as concurrent asyncio tasks
        async def _run_branch(name: str, branch: BranchSpec) -> BranchResult:
            branch_ask = broker.make_branch_ask_prompt(name)
            return await self._execute_branch(
                name, branch, node_name, carry_forward, branch_ask,
            )

        tasks_map: dict[str, asyncio.Task[BranchResult]] = {}
        for name, branch in branches_to_run.items():
            await self._emit_progress(
                f"  |  Branch '{name}': starting ({len(branch.tools)} tools, max {branch.max_turns} turns)"
            )
            tasks_map[name] = asyncio.create_task(_run_branch(name, branch))

        # Wait for all triggered branches
        done, pending = await asyncio.wait(
            tasks_map.values(), timeout=spec.timeout,
        )

        # Cancel timed-out branches
        for task in pending:
            task.cancel()

        # Collect results
        for name, task in tasks_map.items():
            if task in done:
                try:
                    results[name] = task.result()
                    await self._emit_progress(
                        f"  |  Branch '{name}': completed ({results[name].turns_used} turns)"
                    )
                except Exception as exc:
                    results[name] = BranchResult(
                        branch_name=name, success=False, error=str(exc),
                    )
                    await self._emit_progress(
                        f"  |  Branch '{name}': failed — {exc}"
                    )
            else:
                results[name] = BranchResult(
                    branch_name=name, success=False, error="Timed out",
                )
                await self._emit_progress(
                    f"  |  Branch '{name}': timed out"
                )

        # Merge results
        all_tools = []
        for br in results.values():
            all_tools.extend(br.tools_called)
        merged_text = self._merge_branch_results(results)

        node_result = NodeResult(
            tools_called=all_tools,
            final_text=merged_text,
        )
        return node_result, results, merged_text

    async def _execute_branch(
        self,
        branch_name: str,
        branch: BranchSpec,
        parent_node_name: str,
        carry_forward: str,
        ask_user_prompt: Callable[[str], Awaitable[str]] | None = None,
    ) -> BranchResult:
        """Execute a single parallel branch. Returns BranchResult."""
        # Build a synthetic NodeSpec-like context for this branch
        synthetic_node = NodeSpec(
            prompt=branch.prompt,
            tools=branch.tools,
            max_turns=branch.max_turns,
            skills=branch.skills,
            hooks=branch.hooks,
            mcp_servers=branch.mcp_servers,
        )
        scoped_registry, scoped_metadata = self._build_node_context(
            synthetic_node, f"{parent_node_name}/{branch_name}",
            signal_tool=None, is_terminal=True,
        )

        system_prompt = (
            f"# Parallel Branch: {branch_name}\n"
            f"You are executing branch '{branch_name}' of a parallel workflow step.\n\n"
            f"## Your Task\n{branch.prompt}\n\n"
            f"Complete your task and provide the final output.\n\n"
            f"## Context From Prior Steps\n{carry_forward}"
        )

        context = QueryContext(
            api_client=self.api_client,
            tool_registry=scoped_registry,
            permission_checker=self.permission_checker,
            cwd=self.cwd,
            model=self.model,
            system_prompt=system_prompt,
            max_tokens=self.max_tokens,
            max_turns=branch.max_turns,
            tool_metadata=scoped_metadata,
            permission_prompt=self.permission_prompt,
            ask_user_prompt=ask_user_prompt,
        )

        messages: list[ConversationMessage] = [
            ConversationMessage.from_user_text(carry_forward),
        ]

        tools_called: list[str] = []
        final_text = ""
        turns = 0

        try:
            async for event, _usage in run_query(context, messages):
                if isinstance(event, ToolExecutionCompleted):
                    tools_called.append(event.tool_name)
                if isinstance(event, AssistantTurnComplete):
                    final_text = event.message.text
                    turns += 1
        except Exception as exc:
            return BranchResult(
                branch_name=branch_name,
                tools_called=tools_called,
                final_text=final_text,
                turns_used=turns,
                success=False,
                error=str(exc),
            )

        return BranchResult(
            branch_name=branch_name,
            final_text=final_text,
            tools_called=tools_called,
            turns_used=turns,
        )

    @staticmethod
    def _merge_branch_results(results: dict[str, BranchResult]) -> str:
        """Format parallel branch results into carry_forward text."""
        parts = ["## Parallel Results\n"]
        for name, br in results.items():
            if not br.triggered:
                parts.append(f"### Branch: {name}\n*Not triggered (condition not met)*\n")
            elif not br.approved:
                parts.append(f"### Branch: {name}\n*Skipped (approval denied)*\n")
            elif not br.success:
                parts.append(f"### Branch: {name}\n*Failed: {br.error}*\n")
            else:
                parts.append(f"### Branch: {name}\n{br.final_text}\n")
        return "\n".join(parts)


def _branch_result_to_dict(br: BranchResult) -> dict[str, Any]:
    """Convert a BranchResult to a serializable dict for audit."""
    return {
        "branch_name": br.branch_name,
        "triggered": br.triggered,
        "approved": br.approved,
        "success": br.success,
        "error": br.error,
        "turns_used": br.turns_used,
        "tools_called": br.tools_called,
    }
