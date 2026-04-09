"""Tests for background task manager."""

import asyncio
from pathlib import Path

import pytest

from leeway.tasks.manager import BackgroundTaskManager
from leeway.tasks.store import TaskStore
from leeway.tasks.types import TaskState


@pytest.fixture
def manager(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("leeway.tasks.manager.get_data_dir", lambda: tmp_path)
    store = TaskStore(tmp_path / "tasks.json")
    return BackgroundTaskManager(store=store)


@pytest.mark.asyncio
async def test_create_shell_task(manager):
    task = await manager.create_shell_task("echo hello", description="test echo")
    assert task.state == TaskState.RUNNING
    assert task.command == "echo hello"
    # Wait a bit for the process to finish
    await asyncio.sleep(0.5)
    updated = manager.get_task(task.id)
    assert updated is not None
    assert updated.state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_get_output(manager):
    task = await manager.create_shell_task("echo 'line1' && echo 'line2'")
    await asyncio.sleep(0.5)
    output = manager.get_output(task.id, tail_lines=10)
    assert "line1" in output
    assert "line2" in output


@pytest.mark.asyncio
async def test_list_tasks(manager):
    await manager.create_shell_task("echo a")
    await manager.create_shell_task("echo b")
    tasks = manager.list_tasks()
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_stop_task(manager):
    task = await manager.create_shell_task("sleep 30")
    await asyncio.sleep(0.2)
    stopped = await manager.stop_task(task.id)
    assert stopped is True
    updated = manager.get_task(task.id)
    assert updated is not None
    assert updated.state == TaskState.KILLED


@pytest.mark.asyncio
async def test_stop_nonexistent(manager):
    stopped = await manager.stop_task("nonexistent")
    assert stopped is False
