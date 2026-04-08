"""Background task manager — spawns and tracks async tasks."""

from __future__ import annotations

import asyncio
import signal
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from agenttree.config.paths import get_data_dir
from agenttree.tasks.store import TaskStore
from agenttree.tasks.types import TaskRecord, TaskState, TaskType


class BackgroundTaskManager:
    """Create, track, and manage background shell and workflow tasks."""

    def __init__(self, store: TaskStore | None = None) -> None:
        tasks_dir = get_data_dir() / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        self._store = store or TaskStore(get_data_dir() / "tasks.json")
        self._output_dir = tasks_dir
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    async def create_shell_task(
        self,
        command: str,
        cwd: str | None = None,
        description: str = "",
    ) -> TaskRecord:
        """Spawn a shell command as a background task."""
        task = TaskRecord(
            type=TaskType.SHELL,
            command=command,
            cwd=cwd,
            description=description or command[:80],
        )
        output_path = self._output_dir / f"{task.id}.log"
        task.output_path = output_path
        task.state = TaskState.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self._store.save(task)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        self._processes[task.id] = proc
        asyncio.create_task(self._monitor_process(task.id, proc, output_path))
        return task

    async def create_exec_task(
        self,
        args: list[str],
        cwd: str | None = None,
        description: str = "",
    ) -> TaskRecord:
        """Spawn a command as a background task using exec (no shell interpretation)."""
        task = TaskRecord(
            type=TaskType.SHELL,
            command=" ".join(args),
            cwd=cwd,
            description=description or args[0][:80],
        )
        output_path = self._output_dir / f"{task.id}.log"
        task.output_path = output_path
        task.state = TaskState.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self._store.save(task)

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        self._processes[task.id] = proc
        asyncio.create_task(self._monitor_process(task.id, proc, output_path))
        return task

    async def create_workflow_task(
        self,
        workflow_name: str,
        context: str = "",
        cwd: str | None = None,
        description: str = "",
    ) -> TaskRecord:
        """Spawn a workflow execution as a background task."""
        import sys

        task = TaskRecord(
            type=TaskType.WORKFLOW,
            workflow_name=workflow_name,
            workflow_context=context,
            cwd=cwd,
            description=description or f"workflow: {workflow_name}",
        )
        output_path = self._output_dir / f"{task.id}.log"
        task.output_path = output_path
        task.state = TaskState.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self._store.save(task)

        cmd = [
            sys.executable, "-m", "agenttree",
            "-p", f"/{workflow_name} {context}",
            "--output-format", "text",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        self._processes[task.id] = proc
        asyncio.create_task(self._monitor_process(task.id, proc, output_path))
        return task

    async def _monitor_process(
        self,
        task_id: str,
        proc: asyncio.subprocess.Process,
        output_path: Path,
    ) -> None:
        """Read process output and update task state on completion."""
        try:
            assert proc.stdout is not None
            with open(output_path, "wb") as f:
                async for chunk in proc.stdout:
                    f.write(chunk)
            await proc.wait()
        except Exception:
            pass
        finally:
            self._processes.pop(task_id, None)

        task = self._store.get(task_id)
        if task is None:
            return

        task.completed_at = datetime.now(timezone.utc)
        task.exit_code = proc.returncode
        if proc.returncode == 0:
            task.state = TaskState.COMPLETED
        elif proc.returncode and proc.returncode < 0:
            task.state = TaskState.KILLED
        else:
            task.state = TaskState.FAILED
            task.error = f"Exit code: {proc.returncode}"
        self._store.save(task)

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._store.get(task_id)

    def list_tasks(self, state: str | None = None) -> list[TaskRecord]:
        return self._store.list(state)

    def get_output(self, task_id: str, tail_lines: int = 50) -> str:
        """Return the last N lines of a task's output."""
        task = self._store.get(task_id)
        if task is None or task.output_path is None:
            return ""
        try:
            lines = deque(
                Path(task.output_path).read_text(encoding="utf-8", errors="replace").splitlines(),
                maxlen=tail_lines,
            )
            return "\n".join(lines)
        except OSError:
            return ""

    async def stop_task(self, task_id: str) -> bool:
        """Stop a running task (SIGTERM, then SIGKILL after 5s)."""
        proc = self._processes.get(task_id)
        if proc is None:
            return False

        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return False

        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass

        task = self._store.get(task_id)
        if task is not None:
            task.state = TaskState.KILLED
            task.completed_at = datetime.now(timezone.utc)
            self._store.save(task)

        self._processes.pop(task_id, None)
        return True
