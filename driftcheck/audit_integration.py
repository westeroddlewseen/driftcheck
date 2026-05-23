"""Glue that connects the Pipeline to the AuditLog."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from driftcheck.audit_log import AuditEntry, AuditLog, AuditLogError
from driftcheck.pipeline import PipelineResult

logger = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = Path("/var/log/driftcheck/audit.jsonl")
_WARN_THRESHOLD = 10_000


def _resolve_path(raw: str) -> Path:
    """Expand env-vars and user home in *raw*, return a Path."""
    return Path(os.path.expandvars(os.path.expanduser(raw)))


def record_pipeline_results(
    results: List[PipelineResult],
    *,
    log_path: Optional[str] = None,
    log_clean_runs: bool = True,
    run_id: Optional[str] = None,
    warn_above_entries: int = _WARN_THRESHOLD,
) -> None:
    """Write *results* to the audit log.

    Parameters
    ----------
    results:
        Output of ``Pipeline.run()``.
    log_path:
        Override the default log file location.
    log_clean_runs:
        When *False*, only services with drift are logged.
    run_id:
        Optional correlation ID attached to every entry (e.g. a CI run ID).
    warn_above_entries:
        Emit a warning when the log grows beyond this many lines.
    """
    path = _resolve_path(log_path) if log_path else _DEFAULT_LOG_PATH
    audit = AuditLog(path)

    for pr in results:
        if not log_clean_runs and not pr.drift_result.has_drift:
            continue
        entry = AuditEntry.now(
            service=pr.service,
            has_drift=pr.drift_result.has_drift,
            drifted_keys=list(pr.drift_result.diffs.keys()),
            run_id=run_id,
        )
        try:
            audit.append(entry)
        except AuditLogError:
            logger.exception("Failed to write audit entry for service %s", pr.service)

    if warn_above_entries > 0:
        try:
            total = len(audit.read_all())
            if total > warn_above_entries:
                logger.warning(
                    "Audit log at %s has %d entries (threshold %d). "
                    "Consider rotating.",
                    path,
                    total,
                    warn_above_entries,
                )
        except AuditLogError:
            logger.debug("Could not read audit log for size check.", exc_info=True)
