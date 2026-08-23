"""CLI entry для /opsx-resolve-conflict typed runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from opsx_conflict.pipeline import run_go, run_preview, result_to_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opsx_conflict")
    parser.add_argument("mode", choices=["PREVIEW", "GO", "CAPTURE"])
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--fingerprint", default=None, help="Frozen fingerprint for GO")
    parser.add_argument("--lane", action="append", dest="lanes", help="Restrict to lane")
    parser.add_argument(
        "--owner-choice",
        action="append",
        dest="owner_choices",
        metavar="PATH=CHOICE",
        help="Owner decision for path",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo).resolve()
    owner_choices: dict[str, str] = {}
    if args.owner_choices:
        for item in args.owner_choices:
            if "=" in item:
                path, choice = item.split("=", 1)
                owner_choices[path] = choice

    if args.mode == "PREVIEW" or args.mode == "CAPTURE":
        result = run_preview(repo_root)
    else:
        result = run_go(
            repo_root,
            frozen_fingerprint=args.fingerprint,
            owner_choices=owner_choices,
            lanes=args.lanes,
        )

    report = result_to_report(result)
    if args.json or args.mode == "CAPTURE":
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"STATUS: {result.status}")
        print(f"STAGE: {result.stage.value}")
        if result.stop_reason:
            print(f"STOP_REASON: {result.stop_reason}")
        if report.get("PARTITION"):
            print(f"PARTITION lanes: {report['PARTITION']['lanes']}")
            print(f"mixed_scope partitioned: {report['PARTITION']['mixed_scope']}")
        if report.get("CLASSIFICATION"):
            print(f"CLASSIFICATION: {report['CLASSIFICATION']}")

    if result.status in ("STOP_FOR_OWNER", "STALE_EXECUTION", "FAILED"):
        return 2
    if result.status == "PAUSED":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
