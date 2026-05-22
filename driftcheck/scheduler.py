"""Periodic drift-check scheduler using a simple interval loop."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """Raised when the scheduler encounters an unrecoverable error."""


@dataclass
class SchedulerConfig:
    interval_seconds: int = 300
    max_runs: Optional[int] = None  # None means run indefinitely
    on_error: str = "log"  # "log" | "raise"


class Scheduler:
    """Runs a callable at a fixed interval in a background thread."""

    def __init__(self, task: Callable[[], None], config: Optional[SchedulerConfig] = None) -> None:
        if not callable(task):
            raise SchedulerError("task must be callable")
        self._task = task
        self._config = config or SchedulerConfig()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._run_count: int = 0
        self._errors: List[Exception] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler in a daemon background thread."""
        if self._thread and self._thread.is_alive():
            raise SchedulerError("Scheduler is already running")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="driftcheck-scheduler")
        self._thread.start()
        logger.info("Scheduler started (interval=%ds)", self._config.interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scheduler to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        logger.info("Scheduler stopped after %d run(s)", self._run_count)

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def errors(self) -> List[Exception]:
        return list(self._errors)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._execute()
            if self._config.max_runs is not None and self._run_count >= self._config.max_runs:
                logger.debug("Reached max_runs=%d, stopping", self._config.max_runs)
                break
            self._stop_event.wait(timeout=self._config.interval_seconds)

    def _execute(self) -> None:
        try:
            self._task()
            self._run_count += 1
        except Exception as exc:  # noqa: BLE001
            self._errors.append(exc)
            if self._config.on_error == "raise":
                raise SchedulerError(f"Task failed: {exc}") from exc
            logger.error("Scheduler task error (run #%d): %s", self._run_count + 1, exc)
