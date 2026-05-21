"""Converts live ServiceConfig and expected config dicts into comparable snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from driftcheck.service_scanner import ServiceConfig


@dataclass
class Snapshot:
    """Normalised, comparable view of a service configuration."""

    image: Optional[str] = None
    replicas: int = 1
    env_vars: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "image": self.image,
            "replicas": self.replicas,
            "env_vars": dict(self.env_vars),
        }


def snapshot_from_live(service_config: ServiceConfig) -> Snapshot:
    """Build a Snapshot from a live ServiceConfig.

    Args:
        service_config: The live configuration returned by ServiceScanner.

    Returns:
        A normalised Snapshot instance.
    """
    return Snapshot(
        image=service_config.image,
        replicas=service_config.replicas,
        env_vars=dict(service_config.env_vars),
    )


def snapshot_from_expected(config: Dict[str, Any]) -> Snapshot:
    """Build a Snapshot from an expected configuration dictionary.

    The dictionary typically originates from a YAML/JSON file loaded via
    ConfigLoader.  Only recognised keys are mapped; unknown keys are ignored.

    Args:
        config: Raw expected-config dictionary.

    Returns:
        A normalised Snapshot instance.
    """
    env_raw = config.get("env", {})
    if isinstance(env_raw, list):
        # Support [{name: ..., value: ...}] list format
        env_vars: Dict[str, str] = {
            item["name"]: str(item.get("value", ""))
            for item in env_raw
            if "name" in item
        }
    elif isinstance(env_raw, dict):
        env_vars = {k: str(v) for k, v in env_raw.items()}
    else:
        env_vars = {}

    return Snapshot(
        image=config.get("image"),
        replicas=int(config.get("replicas", 1)),
        env_vars=env_vars,
    )
