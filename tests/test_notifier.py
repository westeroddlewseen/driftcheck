"""Tests for driftcheck.notifier."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftcheck.drift_detector import DriftResult
from driftcheck.notifier import Notifier, NotifierConfig, NotifierError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**kwargs) -> NotifierConfig:
    defaults = dict(webhook_url="https://hooks.example.com/abc", channel="#ops")
    defaults.update(kwargs)
    return NotifierConfig(**defaults)


def _result(service: str, diffs: list[str]) -> DriftResult:
    return DriftResult(service=service, has_drift=bool(diffs), diffs=diffs)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_empty_webhook_raises():
    with pytest.raises(NotifierError, match="webhook_url"):
        Notifier(NotifierConfig(webhook_url=""))


# ---------------------------------------------------------------------------
# notify — no drift
# ---------------------------------------------------------------------------

def test_notify_no_drift_posts_ok_message():
    notifier = Notifier(_cfg())
    results = [_result("svc-a", [])]

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        notifier.notify(results, repo="myrepo")

    payload = json.loads(mock_open.call_args[0][0].data.decode())
    assert "no drift" in payload["text"]
    assert "myrepo" in payload["text"]


# ---------------------------------------------------------------------------
# notify — drift present
# ---------------------------------------------------------------------------

def test_notify_drift_posts_service_names():
    notifier = Notifier(_cfg())
    results = [
        _result("svc-a", ["image mismatch"]),
        _result("svc-b", []),
    ]

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        notifier.notify(results, repo="myrepo")

    payload = json.loads(mock_open.call_args[0][0].data.decode())
    assert "svc-a" in payload["text"]
    assert "svc-b" not in payload["text"]
    assert "image mismatch" in payload["text"]


def test_notify_uses_config_channel_and_username():
    notifier = Notifier(_cfg(channel="#infra", username="bot"))

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        notifier.notify([], repo="r")

    payload = json.loads(mock_open.call_args[0][0].data.decode())
    assert payload["channel"] == "#infra"
    assert payload["username"] == "bot"


# ---------------------------------------------------------------------------
# _post — network error
# ---------------------------------------------------------------------------

def test_post_url_error_raises_notifier_error():
    import urllib.error

    notifier = Notifier(_cfg())
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
        with pytest.raises(NotifierError, match="Failed to deliver"):
            notifier.notify([], repo="r")
