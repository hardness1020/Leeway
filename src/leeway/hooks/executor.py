"""Hook executor — runs matched hooks asynchronously."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from leeway.hooks.registry import HookRegistry
from leeway.hooks.types import (
    CommandHookDefinition,
    HookEvent,
    HttpHookDefinition,
)

logger = logging.getLogger(__name__)


class HookExecutor:
    """Executes matching hooks for lifecycle events."""

    def __init__(self, registry: HookRegistry) -> None:
        self._registry = registry

    async def execute_hooks(
        self,
        event: HookEvent,
        context: dict[str, Any] | None = None,
        *,
        tool_name: str | None = None,
        workflow_name: str | None = None,
    ) -> None:
        """Fire all matching hooks. Errors are logged but do not propagate."""
        hooks = self._registry.get_matching(
            event, tool_name=tool_name, workflow_name=workflow_name
        )
        if not hooks:
            return

        payload = json.dumps(context or {})
        tasks = []
        for hook in hooks:
            if isinstance(hook, CommandHookDefinition):
                tasks.append(self._run_command_hook(hook, payload))
            elif isinstance(hook, HttpHookDefinition):
                tasks.append(self._run_http_hook(hook, payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_command_hook(
        self,
        hook: CommandHookDefinition,
        payload: str,
    ) -> None:
        try:
            proc = await asyncio.create_subprocess_shell(
                hook.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"AGENTTREE_HOOK_PAYLOAD": payload},
            )
            await asyncio.wait_for(proc.communicate(payload.encode()), timeout=hook.timeout)
        except asyncio.TimeoutError:
            logger.warning("Command hook timed out: %s", hook.command[:80])
        except Exception:
            logger.warning("Command hook failed: %s", hook.command[:80], exc_info=True)

    async def _run_http_hook(
        self,
        hook: HttpHookDefinition,
        payload: str,
    ) -> None:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=float(hook.timeout)) as client:
                await client.request(
                    method=hook.method,
                    url=hook.url,
                    headers=hook.headers,
                    content=payload,
                )
        except Exception:
            logger.warning("HTTP hook failed: %s %s", hook.method, hook.url, exc_info=True)
