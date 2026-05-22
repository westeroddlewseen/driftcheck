"""Simple file-based snapshot cache for driftcheck."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from driftcheck.snapshot import Snapshot


class CacheError(Exception):
    """Raised when cache read/write operations fail."""


class SnapshotCache:
    """Persist and retrieve Snapshot objects on disk as JSON.

    Parameters
    ----------
    cache_dir:
        Directory where cache files are stored.  Created on first write.
    ttl_seconds:
        Maximum age (in seconds) before a cached entry is considered stale.
        ``None`` disables expiry.
    """

    def __init__(self, cache_dir: str | os.PathLike, ttl_seconds: Optional[int] = 300) -> None:
        self._dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path_for(self, service: str) -> Path:
        safe = service.replace("/", "__").replace(" ", "_")
        return self._dir / f"{safe}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, service: str, snapshot: Snapshot) -> None:
        """Serialise *snapshot* to disk under *service* key."""
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = {"ts": time.time(), "snapshot": snapshot.as_dict()}
        target = self._path_for(service)
        try:
            target.write_text(json.dumps(payload), encoding="utf-8")
        except OSError as exc:
            raise CacheError(f"Failed to write cache for '{service}': {exc}") from exc

    def load(self, service: str) -> Optional[Snapshot]:
        """Return a cached :class:`Snapshot` for *service*, or ``None``.

        Returns ``None`` when the entry is missing or stale.
        """
        target = self._path_for(service)
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheError(f"Failed to read cache for '{service}': {exc}") from exc

        if self.ttl_seconds is not None:
            age = time.time() - payload.get("ts", 0)
            if age > self.ttl_seconds:
                return None

        data = payload["snapshot"]
        return Snapshot(
            service=data["service"],
            image=data.get("image"),
            replicas=data.get("replicas", 1),
            env=data.get("env", {}),
        )

    def invalidate(self, service: str) -> bool:
        """Delete the cache entry for *service*.  Returns ``True`` if deleted."""
        target = self._path_for(service)
        if target.exists():
            target.unlink()
            return True
        return False
