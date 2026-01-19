"""Batch sales plan updater.

Define the SKUs and plan values directly below and run the script.
Only active campaigns (bot_active=True, associated shop active, active_status != "done")
are affected. Duplicate SKUs across multiple active campaigns raise an error.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Iterable

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


SKUS: list[int] = ...
PLAN_FOR_SALES_FOR_DAY: int = ...
TARGET_PRICE_FOR_ORDER: float = ...
MAX_PRICE_FOR_ORDER: float = ...

MAX_CPM = ...

print(len(SKUS))

SKUS = list(set(SKUS))


class DuplicateActiveCampaignError(RuntimeError):
    """Raised when one SKU belongs to multiple active campaigns."""


def _validate_constants() -> tuple[tuple[int, ...], int, float, float]:
    if PLAN_FOR_SALES_FOR_DAY <= 0:
        raise ValueError("plan_for_sales_for_day must be positive")
    if TARGET_PRICE_FOR_ORDER <= 0 or MAX_PRICE_FOR_ORDER <= 0:
        raise ValueError("price thresholds must be positive")
    if MAX_PRICE_FOR_ORDER < TARGET_PRICE_FOR_ORDER:
        raise ValueError("max_price_for_order must be >= target_price_for_order")

    resolved_skus = tuple(int(sku) for sku in SKUS)
    if not resolved_skus:
        raise ValueError("SKUS list must contain at least one value")
    if len(set(resolved_skus)) != len(resolved_skus):
        raise ValueError("SKUS list must not contain duplicates")
    if any(sku <= 0 for sku in resolved_skus):
        raise ValueError("SKUs must be positive integers")

    return resolved_skus, PLAN_FOR_SALES_FOR_DAY, TARGET_PRICE_FOR_ORDER, MAX_PRICE_FOR_ORDER


async def apply_sales_plan(
    skus: Iterable[int],
    plan_for_sales_for_day: int,
    target_price_for_order: float,
    max_price_for_order: float,
) -> int:
    stmt = (
        select(AdvSetting)
        .join(AdvSetting.wb_cabinet)
        .where(
            WBCabinet.active == True,
            AdvSetting.bot_active == True,
            AdvSetting.active_status != "done",
        )
    )
    async with sm() as session:
        result = await session.execute(stmt)
        adv_settings = result.scalars().unique().all()

        sku_to_adv: dict[int, AdvSetting] = {}
        adv_id_to_skus: dict[int, list[int]] = defaultdict(list)
        skus_set = set(skus)
        for adv in adv_settings:
            for raw_nmid in adv.nmids or []:
                try:
                    nmid = int(raw_nmid)
                except (TypeError, ValueError):
                    continue
                if nmid not in skus_set:
                    continue
                previous_adv = sku_to_adv.get(nmid)
                if previous_adv and previous_adv.id != adv.id:
                    raise DuplicateActiveCampaignError(
                        "SKU %s is present in multiple active campaigns (%s, %s)"
                        % (nmid, previous_adv.adv_id, adv.adv_id)
                    )
                sku_to_adv[nmid] = adv

                sku_list = adv_id_to_skus[adv.id]
                if nmid not in sku_list:
                    sku_list.append(nmid)

        if not sku_to_adv:
            logger.warning("No active campaign holds requested SKUs")
            return 0

        for adv in {adv.id: adv for adv in sku_to_adv.values()}.values():
            adv.plan_for_sales_for_day = plan_for_sales_for_day
            adv.target_price_for_order = target_price_for_order
            adv.max_price_for_order = max_price_for_order
            adv.max_cpm = MAX_CPM
            skus = adv_id_to_skus.get(adv.id, [])
            logger.info(
                "Updating adv_id=%s skus=%s",
                adv.adv_id,
                sorted(skus),
            )

        missing_skus = skus_set.difference(sku_to_adv.keys())
        if missing_skus:
            logger.warning(
                "SKUs without active campaigns: %s", sorted(missing_skus)
            )

        await session.commit()
        logger.info(
            "Applied sales plan to %d campaigns covering %d SKUs",
            len({adv.id for adv in sku_to_adv.values()}),
            len(sku_to_adv),
        )
        return len({adv.id for adv in sku_to_adv.values()})


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def _main_async() -> None:
    resolved_skus, plan, target_price, max_price = _validate_constants()
    updated = await apply_sales_plan(
        resolved_skus,
        plan,
        target_price,
        max_price,
    )
    logger.info("Finished updating %d campaigns", updated)


def main() -> None:
    _configure_logging()
    try:
        asyncio.run(_main_async())
    except DuplicateActiveCampaignError as exc:
        logger.error("failed to apply sales plan: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
