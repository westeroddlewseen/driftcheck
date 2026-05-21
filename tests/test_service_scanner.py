"""Tests for ServiceScanner."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.service_scanner import ServiceConfig, ServiceScanner, ServiceScannerError


def _make_proc(stdout: str = "", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    proc.stderr = ""
    return proc


@patch("driftcheck.service_scanner.subprocess.run")
def test_scan_returns_service_config(mock_run: MagicMock) -> None:
    mock_run.side_effect = [
        _make_proc("nginx:1.25"),   # image
        _make_proc("PORT=8080\nDEBUG=true"),  # env vars
        _make_proc("3"),            # replicas
    ]
    scanner = ServiceScanner(namespace="prod")
    cfg = scanner.scan("my-service")

    assert isinstance(cfg, ServiceConfig)
    assert cfg.name == "my-service"
    assert cfg.image == "nginx:1.25"
    assert cfg.replicas == 3
    assert cfg.env_vars == {"PORT": "8080", "DEBUG": "true"}


@patch("driftcheck.service_scanner.subprocess.run")
def test_scan_raises_on_kubectl_failure(mock_run: MagicMock) -> None:
    err = subprocess.CalledProcessError(1, "kubectl")
    err.stderr = "deployment not found"
    mock_run.side_effect = err

    scanner = ServiceScanner()
    with pytest.raises(ServiceScannerError, match="my-service"):
        scanner.scan("my-service")


@patch("driftcheck.service_scanner.subprocess.run")
def test_scan_empty_image_is_none(mock_run: MagicMock) -> None:
    mock_run.side_effect = [
        _make_proc(""),
        _make_proc(""),
        _make_proc("1"),
    ]
    scanner = ServiceScanner()
    cfg = scanner.scan("svc")
    assert cfg.image is None


@patch("driftcheck.service_scanner.subprocess.run")
def test_get_replicas_defaults_to_one_on_error(mock_run: MagicMock) -> None:
    mock_run.side_effect = [
        _make_proc("nginx:latest"),
        _make_proc(""),
        subprocess.CalledProcessError(1, "kubectl"),
    ]
    scanner = ServiceScanner()
    cfg = scanner.scan("svc")
    assert cfg.replicas == 1


@patch("driftcheck.service_scanner.subprocess.run")
def test_env_vars_list_format_ignored_gracefully(mock_run: MagicMock) -> None:
    # If kubectl returns malformed env output, we get empty dict
    mock_run.side_effect = [
        _make_proc("app:v2"),
        _make_proc("NOEQUALSIGN"),
        _make_proc("2"),
    ]
    scanner = ServiceScanner()
    cfg = scanner.scan("svc")
    assert cfg.env_vars == {}
