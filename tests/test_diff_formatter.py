"""Tests for driftcheck.diff_formatter."""
import pytest

from driftcheck.drift_detector import DriftResult
from driftcheck.diff_formatter import DiffFormatter, DiffFormatterError, FormattedDiff


def _make_result(
    service: str = "svc-a",
    has_drift: bool = False,
    differences: dict | None = None,
) -> DriftResult:
    return DriftResult(
        service_name=service,
        has_drift=has_drift,
        differences=differences or {},
    )


def test_unsupported_format_raises():
    with pytest.raises(DiffFormatterError, match="Unsupported format"):
        DiffFormatter(fmt="xml")


def test_default_format_is_text():
    fmt = DiffFormatter()
    assert fmt.fmt == "text"


def test_format_no_drift_returns_ok_text():
    fmt = DiffFormatter()
    result = _make_result(service="api", has_drift=False)
    diff = fmt.format(result)
    assert isinstance(diff, FormattedDiff)
    assert not diff.drifted
    assert "OK" in diff.as_text()
    assert "api" in diff.as_text()


def test_format_with_drift_shows_fields():
    fmt = DiffFormatter()
    result = _make_result(
        service="worker",
        has_drift=True,
        differences={"image": ("v1.0", "v2.0"), "replicas": (3, 1)},
    )
    diff = fmt.format(result)
    assert diff.drifted
    text = diff.as_text()
    assert "DRIFT" in text
    assert "image" in text
    assert "v1.0" in text
    assert "v2.0" in text
    assert "replicas" in text


def test_format_as_dict_structure():
    fmt = DiffFormatter(fmt="dict")
    result = _make_result(
        service="db",
        has_drift=True,
        differences={"image": ("img:1", "img:2")},
    )
    diff = fmt.format(result)
    d = diff.as_dict()
    assert d["service"] == "db"
    assert d["drifted"] is True
    assert len(d["fields"]) == 1
    assert d["fields"][0]["field"] == "image"
    assert d["fields"][0]["expected"] == "img:1"
    assert d["fields"][0]["actual"] == "img:2"


def test_format_many_returns_list():
    fmt = DiffFormatter()
    results = [
        _make_result("svc-a", False),
        _make_result("svc-b", True, {"replicas": (2, 1)}),
    ]
    diffs = fmt.format_many(results)
    assert len(diffs) == 2
    assert diffs[0].service == "svc-a"
    assert diffs[1].service == "svc-b"
    assert diffs[1].drifted


def test_format_invalid_input_raises():
    fmt = DiffFormatter()
    with pytest.raises(DiffFormatterError, match="Expected a DriftResult"):
        fmt.format({"service_name": "bad"})


def test_no_drift_empty_fields():
    fmt = DiffFormatter()
    result = _make_result(service="clean", has_drift=False)
    diff = fmt.format(result)
    assert diff.fields == []
