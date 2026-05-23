"""Baseline management: save and compare snapshots as a known-good reference."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from driftcheck.snapshot import Snapshot


class BaselineError(Exception):
    """Raised when baseline operations fail."""


@dataclass
class BaselineDiff:
    service: str
    field: str
    baseline_value: object
    current_value: object

    def __str__(self) -> str:
        return (
            f"{self.service}.{self.field}: "
            f"baseline={self.baseline_value!r} current={self.current_value!r}"
        )


class BaselineManager:
    """Persists snapshots as a baseline and detects deviations from it."""

    _COMPARE_FIELDS = ("image", "replicas", "env")

    def __init__(self, baseline_dir: str = ".driftcheck/baselines") -> None:
        self._dir = Path(baseline_dir)

    def _path_for(self, service: str) -> Path:
        return self._dir / f"{service}.json"

    def save(self, snapshot: Snapshot) -> None:
        """Persist *snapshot* as the current baseline for its service."""
        self._dir.mkdir(parents=True, exist_ok=True)
        data = snapshot.as_dict()
        data["_saved_at"] = time.time()
        try:
            self._path_for(snapshot.service).write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            raise BaselineError(f"Could not save baseline: {exc}") from exc

    def load(self, service: str) -> Optional[Snapshot]:
        """Return the saved baseline for *service*, or ``None`` if absent."""
        path = self._path_for(service)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BaselineError(f"Could not load baseline for {service!r}: {exc}") from exc
        data.pop("_saved_at", None)
        return Snapshot(**data)

    def diff(self, current: Snapshot) -> list[BaselineDiff]:
        """Return fields that differ between *current* and the saved baseline."""
        baseline = self.load(current.service)
        if baseline is None:
            return []
        diffs: list[BaselineDiff] = []
        for field in self._COMPARE_FIELDS:
            bval = getattr(baseline, field, None)
            cval = getattr(current, field, None)
            if bval != cval:
                diffs.append(BaselineDiff(current.service, field, bval, cval))
        return diffs
