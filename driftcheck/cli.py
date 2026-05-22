"""Command-line interface for driftcheck."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from driftcheck.pipeline import Pipeline, PipelineConfig, PipelineError
from driftcheck.reporter import Reporter, ReporterError
from driftcheck.notifier import Notifier, NotifierConfig, NotifierError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftcheck",
        description="Detect configuration drift between live services and git.",
    )
    parser.add_argument("--repo", required=True, help="Path to the git repository.")
    parser.add_argument(
        "--config", required=True, help="Path to the service config file (YAML/JSON)."
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Kubernetes namespace to scan (default: default).",
    )
    parser.add_argument(
        "--webhook-url",
        default="",
        help="Slack-compatible webhook URL for drift notifications.",
    )
    parser.add_argument(
        "--webhook-channel",
        default="#alerts",
        help="Channel for webhook notifications (default: #alerts).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:  # noqa: D401
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = PipelineConfig(
        repo_path=args.repo,
        config_path=args.config,
        namespace=args.namespace,
    )

    try:
        pipeline = Pipeline(cfg)
        results = pipeline.run()
    except PipelineError as exc:
        print(f"[driftcheck] pipeline error: {exc}", file=sys.stderr)
        return 2

    reporter = Reporter(fmt=args.format)
    try:
        print(reporter.render(results))
    except ReporterError as exc:
        print(f"[driftcheck] reporter error: {exc}", file=sys.stderr)
        return 2

    if args.webhook_url:
        notifier = Notifier(
            NotifierConfig(
                webhook_url=args.webhook_url,
                channel=args.webhook_channel,
            )
        )
        try:
            notifier.notify(
                [pr.drift for pr in results],
                repo=args.repo,
            )
        except NotifierError as exc:
            print(f"[driftcheck] notification error: {exc}", file=sys.stderr)
            # non-fatal — still return based on drift

    has_any_drift = any(pr.drift.has_drift for pr in results)
    return 1 if has_any_drift else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
