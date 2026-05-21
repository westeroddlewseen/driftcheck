"""Compares live service configuration against the expected state from git."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DriftResult:
    """Holds the outcome of a single drift comparison."""

    path: str
    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    changed: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @property
    def has_drift(self) -> bool:
        return bool(self.added or self.removed or self.changed)


class DriftDetector:
    """Detects drift between an expected (git) config and a live config."""

    def compare(
        self,
        expected: dict[str, Any],
        live: dict[str, Any],
        path: str = "<config>",
    ) -> DriftResult:
        """Compare *expected* against *live* and return a :class:`DriftResult`.

        Only top-level keys are compared (shallow diff). Nested structures are
        treated as opaque values.

        Args:
            expected: Configuration parsed from git.
            live:     Configuration retrieved from the running service.
            path:     Logical identifier used in the result (e.g. file path).

        Returns:
            A :class:`DriftResult` describing any differences found.
        """
        result = DriftResult(path=path)

        expected_keys = set(expected)
        live_keys = set(live)

        result.removed = {k: expected[k] for k in expected_keys - live_keys}
        result.added = {k: live[k] for k in live_keys - expected_keys}

        for key in expected_keys & live_keys:
            if expected[key] != live[key]:
                result.changed[key] = (expected[key], live[key])

        return result
