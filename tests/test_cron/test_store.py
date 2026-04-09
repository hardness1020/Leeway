"""Tests for cron store."""

from pathlib import Path

from leeway.cron.store import CronStore
from leeway.cron.types import CronJob, CronScheduleSpec, ShellAction


def _make_job(name: str = "test-job") -> CronJob:
    return CronJob(
        name=name,
        schedule=CronScheduleSpec(expression="*/5 * * * *"),
        action=ShellAction(command="echo hi"),
    )


def test_save_and_get(tmp_path: Path):
    store = CronStore(tmp_path / "cron.json")
    job = _make_job()
    store.save(job)
    loaded = store.get(job.id)
    assert loaded is not None
    assert loaded.name == "test-job"


def test_list(tmp_path: Path):
    store = CronStore(tmp_path / "cron.json")
    j1 = _make_job("a")
    j2 = _make_job("b")
    j2.enabled = False
    store.save(j1)
    store.save(j2)

    assert len(store.list()) == 2
    assert len(store.list(enabled_only=True)) == 1


def test_delete(tmp_path: Path):
    store = CronStore(tmp_path / "cron.json")
    job = _make_job()
    store.save(job)
    assert store.delete(job.id) is True
    assert store.get(job.id) is None
    assert store.delete("nope") is False
