"""Loads an AlertPolicy from a YAML file with sensible defaults."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError as _err:  # pragma: no cover
    raise ImportError("PyYAML is required: pip install pyyaml") from _err

from driftcheck.alert_policy import AlertPolicy, AlertPolicyError

_DEFAULT_POLICY_PATH = Path(__file__).parent / "alert_policy.yaml"


def load_alert_policy(path: Optional[str] = None) -> AlertPolicy:
    """Load an :class:`AlertPolicy` from *path*.

    If *path* is ``None`` the bundled ``alert_policy.yaml`` is used.

    Raises:
        AlertPolicyError: if the file cannot be parsed or contains invalid values.
    """
    resolved = Path(path) if path else _DEFAULT_POLICY_PATH
    try:
        raw = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise AlertPolicyError(f"Cannot read policy file '{resolved}': {exc}") from exc

    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise AlertPolicyError(f"YAML parse error in '{resolved}': {exc}") from exc

    if not isinstance(data, dict):
        raise AlertPolicyError(
            f"Expected a YAML mapping in '{resolved}', got {type(data).__name__}"
        )

    return AlertPolicy.from_dict(data)
