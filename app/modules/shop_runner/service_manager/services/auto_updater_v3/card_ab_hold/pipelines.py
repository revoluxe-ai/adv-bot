"""Setup/Hold entrypoints A/B Hold (spec ``card-ab-hold-mode``).

Отдельные пути vs ordinary ``process_adv_v3`` — decision
``card-ab-hold-write-path-ownership``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.hold_guards import (
    apply_ab_hold_overspend_offs,
    is_ab_hold_campaign_deep_overspend,
    select_ab_hold_overspend_off_keyword_ids,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    SETUP_LOCK_TTL_SEC,
    CardAbHoldSignalRedisCache,
    setup_lock_redis_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.redis_lock_manager import (
    RedisLockManager,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
        ComplexAdv,
        WBShopDataManager,
    )

logger = logging.getLogger(__name__)


async def process_ab_setup(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
) -> None:
    """ENTER setup-tick: классификация + OFF/ЦП persist; mode → ACTIVE.

    Spec card-ab-hold-mode ENTER. Без ordinary NORMAL preamble.
    Single-flight через ``RedisLockManager`` / ``CardAbHoldSetupLock:{adv_id}``.
    """
    _ = wb_shop_data_manager
    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.PENDING_SETUP:
        logger.info(
            "[adv_id=%s] ab_setup skip: mode=%s",
            complex_adv.adv_id,
            mode.value,
        )
        return

    signal_cache = CardAbHoldSignalRedisCache(complex_adv.adv_setting)
    lock_mgr = RedisLockManager(signal_cache.client)
    lock_key = setup_lock_redis_key(int(complex_adv.adv_id))
    token = f"{complex_adv.shop_id}:{uuid4()}"
    acquired = await lock_mgr.acquire(lock_key, token, SETUP_LOCK_TTL_SEC)
    if not acquired:
        logger.warning(
            "[adv_id=%s] ab_setup: lock not acquired",
            complex_adv.adv_id,
        )
        return
    try:
        keywords = await complex_adv.get_keywords()
        plan_max = float(
            getattr(complex_adv.adv_setting, "max_price_for_order", None) or 0
        )
        if plan_max <= 0:
            logger.warning(
                "[adv_id=%s] ab_setup: max_price_for_order missing, skip",
                complex_adv.adv_id,
            )
            return

        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=int(complex_adv.adv_id),
            adv_setting_id=int(complex_adv.adv_setting.id),
            keywords=keywords,
            max_pay_for_order=plan_max,
        )
        complex_adv.adv_setting.card_ab_hold_mode = CardAbHoldMode.ACTIVE.value
        logger.info(
            "[adv_id=%s] ab_setup done pass=%s fail=%s → ACTIVE",
            complex_adv.adv_id,
            pass_n,
            fail_n,
        )
    finally:
        await lock_mgr.release(lock_key, token)


async def process_ab_hold(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
) -> None:
    """HOLD-тик: only overspend/PFO-off guard; bidder вне этого path.

    Spec card-ab-hold-mode HOLD. Ordinary V3 не вызывается.
    """
    _ = wb_shop_data_manager
    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.ACTIVE:
        return

    plan_max = float(
        getattr(complex_adv.adv_setting, "max_price_for_order", None) or 0
    )
    if plan_max <= 0:
        logger.debug(
            "[adv_id=%s] ab_hold: no max_price_for_order, skip guards",
            complex_adv.adv_id,
        )
        return

    fact = complex_adv.fact_pay_for_order
    if not is_ab_hold_campaign_deep_overspend(
        fact_pay_for_order=fact,
        max_pay_for_order=plan_max,
    ):
        logger.debug(
            "[adv_id=%s] ab_hold tick: no deep overspend, structural freeze only",
            complex_adv.adv_id,
        )
        return

    keywords = await complex_adv.get_keywords()
    off_ids = select_ab_hold_overspend_off_keyword_ids(
        keywords, max_pay_for_order=plan_max
    )
    if not off_ids:
        logger.debug(
            "[adv_id=%s] ab_hold: deep overspend but no PFO>max keywords",
            complex_adv.adv_id,
        )
        return
    _ = await apply_ab_hold_overspend_offs(
        adv_id=int(complex_adv.adv_id),
        keyword_ids=off_ids,
    )
