"""High-level pipeline that wires together scanning, snapshotting, and drift detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from driftcheck.config_loader import ConfigLoader, ConfigLoaderError
from driftcheck.drift_detector import DriftDetector, DriftResult
from driftcheck.git_reader import GitReader, GitReaderError
from driftcheck.reporter import Reporter, ReporterError
from driftcheck.service_scanner import ServiceScanner, ServiceScannerError
from driftcheck.snapshot import snapshot_from_expected, snapshot_from_live


class PipelineError(Exception):
    """Raised when the pipeline cannot complete a run."""


@dataclass
class PipelineResult:
    service: str
    drift_result: DriftResult
    report: str


@dataclass
class PipelineConfig:
    repo_path: str
    config_paths: List[str]  # paths inside the repo, one per service
    namespace: str = "default"
    output_format: str = "text"
    context: str = ""


class Pipeline:
    """Orchestrates a full drift-check run for a list of services."""

    def __init__(self, cfg: PipelineConfig) -> None:
        self._cfg = cfg
        self._git = GitReader(cfg.repo_path)
        self._scanner = ServiceScanner(namespace=cfg.namespace, context=cfg.context)
        self._detector = DriftDetector()
        self._reporter = Reporter(output_format=cfg.output_format)

    # ------------------------------------------------------------------
    def run(self) -> List[PipelineResult]:
        results: List[PipelineResult] = []
        for config_path in self._cfg.config_paths:
            result = self._run_one(config_path)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    def _run_one(self, config_path: str) -> PipelineResult:
        try:
            raw = self._git.read_file(config_path)
        except GitReaderError as exc:
            raise PipelineError(f"Git read failed for {config_path!r}: {exc}") from exc

        try:
            loader = ConfigLoader(content=raw, path=config_path)
            expected_dict = loader.load()
        except ConfigLoaderError as exc:
            raise PipelineError(f"Config load failed for {config_path!r}: {exc}") from exc

        service_name: str = expected_dict.get("name", config_path)

        try:
            live_cfg = self._scanner.scan(service_name)
        except ServiceScannerError as exc:
            raise PipelineError(f"Scanner failed for service {service_name!r}: {exc}") from exc

        live_snap = snapshot_from_live(live_cfg)
        expected_snap = snapshot_from_expected(expected_dict)

        drift = self._detector.compare(live_snap, expected_snap)

        try:
            report = self._reporter.render(drift)
        except ReporterError as exc:
            raise PipelineError(f"Reporter failed: {exc}") from exc

        return PipelineResult(service=service_name, drift_result=drift, report=report)
