"""Tests for driftcheck.remediation."""
from __future__ import annotations

import pytest

from driftcheck.drift_detector import DriftResult
from driftcheck.remediation import (
    RemediationAction,
    RemediationAdvisor,
    RemediationReport,
)
from driftcheck.snapshot import Snapshot


def _snap(service: str = "svc", image: str = "img:1", replicas: int = 1, env: dict | None = None) -> Snapshot:
    return Snapshot(service=service, image=image, replicas=replicas, env=env or {})


def _result(drifted: list[str] | None = None) -> DriftResult:
    has = bool(drifted)
    return DriftResult(has_drift=has, drifted_fields=drifted or [])


# ---------------------------------------------------------------------------
# RemediationAction
# ---------------------------------------------------------------------------

def test_action_image_returns_kubectl_set_image():
    action = RemediationAction("api", "image", "img:1", "img:2")
    cmd = action.as_kubectl_patch()
    assert "kubectl set image" in cmd
    assert "api" in cmd
    assert "img:2" in cmd


def test_action_replicas_returns_kubectl_scale():
    action = RemediationAction("api", "replicas", 1, 3)
    cmd = action.as_kubectl_patch()
    assert "kubectl scale" in cmd
    assert "--replicas=3" in cmd


def test_action_unknown_field_returns_comment():
    action = RemediationAction("api", "labels", "a", "b")
    cmd = action.as_kubectl_patch()
    assert cmd.startswith("#")


def test_action_str_delegates_to_as_kubectl_patch():
    action = RemediationAction("api", "image", "img:1", "img:2")
    assert str(action) == action.as_kubectl_patch()


# ---------------------------------------------------------------------------
# RemediationReport
# ---------------------------------------------------------------------------

def test_report_is_empty_when_no_actions():
    assert RemediationReport().is_empty()


def test_report_as_text_no_actions():
    assert "No remediation" in RemediationReport().as_text()


def test_report_as_text_with_actions():
    action = RemediationAction("svc", "image", "old", "new")
    report = RemediationReport(actions=[action])
    text = report.as_text()
    assert "Suggested" in text
    assert "kubectl" in text


# ---------------------------------------------------------------------------
# RemediationAdvisor
# ---------------------------------------------------------------------------

def test_advise_no_drift_returns_empty_report():
    advisor = RemediationAdvisor()
    live = _snap(image="img:1")
    expected = _snap(image="img:1")
    report = advisor.advise(_result(), live, expected)
    assert report.is_empty()


def test_advise_image_drift_creates_action():
    advisor = RemediationAdvisor()
    live = _snap(image="img:1")
    expected = _snap(image="img:2")
    report = advisor.advise(_result(["image"]), live, expected)
    assert len(report.actions) == 1
    assert report.actions[0].field == "image"
    assert report.actions[0].expected_value == "img:2"


def test_advise_replicas_drift_creates_action():
    advisor = RemediationAdvisor()
    live = _snap(replicas=1)
    expected = _snap(replicas=5)
    report = advisor.advise(_result(["replicas"]), live, expected)
    assert len(report.actions) == 1
    assert report.actions[0].field == "replicas"


def test_advise_untracked_field_is_skipped():
    advisor = RemediationAdvisor()
    live = _snap()
    expected = _snap()
    report = advisor.advise(_result(["labels"]), live, expected)
    assert report.is_empty()


def test_advise_multiple_drifted_fields():
    advisor = RemediationAdvisor()
    live = _snap(image="img:1", replicas=1)
    expected = _snap(image="img:2", replicas=3)
    report = advisor.advise(_result(["image", "replicas"]), live, expected)
    assert len(report.actions) == 2
