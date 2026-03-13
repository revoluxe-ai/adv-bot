"""Delete a user by user_telegram_id. Removes or nullifies all dependent rows then deletes the user."""

from __future__ import annotations

import argparse
import asyncio
import sys

try:
    from set_path import add_project_root_to_path
except ImportError:
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv

dotenv.load_dotenv()

from sqlalchemy import delete, or_, select, update

# Ensure ORM registry has AdvSetting before billing/balance_exp_informer models resolve
from app.modules.common_slaves.wildberries.models import AdvSetting  # noqa: F401
from app.modules.billing.event_manager.models import BillingEvent
from app.modules.wb_adv_updater.modules.balance_exp_informer.models import BalanceReminder
from app.payments.db.models import Payment
from app.utils.db.models import Invite, User, UserBalancePayment, UserBonusPayment
from app.utils.db.session_maker import get_async_session_maker


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete user by user_telegram_id. Use --dry-run to only show what would be done."
    )
    parser.add_argument(
        "user_telegram_id",
        type=int,
        help="Telegram ID of the user to delete.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only find and report; do not delete or commit.",
    )
    return parser.parse_args()


async def _run(telegram_id: int, dry_run: bool) -> int:
    async with get_async_session_maker(read_only=False) as session:
        stmt = select(User).where(User.user_telegram_id == telegram_id)
        user = await session.scalar(stmt)
        if user is None:
            print(f"User with user_telegram_id={telegram_id} not found.", file=sys.stderr)
            return 1

        user_id = user.id
        print(f"User: id={user_id}, user_telegram_id={user.user_telegram_id}, username={user.username!r}")

        if dry_run:
            print("Dry-run: would delete/update dependent rows and then delete user. No changes made.")
            return 0

        # Delete or nullify dependencies in FK-safe order
        await session.execute(delete(Payment).where(Payment.user_id == user_id))
        await session.execute(delete(UserBalancePayment).where(UserBalancePayment.user_id == user_id))
        await session.execute(
            update(UserBonusPayment)
            .where(UserBonusPayment.admin_user_id == user_id)
            .values(admin_user_id=None)
        )
        await session.execute(delete(UserBonusPayment).where(UserBonusPayment.user_id == user_id))
        await session.execute(
            update(Invite)
            .where(or_(Invite.issued_to_user_id == user_id, Invite.used_by_user_id == user_id))
            .values(issued_to_user_id=None, used_by_user_id=None)
        )
        await session.execute(delete(BalanceReminder).where(BalanceReminder.user_id == user_id))
        await session.execute(
            update(BillingEvent).where(BillingEvent.user_id == user_id).values(user_id=None)
        )

        await session.delete(user)
        await session.commit()

    print(f"User user_telegram_id={telegram_id} (id={user_id}) deleted.")
    return 0


def main() -> None:
    args = _parse_args()
    exit_code = asyncio.run(_run(args.user_telegram_id, args.dry_run))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
