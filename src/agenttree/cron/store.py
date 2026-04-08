"""Persistent cron job storage."""

from __future__ import annotations

import json
from pathlib import Path

from agenttree.cron.types import CronJob


class CronStore:
    """CRUD storage for cron jobs, backed by a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, CronJob]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {k: CronJob.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_all(self, records: dict[str, CronJob]) -> None:
        data = {k: json.loads(v.model_dump_json()) for k, v in records.items()}
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def save(self, job: CronJob) -> None:
        records = self._load_all()
        records[job.id] = job
        self._save_all(records)

    def get(self, job_id: str) -> CronJob | None:
        return self._load_all().get(job_id)

    def list(self, enabled_only: bool = False) -> list[CronJob]:
        jobs = list(self._load_all().values())
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def delete(self, job_id: str) -> bool:
        records = self._load_all()
        if job_id not in records:
            return False
        del records[job_id]
        self._save_all(records)
        return True
