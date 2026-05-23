"""Helpers that integrate SuppressionManager with the drift pipeline."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from driftcheck.drift_detector import DriftResult
from driftcheck.suppression import SuppressionManager, SuppressionReport
from driftcheck.suppression_loader import load_suppression_manager


def apply_suppressions(
    results: List[DriftResult],
    manager: Optional[SuppressionManager] = None,
    config_path: Optional[Path] = None,
) -> List[DriftResult]:
    """Return a new list of :class:`DriftResult` with suppressed fields removed.

    If a service's drifted fields are *all* suppressed the result is replaced
    with a non-drifting entry so downstream reporters see it as clean.

    Args:
        results:     Original drift results from the pipeline.
        manager:     Pre-built :class:`SuppressionManager` (takes precedence).
        config_path: Path to a suppression YAML config (used when *manager*
                     is *None*).
    """
    if manager is None:
        manager = load_suppression_manager(
            **(({"config_path": config_path}) if config_path else {})
        )

    filtered: List[DriftResult] = []
    for result in results:
        if not result.has_drift:
            filtered.append(result)
            continue

        report: SuppressionReport = manager.filter_drift_fields(
            result.service_name, result.drifted_fields
        )

        if not report.active:
            # All drifts suppressed — emit a clean result.
            filtered.append(
                DriftResult(
                    service_name=result.service_name,
                    has_drift=False,
                    drifted_fields=[],
                )
            )
        else:
            filtered.append(
                DriftResult(
                    service_name=result.service_name,
                    has_drift=True,
                    drifted_fields=report.active,
                )
            )
    return filtered
