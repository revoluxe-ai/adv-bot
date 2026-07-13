"""Cooperative interrupt ordinary V3 до apply (spec ``card-ab-hold-mode``).

Bot пишет ENTER signal в Redis; shop-runner читает и делает early return
до structural apply — «остановлено, безопасно, можно продолжать».
"""

from __future__ import annotations

import logging

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldLastAbortRedisCache,
    CardAbHoldLastAbortSnapshot,
    CardAbHoldSignalKind,
    CardAbHoldSignalRedisCache,
)

logger = logging.getLogger(__name__)


async def abort_ordinary_v3_if_enter_signaled(adv: AdvSetting) -> bool:
    """Вернуть True, если ordinary V3 MUST остановиться до apply.

    При signal ENTER пишет LastAbort (safe/can_continue) и очищает signal.
    """
    signal_cache = CardAbHoldSignalRedisCache(adv)
    snapshot = await signal_cache.get_signal()
    if snapshot is None or snapshot.signal != CardAbHoldSignalKind.ENTER:
        return False
    await CardAbHoldLastAbortRedisCache(adv).set_abort(
        CardAbHoldLastAbortSnapshot(
            reason="enter_requested",
            safe=True,
            can_continue=True,
        )
    )
    await signal_cache.clear()
    logger.info(
        "[adv_id=%s] v3 aborted before apply: CardAbHold ENTER signal",
        adv.adv_id,
    )
    return True
