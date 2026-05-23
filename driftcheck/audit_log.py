"""Audit log: persists drift-check run results to a JSONL file."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class AuditLogError(Exception):
    """Raised when the audit log cannot be read or written."""


@dataclass
class AuditEntry:
    timestamp: str
    service: str
    has_drift: bool
    drifted_keys: List[str] = field(default_factory=list)
    run_id: Optional[str] = None

    @staticmethod
    def now(service: str, has_drift: bool, drifted_keys: List[str],
            run_id: Optional[str] = None) -> "AuditEntry":
        ts = datetime.now(tz=timezone.utc).isoformat()
        return AuditEntry(
            timestamp=ts,
            service=service,
            has_drift=has_drift,
            drifted_keys=drifted_keys,
            run_id=run_id,
        )


class AuditLog:
    """Append-only JSONL audit log for drift-check runs."""

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)

    # ------------------------------------------------------------------
    def append(self, entry: AuditEntry) -> None:
        """Append *entry* to the log file (creates the file if absent)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(entry)) + "\n")
        except OSError as exc:
            raise AuditLogError(f"Cannot write audit log: {exc}") from exc

    def read_all(self) -> List[AuditEntry]:
        """Return every entry recorded in the log, oldest first."""
        if not self._path.exists():
            return []
        entries: List[AuditEntry] = []
        try:
            with self._path.open(encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(AuditEntry(**data))
                    except (json.JSONDecodeError, TypeError) as exc:
                        raise AuditLogError(
                            f"Corrupt audit log at line {lineno}: {exc}"
                        ) from exc
        except OSError as exc:
            raise AuditLogError(f"Cannot read audit log: {exc}") from exc
        return entries

    def clear(self) -> None:
        """Delete the log file if it exists."""
        try:
            if self._path.exists():
                self._path.unlink()
        except OSError as exc:
            raise AuditLogError(f"Cannot clear audit log: {exc}") from exc
