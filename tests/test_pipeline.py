"""Tests for driftcheck.pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftcheck.config_loader import ConfigLoaderError
from driftcheck.drift_detector import DriftResult
from driftcheck.git_reader import GitReaderError
from driftcheck.pipeline import Pipeline, PipelineConfig, PipelineError, PipelineResult
from driftcheck.service_scanner import ServiceConfig, ServiceScannerError
from driftcheck.snapshot import Snapshot


_EXPECTED_YAML = "name: my-svc\nimage: nginx:1.25\nreplicas: 2\nenv:\n  ENV: prod\n"


def _make_pipeline(output_format: str = "text") -> Pipeline:
    cfg = PipelineConfig(
        repo_path="/fake/repo",
        config_paths=["services/my-svc.yaml"],
        output_format=output_format,
    )
    return Pipeline(cfg)


@patch("driftcheck.pipeline.ServiceScanner")
@patch("driftcheck.pipeline.GitReader")
def test_run_returns_pipeline_results(mock_git_cls, mock_scanner_cls):
    mock_git = mock_git_cls.return_value
    mock_git.read_file.return_value = _EXPECTED_YAML

    live_cfg = ServiceConfig(
        name="my-svc", image="nginx:1.25", replicas=2, env={"ENV": "prod"}
    )
    mock_scanner = mock_scanner_cls.return_value
    mock_scanner.scan.return_value = live_cfg

    pipeline = _make_pipeline()
    results = pipeline.run()

    assert len(results) == 1
    assert isinstance(results[0], PipelineResult)
    assert results[0].service == "my-svc"
    assert isinstance(results[0].drift_result, DriftResult)
    assert isinstance(results[0].report, str)


@patch("driftcheck.pipeline.ServiceScanner")
@patch("driftcheck.pipeline.GitReader")
def test_run_no_drift_report_contains_ok(mock_git_cls, mock_scanner_cls):
    mock_git_cls.return_value.read_file.return_value = _EXPECTED_YAML
    mock_scanner_cls.return_value.scan.return_value = ServiceConfig(
        name="my-svc", image="nginx:1.25", replicas=2, env={"ENV": "prod"}
    )
    pipeline = _make_pipeline()
    results = pipeline.run()
    assert "OK" in results[0].report or "no drift" in results[0].report.lower()


@patch("driftcheck.pipeline.GitReader")
def test_run_git_error_raises_pipeline_error(mock_git_cls):
    mock_git_cls.return_value.read_file.side_effect = GitReaderError("not found")
    pipeline = _make_pipeline()
    with pytest.raises(PipelineError, match="Git read failed"):
        pipeline.run()


@patch("driftcheck.pipeline.ServiceScanner")
@patch("driftcheck.pipeline.GitReader")
def test_run_scanner_error_raises_pipeline_error(mock_git_cls, mock_scanner_cls):
    mock_git_cls.return_value.read_file.return_value = _EXPECTED_YAML
    mock_scanner_cls.return_value.scan.side_effect = ServiceScannerError("kubectl fail")
    pipeline = _make_pipeline()
    with pytest.raises(PipelineError, match="Scanner failed"):
        pipeline.run()


@patch("driftcheck.pipeline.ServiceScanner")
@patch("driftcheck.pipeline.GitReader")
def test_run_drift_detected(mock_git_cls, mock_scanner_cls):
    mock_git_cls.return_value.read_file.return_value = _EXPECTED_YAML
    mock_scanner_cls.return_value.scan.return_value = ServiceConfig(
        name="my-svc", image="nginx:1.99", replicas=3, env={"ENV": "staging"}
    )
    pipeline = _make_pipeline()
    results = pipeline.run()
    assert results[0].drift_result.has_drift
