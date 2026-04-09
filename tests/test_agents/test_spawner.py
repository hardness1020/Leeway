"""Tests for agent spawner."""

from pathlib import Path

import pytest

from leeway.agents.spawner import AgentSpawner
from leeway.agents.types import AgentSpec
from leeway.tasks.manager import BackgroundTaskManager
from leeway.tasks.store import TaskStore
from leeway.tasks.types import TaskState


@pytest.fixture
def spawner(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("leeway.tasks.manager.get_data_dir", lambda: tmp_path)
    store = TaskStore(tmp_path / "tasks.json")
    manager = BackgroundTaskManager(store=store)
    return AgentSpawner(task_manager=manager, cwd=str(tmp_path))


@pytest.mark.asyncio
async def test_spawn_simple_task(spawner):
    spec = AgentSpec(task="echo hello from agent")
    task = await spawner.spawn(spec)
    assert task.id is not None
    assert task.state == TaskState.RUNNING


@pytest.mark.asyncio
async def test_spawn_with_workflow(spawner):
    spec = AgentSpec(task="review this code", workflow="code_review")
    task = await spawner.spawn(spec)
    assert task.id is not None
