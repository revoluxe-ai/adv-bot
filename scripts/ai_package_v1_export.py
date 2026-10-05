#!/usr/bin/env python3
"""CLI: read-only AI Package v1 full ZIP для одного магазина (без WB API)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.package_zip_assembler import PackageZipAssembler


def _parse_date(value: str) -> date:
    """Парсит YYYY-MM-DD."""
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    """Аргументы operator CLI (один shop, один ZIP)."""
    parser = argparse.ArgumentParser(
        description="Export AI Package v1 ZIP for one shop (read-only PG/CH).",
    )
    parser.add_argument(
        "--shop-id",
        required=True,
        help="WBCabinet.shop_id (str)",
    )
    parser.add_argument(
        "--period-start",
        required=True,
        type=_parse_date,
        help="Inclusive period start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--period-end",
        required=True,
        type=_parse_date,
        help="Inclusive period end (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write ZIP to path (default: stdout binary)",
    )
    return parser


async def _run_export(args: argparse.Namespace) -> bytes:
    """Собирает ZIP через PackageZipAssembler."""
    period = ExportPeriod(start=args.period_start, end=args.period_end)
    assembler = PackageZipAssembler()
    return await assembler.assemble_zip(args.shop_id, period)


def main(argv: list[str] | None = None) -> int:
    """
    Точка входа Job/operator.

    Returns:
        0 при успехе, 1 при ошибке аргументов или export.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        zip_bytes = asyncio.run(_run_export(args))
    except (ValueError, OSError) as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    if args.output is not None:
        args.output.write_bytes(zip_bytes)
    else:
        sys.stdout.buffer.write(zip_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
