"""Tests for driftcheck.baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from driftcheck.baseline import BaselineDiff, BaselineError, BaselineManager
from driftcheck.snapshot import Snapshot


def _snap(**kwargs) -> Snapshot:
    defaults = dict(
        service="svc-a",
        image="nginx:1.25",
        replicas=2,
        env={"LOG_LEVEL": "info"},
    )
    defaults.update(kwargs)
    return Snapshot(**defaults)


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    snap = _snap()
    mgr.save(snap)
    loaded = mgr.load("svc-a")
    assert loaded is not None
    assert loaded.image == snap.image
    assert loaded.replicas == snap.replicas
    assert loaded.env == snap.env


def test_load_returns_none_when_missing(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    assert mgr.load("nonexistent") is None


def test_save_writes_saved_at_timestamp(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    before = time.time()
    mgr.save(_snap())
    after = time.time()
    raw = json.loads((tmp_path / "svc-a.json").read_text())
    assert before <= raw["_saved_at"] <= after


def test_load_raises_on_corrupt_file(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    (tmp_path / "svc-a.json").write_text("not-json")
    with pytest.raises(BaselineError):
        mgr.load("svc-a")


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

def test_diff_no_changes_returns_empty(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    snap = _snap()
    mgr.save(snap)
    assert mgr.diff(snap) == []


def test_diff_detects_image_change(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    mgr.save(_snap(image="nginx:1.25"))
    diffs = mgr.diff(_snap(image="nginx:1.26"))
    assert len(diffs) == 1
    assert diffs[0].field == "image"
    assert diffs[0].baseline_value == "nginx:1.25"
    assert diffs[0].current_value == "nginx:1.26"


def test_diff_detects_replicas_change(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    mgr.save(_snap(replicas=2))
    diffs = mgr.diff(_snap(replicas=5))
    assert any(d.field == "replicas" for d in diffs)


def test_diff_returns_empty_when_no_baseline(tmp_path):
    mgr = BaselineManager(baseline_dir=str(tmp_path))
    assert mgr.diff(_snap()) == []


def test_baseline_diff_str():
    bd = BaselineDiff("svc-a", "image", "nginx:1.25", "nginx:1.26")
    text = str(bd)
    assert "svc-a" in text
    assert "image" in text
    assert "nginx:1.25" in text
    assert "nginx:1.26" in text
