"""Batch sales plan updater.

Define the SKUs and plan values directly below and run the script.
Only active campaigns (bot_active=True, associated shop active, active_status != "done")
are affected. Duplicate SKUs across multiple active campaigns raise an error.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

SHOP_ID = ...
SKUS: list[int] = ...
PLAN_FOR_SALES_FOR_DAY: int = ...
TARGET_PRICE_FOR_ORDER: float = ...
MAX_PRICE_FOR_ORDER: float = ...

MAX_CPM = ...
SEARCH_BUDGET_LIMIT = 1000
AUTO_BUDGET_LIMIT = 1000
# print(len(SKUS))



class DuplicateActiveCampaignError(RuntimeError):
    """Raised when one SKU belongs to multiple active campaigns."""

#
# def _validate_constants() -> tuple[tuple[int, ...], int, float, float]:
#     if PLAN_FOR_SALES_FOR_DAY <= 0:
#         raise ValueError("plan_for_sales_for_day must be positive")
#     if TARGET_PRICE_FOR_ORDER <= 0 or MAX_PRICE_FOR_ORDER <= 0:
#         raise ValueError("price thresholds must be positive")
#     if MAX_PRICE_FOR_ORDER < TARGET_PRICE_FOR_ORDER:
#         raise ValueError("max_price_for_order must be >= target_price_for_order")
#
#     resolved_skus = tuple(int(sku) for sku in SKUS)
#     if not resolved_skus:
#         raise ValueError("SKUS list must contain at least one value")
#     if len(set(resolved_skus)) != len(resolved_skus):
#         raise ValueError("SKUS list must not contain duplicates")
#     if any(sku <= 0 for sku in resolved_skus):
#         raise ValueError("SKUs must be positive integers")
#
#     return resolved_skus, PLAN_FOR_SALES_FOR_DAY, TARGET_PRICE_FOR_ORDER, MAX_PRICE_FOR_ORDER


async def apply_sales_plan(
) -> int:
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .where(
            WBCabinet.active == True,
            AdvSetting.bot_active == True,
            AdvSetting.active_status != "done",
            WBCabinet.shop_id == SHOP_ID
        )
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_settings = result.scalars().unique().all()

        for adv in adv_settings:
            # adv.plan_for_sales_for_day = plan_for_sales_for_day
            # adv.target_price_for_order = target_price_for_order
            # adv.max_price_for_order = max_price_for_order
            # adv.max_cpm = MAX_CPM
            adv.auto_budget_daily_limit = SEARCH_BUDGET_LIMIT
            adv.search_auto_budget_daily_limit = SEARCH_BUDGET_LIMIT
            adv.auto_budget_watchdog_enabled = True

        await session.commit()



def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def _main_async() -> None:
    updated = await apply_sales_plan(
    )


def main() -> None:
    _configure_logging()
    try:
        asyncio.run(_main_async())
    except DuplicateActiveCampaignError as exc:
        logger.error("failed to apply sales plan: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
