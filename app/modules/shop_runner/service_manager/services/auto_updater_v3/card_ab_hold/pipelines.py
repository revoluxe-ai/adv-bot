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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    capture_minus_snapshot,
    restore_minus_snapshot_if_drift,
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
from app.modules.shop_runner.service_manager.services.minus_phrase_manager import (
    MinusPhraseManagerContainer,
)
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager

if TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHub
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
        ComplexAdv,
        WBShopDataManager,
    )

logger = logging.getLogger(__name__)


async def process_ab_setup(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
    wb_manager_hub: "WBManagerHub",
) -> None:
    """ENTER setup-tick: minus sync+snapshot → OFF/ЦП → mode ACTIVE.

    Spec card-ab-hold-mode ENTER / decision §8. Без ordinary NORMAL preamble.
    Single-flight через ``RedisLockManager`` / ``CardAbHoldSetupLock:{adv_id}``.
    Без успешного minus sync+snapshot ACTIVE не выставляется.
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

        minus_mgr = MinusPhraseManagerContainer(
            _wb_api_manager_hub=wb_manager_hub
        ).minus_phrase_manager()
        # Decision §8: одна setup sync (не ordinary loop), bypass freeze gate.
        await minus_mgr.update_minus_phrases(
            complex_adv, force_ab_hold_setup_sync=True
        )
        wb_modifier = wb_manager_hub.wb_modifier

        async def _get_minus(adv_id: int, nmid: int) -> list[str]:
            return list(await wb_modifier.get_minus_phrases_for_adv(adv_id, nmid))

        snapshot = await capture_minus_snapshot(complex_adv, get_minus=_get_minus)

        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=int(complex_adv.adv_id),
            adv_setting_id=int(complex_adv.adv_setting.id),
            keywords=keywords,
            max_pay_for_order=plan_max,
            minus_phrases_snapshot=snapshot,
        )
        complex_adv.adv_setting.card_ab_hold_mode = CardAbHoldMode.ACTIVE.value
        complex_adv.adv_setting.card_ab_hold_minus_phrases_snapshot = snapshot
        logger.info(
            "[adv_id=%s] ab_setup done pass=%s fail=%s minus=%s → ACTIVE",
            complex_adv.adv_id,
            pass_n,
            fail_n,
            len(snapshot),
        )
    finally:
        await lock_mgr.release(lock_key, token)


async def process_ab_hold(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
    wb_manager_hub: "WBManagerHub",
) -> None:
    """HOLD-тик: minus restore-on-drift + overspend/PFO-off; bidder вне path.

    Spec card-ab-hold-mode HOLD / decision §8. Ordinary V3 не вызывается.
    """
    _ = wb_shop_data_manager
    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.ACTIVE:
        return

    wb_modifier = wb_manager_hub.wb_modifier
    update_ts = AdvActiveKeywordUpdateStateManager()

    async def _get_minus(adv_id: int, nmid: int) -> list[str]:
        return list(await wb_modifier.get_minus_phrases_for_adv(adv_id, nmid))

    async def _set_minus(adv_id: int, nmid: int, phrases: list[str]) -> None:
        _ = await wb_modifier.set_minus_phrases_with_fallback_for_adv(
            adv_id=adv_id,
            nmid=nmid,
            phrases=phrases,
            update_redis_timestamp_manager=update_ts,
        )

    snapshot = getattr(
        complex_adv.adv_setting, "card_ab_hold_minus_phrases_snapshot", None
    )
    _ = await restore_minus_snapshot_if_drift(
        complex_adv,
        snapshot=snapshot,
        get_minus=_get_minus,
        set_minus=_set_minus,
    )

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
