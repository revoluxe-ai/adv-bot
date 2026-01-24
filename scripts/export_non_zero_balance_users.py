from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from scripts.send_message.utils.get_users import export_non_zero_balance_users_to_csv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export users with non-zero Wildberries balances for sales reporting."
    )
    parser.add_argument(
        "--dest",
        "-o",
        type=Path,
        default=Path("send_message/scripts/send_message/non_zero_balance_users.csv"),
        help="CSV file to write (defaults to scripts/send_message/non_zero_balance_users.csv).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on how many users to export.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    asyncio.run(
        export_non_zero_balance_users_to_csv(
            args.dest,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
