"""Tests for cron scheduler logic."""

from datetime import datetime, timezone

from leeway.cron.scheduler import compute_next_run
from leeway.cron.types import (
    CronJob,
    CronScheduleSpec,
    IntervalSchedule,
    OneShotSchedule,
    ShellAction,
)


def _make_job(schedule, **kwargs) -> CronJob:
    return CronJob(
        name="test",
        schedule=schedule,
        action=ShellAction(command="echo test"),
        **kwargs,
    )


def test_interval_first_run():
    job = _make_job(IntervalSchedule(seconds=60))
    nxt = compute_next_run(job)
    assert nxt is not None


def test_interval_after_last_run():
    now = datetime.now(timezone.utc)
    job = _make_job(IntervalSchedule(seconds=120), last_run=now)
    nxt = compute_next_run(job)
    assert nxt is not None
    assert nxt > now


def test_oneshot_not_yet_run():
    from datetime import timedelta

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    job = _make_job(OneShotSchedule(at=future))
    nxt = compute_next_run(job)
    assert nxt is not None
    assert nxt == future.replace(tzinfo=timezone.utc)


def test_oneshot_already_run():
    from datetime import timedelta

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    job = _make_job(OneShotSchedule(at=future), run_count=1)
    nxt = compute_next_run(job)
    assert nxt is None


def test_cron_expression():
    job = _make_job(CronScheduleSpec(expression="*/5 * * * *"))
    nxt = compute_next_run(job)
    assert nxt is not None
