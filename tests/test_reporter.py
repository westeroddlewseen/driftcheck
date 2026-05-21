"""Tests for driftcheck.reporter."""

import json

import pytest

from driftcheck.drift_detector import DriftResult
from driftcheck.reporter import Reporter, ReporterError


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _result(key: str, expected, actual) -> DriftResult:
    return DriftResult(key=key, expected=expected, actual=actual)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

def test_default_format_is_text():
    r = Reporter()
    assert r.fmt == "text"


def test_unsupported_format_raises():
    with pytest.raises(ReporterError, match="Unsupported format 'xml'"):
        Reporter(fmt="xml")


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

def test_text_no_drift_message():
    reporter = Reporter(fmt="text")
    output = reporter.render([])
    assert output == "No drift detected."


def test_text_ok_result():
    reporter = Reporter(fmt="text")
    output = reporter.render([_result("app.version", "1.2", "1.2")])
    assert "[OK] app.version" in output
    assert "expected" not in output


def test_text_drift_result_shows_values():
    reporter = Reporter(fmt="text")
    output = reporter.render([_result("app.version", "1.2", "1.3")])
    assert "[DRIFT] app.version" in output
    assert "'1.2'" in output
    assert "'1.3'" in output


def test_text_multiple_results():
    reporter = Reporter(fmt="text")
    results = [
        _result("a", 1, 1),
        _result("b", 2, 9),
    ]
    output = reporter.render(results)
    assert "[OK] a" in output
    assert "[DRIFT] b" in output


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------

def test_json_empty_list():
    reporter = Reporter(fmt="json")
    data = json.loads(reporter.render([]))
    assert data == []


def test_json_structure():
    reporter = Reporter(fmt="json")
    results = [_result("svc.replicas", 3, 2)]
    data = json.loads(reporter.render(results))
    assert len(data) == 1
    entry = data[0]
    assert entry["key"] == "svc.replicas"
    assert entry["has_drift"] is True
    assert entry["expected"] == 3
    assert entry["actual"] == 2


def test_json_no_drift_flag():
    reporter = Reporter(fmt="json")
    data = json.loads(reporter.render([_result("x", "v1", "v1")]))
    assert data[0]["has_drift"] is False
