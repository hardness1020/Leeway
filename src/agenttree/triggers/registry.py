"""Trigger registry — persistent trigger storage."""

from __future__ import annotations

import json
from pathlib import Path

from agenttree.triggers.types import TriggerDefinition


class TriggerRegistry:
    """CRUD storage for trigger definitions, backed by a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, TriggerDefinition]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {k: TriggerDefinition.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_all(self, records: dict[str, TriggerDefinition]) -> None:
        data = {k: json.loads(v.model_dump_json()) for k, v in records.items()}
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def save(self, trigger: TriggerDefinition) -> None:
        records = self._load_all()
        records[trigger.id] = trigger
        self._save_all(records)

    def get(self, trigger_id: str) -> TriggerDefinition | None:
        return self._load_all().get(trigger_id)

    def list(self) -> list[TriggerDefinition]:
        return sorted(self._load_all().values(), key=lambda t: t.created_at, reverse=True)

    def delete(self, trigger_id: str) -> bool:
        records = self._load_all()
        if trigger_id not in records:
            return False
        del records[trigger_id]
        self._save_all(records)
        return True
