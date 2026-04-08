"""Agent spawner — creates subagent processes."""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

from agenttree.agents.types import AgentSpec
from agenttree.tasks.manager import BackgroundTaskManager
from agenttree.tasks.types import TaskRecord

logger = logging.getLogger(__name__)


class AgentSpawner:
    """Spawns subagent processes that run independently."""

    def __init__(self, task_manager: BackgroundTaskManager, cwd: str) -> None:
        self._task_manager = task_manager
        self._cwd = cwd

    async def spawn(self, spec: AgentSpec) -> TaskRecord:
        """Spawn a new subagent based on the spec.

        Returns a TaskRecord that can be monitored via the task manager.
        """
        cwd = spec.cwd or self._cwd

        if spec.isolation == "worktree":
            cwd = await self._create_worktree(cwd)

        if spec.workflow:
            task = await self._task_manager.create_workflow_task(
                workflow_name=spec.workflow,
                context=spec.task,
                cwd=cwd,
                description=f"agent: {spec.task[:60]}",
            )
        else:
            # Run as a direct prompt via exec (not shell) to prevent injection
            task = await self._task_manager.create_exec_task(
                args=[sys.executable, "-m", "agenttree", "-p", spec.task, "--output-format", "text"],
                cwd=cwd,
                description=f"agent: {spec.task[:60]}",
            )

        return task

    async def _create_worktree(self, base_cwd: str) -> str:
        """Create a git worktree for isolated execution."""
        import uuid

        branch_name = f"agent-{uuid.uuid4().hex[:8]}"
        worktree_path = Path(tempfile.mkdtemp(prefix="agenttree-wt-"))

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "worktree", "add", "-b", branch_name, str(worktree_path),
                cwd=base_cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            if proc.returncode == 0:
                logger.info("Created worktree at %s (branch: %s)", worktree_path, branch_name)
                return str(worktree_path)
        except Exception:
            logger.warning("Failed to create worktree, using base cwd")

        return base_cwd
