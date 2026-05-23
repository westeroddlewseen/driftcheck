"""Remediation advisor: suggests corrective actions for detected drift."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from driftcheck.drift_detector import DriftResult
from driftcheck.snapshot import Snapshot


class RemediationError(Exception):
    """Raised when remediation advice cannot be generated."""


@dataclass
class RemediationAction:
    service: str
    field: str
    current_value: object
    expected_value: object

    def as_kubectl_patch(self) -> str:
        """Return a best-effort kubectl patch command for the drift."""
        if self.field == "image":
            return (
                f"kubectl set image deployment/{self.service} "
                f"{self.service}={self.expected_value}"
            )
        if self.field == "replicas":
            return (
                f"kubectl scale deployment/{self.service} "
                f"--replicas={self.expected_value}"
            )
        return (
            f"# Manual fix required for '{self.field}' on '{self.service}': "
            f"expected={self.expected_value!r}, got={self.current_value!r}"
        )

    def __str__(self) -> str:
        return self.as_kubectl_patch()


@dataclass
class RemediationReport:
    actions: List[RemediationAction] = field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.actions) == 0

    def as_text(self) -> str:
        if self.is_empty():
            return "No remediation actions required."
        lines = ["Suggested remediation actions:"]
        for action in self.actions:
            lines.append(f"  {action}")
        return "\n".join(lines)


class RemediationAdvisor:
    """Generates remediation actions from drift results."""

    TRACKED_FIELDS = ("image", "replicas", "env")

    def advise(self, result: DriftResult, live: Snapshot, expected: Snapshot) -> RemediationReport:
        if not result.has_drift:
            return RemediationReport()

        actions: List[RemediationAction] = []
        for field_name in result.drifted_fields:
            if field_name not in self.TRACKED_FIELDS:
                continue
            current = getattr(live, field_name, None)
            desired = getattr(expected, field_name, None)
            actions.append(
                RemediationAction(
                    service=live.service,
                    field=field_name,
                    current_value=current,
                    expected_value=desired,
                )
            )
        return RemediationReport(actions=actions)
