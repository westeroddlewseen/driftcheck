"""Notifier module — sends drift alerts to configurable channels."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Optional

from driftcheck.drift_detector import DriftResult


class NotifierError(Exception):
    """Raised when a notification cannot be delivered."""


@dataclass
class NotifierConfig:
    webhook_url: str
    channel: str = "#alerts"
    username: str = "driftcheck"
    timeout: int = 10


class Notifier:
    """Sends drift-detection results to a Slack-compatible webhook."""

    def __init__(self, config: NotifierConfig) -> None:
        if not config.webhook_url:
            raise NotifierError("webhook_url must not be empty")
        self._config = config

    # ------------------------------------------------------------------
    def notify(self, results: List[DriftResult], repo: str) -> None:
        """Post a summary message for *results* to the configured webhook."""
        drifted = [r for r in results if r.has_drift]
        if not drifted:
            text = f":white_check_mark: *driftcheck* — no drift detected in `{repo}`."
        else:
            lines = [f":rotating_light: *driftcheck* — drift detected in `{repo}`:"]
            for r in drifted:
                lines.append(f"  • `{r.service}`: {', '.join(r.diffs)}")
            text = "\n".join(lines)

        self._post(text)

    # ------------------------------------------------------------------
    def _post(self, text: str) -> None:
        payload = json.dumps(
            {
                "channel": self._config.channel,
                "username": self._config.username,
                "text": text,
            }
        ).encode()

        req = urllib.request.Request(
            self._config.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout):
                pass
        except urllib.error.URLError as exc:
            raise NotifierError(f"Failed to deliver notification: {exc}") from exc
