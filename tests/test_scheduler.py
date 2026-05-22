"""Tests for driftcheck.scheduler."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from driftcheck.scheduler import Scheduler, SchedulerConfig, SchedulerError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scheduler(task=None, **kwargs):
    task = task or MagicMock()
    cfg = SchedulerConfig(**kwargs) if kwargs else SchedulerConfig()
    return Scheduler(task, cfg), task


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_non_callable_raises():
    with pytest.raises(SchedulerError, match="callable"):
        Scheduler("not-a-function")  # type: ignore[arg-type]


def test_default_config_applied():
    sched, _ = _make_scheduler()
    assert sched.run_count == 0
    assert sched.errors == []


# ---------------------------------------------------------------------------
# max_runs behaviour (synchronous via _execute)
# ---------------------------------------------------------------------------

def test_run_count_increments_on_success():
    sched, task = _make_scheduler()
    sched._execute()
    sched._execute()
    assert sched.run_count == 2
    assert task.call_count == 2


def test_error_logged_when_on_error_is_log():
    boom = MagicMock(side_effect=RuntimeError("oops"))
    sched = Scheduler(boom, SchedulerConfig(on_error="log"))
    sched._execute()  # should not raise
    assert len(sched.errors) == 1
    assert isinstance(sched.errors[0], RuntimeError)
    assert sched.run_count == 0  # count only increments on success


def test_error_raises_when_on_error_is_raise():
    boom = MagicMock(side_effect=ValueError("bad"))
    sched = Scheduler(boom, SchedulerConfig(on_error="raise"))
    with pytest.raises(SchedulerError, match="bad"):
        sched._execute()


# ---------------------------------------------------------------------------
# Thread-based integration tests (short interval)
# ---------------------------------------------------------------------------

def test_start_stop_runs_task_at_least_once():
    event = threading.Event()
    calls = []

    def task():
        calls.append(1)
        event.set()

    sched = Scheduler(task, SchedulerConfig(interval_seconds=60, max_runs=None))
    sched.start()
    event.wait(timeout=2)
    sched.stop(timeout=2)
    assert len(calls) >= 1


def test_max_runs_stops_loop():
    sched, task = _make_scheduler(interval_seconds=0, max_runs=2)
    sched.start()
    # Give thread time to complete both runs
    time.sleep(0.2)
    sched.stop(timeout=1)
    assert sched.run_count == 2


def test_double_start_raises():
    sched, _ = _make_scheduler(interval_seconds=60)
    sched.start()
    try:
        with pytest.raises(SchedulerError, match="already running"):
            sched.start()
    finally:
        sched.stop(timeout=1)
