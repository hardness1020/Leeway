"""Shared runtime assembly for headless and React TUI modes."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from leeway.api.client import AnthropicApiClient, SupportsStreamingMessages
from leeway.api.openai_client import OpenAICompatibleClient
from leeway.api.provider import auth_status, detect_provider
from leeway.config import load_settings
from leeway.engine import QueryEngine
from leeway.engine.stream_events import StreamEvent
from leeway.permissions import PermissionChecker
from leeway.prompts import build_runtime_system_prompt
from leeway.state import AppState, AppStateStore
from leeway.agents.spawner import AgentSpawner
from leeway.cron.store import CronStore
from leeway.hooks import HookExecutor, HookRegistry
from leeway.triggers.registry import TriggerRegistry
from leeway.skills import load_skill_registry
from leeway.tasks import BackgroundTaskManager, TaskStore
from leeway.tools import SkillTool, ToolRegistry, WorkflowTool, create_default_tool_registry
from leeway.workflow.registry import load_workflow_registry

from typing import Any

PermissionPrompt = Callable[[str, str], Awaitable[bool]]
AskUserPrompt = Callable[[str], Awaitable[str]]
SystemPrinter = Callable[[str], Awaitable[None]]
StreamRenderer = Callable[[StreamEvent], Awaitable[None]]
ClearHandler = Callable[[], Awaitable[None]]

# Callback to show an interactive select picker in the frontend.
# Args: title, submit_prefix, options (list of {value, label, description?})
SelectRequest = Callable[[str, str, list[dict[str, Any]]], Awaitable[None]]


@dataclass
class RuntimeBundle:
    """Shared runtime objects for one interactive session."""

    api_client: SupportsStreamingMessages
    cwd: str
    tool_registry: ToolRegistry
    app_state: AppStateStore
    engine: QueryEngine
    external_api_client: bool
    session_id: str = ""


async def build_runtime(
    *,
    prompt: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
    api_client: SupportsStreamingMessages | None = None,
    permission_prompt: PermissionPrompt | None = None,
    ask_user_prompt: AskUserPrompt | None = None,
) -> RuntimeBundle:
    """Build the shared runtime for an Leeway session."""
    settings = load_settings().merge_cli_overrides(
        model=model,
        base_url=base_url,
        system_prompt=system_prompt,
        api_key=api_key,
        api_format=api_format,
    )
    cwd = str(Path.cwd())

    if api_client:
        resolved_api_client = api_client
    elif settings.api_format == "openai":
        resolved_api_client = OpenAICompatibleClient(
            api_key=settings.resolve_api_key(),
            base_url=settings.base_url,
        )
    else:
        resolved_api_client = AnthropicApiClient(
            api_key=settings.resolve_api_key(),
            base_url=settings.base_url,
        )

    tool_registry = create_default_tool_registry()

    # Skills
    skill_registry = load_skill_registry(cwd)
    if skill_registry.list_skills():
        tool_registry.register(SkillTool(skill_registry=skill_registry))

    # Background tasks
    from leeway.config.paths import get_data_dir

    data_dir = get_data_dir()
    task_manager = BackgroundTaskManager(
        store=TaskStore(data_dir / "tasks.json"),
    )

    # Cron store
    cron_store = CronStore(data_dir / "cron_jobs.json")

    # Hooks
    hook_registry = HookRegistry()
    for hook_def in settings.hooks:
        from leeway.hooks.types import CommandHookDefinition, HttpHookDefinition

        if hook_def.get("type") == "command":
            hook_registry.register(CommandHookDefinition.model_validate(hook_def))
        elif hook_def.get("type") == "http":
            hook_registry.register(HttpHookDefinition.model_validate(hook_def))
    hook_executor = HookExecutor(hook_registry)

    # MCP
    mcp_manager = None
    if settings.mcp_servers:
        try:
            from leeway.mcp.client import McpClientManager
            from leeway.mcp.adapter import register_mcp_tools
            from leeway.mcp.types import McpServerConfig

            mcp_manager = McpClientManager()
            configs = [McpServerConfig.model_validate(c) for c in settings.mcp_servers]
            await mcp_manager.connect_all(configs)
            registered = register_mcp_tools(tool_registry, mcp_manager)
            if registered:
                import logging

                logging.getLogger(__name__).info("Registered %d MCP tools", registered)
        except ImportError:
            import logging

            logging.getLogger(__name__).warning(
                "MCP servers configured but 'mcp' package not installed. "
                "Install with: pip install leeway[mcp]"
            )
            mcp_manager = None

    # Plugins — merge skills, hooks from plugin directories
    from leeway.plugins.loader import PluginLoader

    plugin_loader = PluginLoader(cwd)
    plugin_loader.load_all(skill_registry, hook_registry)

    provider = detect_provider(settings)
    app_state = AppStateStore(
        AppState(
            model=settings.model,
            permission_mode=settings.permission.mode.value,
            theme=settings.theme,
            cwd=cwd,
            provider=provider.name,
            auth_status=auth_status(settings),
            base_url=settings.base_url or "",
            fast_mode=settings.fast_mode,
            effort=settings.effort,
            passes=settings.passes,
            session_start_ms=time.time() * 1000,
        )
    )

    workflow_registry = load_workflow_registry(cwd)
    if workflow_registry.list_workflows():
        tool_registry.register(
            WorkflowTool(
                workflow_registry=workflow_registry,
                api_client=resolved_api_client,
                permission_checker=PermissionChecker(settings.permission),
                model=settings.model,
                max_tokens=settings.max_tokens,
                on_progress=_make_workflow_progress(app_state),
            )
        )

    engine = QueryEngine(
        api_client=resolved_api_client,
        tool_registry=tool_registry,
        permission_checker=PermissionChecker(settings.permission),
        cwd=cwd,
        model=settings.model,
        system_prompt=build_runtime_system_prompt(settings, cwd=cwd, latest_user_prompt=prompt),
        max_tokens=settings.max_tokens,
        permission_prompt=permission_prompt,
        ask_user_prompt=ask_user_prompt,
        tool_metadata={
            "task_manager": task_manager,
            "cron_store": cron_store,
            "hook_executor": hook_executor,
            "hook_registry": hook_registry,
            "skill_registry": skill_registry,
            "mcp_manager": mcp_manager,
            "trigger_registry": TriggerRegistry(data_dir / "triggers.json"),
            "agent_spawner": AgentSpawner(task_manager=task_manager, cwd=cwd),
        },
    )

    from uuid import uuid4

    return RuntimeBundle(
        api_client=resolved_api_client,
        cwd=cwd,
        tool_registry=tool_registry,
        app_state=app_state,
        engine=engine,
        external_api_client=api_client is not None,
        session_id=uuid4().hex[:12],
    )


async def start_runtime(bundle: RuntimeBundle) -> None:
    """Run session start tasks (currently a no-op)."""
    pass


async def close_runtime(bundle: RuntimeBundle) -> None:
    """Close runtime-owned resources."""
    mcp_manager = bundle.engine._tool_metadata.get("mcp_manager") if bundle.engine._tool_metadata else None
    if mcp_manager is not None:
        await mcp_manager.close_all()


def sync_app_state(bundle: RuntimeBundle) -> None:
    """Refresh UI state from current settings."""
    settings = load_settings()
    provider = detect_provider(settings)
    usage = bundle.engine.total_usage
    bundle.app_state.set(
        model=bundle.engine.model,
        permission_mode=settings.permission.mode.value,
        theme=settings.theme,
        cwd=bundle.cwd,
        provider=provider.name,
        auth_status=auth_status(settings),
        base_url=settings.base_url or "",
        fast_mode=settings.fast_mode,
        effort=settings.effort,
        passes=settings.passes,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )


# ---------------------------------------------------------------------------
# Workflow progress → AppState bridge
# ---------------------------------------------------------------------------

_RE_START = re.compile(r"▶ Starting workflow '([^']+)' at node '([^']+)'")
_RE_NODE = re.compile(r"● Node '([^']+)'")
_RE_PARALLEL = re.compile(r"\|\| Parallel node '([^']+)'")
_RE_BRANCH_START = re.compile(r"\|  Branch '([^']+)': starting")
_RE_BRANCH_DONE = re.compile(r"\|  Branch '([^']+)': (?:completed|failed|timed out)")
_RE_COMPLETE = re.compile(r"✓ Workflow '([^']+)' complete")


def _make_workflow_progress(app_state: AppStateStore) -> Callable[[str], Awaitable[None]]:
    """Return an async callback that updates AppState from workflow progress messages."""

    async def _on_progress(message: str) -> None:
        m = _RE_START.search(message)
        if m:
            app_state.set(
                workflow_name=m.group(1),
                workflow_node=m.group(2),
                workflow_parallel_branches=[],
            )
            return

        m = _RE_NODE.search(message)
        if m:
            app_state.set(workflow_node=m.group(1), workflow_parallel_branches=[])
            return

        m = _RE_PARALLEL.search(message)
        if m:
            app_state.set(workflow_node=m.group(1), workflow_parallel_branches=[])
            return

        m = _RE_BRANCH_START.search(message)
        if m:
            branches = list(app_state.get().workflow_parallel_branches)
            branches.append(m.group(1))
            app_state.set(workflow_parallel_branches=branches)
            return

        m = _RE_BRANCH_DONE.search(message)
        if m:
            branches = [b for b in app_state.get().workflow_parallel_branches if b != m.group(1)]
            app_state.set(workflow_parallel_branches=branches)
            return

        m = _RE_COMPLETE.search(message)
        if m:
            app_state.set(
                workflow_name="",
                workflow_node="",
                workflow_parallel_branches=[],
            )
            return

    return _on_progress


# ---------------------------------------------------------------------------
# Minimal slash-command dispatch
# ---------------------------------------------------------------------------

BUILTIN_COMMANDS: list[str] = [
    "/exit",
    "/clear",
    "/help",
    "/compact",
    "/model",
    "/status",
    "/permissions",
    "/permissions set",
    "/workflows",
    "/skills",
    "/tasks",
    "/cron",
]


def get_command_names(cwd: str | None = None) -> list[str]:
    """Return the list of slash commands the backend understands.

    Includes dynamically discovered workflow names as ``/<name>``.
    """
    commands = list(BUILTIN_COMMANDS)
    if cwd is not None:
        registry = load_workflow_registry(cwd)
        for wf in registry.list_workflows():
            commands.append(f"/{wf.name}")
    return commands


async def _dispatch_command(
    bundle: RuntimeBundle,
    line: str,
    *,
    print_system: SystemPrinter,
    clear_output: ClearHandler,
    select_request: SelectRequest | None = None,
) -> tuple[bool, bool]:
    """Try to handle *line* as a slash command.

    Returns ``(handled, should_continue)``.
    """
    stripped = line.strip()
    parts = stripped.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/exit":
        await print_system("Goodbye!")
        return True, False

    if cmd == "/clear":
        bundle.engine.clear()
        await clear_output()
        await print_system("Conversation cleared.")
        return True, True

    if cmd == "/help":
        lines = [
            "Available commands:",
            "  /exit              - Exit the session",
            "  /clear             - Clear conversation history",
            "  /help              - Show this help message",
            "  /compact           - Compact conversation (reduce token usage)",
            "  /model             - Show current model",
            "  /model <name>      - Switch model",
            "  /status            - Show session status",
            "  /permissions set <mode> - Set permission mode (default, plan, full_auto)",
            "  /workflows         - Browse available workflows",
            "  /workflows <name>  - Show workflow graph",
            "  /<name> <context>  - Run a workflow directly",
        ]
        await print_system("\n".join(lines))
        return True, True

    if cmd == "/compact":
        from leeway.services.compact import compact_conversation

        settings = load_settings()
        messages = bundle.engine.messages
        if len(messages) <= 6:
            await print_system("Not enough messages to compact.")
            return True, True
        compacted = await compact_conversation(
            messages,
            api_client=bundle.api_client,
            model=settings.model,
            preserve_recent=6,
        )
        bundle.engine.load_messages(compacted)
        await print_system(f"Compacted {len(messages)} -> {len(compacted)} messages.")
        return True, True

    if cmd == "/model":
        if args:
            bundle.engine.set_model(args)
            bundle.app_state.set(model=args)
            await print_system(f"Model switched to: {args}")
        else:
            state = bundle.app_state.get()
            await print_system(f"Current model: {state.model}")
        return True, True

    if cmd == "/status":
        state = bundle.app_state.get()
        lines = [
            f"Model: {state.model}",
            f"Provider: {state.provider}",
            f"Auth: {state.auth_status}",
            f"Permission mode: {state.permission_mode}",
            f"Working directory: {state.cwd}",
        ]
        if state.base_url:
            lines.append(f"Base URL: {state.base_url}")
        await print_system("\n".join(lines))
        return True, True

    if cmd == "/permissions":
        if args.startswith("set "):
            mode_str = args[4:].strip()
            from leeway.config.settings import save_settings
            from leeway.permissions.modes import PermissionMode

            try:
                mode = PermissionMode(mode_str)
            except ValueError:
                await print_system(
                    f"Unknown mode '{mode_str}'. Use: default, plan, or full_auto"
                )
                return True, True
            settings = load_settings()
            settings.permission.mode = mode
            save_settings(settings)
            bundle.engine.set_permission_checker(PermissionChecker(settings.permission))
            bundle.app_state.set(permission_mode=mode.value)
            await print_system(f"Permission mode set to: {mode.value}")
        else:
            state = bundle.app_state.get()
            await print_system(f"Permission mode: {state.permission_mode}")
        return True, True

    if cmd == "/workflows":
        from leeway.workflow.graph import render_workflow_graph

        registry = load_workflow_registry(bundle.cwd)
        workflows = registry.list_workflows()

        if args:
            # Direct lookup by name — show the graph
            selected = registry.get(args)
            if selected is None:
                await print_system(f"Workflow not found: '{args}'")
                return True, True
            graph = render_workflow_graph(selected)
            await print_system(graph)
            return True, True

        # No args — show interactive picker if available
        if not workflows:
            await print_system(
                "No workflows discovered.\n\n"
                "Place .yaml files in ~/.leeway/workflows/ or <project>/.leeway/workflows/"
            )
            return True, True

        if select_request is not None:
            options = [
                {
                    "value": w.name,
                    "label": w.name,
                    "description": w.description or f"{len(w.nodes)} nodes",
                }
                for w in workflows
            ]
            await select_request("Workflows", "/workflows ", options)
            return True, True

        # Fallback for non-interactive mode: print the list
        from leeway.workflow.graph import render_workflow_list
        await print_system(render_workflow_list(workflows))
        return True, True

    if cmd == "/skills":
        registry = load_skill_registry(bundle.cwd)
        skills = registry.list_skills()
        if not skills:
            await print_system(
                "No skills found.\n\n"
                "Place .md files in ~/.leeway/skills/ or <project>/.leeway/skills/"
            )
            return True, True
        lines = ["Available skills:"]
        for s in skills:
            desc = f" — {s.description}" if s.description else ""
            lines.append(f"  {s.name}{desc} [{s.source}]")
        await print_system("\n".join(lines))
        return True, True

    if cmd == "/cron":
        cron_st: CronStore | None = bundle.engine._tool_metadata.get("cron_store")  # type: ignore[union-attr]
        if cron_st is None:
            await print_system("Cron store not available.")
            return True, True
        jobs = cron_st.list()
        if not jobs:
            await print_system("No cron jobs. Use the cron_create tool to add one.")
            return True, True
        lines = [f"{'ID':<14} {'Name':<20} {'Enabled':<9} {'Runs':<6} {'Last Status'}"]
        lines.append("-" * 70)
        for j in jobs:
            status = j.last_status or "-"
            lines.append(
                f"{j.id:<14} {j.name[:18]:<20} {'yes' if j.enabled else 'no':<9} "
                f"{j.run_count:<6} {status[:20]}"
            )
        await print_system("\n".join(lines))
        return True, True

    if cmd == "/tasks":
        mgr: BackgroundTaskManager | None = bundle.engine._tool_metadata.get("task_manager")  # type: ignore[union-attr]
        if mgr is None:
            await print_system("Task manager not available.")
            return True, True
        tasks = mgr.list_tasks()
        if not tasks:
            await print_system("No background tasks.")
            return True, True
        lines = [f"{'ID':<14} {'Type':<10} {'State':<12} {'Description'}"]
        lines.append("-" * 60)
        for t in tasks[:20]:
            lines.append(f"{t.id:<14} {t.type.value:<10} {t.state.value:<12} {t.description[:40]}")
        await print_system("\n".join(lines))
        return True, True

    # ── Fallback: try matching /<name> as a workflow ──
    wf_name = cmd.lstrip("/")
    registry = load_workflow_registry(bundle.cwd)
    defn = registry.get(wf_name)
    if defn is not None:
        from leeway.workflow.engine import WorkflowEngine

        if not args:
            await print_system(f"Usage: /{wf_name} <context describing what to work on>")
            return True, True

        state_progress = _make_workflow_progress(bundle.app_state)

        async def _progress_both(msg: str) -> None:
            await state_progress(msg)
            await print_system(msg)

        engine = WorkflowEngine(
            workflow=defn,
            api_client=bundle.api_client,
            full_tool_registry=bundle.tool_registry,
            permission_checker=PermissionChecker(load_settings().permission),
            cwd=Path(bundle.cwd),
            model=bundle.app_state.get().model,
            max_tokens=load_settings().max_tokens,
            tool_metadata=bundle.engine._tool_metadata,
            on_progress=_progress_both,
            permission_prompt=bundle.engine._permission_prompt,
            ask_user_prompt=bundle.engine._ask_user_prompt,
        )
        result = await engine.execute(user_context=args)
        # Ensure statusline clears workflow state even on error/early exit
        bundle.app_state.set(
            workflow_name="",
            workflow_node="",
            workflow_parallel_branches=[],
        )
        await print_system(result.format_output())
        return True, True

    return False, True


async def handle_line(
    bundle: RuntimeBundle,
    line: str,
    *,
    print_system: SystemPrinter,
    render_event: StreamRenderer,
    clear_output: ClearHandler,
    select_request: SelectRequest | None = None,
) -> bool:
    """Handle one submitted line."""
    # Check for slash commands first
    if line.strip().startswith("/"):
        handled, should_continue = await _dispatch_command(
            bundle, line,
            print_system=print_system,
            clear_output=clear_output,
            select_request=select_request,
        )
        if handled:
            sync_app_state(bundle)
            return should_continue

    settings = load_settings()
    bundle.engine.set_system_prompt(
        build_runtime_system_prompt(settings, cwd=bundle.cwd, latest_user_prompt=line)
    )
    # Inject workflow progress callback so LLM-invoked workflows emit progress
    if bundle.engine._tool_metadata is not None:
        state_progress = _make_workflow_progress(bundle.app_state)

        async def _progress_both(msg: str) -> None:
            await state_progress(msg)
            await print_system(msg)

        bundle.engine._tool_metadata["workflow_progress"] = _progress_both
    async for event in bundle.engine.submit_message(line):
        await render_event(event)
    sync_app_state(bundle)
    return True
