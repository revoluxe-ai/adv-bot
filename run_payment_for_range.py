"""Run billing for a specified date range using process_payment_for_advs."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime, time, timedelta

import dotenv

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.modules.billing.billing import _process_payment_for_advs, Pricer
from app.modules.billing.di import BillingContainer
from python_modules.logger import setup_logging
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run daily billing for a range of dates via process_payment_for_advs."
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        required=True,
        help="Starting date (inclusive) in YYYY-MM-DD.",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        required=True,
        help="Ending date (inclusive) in YYYY-MM-DD.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Log the planned dates without executing billing.",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected YYYY-MM-DD."
        ) from exc


def iterate_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


async def run_billing_for_range(
    start_date: date,
    end_date: date,
    dry_run: bool,
) -> None:
    async with await DIManager.create(AppContainer) as app_container: # type: ignore
        billing_container = BillingContainer(
            redis_client_wrapper=app_container.redis_client_wrapper,
        )
        pricer = Pricer()
        redis_manager = billing_container.redis_manager()
        for target_date in iterate_dates(start_date, end_date):
            current_dt = datetime.combine(target_date, time.min)
            logger.info("Processing billing for %s", target_date.isoformat())
            if dry_run:
                logger.info(
                    "Dry run enabled; skipping actual billing for %s",
                    target_date.isoformat(),
                )
                continue
            await _process_payment_for_advs(
                current_date_time=current_dt,
                pricer=pricer,
                redis_manager=redis_manager,
                skip_by_redis=False
            )




async def _main() -> None:
    args = parse_args()
    start = parse_date(args.from_date)
    end = parse_date(args.to_date)
    if start > end:
        raise SystemExit("Start date must be <= end date.")
    await run_billing_for_range(start, end, args.dry_run)


def main() -> None:
    dotenv.load_dotenv()
    setup_logging()
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")


if __name__ == "__main__":
    main()
