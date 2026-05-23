"""Load SuppressionManager from YAML configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from driftcheck.suppression import SuppressionError, SuppressionManager, SuppressionRule

_DEFAULT_CONFIG = Path(__file__).parent / "suppression_config.yaml"


def _parse_rules(raw: List[Dict[str, Any]]) -> List[SuppressionRule]:
    rules: List[SuppressionRule] = []
    for item in raw:
        if "service" not in item:
            raise SuppressionError("Each suppression rule must have a 'service' key.")
        rules.append(
            SuppressionRule(
                service=item["service"],
                fields=item.get("fields", []),
                reason=item.get("reason"),
            )
        )
    return rules


def load_suppression_manager(
    config_path: Path = _DEFAULT_CONFIG,
) -> SuppressionManager:
    """Return a :class:`SuppressionManager` configured from *config_path*."""
    if not config_path.exists():
        return SuppressionManager()
    with config_path.open() as fh:
        data = yaml.safe_load(fh) or {}
    raw_rules = data.get("suppression", {}).get("rules", [])
    return SuppressionManager(rules=_parse_rules(raw_rules))
