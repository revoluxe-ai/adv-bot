"""Cooperative interrupt ordinary V3 до apply (spec ``card-ab-hold-mode``).

Bot пишет ENTER signal в Redis; shop-runner читает и делает early return
до structural apply — «остановлено, безопасно, можно продолжать».

Defense-in-depth (decision §4): PG ``card_ab_hold_mode`` — SoT. Если durable
mode уже ``PENDING_SETUP`` / ``ACTIVE`` (окно commit→Redis ENTER, Redis miss,
stale in-memory ComplexAdv), ordinary V3 тоже MUST abort до structural write.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    is_ab_hold_structural_freeze,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldLastAbortRedisCache,
    CardAbHoldLastAbortSnapshot,
    CardAbHoldSignalKind,
    CardAbHoldSignalRedisCache,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


async def _fetch_durable_card_ab_hold_mode(adv_id: int) -> CardAbHoldMode | None:
    """Свежий PG mode по ``adv_id``; ``None`` при ошибке чтения (fail-open).

    Не использует in-memory ``AdvSetting`` — после enable bot-пода объект
    shop-runner часто ещё показывает ``OFF``.
    """
    try:
        async with sm() as session:
            raw = await session.scalar(
                select(AdvSetting.card_ab_hold_mode).where(
                    AdvSetting.adv_id == adv_id
                )
            )
        return normalize_card_ab_hold_mode(raw)
    except Exception:
        logger.warning(
            "[adv_id=%s] card_ab_hold interrupt: PG mode read failed (fail-open)",
            adv_id,
            exc_info=True,
        )
        return None


async def _record_safe_abort(adv: AdvSetting, *, reason: str) -> None:
    """Записать LastAbort (safe/can_continue) для UI poll после interrupt."""
    await CardAbHoldLastAbortRedisCache(adv).set_abort(
        CardAbHoldLastAbortSnapshot(
            reason=reason,
            safe=True,
            can_continue=True,
        )
    )


async def abort_ordinary_v3_if_enter_signaled(adv: AdvSetting) -> bool:
    """Вернуть True, если ordinary V3 MUST остановиться до structural apply.

    Порядок:
    1. Redis ENTER — cooperative interrupt + clear signal + LastAbort.
    2. Fresh PG mode PENDING/ACTIVE — belt-and-suspenders при отсутствии signal.

    Side effects: Redis LastAbort; при ENTER — clear signal; при PG freeze MAY
    обновить ``adv.card_ab_hold_mode`` in-memory для согласованности тика.
    """
    signal_cache = CardAbHoldSignalRedisCache(adv)
    snapshot = await signal_cache.get_signal()
    if snapshot is not None and snapshot.signal == CardAbHoldSignalKind.ENTER:
        await _record_safe_abort(adv, reason="enter_requested")
        await signal_cache.clear()
        logger.info(
            "[adv_id=%s] v3 aborted before apply: CardAbHold ENTER signal",
            adv.adv_id,
        )
        return True

    adv_id = int(adv.adv_id)
    mode = await _fetch_durable_card_ab_hold_mode(adv_id)
    if mode is not None and is_ab_hold_structural_freeze(mode):
        await _record_safe_abort(adv, reason="durable_mode_freeze")
        if hasattr(adv, "card_ab_hold_mode"):
            adv.card_ab_hold_mode = mode.value
        logger.info(
            "[adv_id=%s] v3 aborted before apply: durable CardAbHold mode=%s",
            adv_id,
            mode.value,
        )
        return True
    return False
