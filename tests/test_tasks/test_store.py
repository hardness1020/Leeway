"""Tests for task store."""

from pathlib import Path

from agenttree.tasks.store import TaskStore
from agenttree.tasks.types import TaskRecord, TaskState, TaskType


def test_save_and_get(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.json")
    task = TaskRecord(type=TaskType.SHELL, command="echo hi", description="Test task")
    store.save(task)

    loaded = store.get(task.id)
    assert loaded is not None
    assert loaded.command == "echo hi"
    assert loaded.state == TaskState.PENDING


def test_list_tasks(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.json")
    t1 = TaskRecord(type=TaskType.SHELL, command="echo 1", state=TaskState.RUNNING)
    t2 = TaskRecord(type=TaskType.SHELL, command="echo 2", state=TaskState.COMPLETED)
    store.save(t1)
    store.save(t2)

    assert len(store.list()) == 2
    assert len(store.list(state="running")) == 1
    assert len(store.list(state="completed")) == 1


def test_delete(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.json")
    task = TaskRecord(type=TaskType.SHELL, command="echo x")
    store.save(task)
    assert store.delete(task.id) is True
    assert store.get(task.id) is None
    assert store.delete("nonexistent") is False


def test_empty_store(tmp_path: Path):
    store = TaskStore(tmp_path / "tasks.json")
    assert store.list() == []
    assert store.get("nope") is None
