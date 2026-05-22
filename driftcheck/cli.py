"""Command-line interface for driftcheck."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from driftcheck.pipeline import Pipeline, PipelineConfig, PipelineError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="driftcheck",
        description="Detect configuration drift between deployed services and git.",
    )
    parser.add_argument(
        "--repo",
        required=True,
        metavar="PATH",
        help="Path to the local git repository.",
    )
    parser.add_argument(
        "--config",
        dest="configs",
        required=True,
        action="append",
        metavar="FILE",
        help="Repo-relative path to a service config file (repeatable).",
    )
    parser.add_argument(
        "--namespace",
        default="default",
        help="Kubernetes namespace (default: default).",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Kubernetes context to use.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = PipelineConfig(
        repo_path=args.repo,
        config_paths=args.configs,
        namespace=args.namespace,
        context=args.context,
        output_format=args.output_format,
    )

    pipeline = Pipeline(cfg)
    exit_code = 0

    try:
        results = pipeline.run()
    except PipelineError as exc:
        print(f"[driftcheck] ERROR: {exc}", file=sys.stderr)
        return 2

    for result in results:
        print(result.report)
        if result.drift_result.has_drift:
            exit_code = 1

    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
