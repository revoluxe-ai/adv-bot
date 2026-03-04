"""Запуск биллинга для одного кабинета по shop_id (debug: без Redis-skip, с выводом result)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, time

from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

import dotenv  # noqa: E402

from sqlalchemy import select

from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.modules.billing.billing import _process_single_cabinet, Pricer
from app.modules.billing.di import BillingContainer
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from python_modules.logger import setup_logging

dotenv.load_dotenv()

logger = logging.getLogger(__name__)
sm = get_async_session_maker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run billing for a single cabinet by shop_id (debug: skip_by_redis=False)."
    )
    parser.add_argument(
        "shop_id",
        type=str,
        help="Shop ID (WBCabinet.shop_id) магазина.",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        default=None,
        help="Дата в YYYY-MM-DD (по умолчанию — сегодня по серверу).",
    )
    return parser.parse_args()


async def resolve_cabinet_id_by_shop_id(shop_id: str) -> int | None:
    """Вернуть WBCabinet.id по shop_id или None, если не найден."""
    async with sm(read_only=True) as session:
        result = await session.execute(
            select(WBCabinet.id).where(WBCabinet.shop_id == shop_id)
        )
        return result.scalar_one_or_none()


async def run_billing_for_shop(shop_id: str, current_dt: datetime) -> None:
    cabinet_id = await resolve_cabinet_id_by_shop_id(shop_id)
    if cabinet_id is None:
        logger.error("Кабинет с shop_id=%s не найден.", shop_id)
        sys.exit(1)

    async with await DIManager.create(AppContainer) as app_container:  # type: ignore
        billing_container = BillingContainer(
            redis_client_wrapper=app_container.redis_client_wrapper,
        )
        pricer = Pricer()
        redis_manager = billing_container.redis_manager()
        result = await _process_single_cabinet(
            cabinet_id=cabinet_id,
            current_dt=current_dt,
            pricer=pricer,
            redis_manager=redis_manager,
            skip_by_redis=False,
        )
        logger.info(
            "Cabinet %s (shop_id=%s): processed=%s, payment_successful=%s, reason=%s, campaigns=%s, price_for_day=%s",
            result.get("cabinet_id"),
            shop_id,
            result.get("processed"),
            result.get("payment_successful"),
            result.get("reason"),
            result.get("campaigns"),
            result.get("price_for_day"),
        )
        print(result)


async def _main() -> None:
    args = parse_args()
    if args.target_date:
        target_date = datetime.strptime(args.target_date, "%Y-%m-%d").date()
        current_dt = datetime.combine(target_date, time.min)
    else:
        current_dt = datetime.now()
    await run_billing_for_shop(args.shop_id, current_dt)


def main() -> None:
    setup_logging()
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.warning("Interrupted.")


if __name__ == "__main__":
    main()
