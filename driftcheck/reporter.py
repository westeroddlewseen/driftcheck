"""Formats and outputs drift detection results."""

from __future__ import annotations

import json
from typing import List

from driftcheck.drift_detector import DriftResult


class ReporterError(Exception):
    """Raised when an unsupported output format is requested."""


class Reporter:
    """Renders a list of DriftResult objects in a chosen format."""

    SUPPORTED_FORMATS = ("text", "json")

    def __init__(self, fmt: str = "text") -> None:
        if fmt not in self.SUPPORTED_FORMATS:
            raise ReporterError(
                f"Unsupported format '{fmt}'. "
                f"Choose one of: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        self.fmt = fmt

    def render(self, results: List[DriftResult]) -> str:
        """Return a formatted string representation of *results*."""
        if self.fmt == "json":
            return self._render_json(results)
        return self._render_text(results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_text(self, results: List[DriftResult]) -> str:
        if not results:
            return "No drift detected."

        lines: List[str] = []
        for r in results:
            status = "DRIFT" if r.has_drift else "OK"
            lines.append(f"[{status}] {r.key}")
            if r.has_drift:
                lines.append(f"  expected : {r.expected!r}")
                lines.append(f"  actual   : {r.actual!r}")
        return "\n".join(lines)

    def _render_json(self, results: List[DriftResult]) -> str:
        payload = [
            {
                "key": r.key,
                "has_drift": r.has_drift,
                "expected": r.expected,
                "actual": r.actual,
            }
            for r in results
        ]
        return json.dumps(payload, indent=2)
