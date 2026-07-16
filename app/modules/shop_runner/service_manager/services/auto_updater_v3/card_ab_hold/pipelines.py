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
    capture_allowed_phrase_set,
    normalize_allowed_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldSetupBlockKind,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    SETUP_LOCK_TTL_SEC,
    CardAbHoldSetupBlockRedisCache,
    CardAbHoldSetupBlockSnapshot,
    CardAbHoldSignalRedisCache,
    setup_lock_redis_key,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
    persist_ab_hold_degraded_flag,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.redis_lock_manager import (
    RedisLockManager,
)
from app.modules.shop_runner.service_manager.services.minus_phrase_manager import (
    MinusPhraseManagerContainer,
)

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
    """ENTER setup-tick: capture allowed-set → snapshot → enforce → OFF/ЦП → ACTIVE.

    Spec card-ab-hold-mode ENTER / decision §8 (primary invariant = allowed-set).
    Без ordinary NORMAL preamble. Single-flight через ``RedisLockManager`` /
    ``CardAbHoldSetupLock:{adv_id}``. Без зафиксированного allowed-set snapshot
    ACTIVE не выставляется; минус приводится к «всё вне allowed-set» (enforcement).
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
    # decision §14b: канал actionable-причины блока setup для UI (без PG-миграции).
    block_cache = CardAbHoldSetupBlockRedisCache(complex_adv.adv_setting)
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
            # decision §14a/§14b: обычно отсекается hard-gate на enable; если план
            # max CPO пропал уже после ENTER — фиксируем детерминированную причину,
            # чтобы UI PENDING показал actionable-текст, а не generic «Подготовка…».
            logger.warning(
                "[adv_id=%s] ab_setup: max_price_for_order missing, skip",
                complex_adv.adv_id,
            )
            await block_cache.set_block(
                CardAbHoldSetupBlockSnapshot(
                    kind=CardAbHoldSetupBlockKind.MISSING_MAX_CPO
                )
            )
            return

        # Decision §8: primary invariant — заморозить разрешённый (allowed) набор
        # фраз (тексты ключей status != BAD), а не список минус-фраз.
        allowed_texts = capture_allowed_phrase_set(keywords)

        # Spec card-ab-hold-mode «ACTIVE without ENTER setup snapshot is forbidden»
        # (line: «hold enforcement does not treat an empty/missing allowed-set
        # snapshot as a successful freeze») + decision §8: пустой allowed-set — это
        # НЕ валидная заморозка, а вырожденное состояние (все ключи BAD / ключей нет
        # / shelf-only без keyword-surface). Enforcement с allowed=∅ заминусовал бы
        # всё наблюдаемое (freeze-to-zero), а mode ушёл бы в ACTIVE, и UI заявил бы
        # чистый testable hold. Поэтому НЕ enforce и НЕ переводим в ACTIVE: остаёмся
        # в PENDING_SETUP (visible non-ready); следующий тик повторит попытку, когда
        # появятся non-BAD ключи. Lock снимается в finally.
        if not allowed_texts:
            logger.error(
                "[adv_id=%s] ab_setup aborted: allowed-set пуст (нет non-BAD ключей) — "
                "freeze невозможен, mode остаётся PENDING_SETUP (не ACTIVE)",
                complex_adv.adv_id,
            )
            # decision §14b: детерминированный блок — surface actionable-причину в
            # статусе PENDING (не молчаливый вечный PENDING).
            await block_cache.set_block(
                CardAbHoldSetupBlockSnapshot(
                    kind=CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET
                )
            )
            return

        minus_mgr = MinusPhraseManagerContainer(
            _wb_api_manager_hub=wb_manager_hub
        ).minus_phrase_manager()
        # Одна setup sync (не ordinary loop): привести WB к allowed-set —
        # исключить всё наблюдаемое вне набора в пределах WB minus cap.
        enforce = await minus_mgr.enforce_frozen_allowed_set(complex_adv, allowed_texts)
        degraded = bool(enforce["cap_exceeded"])

        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=int(complex_adv.adv_id),
            adv_setting_id=int(complex_adv.adv_setting.id),
            keywords=keywords,
            max_pay_for_order=plan_max,
            allowed_phrases_snapshot=allowed_texts,
            degraded=degraded,
        )
        complex_adv.adv_setting.card_ab_hold_mode = CardAbHoldMode.ACTIVE.value
        complex_adv.adv_setting.card_ab_hold_allowed_phrases_snapshot = allowed_texts
        complex_adv.adv_setting.card_ab_hold_degraded = degraded
        # decision §14b: setup завершён (→ ACTIVE) — снять причину блока PENDING.
        await block_cache.clear()
        if degraded:
            logger.error(
                "[adv_id=%s] ab_setup allowed-set enforcement degraded on %s target(s): "
                "hold NOT guaranteed clean (WB minus cap / open-match)",
                complex_adv.adv_id,
                len(enforce["cap_exceeded"]),
            )
        logger.info(
            "[adv_id=%s] ab_setup done pass=%s fail=%s allowed=%s enforce_written=%s → ACTIVE",
            complex_adv.adv_id,
            pass_n,
            fail_n,
            len(allowed_texts),
            enforce["written"],
        )
    finally:
        await lock_mgr.release(lock_key, token)


async def process_ab_hold(
    complex_adv: "ComplexAdv",
    *,
    wb_shop_data_manager: "WBShopDataManager",
    wb_manager_hub: "WBManagerHub",
) -> None:
    """HOLD-тик: allowed-set enforcement + overspend/PFO-off; bidder вне path.

    Spec card-ab-hold-mode HOLD / decision §8. Ordinary V3 не вызывается.
    Hold-protection (≠ ordinary recalc) удерживает поверхность трат равной
    замороженному allowed-set: новые/не-разрешённые фразы исключаются, снятые
    разрешённые восстанавливаются; при превышении WB minus cap — видимая деградация.
    """
    _ = wb_shop_data_manager
    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.ACTIVE:
        return

    allowed = normalize_allowed_snapshot(
        getattr(complex_adv.adv_setting, "card_ab_hold_allowed_phrases_snapshot", None)
    )
    minus_mgr = MinusPhraseManagerContainer(
        _wb_api_manager_hub=wb_manager_hub
    ).minus_phrase_manager()
    enforce = await minus_mgr.enforce_frozen_allowed_set(complex_adv, allowed)
    degraded = bool(enforce["cap_exceeded"])
    # decision §8: честная деградация MUST быть durable, чтобы UI (bot-под) не
    # заявлял чистый hold. Пишем в PG только при смене флага (self-healing включён).
    if degraded != bool(
        getattr(complex_adv.adv_setting, "card_ab_hold_degraded", False)
    ):
        await persist_ab_hold_degraded_flag(
            adv_setting_id=int(complex_adv.adv_setting.id),
            degraded=degraded,
        )
        complex_adv.adv_setting.card_ab_hold_degraded = degraded
    if degraded:
        logger.error(
            "[adv_id=%s] ab_hold allowed-set enforcement degraded on %s target(s): "
            "hold NOT guaranteed clean (WB minus cap / open-match)",
            complex_adv.adv_id,
            len(enforce["cap_exceeded"]),
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
