"""A/B Hold ENTER: one-shot сброс Search common bid на WB minimum (decision §19).

Spec ``card-ab-hold-mode`` requirement
«ENTER resets Search common bid to WB minimum then freezes it».

Owned write-path = A/B Hold setup/ENTER (shop-runner), не ordinary
``update_common_bid_in_search_adv`` и не bidder/cluster. Continuous ordinary
updater остаётся Forbidden under ``PENDING_SETUP`` / ``ACTIVE`` (structural
freeze). Повторный reset — только после EXIT → новый ENTER (Redis done-маркер
снимается на EXIT).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
    SetCommonBidsCommandItem,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.redis_coordination import (
    CardAbHoldCommonBidEnterResetRedisCache,
)
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)
from app.shared.domains.wb.enums import AdvType

if TYPE_CHECKING:
    from app.core.di.wb_manager_hub import WBManagerHub
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
        ComplexAdv,
        WBShopDataManager,
    )

logger = logging.getLogger(__name__)

CommonBidEnterResetStatus = Literal[
    "written",
    "already_done",
    "skipped_wrong_mode",
    "skipped_no_search",
    "skipped_no_items",
    "degraded_missing_min",
    "degraded_wb_error",
]


@dataclass(frozen=True, slots=True)
class CommonBidEnterResetResult:
    """Исход one-shot ENTER reset Search common bid.

    Attributes:
        status: итог попытки (written / already_done / skip / degrade).
        nmid_to_bid: фактически отправленные nm→min ставки (пусто если не писали).
        detail: краткая причина для логов / UI degrade.
    """

    status: CommonBidEnterResetStatus
    nmid_to_bid: dict[int, int]
    detail: str = ""


def resolve_search_min_bids_for_nmids(
    *,
    nmids: list[int],
    min_nmids_bids: AdvMinNmidsBids | None,
) -> dict[int, int] | None:
    """Собрать nmid→WB search min; ``None`` если SoT минимума недоступен.

    Args:
        nmids: nm кампании (все должны иметь min в ``search``).
        min_nmids_bids: SoT минимумов с ComplexAdv / backfill.

    Returns:
        dict nmid→min либо ``None``, если min отсутствует хотя бы для одного nmid
        или ``min_nmids_bids`` / ``search`` пусты при непустых nmids.
    """
    if not nmids:
        return {}
    if min_nmids_bids is None or not min_nmids_bids.search:
        return None
    resolved: dict[int, int] = {}
    for nmid in nmids:
        raw = min_nmids_bids.search.get(int(nmid))
        if raw is None:
            return None
        resolved[int(nmid)] = int(raw)
    return resolved


def build_set_common_bids_to_min_command(
    complex_adv: "ComplexAdv",
    nmid_to_min: dict[int, int],
) -> SetCommonBidsCommand | None:
    """Собрать ``SetCommonBidsCommand`` на WB minimum по всем nm.

    Args:
        complex_adv: кампания (нужен search placement / ComplexAdv shape).
        nmid_to_min: уже резолвнутые минимумы.

    Returns:
        Команда или ``None``, если нечего писать.
    """
    if not nmid_to_min:
        return None
    items = [
        SetCommonBidsCommandItem(
            complex_adv=complex_adv,
            adv_type=AdvType.SEARCH,
            target_nmid=nmid,
            new_bid=bid,
        )
        for nmid, bid in sorted(nmid_to_min.items())
    ]
    return SetCommonBidsCommand(items=items)


async def ensure_search_common_bid_reset_on_enter(
    complex_adv: "ComplexAdv",
    *,
    wb_manager_hub: "WBManagerHub",
    wb_shop_data_manager: "WBShopDataManager | None" = None,
) -> CommonBidEnterResetResult:
    """Один раз на ENTER сбросить Search common bid на WB min (идемпотентно).

    Вызывать из ``process_ab_setup`` / ``process_ab_epoch`` при
    ``PENDING_SETUP``. Не вызывать из ordinary common-bid updater и не из
    ``process_ab_hold`` (ACTIVE freeze).

    Args:
        complex_adv: кампания shop-runner.
        wb_manager_hub: WB write + Redis.
        wb_shop_data_manager: опциональный backfill ``min_nmids_bids``.

    Returns:
        ``CommonBidEnterResetResult`` с статусом попытки.
    """
    mode = normalize_card_ab_hold_mode(complex_adv.card_ab_hold_mode)
    if mode != CardAbHoldMode.PENDING_SETUP:
        return CommonBidEnterResetResult(
            status="skipped_wrong_mode",
            nmid_to_bid={},
            detail=f"mode={mode.value}",
        )

    done_cache = CardAbHoldCommonBidEnterResetRedisCache(complex_adv.adv_setting)
    if await done_cache.is_done():
        return CommonBidEnterResetResult(
            status="already_done",
            nmid_to_bid={},
            detail="enter reset already completed for this hold episode",
        )

    search_adv_id = getattr(complex_adv, "search_adv_id", None)
    if search_adv_id is None:
        await done_cache.mark_done()
        logger.warning(
            "[adv_id=%s] ab_hold ENTER common-bid reset skipped: no search_adv_id",
            complex_adv.adv_id,
        )
        return CommonBidEnterResetResult(
            status="skipped_no_search",
            nmid_to_bid={},
            detail="no search_adv_id",
        )

    nmids = [int(n) for n in list(complex_adv.nmids)]
    min_bids = complex_adv.min_nmids_bids
    if (min_bids is None or not min_bids.search) and wb_shop_data_manager is not None:
        try:
            ok = await wb_shop_data_manager.backfill_min_bids_for_adv(complex_adv)
            if not ok:
                logger.error(
                    "[adv_id=%s] ab_hold ENTER common-bid reset degraded: "
                    "min_bids backfill failed",
                    complex_adv.adv_id,
                )
        except Exception:
            logger.exception(
                "[adv_id=%s] ab_hold ENTER common-bid reset degraded: "
                "min_bids backfill raised",
                complex_adv.adv_id,
            )
        min_bids = complex_adv.min_nmids_bids

    nmid_to_min = resolve_search_min_bids_for_nmids(
        nmids=nmids,
        min_nmids_bids=min_bids,
    )
    if nmid_to_min is None:
        logger.error(
            "[adv_id=%s] ab_hold ENTER common-bid reset degraded: "
            "search_adv_min_bids unavailable for nmids=%s — will retry next tick "
            "(decision §19 / visible degrade, not silent skip of contract)",
            complex_adv.adv_id,
            nmids,
        )
        return CommonBidEnterResetResult(
            status="degraded_missing_min",
            nmid_to_bid={},
            detail="search min bids missing",
        )

    command = build_set_common_bids_to_min_command(complex_adv, nmid_to_min)
    if command is None:
        await done_cache.mark_done()
        return CommonBidEnterResetResult(
            status="skipped_no_items",
            nmid_to_bid={},
            detail="empty nmids",
        )

    try:
        await wb_manager_hub.wb_modifier.update_search_adv_common_cpm(command)
        redis_client = wb_manager_hub.redis_client_wrapper
        await RedisCommonBidValueManager(redis_client).set_bids(
            int(search_adv_id),
            nmid_to_min,
        )
    except Exception as exc:
        logger.exception(
            "[adv_id=%s] ab_hold ENTER common-bid reset WB write failed: %s — "
            "will retry next tick (decision §19)",
            complex_adv.adv_id,
            exc,
        )
        return CommonBidEnterResetResult(
            status="degraded_wb_error",
            nmid_to_bid={},
            detail=str(exc),
        )

    await done_cache.mark_done()
    logger.info(
        "[adv_id=%s] ab_hold ENTER Search common-bid reset-to-min written nmids=%s",
        complex_adv.adv_id,
        sorted(nmid_to_min),
    )
    return CommonBidEnterResetResult(
        status="written",
        nmid_to_bid=dict(nmid_to_min),
        detail="ok",
    )
