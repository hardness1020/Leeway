"""Cron scheduler daemon entry point."""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

from agenttree.config.paths import get_data_dir
from agenttree.cron.scheduler import CronScheduler
from agenttree.cron.store import CronStore
from agenttree.tasks.manager import BackgroundTaskManager
from agenttree.tasks.store import TaskStore


def _pid_path() -> Path:
    return get_data_dir() / "scheduler.pid"


def is_scheduler_running() -> bool:
    """Check if the scheduler daemon is running."""
    pid_file = _pid_path()
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # signal 0 = check existence
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        pid_file.unlink(missing_ok=True)
        return False


def start_scheduler() -> None:
    """Start the scheduler in the current process (foreground)."""
    pid_file = _pid_path()
    if is_scheduler_running():
        print("Scheduler is already running.")
        sys.exit(1)

    pid_file.write_text(str(os.getpid()))

    data_dir = get_data_dir()
    store = CronStore(data_dir / "cron_jobs.json")
    task_store = TaskStore(data_dir / "tasks.json")
    task_manager = BackgroundTaskManager(store=task_store)
    scheduler = CronScheduler(store=store, task_manager=task_manager)

    def _shutdown(signum, frame):
        scheduler.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        asyncio.run(scheduler.run())
    finally:
        pid_file.unlink(missing_ok=True)


def stop_scheduler() -> None:
    """Stop the running scheduler daemon."""
    pid_file = _pid_path()
    if not pid_file.exists():
        print("Scheduler is not running.")
        return
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to scheduler (PID {pid}).")
    except (ValueError, ProcessLookupError):
        print("Scheduler process not found.")
        pid_file.unlink(missing_ok=True)


def scheduler_status() -> None:
    """Print scheduler status."""
    if is_scheduler_running():
        pid = int(_pid_path().read_text().strip())
        print(f"Scheduler is running (PID {pid}).")
        store = CronStore(get_data_dir() / "cron_jobs.json")
        jobs = store.list()
        enabled = sum(1 for j in jobs if j.enabled)
        print(f"Jobs: {len(jobs)} total, {enabled} enabled.")
    else:
        print("Scheduler is not running.")
