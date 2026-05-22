"""Tests for driftcheck.cli."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftcheck.cli import build_parser, main
from driftcheck.drift_detector import DriftResult
from driftcheck.pipeline import PipelineError, PipelineResult


def _make_result(has_drift: bool = False) -> PipelineResult:
    drift = DriftResult(diffs={}, has_drift=has_drift)
    return PipelineResult(service="svc", drift_result=drift, report="OK" if not has_drift else "DRIFT")


def test_build_parser_requires_repo():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--config", "svc.yaml"])


def test_build_parser_requires_config():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--repo", "/repo"])


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["--repo", "/r", "--config", "a.yaml"])
    assert args.namespace == "default"
    assert args.output_format == "text"
    assert args.context == ""


@patch("driftcheck.cli.Pipeline")
def test_main_returns_zero_on_no_drift(mock_pipeline_cls):
    mock_pipeline_cls.return_value.run.return_value = [_make_result(has_drift=False)]
    code = main(["--repo", "/r", "--config", "svc.yaml"])
    assert code == 0


@patch("driftcheck.cli.Pipeline")
def test_main_returns_one_on_drift(mock_pipeline_cls):
    mock_pipeline_cls.return_value.run.return_value = [_make_result(has_drift=True)]
    code = main(["--repo", "/r", "--config", "svc.yaml"])
    assert code == 1


@patch("driftcheck.cli.Pipeline")
def test_main_returns_two_on_pipeline_error(mock_pipeline_cls):
    mock_pipeline_cls.return_value.run.side_effect = PipelineError("boom")
    code = main(["--repo", "/r", "--config", "svc.yaml"])
    assert code == 2


@patch("driftcheck.cli.Pipeline")
def test_main_multiple_configs_all_ok(mock_pipeline_cls):
    mock_pipeline_cls.return_value.run.return_value = [
        _make_result(has_drift=False),
        _make_result(has_drift=False),
    ]
    code = main(["--repo", "/r", "--config", "a.yaml", "--config", "b.yaml"])
    assert code == 0


@patch("driftcheck.cli.Pipeline")
def test_main_format_json_passed_to_pipeline(mock_pipeline_cls):
    mock_pipeline_cls.return_value.run.return_value = [_make_result()]
    main(["--repo", "/r", "--config", "svc.yaml", "--format", "json"])
    call_cfg = mock_pipeline_cls.call_args[0][0]
    assert call_cfg.output_format == "json"
