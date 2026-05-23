"""Loads remediation configuration from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from driftcheck.remediation import RemediationAdvisor

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "remediation_config.yaml"


def _load_raw(path: Path) -> Dict[str, Any]:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def load_remediation_advisor(config_path: Path | None = None) -> RemediationAdvisor:
    """Return a RemediationAdvisor configured from *config_path*.

    Falls back to the bundled ``remediation_config.yaml`` when *config_path*
    is not supplied.
    """
    raw = _load_raw(config_path or _DEFAULT_CONFIG_PATH)
    section: Dict[str, Any] = raw.get("remediation", {})

    tracked: List[str] = section.get("tracked_fields", RemediationAdvisor.TRACKED_FIELDS)

    advisor = RemediationAdvisor()
    advisor.TRACKED_FIELDS = tuple(tracked)  # type: ignore[assignment]
    return advisor
