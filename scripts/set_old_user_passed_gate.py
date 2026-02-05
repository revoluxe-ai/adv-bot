"""One-time migration: set passed_gate=True and passed_gate_reason=OLD_USER for users who have non-zero cabinet balance or cabinet payment history."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv()

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.passed_gate_reason import PassedGateReason
from app.utils.db.session_maker import get_async_session_maker

LOG = logging.getLogger(__name__)

# Float tolerance for "balance != 0" to avoid float noise
BALANCE_ZERO_TOLERANCE = 1e-9


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set passed_gate=OLD_USER for users with non-zero cabinet balance or cabinet payment history."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count and log; do not commit.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Commit every N updated users (default 500). 0 = single commit at end.",
    )
    return parser.parse_args()


def _user_total_cabinet_balance(user: User) -> float:
    """Sum of calculated_balance + calculated_bonus over all user cabinets."""
    total = 0.0
    for wb_uc in user.wb_user_cabinets:
        cabinet = wb_uc.wb_cabinet
        if cabinet is None:
            continue
        total += float(cabinet.calculated_balance) + float(cabinet.calculated_bonus)
    return total


def _user_has_cabinet_payments(user: User) -> bool:
    """True if any cabinet has at least one balance or bonus payment."""
    for wb_uc in user.wb_user_cabinets:
        cabinet = wb_uc.wb_cabinet
        if cabinet is None:
            continue
        if (cabinet.balance_payments and len(cabinet.balance_payments) > 0) or (
            cabinet.bonus_payments and len(cabinet.bonus_payments) > 0
        ):
            return True
    return False


def _should_set_old_user(user: User, total_balance: float) -> bool:
    """True if user qualifies for OLD_USER and gate is not already passed."""
    if user.passed_gate and user.passed_gate_reason is not None:
        return False
    non_zero_balance = abs(total_balance) >= BALANCE_ZERO_TOLERANCE
    has_payments = _user_has_cabinet_payments(user)
    return bool(non_zero_balance or has_payments)


async def _run(dry_run: bool, batch_size: int) -> None:
    updated_count = 0
    processed_count = 0

    async with get_async_session_maker(read_only=False) as session:
        stmt = (
            select(User)
            .options(
                selectinload(User.wb_user_cabinets).selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.balance_payments),
                selectinload(User.wb_user_cabinets).selectinload(WBUserCabinet.wb_cabinet).selectinload(WBCabinet.bonus_payments),
            )
        )
        result = await session.execute(stmt)
        users = result.scalars().unique().all()

        for user in users:
            processed_count += 1
            total_balance = _user_total_cabinet_balance(user)
            if not _should_set_old_user(user, total_balance):
                continue

            user.passed_gate = True
            user.passed_gate_reason = PassedGateReason.OLD_USER
            user.passed_gate_at = datetime.now(timezone.utc)
            updated_count += 1

            if batch_size > 0 and updated_count % batch_size == 0 and not dry_run:
                await session.commit()
                LOG.info("Committed batch: %d users updated so far", updated_count)

        if not dry_run and updated_count > 0:
            await session.commit()

    LOG.info(
        "Processed %d users, set passed_gate=OLD_USER for %d users (dry_run=%s)",
        processed_count,
        updated_count,
        dry_run,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    asyncio.run(_run(dry_run=args.dry_run, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
