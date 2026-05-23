"""Alert policy: decides whether a drift event should trigger a notification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


class AlertPolicyError(Exception):
    """Raised when alert policy configuration is invalid."""


@dataclass
class AlertPolicy:
    """Defines rules that control when alerts are sent.

    Attributes:
        min_drifted_services: minimum number of drifted services required to fire.
        ignored_services: service names that should never trigger alerts.
        require_image_drift: only alert when image tag has changed.
    """

    min_drifted_services: int = 1
    ignored_services: List[str] = field(default_factory=list)
    require_image_drift: bool = False

    def __post_init__(self) -> None:
        if self.min_drifted_services < 1:
            raise AlertPolicyError(
                "min_drifted_services must be >= 1, "
                f"got {self.min_drifted_services}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "AlertPolicy":
        """Build an AlertPolicy from a plain dictionary (e.g. loaded from YAML)."""
        try:
            return cls(
                min_drifted_services=int(data.get("min_drifted_services", 1)),
                ignored_services=list(data.get("ignored_services", [])),
                require_image_drift=bool(data.get("require_image_drift", False)),
            )
        except (TypeError, ValueError) as exc:
            raise AlertPolicyError(f"Invalid alert policy data: {exc}") from exc

    def should_alert(self, drifted_services: List[str], image_drifted: bool = False) -> bool:
        """Return True when the policy conditions are satisfied.

        Args:
            drifted_services: names of services detected as drifted.
            image_drifted: whether at least one service has an image drift.
        """
        filtered = [
            svc for svc in drifted_services if svc not in self.ignored_services
        ]
        if len(filtered) < self.min_drifted_services:
            return False
        if self.require_image_drift and not image_drifted:
            return False
        return True
