"""Scans running services and retrieves their live configuration."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ServiceScannerError(Exception):
    """Raised when service scanning fails."""


@dataclass
class ServiceConfig:
    """Holds the live configuration snapshot of a single service."""

    name: str
    env_vars: Dict[str, str] = field(default_factory=dict)
    image: Optional[str] = None
    replicas: int = 1


class ServiceScanner:
    """Retrieves live configuration for deployed services."""

    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace

    def scan(self, service_name: str) -> ServiceConfig:
        """Scan a running service and return its configuration.

        Args:
            service_name: The name of the service to inspect.

        Returns:
            A ServiceConfig populated with live data.

        Raises:
            ServiceScannerError: If the service cannot be found or scanned.
        """
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", service_name,
                 "-n", self.namespace, "-o", "jsonpath={.spec.template.spec.containers[0].image}"],
                capture_output=True,
                text=True,
                check=True,
            )
            image = result.stdout.strip() or None
        except subprocess.CalledProcessError as exc:
            raise ServiceScannerError(
                f"Failed to scan service '{service_name}': {exc.stderr.strip()}"
            ) from exc

        env_vars = self._get_env_vars(service_name)
        replicas = self._get_replicas(service_name)
        return ServiceConfig(name=service_name, env_vars=env_vars, image=image, replicas=replicas)

    def _get_env_vars(self, service_name: str) -> Dict[str, str]:
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", service_name,
                 "-n", self.namespace,
                 "-o", "jsonpath={range .spec.template.spec.containers[0].env[*]}{.name}={.value}\n{end}"],
                capture_output=True, text=True, check=True,
            )
            env: Dict[str, str] = {}
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
            return env
        except subprocess.CalledProcessError:
            return {}

    def _get_replicas(self, service_name: str) -> int:
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", service_name,
                 "-n", self.namespace,
                 "-o", "jsonpath={.spec.replicas}"],
                capture_output=True, text=True, check=True,
            )
            return int(result.stdout.strip() or "1")
        except (subprocess.CalledProcessError, ValueError):
            return 1
