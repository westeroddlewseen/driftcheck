"""Formats drift diffs into human-readable or structured output."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from driftcheck.drift_detector import DriftResult


class DiffFormatterError(Exception):
    """Raised when formatting fails."""


@dataclass
class FieldDiff:
    field: str
    expected: Any
    actual: Any

    def __str__(self) -> str:
        return f"  {self.field}: expected={self.expected!r}, actual={self.actual!r}"


@dataclass
class FormattedDiff:
    service: str
    drifted: bool
    fields: List[FieldDiff]

    def as_text(self) -> str:
        if not self.drifted:
            return f"[OK] {self.service}: no drift detected"
        lines = [f"[DRIFT] {self.service}:"]
        for fd in self.fields:
            lines.append(str(fd))
        return "\n".join(lines)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "drifted": self.drifted,
            "fields": [
                {"field": fd.field, "expected": fd.expected, "actual": fd.actual}
                for fd in self.fields
            ],
        }


class DiffFormatter:
    """Converts DriftResult objects into FormattedDiff instances."""

    SUPPORTED_FORMATS = ("text", "dict")

    def __init__(self, fmt: str = "text") -> None:
        if fmt not in self.SUPPORTED_FORMATS:
            raise DiffFormatterError(
                f"Unsupported format {fmt!r}. Choose from {self.SUPPORTED_FORMATS}."
            )
        self.fmt = fmt

    def format(self, result: DriftResult) -> FormattedDiff:
        """Build a FormattedDiff from a DriftResult."""
        if not isinstance(result, DriftResult):
            raise DiffFormatterError("Expected a DriftResult instance.")

        field_diffs: List[FieldDiff] = []
        for key, (expected, actual) in (result.differences or {}).items():
            field_diffs.append(FieldDiff(field=key, expected=expected, actual=actual))

        return FormattedDiff(
            service=result.service_name,
            drifted=result.has_drift,
            fields=field_diffs,
        )

    def format_many(self, results: List[DriftResult]) -> List[FormattedDiff]:
        """Format a list of DriftResult objects."""
        return [self.format(r) for r in results]
