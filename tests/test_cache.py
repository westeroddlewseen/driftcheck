"""Tests for driftcheck.cache."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from driftcheck.cache import CacheError, SnapshotCache
from driftcheck.snapshot import Snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(service: str = "web") -> Snapshot:
    return Snapshot(service=service, image="nginx:1.25", replicas=2, env={"PORT": "80"})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache")
    snap = _snapshot()
    cache.save("web", snap)
    result = cache.load("web")
    assert result is not None
    assert result.service == snap.service
    assert result.image == snap.image
    assert result.replicas == snap.replicas
    assert result.env == snap.env


def test_load_returns_none_when_missing(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache")
    assert cache.load("nonexistent") is None


def test_load_returns_none_when_stale(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache", ttl_seconds=1)
    cache.save("web", _snapshot())
    # Manually backdate the timestamp
    p = list((tmp_path / "cache").glob("*.json"))[0]
    payload = json.loads(p.read_text())
    payload["ts"] = time.time() - 10
    p.write_text(json.dumps(payload))
    assert cache.load("web") is None


def test_load_ignores_ttl_when_none(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache", ttl_seconds=None)
    cache.save("web", _snapshot())
    p = list((tmp_path / "cache").glob("*.json"))[0]
    payload = json.loads(p.read_text())
    payload["ts"] = 0  # ancient
    p.write_text(json.dumps(payload))
    assert cache.load("web") is not None


def test_invalidate_removes_entry(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache")
    cache.save("web", _snapshot())
    removed = cache.invalidate("web")
    assert removed is True
    assert cache.load("web") is None


def test_invalidate_returns_false_when_missing(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path / "cache")
    assert cache.invalidate("ghost") is False


def test_save_creates_cache_dir(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "cache"
    cache = SnapshotCache(nested)
    cache.save("svc", _snapshot("svc"))
    assert nested.exists()


def test_load_raises_cache_error_on_corrupt_file(tmp_path: Path) -> None:
    cache = SnapshotCache(tmp_path)
    (tmp_path / "web.json").write_text("not-json")
    with pytest.raises(CacheError, match="Failed to read cache"):
        cache.load("web")
