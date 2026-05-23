"""Drift suppression rules — allows certain drift findings to be silenced."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional


class SuppressionError(Exception):
    """Raised when suppression configuration is invalid."""


@dataclass
class SuppressionRule:
    """A single suppression rule."""

    service: str  # glob pattern, e.g. "payments-*"
    fields: List[str] = field(default_factory=list)  # empty = suppress all fields
    reason: Optional[str] = None

    def matches(self, service_name: str, drift_field: str) -> bool:
        """Return True if this rule suppresses *drift_field* for *service_name*."""
        if not fnmatch.fnmatch(service_name, self.service):
            return False
        if not self.fields:
            return True
        return drift_field in self.fields


@dataclass
class SuppressionReport:
    """Summary of which drifts were suppressed."""

    suppressed: List[str] = field(default_factory=list)  # "service:field" strings
    active: List[str] = field(default_factory=list)       # drifts that survived

    @property
    def any_suppressed(self) -> bool:
        return bool(self.suppressed)


class SuppressionManager:
    """Applies suppression rules to a set of drift findings."""

    def __init__(self, rules: Optional[List[SuppressionRule]] = None) -> None:
        self.rules: List[SuppressionRule] = rules or []

    def is_suppressed(self, service_name: str, drift_field: str) -> bool:
        """Return True if any rule suppresses this service/field combination."""
        return any(r.matches(service_name, drift_field) for r in self.rules)

    def filter_drift_fields(
        self, service_name: str, drifted_fields: List[str]
    ) -> SuppressionReport:
        """Split *drifted_fields* into suppressed and active lists."""
        report = SuppressionReport()
        for f in drifted_fields:
            key = f"{service_name}:{f}"
            if self.is_suppressed(service_name, f):
                report.suppressed.append(key)
            else:
                report.active.append(key)
        return report
