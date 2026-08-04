"""Argparse для wb_api_readonly_ops."""

from __future__ import annotations

import argparse

from scripts.wb_api_readonly_ops.models import Mode

DEFAULT_MAX_SECONDS = 180.0
DEFAULT_MAX_CALLS = 40


def build_parser() -> argparse.ArgumentParser:
    """CLI: обязательные --shop-id и --mode."""
    parser = argparse.ArgumentParser(
        prog="wb_api_readonly_ops",
        description=(
            "Owner-local WB API read-only preflight/collect via existing stack. "
            "Not Web READ_ONLY_PREFLIGHT_PASS."
        ),
    )
    parser.add_argument(
        "--shop-id",
        required=True,
        help="WB cabinet shop_id (never hardcoded)",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=[Mode.PREFLIGHT.value, Mode.COLLECT.value],
        help="preflight=smallest probe; collect=best-effort pull",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=DEFAULT_MAX_SECONDS,
        help="run ceiling wall-clock seconds (default 180)",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help="run ceiling family API calls (default 40)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="override outputs dir (default scripts/wb_api_readonly_ops/outputs)",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать argv; unknown mode → SystemExit non-zero via argparse."""
    return build_parser().parse_args(argv)
