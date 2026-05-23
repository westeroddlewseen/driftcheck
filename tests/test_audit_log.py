"""Tests for driftcheck.audit_log."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftcheck.audit_log import AuditEntry, AuditLog, AuditLogError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _log(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.jsonl")


def _entry(**kwargs) -> AuditEntry:
    defaults = dict(
        timestamp="2024-01-01T00:00:00+00:00",
        service="svc-a",
        has_drift=False,
        drifted_keys=[],
        run_id=None,
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_append_creates_file(tmp_path):
    log = _log(tmp_path)
    log.append(_entry())
    assert (tmp_path / "audit.jsonl").exists()


def test_read_all_empty_when_no_file(tmp_path):
    log = _log(tmp_path)
    assert log.read_all() == []


def test_roundtrip_single_entry(tmp_path):
    log = _log(tmp_path)
    e = _entry(service="svc-b", has_drift=True, drifted_keys=["image"])
    log.append(e)
    entries = log.read_all()
    assert len(entries) == 1
    assert entries[0].service == "svc-b"
    assert entries[0].has_drift is True
    assert entries[0].drifted_keys == ["image"]


def test_roundtrip_multiple_entries(tmp_path):
    log = _log(tmp_path)
    for i in range(3):
        log.append(_entry(service=f"svc-{i}"))
    entries = log.read_all()
    assert [e.service for e in entries] == ["svc-0", "svc-1", "svc-2"]


def test_clear_removes_file(tmp_path):
    log = _log(tmp_path)
    log.append(_entry())
    log.clear()
    assert not (tmp_path / "audit.jsonl").exists()


def test_clear_is_idempotent(tmp_path):
    log = _log(tmp_path)
    log.clear()  # file does not exist yet — should not raise


def test_corrupt_line_raises_audit_log_error(tmp_path):
    p = tmp_path / "audit.jsonl"
    p.write_text("not-json\n", encoding="utf-8")
    log = AuditLog(p)
    with pytest.raises(AuditLogError, match="Corrupt"):
        log.read_all()


def test_now_factory_sets_timestamp():
    e = AuditEntry.now(service="x", has_drift=False, drifted_keys=[])
    assert "T" in e.timestamp  # ISO-8601
    assert e.service == "x"


def test_write_error_raises_audit_log_error(tmp_path):
    """Passing a directory as the log path triggers an OSError on open."""
    log = AuditLog(tmp_path)  # tmp_path itself is a directory
    with pytest.raises(AuditLogError, match="Cannot write"):
        log.append(_entry())
