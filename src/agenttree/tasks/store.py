"""Persistent task storage backed by a JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from agenttree.tasks.types import TaskRecord


class TaskStore:
    """CRUD storage for task records."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, TaskRecord]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {k: TaskRecord.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_all(self, records: dict[str, TaskRecord]) -> None:
        data = {k: json.loads(v.model_dump_json()) for k, v in records.items()}
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def save(self, task: TaskRecord) -> None:
        records = self._load_all()
        records[task.id] = task
        self._save_all(records)

    def get(self, task_id: str) -> TaskRecord | None:
        return self._load_all().get(task_id)

    def list(self, state: str | None = None) -> list[TaskRecord]:
        records = self._load_all()
        tasks = list(records.values())
        if state:
            tasks = [t for t in tasks if t.state.value == state]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def delete(self, task_id: str) -> bool:
        records = self._load_all()
        if task_id not in records:
            return False
        del records[task_id]
        self._save_all(records)
        return True
